from __future__ import annotations

import streamlit as st

from . import main as app
from .models import Permission
from .system_lab import render_system_lab
from .workspaces import live_workspace_gate_errors, workspace_environment, workspace_label


def _workspace_pages(principal) -> list[str]:
    pages = app._workspace_pages(principal)
    if principal.can(Permission.MANAGE_USERS) and "System Lab" not in pages:
        try:
            admin_index = pages.index("Administration")
        except ValueError:
            admin_index = len(pages)
        pages.insert(admin_index, "System Lab")
    return pages


def _identity_panel(principal) -> str:
    if principal.authenticated:
        st.sidebar.success(f"Authenticated as: {principal.display_name}")
        st.sidebar.caption(f"Role: {principal.role.value.replace('_', ' ').title()}")
    else:
        st.sidebar.info("Synthetic demo session — no client identity or client data")

    options = list(principal.engagement_ids)
    selected = st.sidebar.selectbox(
        "Authorized workspace",
        options,
        format_func=workspace_label,
    )
    if not principal.can_access(selected):
        st.error("Workspace authorization failed.")
        st.stop()

    environment = workspace_environment(selected)
    if environment == "LIVE":
        st.sidebar.warning("LIVE workspace · real operational data")
    elif environment == "DEMO":
        st.sidebar.caption("DEMO workspace · synthetic data only")
    else:
        st.sidebar.caption("Authorized engagement workspace")

    if principal.authenticated and st.sidebar.button("Log out"):
        st.logout()
    return selected


def _intake_upload_key(generation: int) -> str:
    return f"secure-intake-upload-{generation}"


def _render_secure_intake(*, app_mode, principal, engagement_id, storage, core) -> None:
    if not principal.can(Permission.UPLOAD):
        st.error("Your role does not permit source uploads.")
        st.stop()

    st.title("Secure Intake")
    if app_mode == "demo":
        st.info(
            "Demo uploads are AES-256-GCM encrypted on ephemeral local storage and may disappear on restart. "
            "Use synthetic files only."
        )
        st.warning(
            "Android/Chrome currently has a confirmed Streamlit file-picker timeout bug. For this synthetic test, "
            "choose the file promptly after opening the picker. If the tile turns red, use Reset upload control. "
            "System Lab → Clean Room can test the server-side intake path without the mobile picker."
        )

    classification = st.selectbox(
        "Document classification",
        ["Operational Audit", "Business Record", "Financial Record", "Correspondence", "Other"],
    )

    generation = int(st.session_state.get("_intake_upload_generation", 0))
    upload_key = _intake_upload_key(generation)
    uploaded = st.file_uploader(
        "Upload a source record",
        key=upload_key,
        max_upload_size=200,
        help=(
            "If a mobile upload shows a red ! or stalls after returning from the Android file picker, "
            "tap Reset upload control and choose the file again."
        ),
    )

    reset_col, status_col = st.columns([1, 2])
    if reset_col.button("Reset upload control", key=f"reset-{upload_key}"):
        st.session_state["_intake_upload_generation"] = generation + 1
        st.rerun()

    if uploaded is None:
        status_col.caption(
            "Mobile recovery: if the file tile turns red, reset the upload control rather than refreshing the whole app."
        )
    else:
        status_col.success(f"Ready to register: {uploaded.name} · {uploaded.size / 1024:.1f} KB")

    if st.button("Register source", type="primary", disabled=uploaded is None):
        result = app.ingest_file(
            principal=principal,
            engagement_id=engagement_id,
            filename=uploaded.name,
            data=uploaded.getvalue(),
            classification=classification,
            storage=storage,
            core=core,
        )
        st.success("Source intake completed")
        st.write("✓ Engagement authorization verified")
        st.write("✓ File encrypted before storage")
        st.write("✓ SHA-256 content hash generated")
        st.write(f"✓ Source {result['source']['source_id']} registered")
        st.write("✓ Audit actor recorded")
        st.session_state["_intake_upload_generation"] = generation + 1
        st.rerun()


def run() -> None:
    st.set_page_config(page_title="Coletti & Co. | ColettiOS", page_icon="◈", layout="wide")
    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = app._runtime()

    engagement_id = _identity_panel(principal)
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

    page = st.sidebar.radio("Workspace", _workspace_pages(principal))
    manifest = core.manifest(engagement_id)

    internal_user = principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)
    reports = app.build_report_bundle(manifest) if internal_user else {}
    records = app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = app.sync_drafts(records, reports)
        app._save_publication_records(publication_store, principal, engagement_id, records)

    if page == "Command Center":
        st.title("Coletti & Co.")
        st.caption("Commercial interface powered by ColettiOS contracts")
        environment = workspace_environment(engagement_id)
        if environment == "DEMO":
            st.warning("SYNTHETIC DEMO ONLY — do not upload real client, legal, medical, financial, or identifying records.")
        elif environment == "LIVE":
            st.success("LIVE WORKSPACE — authenticated production Core and durable encrypted storage are active.")
        if internal_user:
            app._render_internal_command_center(manifest, reports, records)
        else:
            app._render_client_command_center(manifest, records)

    elif page == "Engagements":
        st.title("Engagements")
        rows = [
            {
                "Workspace": workspace_label(eid),
                "Environment": workspace_environment(eid),
                "ID": eid,
                "Status": "ACTIVE",
            }
            for eid in principal.engagement_ids
        ]
        st.dataframe(rows, use_container_width=True)

    elif page == "Intake":
        _render_secure_intake(
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )

    elif page == "Evidence":
        if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)):
            st.error("Your role does not permit access to the internal evidence workspace.")
            st.stop()
        st.title("Evidence Workspace")
        st.subheader("Sources")
        st.dataframe(list(manifest.get("sources", {}).values()), use_container_width=True)
        st.subheader("Propositions")
        st.dataframe(list(manifest.get("propositions", {}).values()), use_container_width=True)
        st.subheader("Contradictions")
        st.dataframe(list(manifest.get("contradictions", {}).values()), use_container_width=True)

    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)

    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        app._render_analysis(manifest)

    elif page == "Reports":
        if internal_user:
            app._render_internal_reports(manifest, reports, records)
        else:
            app._render_client_reports(records)

    elif page == "System Lab":
        render_system_lab(
            principal=principal,
            manifest=manifest,
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
            engagement_id=engagement_id,
        )

    elif page == "Administration":
        st.title("Administration & Security")
        if not principal.can(Permission.MANAGE_USERS):
            st.error("Your role does not permit administration.")
            st.stop()
        st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
        st.subheader("Authentication & Security Release Gate")
        for label, implemented in app.SECURITY_CONTROLS:
            st.write(f"{'✅' if implemented else '🔨'} {label}")
        st.subheader("Audit log")
        st.dataframe(manifest.get("audit_log", []), use_container_width=True)
