from coletti_advisory import (
    experience_shell,
    owner_console_live_ui,
    owner_console_notifications,
    owner_console_runtime,
    owner_console_ui,
    owner_page_integration,
    profile_menu_patch,
)
from coletti_advisory.demo_controls import patch_demo_data_control
from coletti_advisory.demo_selector_fix import patch_demo_selector_resolution
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
from coletti_advisory.profile_menu_patch import patch_profile_menus
from coletti_advisory.report_presentation import patch_report_presentation

# Replace the legacy presentation layer without changing authorization, workflow,
# evidence, review, or publication behavior.
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

# One explicit selected-case state now drives the sidebar, Cases, Clients, and
# each owner case-production stage. In synthetic mode this visible Authorized
# workspace selector also owns Client/Employee/Admin/Owner experience switching.
if not getattr(experience_shell, "_shared_engagement_selector_patched", False):
    patch_shared_engagement_selector(experience_shell)

# Resolve the selected synthetic persona without rendering the retired second
# demo switcher. This leaves Authorized workspace as the single visible control.
patch_demo_selector_resolution(owner_console_runtime)

if not getattr(owner_console_runtime, "_owner_page_integration_patched", False):
    patch_owner_page_integration(owner_console_runtime)

# Replace static upper-right identity pills with permission-aware personal
# profile menus across client, employee, admin, and owner experiences.
if not getattr(experience_shell, "_profile_menus_patched", False):
    patch_profile_menus(
        experience_shell,
        owner_console_ui,
        owner_console_notifications,
        owner_console_runtime,
    )

# Install the approved 2026-09-10 Owner Console information architecture after
# the integration/profile layers so it is the final owner presentation contract.
patch_owner_console_structure(
    owner_console_ui,
    owner_console_live_ui,
    owner_console_runtime,
    owner_console_notifications,
    owner_page_integration,
    profile_menu_patch,
)

# The responsive layer intentionally adjusts layout/touch density. Apply a final
# visual-only pass afterward so mobile keeps the same quiet-luxury geometry and
# palette instead of drifting toward generic rounded consumer-app styling.
_patched_theme = experience_shell._apply_brand_theme


def _final_theme() -> None:
    _patched_theme()
    apply_luxury_mobile_overrides()


experience_shell._apply_brand_theme = _final_theme
run_reference_workspace(experience_shell)
