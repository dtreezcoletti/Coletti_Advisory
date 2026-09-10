from __future__ import annotations

from .demo_controls import (
    DEMO_EXPERIENCES,
    demo_experience_switching_available,
    principal_for_demo_experience,
)


def patch_demo_selector_resolution(owner_runtime) -> None:
    """Keep Authorized workspace as the one visible synthetic persona selector.

    owner_console_runtime historically rendered a separate demo switcher before
    calling the shared workspace selector. The shared selector now owns the UI;
    this replacement only resolves the already-selected persona from session
    state before the rest of the runtime determines the experience.
    """
    if getattr(owner_runtime, "_demo_selector_resolution_patched", False):
        return

    def resolve_without_render(shell, *, app_mode: str, principal, core):
        if not demo_experience_switching_available(
            app_mode=app_mode,
            principal=principal,
            core=core,
        ):
            return principal
        labels = [label for label, _role, _description in DEMO_EXPERIENCES]
        selected = shell.st.session_state.get("_coletti_demo_experience", labels[0])
        if selected not in labels:
            selected = labels[0]
            shell.st.session_state["_coletti_demo_experience"] = selected
        return principal_for_demo_experience(principal, selected)

    owner_runtime.render_demo_experience_switcher = resolve_without_render
    owner_runtime._demo_selector_resolution_patched = True
