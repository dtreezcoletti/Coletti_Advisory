from coletti_advisory import experience_shell
from coletti_advisory import report_presentation
from coletti_advisory.demo_controls import patch_demo_data_control
from coletti_advisory.luxury_mobile import apply_luxury_mobile_overrides
from coletti_advisory.luxury_theme import apply_luxury_theme
from coletti_advisory.mobile_ui import patch_mobile_theme
from coletti_advisory.owner_console_runtime import run_reference_workspace
from coletti_advisory.record_vocabulary import patch_app_display, patch_report_presentation
from coletti_advisory.report_presentation import patch_report_presentation as patch_report_layout

# Replace the legacy presentation layer without changing authorization, workflow,
# source/record controls, review, or publication behavior.
experience_shell._apply_brand_theme = apply_luxury_theme

# IMP-070 is applied at the presentation boundary. Stored payload/API compatibility
# identifiers are deliberately left intact while visible terminology uses Record,
# Record State, and Source State as appropriate.
patch_app_display(experience_shell.app)
patch_report_presentation(report_presentation)

if not getattr(experience_shell, "_mobile_ui_patched", False):
    patch_mobile_theme(experience_shell)
    experience_shell._mobile_ui_patched = True

if not getattr(experience_shell, "_demo_data_control_patched", False):
    patch_demo_data_control(experience_shell)
    experience_shell._demo_data_control_patched = True

if not getattr(experience_shell, "_report_presentation_patched", False):
    patch_report_layout(experience_shell.app)
    experience_shell._report_presentation_patched = True

# The responsive layer intentionally adjusts layout/touch density. Apply a final
# visual-only pass afterward so mobile keeps the same quiet-luxury geometry and
# palette instead of drifting toward generic rounded consumer-app styling.
_patched_theme = experience_shell._apply_brand_theme


def _final_theme() -> None:
    _patched_theme()
    apply_luxury_mobile_overrides()


experience_shell._apply_brand_theme = _final_theme
run_reference_workspace(experience_shell)
