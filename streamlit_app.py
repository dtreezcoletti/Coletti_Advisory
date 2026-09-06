from coletti_advisory import experience_shell
from coletti_advisory.luxury_mobile import apply_luxury_mobile_overrides
from coletti_advisory.luxury_theme import apply_luxury_theme
from coletti_advisory.mobile_ui import patch_mobile_theme

# Replace the legacy presentation layer without changing authorization, workflow,
# evidence, review, or publication behavior.
experience_shell._apply_brand_theme = apply_luxury_theme

if not getattr(experience_shell, "_mobile_ui_patched", False):
    patch_mobile_theme(experience_shell)
    experience_shell._mobile_ui_patched = True

# The responsive layer intentionally adjusts layout/touch density. Apply a final
# visual-only pass afterward so mobile keeps the same quiet-luxury geometry and
# palette instead of drifting toward generic rounded consumer-app styling.
_patched_theme = experience_shell._apply_brand_theme


def _final_theme() -> None:
    _patched_theme()
    apply_luxury_mobile_overrides()


experience_shell._apply_brand_theme = _final_theme
experience_shell.run()
