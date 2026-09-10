from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .analysis import build_analytical_issues
from .commercial_config import DEFAULT_COMMERCIAL_CONFIG
from .connection_architecture import page_for, role_has_capability
from .document_processing import extract_candidate_statements
from .models import Permission, Role
from .publication import PublicationStatus
from .universal_ingestion import (
    ArchiveItem,
    IngestionSafetyError,
    download_google_drive_file,
    inspect_zip,
)


def _page_key(principal) -> str:
    return f"_owner_reference_page:{principal.user_id}"


def _drill_context_key(principal) -> str:
    return f"_drill_through_context:{principal.user_id}"


def _goto(principal, page: str, *, object_type: str | None = None, filters: Mapping[str, Any] | None = None) -> None:
    if object_type:
        st.session_state[_drill_context_key(principal)] = {
            "object_type": object_type,
            "page": page,
            "filters": dict(filters or {}),
        }
    st.session_state[_page_key(principal)] = page
    st.rerun()


def _queue_extraction(legacy, source_id: str, filename: str, data: bytes) -> dict[str, Any]:
    extraction = extract_candidate_statements(filename, data)
    legacy._processing_queue()[source_id] = {
        "source_id": source_id,
        "filename": filename,
        **extraction.to_dict(),
    }
    return {
        "source_id": source_id,
        "candidate_count": len(extraction.candidates),
        "extraction_method": extraction.extraction_method,
        "warnings": list(extraction.warnings),
    }


def _register_file(
    legacy,
    *,
    principal,
    engagement_id: str,
    storage,
    core,
    filename: str,
    data: bytes,
    classification: str,
    metadata: Mapping[str, Any] | None = None,
    queue_extraction: bool = True,
) -> tuple[str, dict[str, Any] | None]:
    result = legacy.app.ingest_file(
        principal=principal,
        engagement_id=engagement_id,
        filename=filename,
        data=data,
        classification=classification,
        storage=storage,
        core=core,
        metadata=metadata,
    )
    source_id = result["source"]["source_id"]
    extraction = _queue_extraction(legacy, source_id, filename, data) if queue_extraction else None
    return source_id, extraction


def _register_archive_item(
    legacy,
    *,
    principal,
    engagement_id: str,
    storage,
    core,
    item: ArchiveItem,
    classification: str,
    parent_source_id: str,
    depth: int,
) -> list[str]:
    is_nested_archive = item.filename.lower().endswith(".zip")
    source_id, _ = _register_file(
        legacy,
        principal=principal,
        engagement_id=engagement_id,
        storage=storage,
        core=core,
        filename=item.filename,
        data=item.data,
        classification=classification,
        metadata={
            "ingestion_method": "zip_archive",
            "parent_source_id": parent_source_id,
            "archive_path": item.path,
            "archive_depth": depth,
            "archive_container": is_nested_archive,
        },
        queue_extraction=not is_nested_archive,
    )
    registered = [source_id]
    for child in item.nested:
        registered.extend(
            _register_archive_item(
                legacy,
                principal=principal,
                engagement_id=engagement_id,
                storage=storage,
                core=core,
                item=child,
                classification=classification,
                parent_source_id=source_id,
                depth=depth + 1,
            )
        )
    return registered


def _ingest_payload(
    legacy,
    *,
    principal,
    engagement_id: str,
    storage,
    core,
    filename: str,
    data: bytes,
    classification: str,
    ingestion_method: str,
) -> dict[str, Any]:
    if filename.lower().endswith(".zip"):
        inspection = inspect_zip(data)
        parent_id, _ = _register_file(
            legacy,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
            filename=filename,
            data=data,
            classification=classification,
            metadata={
                "ingestion_method": ingestion_method,
                "archive_container": True,
                "archive_member_count": inspection.file_count,
                "archive_uncompressed_bytes": inspection.total_uncompressed_bytes,
            },
            queue_extraction=False,
        )
        child_ids: list[str] = []
        for item in inspection.items:
            child_ids.extend(
                _register_archive_item(
                    legacy,
                    principal=principal,
                    engagement_id=engagement_id,
                    storage=storage,
                    core=core,
                    item=item,
                    classification=classification,
                    parent_source_id=parent_id,
                    depth=1,
                )
            )
        return {
            "source_id": parent_id,
            "archive": True,
            "child_source_ids": child_ids,
            "candidate_count": sum(
                len((legacy._processing_queue().get(source_id) or {}).get("candidates") or [])
                for source_id in child_ids
            ),
            "extraction_method": "ZIP_SAFE_EXTRACTION",
            "warnings": [],
        }

    source_id, extraction = _register_file(
        legacy,
        principal=principal,
        engagement_id=engagement_id,
        storage=storage,
        core=core,
        filename=filename,
        data=data,
        classification=classification,
        metadata={"ingestion_method": ingestion_method},
        queue_extraction=True,
    )
    return extraction or {
        "source_id": source_id,
        "candidate_count": 0,
        "extraction_method": "NONE",
        "warnings": [],
    }


