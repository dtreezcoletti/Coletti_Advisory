from coletti_advisory import experience_shell
from coletti_advisory.luxury_theme import apply_luxury_theme
from coletti_advisory.mobile_ui import patch_mobile_theme

# Replace the legacy presentation layer without changing any authorization,
# workflow, evidence, review, or publication behavior. Mobile CSS then wraps the
# luxury theme so the same visual system remains intact on phone/tablet widths.
experience_shell._apply_brand_theme = apply_luxury_theme

if not getattr(experience_shell, "_mobile_ui_patched", False):
    patch_mobile_theme(experience_shell)
    experience_shell._mobile_ui_patched = True

experience_shell.run()
