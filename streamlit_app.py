from coletti_advisory import experience_shell
from coletti_advisory.mobile_ui import patch_mobile_theme

if not getattr(experience_shell, "_mobile_ui_patched", False):
    patch_mobile_theme(experience_shell)
    experience_shell._mobile_ui_patched = True

experience_shell.run()