def _render_universal_secure_intake(legacy, *, app_mode, principal, engagement_id, storage, core) -> None:
    if not principal.can(Permission.UPLOAD):
        st.error("Your role does not permit source uploads.")
        st.stop()

    st.title("Secure Intake")
    st.caption("One controlled ingestion gateway for device uploads, ZIP packages, and Google Drive. Every accepted item enters the same case-scoped source and provenance pipeline.")
    if app_mode == "demo":
        st.warning("Synthetic demo only · upload/import non-sensitive test records.")

    last_intake = st.session_state.pop("_last_intake_result", None)
    if last_intake:
        st.success(f"Source intake completed · {last_intake['source_id']}")
        if last_intake.get("archive"):
            st.caption(
                f"ZIP package preserved as the parent source · {len(last_intake.get('child_source_ids') or [])} extracted child source(s) registered with archive lineage."
            )
        else:
            st.caption(
                f"Extraction: {last_intake.get('candidate_count', 0)} candidate statement(s) queued for human review · method: {last_intake.get('extraction_method', 'unknown')}"
            )
        for warning in last_intake.get("warnings", []):
            st.warning(warning)

    classification = st.selectbox(
        "Source classification",
        list(DEFAULT_COMMERCIAL_CONFIG.source_classifications),
        key=f"universal-intake-classification:{principal.user_id}:{engagement_id}",
    )

    device_tab, drive_tab = st.tabs(("From this device / ZIP", "Google Drive"))
    with device_tab:
        st.caption("Upload individual records or a ZIP package. ZIP contents are safely inspected, extracted, registered as child sources, and linked back to the original archive.")
        generation_key = f"_universal_intake_generation:{principal.user_id}:{engagement_id}"
        generation = int(st.session_state.get(generation_key, 0))
        uploaded = st.file_uploader(
            "Upload record or ZIP package",
            key=f"universal-upload:{principal.user_id}:{engagement_id}:{generation}",
            max_upload_size=200,
        )
        if st.button("Register upload", type="primary", disabled=uploaded is None, key=f"universal-register:{principal.user_id}:{engagement_id}:{generation}"):
            try:
                result = _ingest_payload(
                    legacy,
                    principal=principal,
                    engagement_id=engagement_id,
                    storage=storage,
                    core=core,
                    filename=uploaded.name,
                    data=uploaded.getvalue(),
                    classification=classification,
                    ingestion_method="device_upload",
                )
                st.session_state["_last_intake_result"] = result
                st.session_state[generation_key] = generation + 1
                st.rerun()
            except IngestionSafetyError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Upload failed before the source package was fully registered. No silent success was recorded.")

    with drive_tab:
        if not role_has_capability(principal.role, "google_drive_import"):
            st.info("Google Drive import is not available to this role.")
        else:
            st.caption("Google Drive is available in every upload-capable profile. This build supports controlled share-link import now; private OAuth browsing activates only after Google authorization is connected.")
            drive_url = st.text_input(
                "Google Drive file link",
                placeholder="https://drive.google.com/file/d/... or https://docs.google.com/document/d/...",
                key=f"universal-drive-url:{principal.user_id}:{engagement_id}",
            )
            synthetic_ok = True
            if app_mode == "demo":
                synthetic_ok = st.checkbox(
                    "I confirm this Drive file is synthetic/non-sensitive test material.",
                    key=f"universal-drive-demo-ack:{principal.user_id}:{engagement_id}",
                )
            if st.button(
                "Import from Google Drive",
                type="primary",
                disabled=not drive_url.strip() or not synthetic_ok,
                key=f"universal-drive-import:{principal.user_id}:{engagement_id}",
            ):
                try:
                    with st.spinner("Importing through the controlled ingestion gateway…"):
                        filename, data = download_google_drive_file(drive_url)
                        result = _ingest_payload(
                            legacy,
                            principal=principal,
                            engagement_id=engagement_id,
                            storage=storage,
                            core=core,
                            filename=filename,
                            data=data,
                            classification=classification,
                            ingestion_method="google_drive_share_link",
                        )
                    st.session_state["_last_intake_result"] = result
                    st.rerun()
                except (IngestionSafetyError, ValueError) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Google Drive import failed before registration. No source was silently created as successful.")


def _morning_target(title: str) -> tuple[str, str]:
    return {
        "Since Yesterday": ("implementation", "Implementation"),
        "Due Today": ("due_today", "Dispatcher"),
        "Decisions": ("decision", "Decisions"),
        "Carryover": ("carryover", "Dispatcher"),
        "Blockers": ("blocker", "Fix Center"),
        "Capacity": ("capacity", "Capacity"),
        "Success Definition": ("due_today", "Dispatcher"),
    }[title]


