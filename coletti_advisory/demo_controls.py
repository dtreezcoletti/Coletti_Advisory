from __future__ import annotations

from dataclasses import replace

from .core_adapter import SyntheticCoreAdapter
from .models import Principal, Role
from .workspaces import workspace_environment


DEMO_EXPERIENCES: tuple[tuple[str, Role, str], ...] = (
    ("Owner Console", Role.OWNER, "Your full owner experience"),
    ("Admin Workspace", Role.ADMIN, "Team workspace plus administration permissions"),
    ("Employee Workspace", Role.ANALYST, "Standard internal analyst/reviewer workflow"),
    ("Client Portal", Role.CLIENT, "Client-safe portal with internal analysis hidden"),
)


def demo_data_available(*, app_mode: str, engagement_id: str, core) -> bool:
    """Return True only for the synthetic/demo execution path."""
    return (
        app_mode.lower() == "demo"
        and workspace_environment(engagement_id).lower() == "demo"
        and isinstance(core, SyntheticCoreAdapter)
    )


def demo_experience_switching_available(*, app_mode: str, principal: Principal, core) -> bool:
    """Fail closed unless this is the anonymous synthetic demo identity and dataset."""
    if principal.authenticated or principal.organization_id != "org-synthetic":
        return False
    if not principal.engagement_ids:
        return False
    return all(
        demo_data_available(app_mode=app_mode, engagement_id=engagement_id, core=core)
        for engagement_id in principal.engagement_ids
    )


def principal_for_demo_experience(principal: Principal, selection: str) -> Principal:
    """Return a synthetic persona with real role permissions but no live identity."""
    if principal.authenticated or principal.organization_id != "org-synthetic":
        raise PermissionError("Demo experience switching is restricted to the anonymous synthetic tenant")

    match = next((item for item in DEMO_EXPERIENCES if item[0] == selection), None)
    if match is None:
        raise ValueError("Unknown demo experience")

    _label, role, _description = match
    persona_name = {
        Role.OWNER: "Synthetic Owner",
        Role.ADMIN: "Synthetic Administrator",
        Role.ANALYST: "Synthetic Employee",
        Role.CLIENT: "Synthetic Client",
    }[role]
    return replace(
        principal,
        email=f"demo+{role.value}@synthetic.invalid",
        display_name=persona_name,
        role=role,
        authenticated=False,
    )


def render_demo_experience_switcher(experience_shell, *, app_mode: str, principal: Principal, core) -> Principal:
    """Render the persona switcher and return the selected synthetic principal.

    Every persona uses the same synthetic organization/workspace so an action can
    be tested from one interface and inspected from another. Only the role and
    presentation identity change. This function is intentionally unavailable for
    authenticated identities or non-synthetic workspaces.
    """
    if not demo_experience_switching_available(app_mode=app_mode, principal=principal, core=core):
        return principal

    labels = [label for label, _role, _description in DEMO_EXPERIENCES]
    current = experience_shell.st.session_state.get("_coletti_demo_experience", labels[0])
    if current not in labels:
        current = labels[0]
        experience_shell.st.session_state["_coletti_demo_experience"] = current

    experience_shell.st.sidebar.divider()
    experience_shell.st.sidebar.caption("DEMO EXPERIENCE SWITCHER")
    selected = experience_shell.st.sidebar.selectbox(
        "View ColettiOS as",
        labels,
        index=labels.index(current),
        key="_coletti_demo_experience",
        help="Synthetic demo only. This changes the simulated role/interface, never a live user's authorization.",
    )
    simulated = principal_for_demo_experience(principal, selected)
    description = next(description for label, _role, description in DEMO_EXPERIENCES if label == selected)
    experience_shell.st.sidebar.caption(description)
    experience_shell.st.sidebar.caption(
        "Same synthetic case across views · actions remain inside the demo tenant"
    )
    return simulated


def _save_empty_publication_state(experience_shell, *, principal, engagement_id: str) -> None:
    publication_store = experience_shell.st.session_state.get("_coletti_publication_store")
    if publication_store is not None:
        publication_store.save(
            organization_id=principal.organization_id,
            engagement_id=engagement_id,
            records={},
        )


def _reset_demo_data(experience_shell, *, principal, engagement_id: str, core) -> None:
    """Restore the canonical pre-populated synthetic demonstration.

    This function intentionally does not call st.rerun(). Streamlit button callbacks
    execute before the framework's normal full-script rerun, which prevents the
    partial-render/blank-workspace behavior caused by forcing a rerun from inside
    the sidebar render path.
    """
    if not isinstance(core, SyntheticCoreAdapter):
        raise PermissionError("Demo reset is restricted to the synthetic Core adapter")
    core.reset_demo_data()
    _save_empty_publication_state(
        experience_shell,
        principal=principal,
        engagement_id=engagement_id,
    )
    experience_shell.st.session_state.pop("_last_intake_result", None)
    experience_shell.st.session_state["_document_processing_queue"] = {}
    experience_shell.st.session_state.pop("_demo_data_cleared_notice", None)
    experience_shell.st.session_state["_demo_data_loaded_notice"] = True


