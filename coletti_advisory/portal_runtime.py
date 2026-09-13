from __future__ import annotations

import streamlit as st

from . import client_operations
from . import owner_console_runtime as owner_runtime
from . import portal_case_lifecycle as lifecycle
from .demo_controls import render_demo_experience_switcher
from .models import Permission, Role
from .owner_console_notifications import render_live_owner_topbar
from .owner_console_style import OWNER_REFERENCE_CSS
from .workspaces import live_workspace_gate_errors


CLIENT_PAGES = (
    "Dashboard",
    "My Case",
    "Upload Documents",
    "Requests & To-Do",
    "Progress",
    "Reports",
    "Messages",
    "My Account",
    "Help & Support",
)

ADMIN_PAGES = (
    "Dashboard",
    "Clients",
    "Cases",
    "Secure Intake",
    "Records",
    "Review Center",
    "Analysis",
    "Reports",
    "Requests & To-Do",
    "Messages",
    "Administration",
)


def _employee_pages(principal) -> tuple[str, ...]:
    pages = ["Dashboard", "Cases"]
    if principal.can(Permission.UPLOAD):
        pages.append("Secure Intake")
    pages.append("Records")
    if principal.can(Permission.REVIEW):
        pages.append("Review Center")
    if principal.can(Permission.ANALYZE):
        pages.append("Analysis")
    pages.extend(("Reports", "Requests & To-Do", "Messages"))
    return tuple(pages)


def _experience(principal) -> str:
    if principal.role == Role.OWNER:
        return "owner"
    if principal.role == Role.ADMIN:
        return "admin"
    if principal.role in {Role.CLIENT, Role.READ_ONLY}:
        return "client"
    return "employee"


def _pages(principal, experience: str) -> tuple[str, ...]:
    if experience == "client":
        return CLIENT_PAGES
    if experience == "admin":
        return ADMIN_PAGES
    return _employee_pages(principal)


def _topbar(shell, principal, experience: str) -> None:
    labels = {
        "client": "Client Portal",
        "employee": "Team Workspace",
        "admin": "Admin Console",
    }
    title = labels.get(experience, "Coletti & Co.")
    role = principal.role.value.replace("_", " ").title()
    st.markdown(
        f"<div class='cc-topline'><div><div class='cc-kicker'>{shell._esc(title)}</div>"
        f"<div class='cc-topline-title'>{shell._esc(title)}</div></div>"
        f"<div class='cc-pill'>{shell._esc(principal.display_name)} &nbsp;·&nbsp; {shell._esc(role)}</div></div>",
        unsafe_allow_html=True,
    )


def _select_page(shell, principal, experience: str) -> str:
    pages = _pages(principal, experience)
    key = f"_integrated_portal_navigation:{principal.user_id}:{experience}"
    requested = st.session_state.pop("_portal_requested_page", None)
    profile_requested = st.session_state.pop(f"_coletti_profile_requested_page:{principal.user_id}", None)
    candidate = requested or profile_requested
    if candidate in pages:
        st.session_state[key] = candidate
    elif st.session_state.get(key) not in pages:
        st.session_state[key] = pages[0]
    return st.sidebar.radio(
        "Navigation",
        pages,
        format_func=lambda value: f"{shell._PAGE_ICONS.get(value, '•')}   {value}",
        label_visibility="collapsed",
        key=key,
    )


