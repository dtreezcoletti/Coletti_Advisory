from __future__ import annotations

import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import streamlit as st

from . import owner_console_ui as owner_ui
from .demo_controls import render_demo_experience_switcher
from .models import Permission, Role
from .owner_console_dari import render_owner_dari
from .owner_console_live_ui import render_live_owner_dashboard, render_owner_page_live
from .owner_console_notifications import render_live_owner_topbar
from .owner_console_style import OWNER_REFERENCE_CSS
from .workspaces import live_workspace_gate_errors

# Keep the reference owner presentation layer, but route the owner home,
# approvals, Dispatcher, and notification surfaces through the live control-plane
# adapter. Non-owner experiences and existing evidence/review/publication
# workflows remain untouched.
owner_ui._render_dari = render_owner_dari

# The owner reference console previously exposed the evidence workspace but not the
# secure source-registration surface. Add a dedicated owner navigation entry that
# reuses the existing permission-gated intake pipeline rather than creating a
# separate upload/storage path.
if not any(label == "Record Ingestion" for label, _icon in owner_ui.OWNER_MAIN_NAV):
    _owner_main_nav = list(owner_ui.OWNER_MAIN_NAV)
    _evidence_index = next(
        (index for index, (label, _icon) in enumerate(_owner_main_nav) if label == "Evidence"),
        len(_owner_main_nav),
    )
    _owner_main_nav.insert(_evidence_index, ("Record Ingestion", "⇧"))
    owner_ui.OWNER_MAIN_NAV = tuple(_owner_main_nav)

_owner_sidebar = owner_ui._owner_sidebar
_original_owner_page = owner_ui._render_owner_page

_DRIVE_MAX_BYTES = 200 * 1024 * 1024
_GOOGLE_FILE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


def _google_drive_target(raw_url: str) -> tuple[str, str]:
    """Convert a Google Drive/Docs share link into a controlled download URL."""
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"drive.google.com", "docs.google.com"}:
        raise ValueError("Use an https://drive.google.com or https://docs.google.com file link.")

    parts = [part for part in parsed.path.split("/") if part]
    file_id = None
    kind = None

    if parsed.hostname == "docs.google.com" and len(parts) >= 3 and parts[1] == "d":
        kind = parts[0]
        file_id = parts[2]
    elif parsed.hostname == "drive.google.com":
        if len(parts) >= 3 and parts[0] == "file" and parts[1] == "d":
            file_id = parts[2]
        else:
            file_id = parse_qs(parsed.query).get("id", [None])[0]

    if not file_id or not _GOOGLE_FILE_ID_RE.match(file_id):
        raise ValueError("That link does not contain a supported Google Drive file ID.")

    short_id = file_id[:8]
    if kind == "document":
        return f"https://docs.google.com/document/d/{file_id}/export?format=pdf", f"google-doc-{short_id}.pdf"
    if kind == "spreadsheets":
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx", f"google-sheet-{short_id}.xlsx"
    if kind == "presentation":
        return f"https://docs.google.com/presentation/d/{file_id}/export?format=pptx", f"google-slides-{short_id}.pptx"
    if kind is not None:
        raise ValueError("That Google file type is not supported for direct import yet.")

    return (
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        f"google-drive-{short_id}",
    )