def _clear_demo_data(experience_shell, *, principal, engagement_id: str, core) -> None:
    """Clear the synthetic case so the operator can test the workflow from intake.

    Only synthetic Core state, demo publication state, and session-only extraction
    staging are cleared. There is deliberately no production/HTTP equivalent.
    """
    if not isinstance(core, SyntheticCoreAdapter):
        raise PermissionError("Demo clear is restricted to the synthetic Core adapter")
    core.clear_demo_data()
    _save_empty_publication_state(
        experience_shell,
        principal=principal,
        engagement_id=engagement_id,
    )
    experience_shell.st.session_state.pop("_last_intake_result", None)
    experience_shell.st.session_state["_document_processing_queue"] = {}
    experience_shell.st.session_state.pop("_demo_data_loaded_notice", None)
    experience_shell.st.session_state["_demo_data_cleared_notice"] = True


def patch_demo_data_control(experience_shell) -> None:
    """Add unmistakable demo-data actions without changing live-workspace behavior."""

    original_sidebar_identity = experience_shell._sidebar_identity
    original_select_engagement = experience_shell._select_engagement
    original_topbar = experience_shell._topbar

    def select_engagement_with_demo_tracking(principal) -> str:
        selected = original_select_engagement(principal)
        experience_shell.st.session_state["_coletti_selected_engagement"] = selected
        return selected

    def sidebar_identity_with_demo_control(principal, engagement_id: str) -> None:
        original_sidebar_identity(principal, engagement_id)

        app_mode = experience_shell.app._secret("APP_MODE", "demo").lower()
        core = experience_shell.st.session_state.get("_coletti_core")
        if not demo_data_available(
            app_mode=app_mode,
            engagement_id=engagement_id,
            core=core,
        ):
            return

        def reset_sidebar_demo() -> None:
            _reset_demo_data(
                experience_shell,
                principal=principal,
                engagement_id=engagement_id,
                core=core,
            )

        def clear_sidebar_demo() -> None:
            _clear_demo_data(
                experience_shell,
                principal=principal,
                engagement_id=engagement_id,
                core=core,
            )

        experience_shell.st.sidebar.divider()
        experience_shell.st.sidebar.caption("DEMONSTRATION")
        experience_shell.st.sidebar.button(
            "Load Demo Data",
            key="load_demo_data_sidebar",
            type="primary",
            use_container_width=True,
            help="Restore the prepared Coletti & Co. synthetic demonstration with sample sources, findings, and an open contradiction.",
            on_click=reset_sidebar_demo,
        )
        experience_shell.st.sidebar.button(
            "Clear Demo Data",
            key="clear_demo_data_sidebar",
            use_container_width=True,
            help="Erase the synthetic case state and extraction queue so you can begin at intake and work the case all the way through yourself.",
            on_click=clear_sidebar_demo,
        )

        if experience_shell.st.session_state.get("_demo_data_loaded_notice", False):
            experience_shell.st.sidebar.success("Prepared demo data restored")
        if experience_shell.st.session_state.get("_demo_data_cleared_notice", False):
            experience_shell.st.sidebar.success("Demo case cleared · start at intake")
        experience_shell.st.sidebar.caption("Synthetic records only · never connected to a live client case")

    def topbar_with_demo_control(principal, experience: str) -> None:
        original_topbar(principal, experience)

        engagement_id = experience_shell.st.session_state.get("_coletti_selected_engagement")
        core = experience_shell.st.session_state.get("_coletti_core")
        app_mode = experience_shell.app._secret("APP_MODE", "demo").lower()
        if not engagement_id or not demo_data_available(
            app_mode=app_mode,
            engagement_id=engagement_id,
            core=core,
        ):
            return

        def reset_main_demo() -> None:
            _reset_demo_data(
                experience_shell,
                principal=principal,
                engagement_id=engagement_id,
                core=core,
            )

        experience_shell.st.caption("DEMO WORKSPACE · Synthetic records only")
        experience_shell.st.button(
            "Load Demo Data",
            key="load_demo_data_main",
            type="primary",
            use_container_width=True,
            help="Restore the prepared synthetic demonstration.",
            on_click=reset_main_demo,
        )

        if experience_shell.st.session_state.pop("_demo_data_loaded_notice", False):
            experience_shell.st.success("Prepared demo data restored")
        if experience_shell.st.session_state.pop("_demo_data_cleared_notice", False):
            experience_shell.st.success("Demo case cleared. Start at intake and work the synthetic case from the beginning.")

    experience_shell._select_engagement = select_engagement_with_demo_tracking
    experience_shell._sidebar_identity = sidebar_identity_with_demo_control
    experience_shell._topbar = topbar_with_demo_control