def _render_common_page(
    shell,
    page: str,
    *,
    principal,
    engagement_id: str,
    manifest: dict,
    records: dict,
    reports: dict,
    storage,
    core,
    publication_store,
    app_mode: str,
    storage_backend: str,
    core_backend: str,
    experience: str,
) -> None:
    internal_user = experience in {"employee", "admin"}

    if page == "Dashboard":
        if experience == "client":
            return lifecycle.render_client_dashboard(shell, principal, engagement_id, manifest, records)
        if experience == "admin":
            return lifecycle.render_admin_dashboard(shell, principal, engagement_id, manifest, records, reports)
        return lifecycle.render_employee_dashboard(shell, principal, engagement_id, manifest, records, reports)

    if page in {"My Case", "Progress", "Cases"}:
        controls = experience in {"employee", "admin"}
        title = "Your Case Progress" if experience == "client" else ("Admin Case Control" if experience == "admin" else "Assigned Case")
        return lifecycle.render_lifecycle(principal, engagement_id, controls=controls, title=title)

    if page == "Clients":
        if principal.role != Role.ADMIN:
            st.error("Client administration is restricted to Admin/Owner authority.")
            return
        return client_operations.render_clients_operating_surface(
            shell,
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

    if page in {"Upload Documents", "Secure Intake"}:
        lifecycle.page_heading(
            "Records · Secure Intake",
            "Secure Record Intake",
            "Device uploads, ZIP packages, Google Drive files, and email records enter the same Case-scoped provenance pipeline.",
        )
        return shell.legacy._render_secure_intake(
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )

    if page == "Records":
        lifecycle.page_heading("Records · Provenance", "Case Records", "Case-scoped records and source lineage remain tied to the canonical Case identity.")
        return shell.legacy._render_evidence_workspace(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
            manifest=manifest,
        )

    if page == "Requests & To-Do":
        return lifecycle.render_requests(principal, engagement_id, allow_create=experience in {"employee", "admin"})

    if page == "Messages":
        return lifecycle.render_messages(principal, engagement_id, allow_internal=experience in {"employee", "admin"})

    if page == "Review Center":
        lifecycle.page_heading("Human Review", "Review Center", "Human review remains a required checkpoint before report publication or professional handoff.")
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            return
        return shell.app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)

    if page == "Analysis":
        lifecycle.page_heading("Reconstruction · Analysis", "Analysis", "Analysis may organize and reconcile the condition of records; it does not determine protected professional effect.")
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            return
        return shell.app._render_analysis(manifest)

    if page == "Reports":
        lifecycle.page_heading("Reports · Controlled Publication", "Reports", "Draft, review, approval, publication, and Client delivery remain distinct states.")
        if internal_user:
            return shell.app._render_internal_reports(manifest, reports, records)
        return shell.app._render_client_reports(records)

    if page == "My Account":
        lifecycle.page_heading("Client Portal · Identity", "My Account", "Identity and access are separate from Client and Case authorization.")
        return shell._render_account(principal, engagement_id)

    if page == "Help & Support":
        lifecycle.page_heading("Client Portal · Support", "Help & Support", "Support does not change Case state or bypass controlled workflow gates.")
        return shell._render_help()

    if page == "Administration":
        lifecycle.page_heading("Administration · Security", "Administration & Security", "Role, access, and system controls remain permission-scoped and audited.")
        return shell._render_administration(app_mode, storage_backend, core_backend, manifest, principal)

    st.warning(f"The {page} surface is not yet connected in this runtime.")


def run_integrated_portal_workspace(shell) -> None:
    st.set_page_config(
        page_title="Coletti & Co. | Controlled Workspace",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    shell._apply_brand_theme()
    st.markdown(OWNER_REFERENCE_CSS, unsafe_allow_html=True)

    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = shell.app._runtime()
    shell._sidebar_brand()
    principal = render_demo_experience_switcher(shell, app_mode=app_mode, principal=principal, core=core)

    if not principal.engagement_ids:
        lifecycle.page_heading("Secure Access", "No Case workspace is assigned", "Your authenticated identity is valid, but no Case authorization is currently active.")
        st.info("Client intake and pre-Case onboarding remain available through the Secure Client Gateway. Case data is not fabricated without an authorized Case.")
        return

    shell._sidebar_identity(principal, principal.engagement_ids[0])
    engagement_id = shell._select_engagement(principal)
    st.session_state["_portal_active_case_id"] = engagement_id

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

    experience = _experience(principal)
    manifest = core.manifest(engagement_id)
    internal_user = experience in {"employee", "admin", "owner"}
    reports = shell.app.build_report_bundle(manifest) if internal_user else {}
    records = shell.app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = shell.app.sync_drafts(records, reports)
        shell.app._save_publication_records(publication_store, principal, engagement_id, records)

    if experience == "owner":
        page = owner_runtime._owner_sidebar(shell, principal, engagement_id)
        if principal.authenticated:
            st.sidebar.divider()
            if st.sidebar.button("Log out", use_container_width=True, key="owner_logout_integrated"):
                st.logout()
        render_live_owner_topbar(principal, manifest, tuple(principal.engagement_ids), core=core, engagement_id=engagement_id)
        if page == "Cases":
            lifecycle.render_lifecycle(principal, engagement_id, controls=True, title="Owner Case Lifecycle")
            st.divider()
        return owner_runtime._render_owner_page(
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

    page = _select_page(shell, principal, experience)
    if principal.authenticated:
        st.sidebar.divider()
        if st.sidebar.button("Log out", use_container_width=True, key=f"{experience}_logout_integrated"):
            st.logout()
    _topbar(shell, principal, experience)
    return _render_common_page(
        shell,
        page,
        principal=principal,
        engagement_id=engagement_id,
        manifest=manifest,
        records=records,
        reports=reports,
        storage=storage,
        core=core,
        publication_store=publication_store,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        experience=experience,
    )