def _connected_morning_renderer(structure_patch, owner_ui, principal, cards: list[tuple[str, str]], *, start_page: bool) -> None:
    if tuple(title for title, _body in cards) != structure_patch.MORNING_CARD_TITLES:
        raise RuntimeError("Owner morning brief structure drifted from the approved seven-card contract")

    st.markdown(
        f"<section class='oc-day'><div class='oc-kicker'>{'Start My Day' if start_page else 'My Workspace'}</div>"
        f"<h1>{owner_ui._esc(owner_ui._greeting())}, {owner_ui._esc(owner_ui._first_name(principal))}.</h1>"
        "<div style='font-family:var(--oc-serif);font-size:1.08rem'>What needs me today.</div></section>",
        unsafe_allow_html=True,
    )
    columns = st.columns(4)
    for idx, (title, body) in enumerate(cards):
        object_type, page = _morning_target(title)
        with columns[idx % 4]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(body)
                if st.button("Open →", key=f"drill-morning:{title}", use_container_width=True):
                    _goto(principal, page, object_type=object_type, filters={"source": "morning_card", "title": title})

    if start_page:
        if st.button("Acknowledge & enter My Workspace →", type="primary", use_container_width=True, key="ack_start_my_day_connected"):
            st.session_state[owner_ui._start_my_day_key(principal)] = True
            st.session_state[_page_key(principal)] = "My Workspace"
            st.rerun()


def _connected_live_kpis(owner_live_ui, principal, snapshot: Mapping[str, Any], manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    counts = snapshot.get("counts") or {}
    review_tasks = sum(
        1 for task in snapshot.get("tasks") or []
        if str(task.get("lifecycle_state") or "").upper() in {"REVIEW", "AWAITING HUMAN DECISION", "READY FOR APPROVAL"}
    )
    local_reviews = len(build_analytical_issues(dict(manifest)))
    active_cases = int((snapshot.get("case_counts") or {}).get("active_cases") or 0) or len(principal.engagement_ids)
    report_signoffs = sum(
        1 for record in records.values()
        if getattr(record, "status", None) in {PublicationStatus.IN_REVIEW, PublicationStatus.APPROVED}
    )
    items = (
        ("My Approvals", str(counts.get("approvals", 0)), "decision", "Decisions"),
        ("Pending Reviews", str(review_tasks + local_reviews), "decision", "Decisions"),
        ("Active Cases", str(active_cases), "case", "Cases"),
        ("Reports Awaiting Sign-off", str(report_signoffs), "report", "Reports"),
    )
    cols = st.columns(4)
    for idx, (label, value, object_type, page) in enumerate(items):
        with cols[idx]:
            with st.container(border=True):
                st.metric(label, value)
                if st.button("Open →", key=f"drill-kpi:{label}", use_container_width=True):
                    _goto(principal, page, object_type=object_type, filters={"source": "owner_kpi", "label": label})


def _connected_dari_renderer(owner_live_ui, original, core, principal, engagement_id: str, snapshot: Mapping[str, Any]) -> None:
    original(core, principal, engagement_id, snapshot)
    answer = st.session_state.get("_owner_dari_live_answer")
    if not answer:
        return
    text = str(answer).lower()
    if "decision" in text or "approval" in text:
        object_type, page, label = "decision", "Decisions", "Open decisions"
    elif "blocker" in text or "problem" in text or "conflict" in text:
        object_type, page, label = "blocker", "Fix Center", "Open related problems"
    elif "due today" in text or "overdue" in text or "start with" in text or "dispatcher" in text:
        object_type, page, label = "due_today", "Dispatcher", "Open Dispatcher work"
    elif "change" in text or "implementation" in text:
        object_type, page, label = "implementation", "Implementation", "Open implementation record"
    else:
        object_type, page, label = "case", "Cases", "Open related workspace"
    if st.button(label, key="dari-drill-through", use_container_width=True):
        _goto(principal, page, object_type=object_type, filters={"source": "dari_result"})


def patch_interface_connections(experience_shell, owner_console_runtime, owner_structure_patch, owner_live_ui, owner_ui) -> None:
    """Install one connection layer over the existing role-specific presentation surfaces.

    This is intentionally narrow: source ingestion, dashboard drill-through, KPI
    drill-through, and DARI drill-through all resolve through canonical records/
    destinations rather than creating new duplicate operating state.
    """
    if getattr(experience_shell, "_connection_architecture_patched", False):
        return

    legacy = experience_shell.legacy

    def secure_intake(*, app_mode, principal, engagement_id, storage, core):
        return _render_universal_secure_intake(
            legacy,
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )

    legacy._render_secure_intake = secure_intake
    # Owner Record Ingestion already calls the shared secure-intake renderer. Remove
    # its old owner-only Drive appendage so all roles use the same universal gateway.
    owner_console_runtime._render_google_drive_import = lambda shell, **kwargs: None

    owner_structure_patch._render_morning = lambda owner_ui_module, principal, cards, start_page: _connected_morning_renderer(
        owner_structure_patch,
        owner_ui_module,
        principal,
        cards,
        start_page=start_page,
    )

    owner_live_ui._render_live_kpis = lambda principal, snapshot, manifest, records: _connected_live_kpis(
        owner_live_ui,
        principal,
        snapshot,
        manifest,
        records,
    )

    original_dari = owner_live_ui._render_dari_live
    owner_live_ui._render_dari_live = lambda core, principal, engagement_id, snapshot: _connected_dari_renderer(
        owner_live_ui,
        original_dari,
        core,
        principal,
        engagement_id,
        snapshot,
    )

    experience_shell._connection_architecture_patched = True
