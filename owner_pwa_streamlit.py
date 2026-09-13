import streamlit as st

from coletti_advisory import (
    client_operations,
    experience_shell,
    owner_console_live_ui,
    owner_console_notifications,
    owner_console_runtime,
    owner_console_structure_patch,
    owner_console_ui,
    owner_page_integration,
    profile_menu_patch,
    supabase_auth,
)
from coletti_advisory.client_dari_context import patch_clients_dari_context
from coletti_advisory.client_operations import patch_clients_operating_surface
from coletti_advisory.cross_interface_connections import patch_cross_interface_dashboards
from coletti_advisory.demo_controls import patch_demo_data_control
from coletti_advisory.demo_selector_fix import patch_demo_selector_resolution
from coletti_advisory.interface_connection_patch import patch_interface_connections
from coletti_advisory.luxury_mobile import apply_luxury_mobile_overrides
from coletti_advisory.luxury_theme import apply_luxury_theme
from coletti_advisory.mobile_ui import patch_mobile_theme
from coletti_advisory.owner_console_runtime import run_reference_workspace
from coletti_advisory.owner_console_structure_patch import patch_owner_console_structure
from coletti_advisory.owner_evidence_workspace import patch_owner_evidence_workspace
from coletti_advisory.owner_page_integration import (
    patch_owner_page_integration,
    patch_shared_engagement_selector,
)
from coletti_advisory.owner_pwa_patch import patch_owner_pwa
from coletti_advisory.portal_case_lifecycle import render_lifecycle
from coletti_advisory.profile_menu_patch import patch_profile_menus
from coletti_advisory.report_presentation import patch_report_presentation


# Preserve the existing ColettiOS Owner Console presentation and behavior.
experience_shell._apply_brand_theme = apply_luxury_theme

if not getattr(experience_shell, "_mobile_ui_patched", False):
    patch_mobile_theme(experience_shell)
    experience_shell._mobile_ui_patched = True

if not getattr(experience_shell, "_demo_data_control_patched", False):
    patch_demo_data_control(experience_shell)
    experience_shell._demo_data_control_patched = True

if not getattr(experience_shell, "_report_presentation_patched", False):
    patch_report_presentation(experience_shell.app)
    experience_shell._report_presentation_patched = True

if not getattr(owner_console_runtime, "_ingested_materials_workspace_patched", False):
    patch_owner_evidence_workspace(owner_console_runtime)

if not getattr(experience_shell, "_shared_engagement_selector_patched", False):
    patch_shared_engagement_selector(experience_shell)

patch_demo_selector_resolution(owner_console_runtime)

if not getattr(owner_console_runtime, "_owner_page_integration_patched", False):
    patch_owner_page_integration(owner_console_runtime)

if not getattr(experience_shell, "_profile_menus_patched", False):
    patch_profile_menus(
        experience_shell,
        owner_console_ui,
        owner_console_notifications,
        owner_console_runtime,
    )

patch_owner_console_structure(
    owner_console_ui,
    owner_console_live_ui,
    owner_console_runtime,
    owner_console_notifications,
    owner_page_integration,
    profile_menu_patch,
)

patch_interface_connections(
    experience_shell,
    owner_console_runtime,
    owner_console_structure_patch,
    owner_console_live_ui,
    owner_console_ui,
)
patch_cross_interface_dashboards(experience_shell)

# Install the permanent Client relationship operating surface and constrained
# DARI Client context before the Owner-PWA wrapper captures the Owner renderer.
patch_clients_operating_surface(owner_console_runtime)
patch_clients_dari_context(client_operations, owner_console_live_ui)

# Add the owner-private workspace, safe owner-only fallback workspace, and
# Supabase logout behavior after the canonical console patches are installed.
patch_owner_pwa(owner_console_runtime, owner_console_ui)

# Cases in the Owner PWA must read the same authoritative 13-checkpoint Case
# lifecycle as Client/Employee/Admin portals; keep the existing Case workspace
# immediately below the lifecycle control surface.
if not getattr(owner_console_runtime, "_owner_pwa_lifecycle_patched", False):
    _owner_page_with_private_workspace = owner_console_runtime._render_owner_page

    def _owner_page_with_lifecycle(shell, page: str, **kwargs):
        if page == "Cases":
            render_lifecycle(
                kwargs["principal"],
                kwargs["engagement_id"],
                controls=True,
                title="Owner Case Lifecycle",
            )
            st.divider()
        return _owner_page_with_private_workspace(shell, page, **kwargs)

    owner_console_runtime._render_owner_page = _owner_page_with_lifecycle
    owner_console_runtime._owner_pwa_lifecycle_patched = True

# Keep the quiet-luxury mobile geometry after responsive patches.
_patched_theme = experience_shell._apply_brand_theme


def _final_theme() -> None:
    _patched_theme()
    apply_luxury_mobile_overrides()


experience_shell._apply_brand_theme = _final_theme

# Recovery stays outside the authenticated Streamlit surface. Show a clear
# owner-safe link only when there is no active Supabase Auth session.
if supabase_auth.current_access_token() is None:
    st.markdown(
        """
        <div style="max-width: 665px; margin: 0 auto 10px auto; text-align: right;">
          <a href="/forgot-password" target="_self"
             style="font-family: Arial, sans-serif; font-size: 13px; color: #6c655c; text-decoration: underline;">
             Forgot password?
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

run_reference_workspace(experience_shell)