def _download_google_drive_file(raw_url: str) -> tuple[str, bytes]:
    download_url, default_name = _google_drive_target(raw_url)
    request = Request(download_url, headers={"User-Agent": "ColettiOS-Record-Ingestion/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > _DRIVE_MAX_BYTES:
                raise ValueError("Google Drive file exceeds the 200 MB intake limit.")
            data = response.read(_DRIVE_MAX_BYTES + 1)
            if len(data) > _DRIVE_MAX_BYTES:
                raise ValueError("Google Drive file exceeds the 200 MB intake limit.")

            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type.startswith("text/html"):
                raise ValueError(
                    "Google returned an access page instead of the file. Make the test file accessible by link and try again."
                )

            disposition = response.headers.get("Content-Disposition") or ""
            filename_match = re.search(r'filename="?([^";]+)', disposition, flags=re.IGNORECASE)
            filename = filename_match.group(1).strip() if filename_match else default_name
            return filename, data
    except HTTPError as exc:
        raise ValueError(f"Google Drive returned HTTP {exc.code}; verify the file sharing setting.") from exc
    except URLError as exc:
        raise ValueError("ColettiOS could not reach Google Drive from this sandbox runtime.") from exc


def _register_imported_source(shell, *, principal, engagement_id: str, storage, core, filename: str, data: bytes, classification: str) -> str:
    result = shell.app.ingest_file(
        principal=principal,
        engagement_id=engagement_id,
        filename=filename,
        data=data,
        classification=classification,
        storage=storage,
        core=core,
    )
    extraction = shell.legacy.extract_candidate_statements(filename, data)
    source_id = result["source"]["source_id"]
    shell.legacy._processing_queue()[source_id] = {
        "source_id": source_id,
        "filename": filename,
        **extraction.to_dict(),
    }
    st.session_state["_last_intake_result"] = {
        "source_id": source_id,
        "candidate_count": len(extraction.candidates),
        "extraction_method": extraction.extraction_method,
        "warnings": list(extraction.warnings),
    }
    return source_id


def _render_google_drive_import(shell, **kwargs) -> None:
    principal = kwargs["principal"]
    if not principal.can(Permission.UPLOAD):
        return

    st.divider()
    st.subheader("Google Drive Import")
    st.caption(
        "Import a single Drive file into the same controlled source-registration and extraction pipeline. "
        "This slot currently uses share links; private Google account OAuth is not wired into the sandbox runtime yet."
    )

    drive_url = st.text_input(
        "Google Drive file link",
        placeholder="https://drive.google.com/file/d/... or https://docs.google.com/document/d/...",
        key="owner_google_drive_import_url",
    )
    filename_override = st.text_input(
        "Imported filename (optional)",
        placeholder="Leave blank to use the Drive/export filename",
        key="owner_google_drive_filename_override",
    )
    classification = st.selectbox(
        "Google Drive source classification",
        list(shell.legacy.DEFAULT_COMMERCIAL_CONFIG.source_classifications),
        key="owner_google_drive_classification",
    )

    synthetic_ok = True
    if kwargs["app_mode"] == "demo":
        st.warning("Sandbox rule: import synthetic/non-sensitive test records only.")
        synthetic_ok = st.checkbox(
            "I confirm this Google Drive file is synthetic/non-sensitive test material.",
            key="owner_google_drive_synthetic_ack",
        )

    if st.button(
        "Import from Google Drive",
        type="primary",
        use_container_width=True,
        disabled=not drive_url.strip() or not synthetic_ok,
        key="owner_google_drive_import_button",
    ):
        try:
            with st.spinner("Importing Google Drive record…"):
                detected_name, data = _download_google_drive_file(drive_url)
                filename = filename_override.strip() or detected_name
                source_id = _register_imported_source(
                    shell,
                    principal=principal,
                    engagement_id=kwargs["engagement_id"],
                    storage=kwargs["storage"],
                    core=kwargs["core"],
                    filename=filename,
                    data=data,
                    classification=classification,
                )
            st.success(f"Google Drive import registered · {source_id}")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Google Drive import failed before registration. No source was created.")


def _render_owner_page(shell, page: str, **kwargs) -> None:
    if page == "Record Ingestion":
        shell.legacy._render_secure_intake(
            app_mode=kwargs["app_mode"],
            principal=kwargs["principal"],
            engagement_id=kwargs["engagement_id"],
            storage=kwargs["storage"],
            core=kwargs["core"],
        )
        _render_google_drive_import(shell, **kwargs)
        return None
    if page == "My Workspace":
        return render_live_owner_dashboard(
            shell,
            kwargs["principal"],
            kwargs["engagement_id"],
            kwargs["manifest"],
            kwargs["records"],
            kwargs["reports"],
            kwargs["core"],
        )
    return render_owner_page_live(_original_owner_page, shell, page, **kwargs)


def run_reference_workspace(shell) -> None:
    st.set_page_config(
        page_title="ColettiOS | Owner Console",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    shell._apply_brand_theme()
    st.markdown(OWNER_REFERENCE_CSS, unsafe_allow_html=True)

    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = shell.app._runtime()
    shell._sidebar_brand()
    shell._sidebar_identity(principal, principal.engagement_ids[0])
    principal = render_demo_experience_switcher(
        shell,
        app_mode=app_mode,
        principal=principal,
        core=core,
    )
    engagement_id = shell._select_engagement(principal)

    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if gate_errors:
        st.error("Coletti & Co. Live is configured but locked until the production gate is open.")
        for error in gate_errors:
            st.write(f"• {error}")
        st.stop()

    experience = shell._experience(principal)
    manifest = core.manifest(engagement_id)
    internal_user = experience in {"employee", "owner"}
    reports = shell.app.build_report_bundle(manifest) if internal_user else {}
    records = shell.app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = shell.app.sync_drafts(records, reports)
        shell.app._save_publication_records(publication_store, principal, engagement_id, records)

    if experience == "owner":
        page = _owner_sidebar(shell, principal, engagement_id)
        if principal.authenticated:
            st.sidebar.divider()
            if st.sidebar.button("Log out", use_container_width=True, key="owner_logout"):
                st.logout()
        render_live_owner_topbar(
            principal,
            manifest,
            tuple(principal.engagement_ids),
            core=core,
            engagement_id=engagement_id,
        )
        _render_owner_page(
            shell,
            page,
            principal=principal,
            engagement_id=engagement_id,
            manifest=manifest,
            records=records,
            reports=reports,
            core=core,
            storage=storage,
            publication_store=publication_store,
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
        )
        return

    pages = shell._visible_pages(principal)
    nav_key = f"_coletti_navigation:{principal.user_id}:{experience}"
    requested_page = st.session_state.pop(
        f"_coletti_profile_requested_page:{principal.user_id}",
        None,
    )
    if requested_page in pages:
        st.session_state[nav_key] = requested_page
    elif st.session_state.get(nav_key) not in pages:
        st.session_state[nav_key] = pages[0]

    page = st.sidebar.radio(
        "Navigation",
        pages,
        format_func=lambda value: f"{shell._PAGE_ICONS.get(value, '•')}   {value}",
        label_visibility="collapsed",
        key=nav_key,
    )
    if principal.authenticated:
        st.sidebar.divider()
        if st.sidebar.button("Log out", use_container_width=True, key="non_owner_logout"):
            st.logout()

    shell._topbar(principal, experience)

    if page == "Dashboard":
        if experience == "client":
            shell._client_dashboard(principal, engagement_id, manifest, records)
        else:
            shell._employee_dashboard(principal, engagement_id, manifest, records, reports)
    elif page == "My Case":
        shell._render_client_case(engagement_id, manifest, records)
    elif page == "Upload Documents":
        shell.legacy._render_secure_intake(app_mode=app_mode, principal=principal, engagement_id=engagement_id, storage=storage, core=core)
    elif page == "Requests & To-Do":
        shell._render_client_requests()
    elif page == "Progress":
        st.title("Progress")
        shell._progress_panel(records, manifest)
        st.caption("Progress is deliberately client-safe and does not expose internal review notes or draft conclusions.")
    elif page == "Messages":
        shell._render_client_messages()
    elif page == "My Account":
        shell._render_account(principal, engagement_id)
    elif page == "Help & Support":
        shell._render_help()
    elif page == "Engagements":
        shell._render_engagements(principal)
    elif page == "Secure Intake":
        shell.legacy._render_secure_intake(app_mode=app_mode, principal=principal, engagement_id=engagement_id, storage=storage, core=core)
    elif page == "Evidence":
        shell.legacy._render_evidence_workspace(principal=principal, engagement_id=engagement_id, core=core, manifest=manifest)
    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        shell.app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)
    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        shell.app._render_analysis(manifest)
    elif page == "Reports":
        if internal_user:
            shell.app._render_internal_reports(manifest, reports, records)
        else:
            shell.app._render_client_reports(records)
    elif page == "System Lab":
        if principal.role != Role.OWNER:
            st.error("System Lab is owner-only.")
            st.stop()
        shell.render_system_lab(principal=principal, manifest=manifest, app_mode=app_mode, storage_backend=storage_backend, core_backend=core_backend, engagement_id=engagement_id)
    elif page == "Administration":
        shell._render_administration(app_mode, storage_backend, core_backend, manifest, principal)
