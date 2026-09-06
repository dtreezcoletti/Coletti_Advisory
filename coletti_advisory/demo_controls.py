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


def patch_demo_data_control(experience_shell) -> None:
    """Add an unmistakable demo-data action without changing live-workspace behavior."""

    original_sidebar_identity = experience_shell._sidebar_identity

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
            type="primary",
            use_container_width=True,
            help="Restore the canonical synthetic Coletti & Co. demonstration. This control is unavailable for live client workspaces.",
        ):
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

        if experience_shell.st.session_state.pop("_demo_data_loaded_notice", False):
            experience_shell.st.sidebar.success("Demo data restored")
        experience_shell.st.sidebar.caption("Synthetic records only · never connected to a live client case")

    experience_shell._sidebar_identity = sidebar_identity_with_demo_control
