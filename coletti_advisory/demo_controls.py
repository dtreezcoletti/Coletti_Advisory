from __future__ import annotations

from .core_adapter import SyntheticCoreAdapter
from .workspaces import workspace_environment


def demo_data_available(*, app_mode: str, engagement_id: str, core) -> bool:
    """Return True only for the synthetic/demo execution path."""
    return (
        app_mode.lower() == "demo"
        and workspace_environment(engagement_id).lower() == "demo"
        and isinstance(core, SyntheticCoreAdapter)
    )


def _reset_demo_data(experience_shell, *, principal, engagement_id: str, core) -> None:
    """Restore the canonical synthetic dataset and clear demo publication state."""
    core.reset_demo_data()
    publication_store = experience_shell.st.session_state.get("_coletti_publication_store")
    if publication_store is not None:
        publication_store.save(
            organization_id=principal.organization_id,
            engagement_id=engagement_id,
            records={},
        )
    experience_shell.st.session_state["_demo_data_loaded_notice"] = True
    experience_shell.st.rerun()


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

        experience_shell.st.sidebar.divider()
        experience_shell.st.sidebar.caption("DEMONSTRATION")
        if experience_shell.st.sidebar.button(
            "Load Demo Data",
            key="load_demo_data_sidebar",
            type="primary",
            use_container_width=True,
            help="Restore the canonical synthetic Coletti & Co. demonstration. This control is unavailable for live client workspaces.",
        ):
            _reset_demo_data(
                experience_shell,
                principal=principal,
                engagement_id=engagement_id,
                core=core,
            )

        if experience_shell.st.session_state.pop("_demo_data_loaded_notice", False):
            experience_shell.st.sidebar.success("Demo data restored")
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

        experience_shell.st.caption("DEMO WORKSPACE · Synthetic records only")
        if experience_shell.st.button(
            "Load Demo Data",
            key="load_demo_data_main",
            type="primary",
            use_container_width=True,
            help="Restore the canonical synthetic demonstration to a clean starting state.",
        ):
            _reset_demo_data(
                experience_shell,
                principal=principal,
                engagement_id=engagement_id,
                core=core,
            )

        if experience_shell.st.session_state.pop("_demo_data_loaded_notice", False):
            experience_shell.st.success("Demo data restored")

    experience_shell._select_engagement = select_engagement_with_demo_tracking
    experience_shell._sidebar_identity = sidebar_identity_with_demo_control
    experience_shell._topbar = topbar_with_demo_control
