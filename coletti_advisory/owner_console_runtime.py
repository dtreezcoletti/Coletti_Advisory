from __future__ import annotations

import streamlit as st

from . import owner_console_ui as owner_ui
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
_owner_sidebar = owner_ui._owner_sidebar
_original_owner_page = owner_ui._render_owner_page


def _render_owner_page(shell, page: str, **kwargs) -> None:
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
    page = st.sidebar.radio(
        "Navigation",
        pages,
        format_func=lambda value: f"{shell._PAGE_ICONS.get(value, '•')}   {value}",
        label_visibility="collapsed",
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
