"""PEL-001: Owner-only, read-through Execution Center for existing Dispatcher.

The view deliberately does NOT issue production commands or advertise an
unverified worker as online. It reuses the current authenticated Core snapshot.
"""
from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .models import Role
from .owner_console_live import OwnerControlPlaneClient, OwnerControlPlaneUnavailable


PAGE = "Execution Center"


def _safe_rows(items: Any, *, keys: tuple[str, ...], limit: int = 30) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    rows: list[dict[str, str]] = []
    for item in items[:limit]:
        if not isinstance(item, Mapping):
            continue
        rows.append({key: str(item.get(key) or "—")[:180] for key in keys})
    return rows


def _navigate(principal: Any, destination: str) -> None:
    st.session_state[f"_owner_reference_page:{principal.user_id}"] = destination
    st.rerun()


def render_execution_center(*, principal: Any, engagement_id: str, core: Any) -> None:
    """Render live data when authenticated, otherwise explicitly show no proof."""
    if getattr(principal, "role", None) != Role.OWNER or not getattr(principal, "authenticated", False):
        st.error("Execution Center requires an authenticated Owner.")
        return

    st.title("Execution Center")
    st.caption("Owner-only view · Live Dispatcher readings where available · No automatic production promotion")
    if st.button("Refresh operating snapshot", key="pel-001-refresh"):
        st.rerun()

    st.info(
        "Engineering execution remains separately gated. A registered worker, "
        "source-code commit, or planned lease does not prove an active worker. "
        "Production execution requires a verified worker heartbeat and a "
        "valid, enforced institutional execution lease."
    )

    try:
        control = OwnerControlPlaneClient(core)
        snapshot = control.snapshot(principal, engagement_id)
        if not isinstance(snapshot, dict):
            raise OwnerControlPlaneUnavailable("Invalid snapshot")
    except (OwnerControlPlaneUnavailable, ValueError, TypeError):
        st.warning(
            "Authoritative Owner/Dispatcher snapshot unavailable in this session. "
            "No operational counts are inferred. Check the Core service and access controls."
        )
        return

    tasks = snapshot.get("tasks")
    approvals = snapshot.get("approvals")
    if not isinstance(tasks, list) or not isinstance(approvals, list):
        st.warning("The Core responded, but the required task or approval evidence is missing.")
        return

    left, middle, right = st.columns(3)
    left.metric("Dispatcher tasks received", len(tasks))
    middle.metric("Owner decisions received", len(approvals))
    right.metric("Worker verified", "Not established")
    st.caption("Task and approval figures are from the current authenticated Core snapshot; "
               "worker status is not connected to a verified heartbeat endpoint.")

    st.subheader("Current Dispatcher work")
    task_rows = _safe_rows(
        tasks,
        keys=("title", "lifecycle_state", "owning_domain", "updated_at"),
    )
    if task_rows:
        st.dataframe(task_rows, hide_index=True, use_container_width=True)
    else:
        st.info("No task rows were returned in the current authorized snapshot.")

    st.subheader("Decisions requiring attention")
    approval_rows = _safe_rows(
        approvals,
        keys=("title", "approval_key", "current_state", "owning_domain"),
    )
    if approval_rows:
        st.dataframe(approval_rows, hide_index=True, use_container_width=True)
    else:
        st.info("No decision rows were returned in the current authorized snapshot.")

    st.subheader("Continue in the existing workspace")
    case_col, dispatch_col, team_col = st.columns(3)
    if case_col.button("Open Case Queue", key="pel-001-case", use_container_width=True):
        _navigate(principal, "Case Queue")
    if dispatch_col.button("Open Dispatcher", key="pel-001-dispatch", use_container_width=True):
        _navigate(principal, "Dispatcher")
    if team_col.button("Open Team", key="pel-001-team", use_container_width=True):
        _navigate(principal, "Team")


def patch_execution_center(owner_runtime: Any) -> None:
    """Integrate with the existing Owner Streamlit sidebar and page renderer."""
    if getattr(owner_runtime, "_pel_001_execution_center_patched", False):
        return
    original_sidebar = owner_runtime._owner_sidebar
    original_render = owner_runtime._render_owner_page

    def sidebar(shell: Any, principal: Any, engagement_id: str) -> str:
        active = original_sidebar(shell, principal, engagement_id)
        if getattr(principal, "role", None) != Role.OWNER:
            return active
        page_key = f"_owner_reference_page:{principal.user_id}"
        st.sidebar.divider()
        st.sidebar.caption("OPERATIONS")
        if st.sidebar.button(
            "◈   Execution Center",
            key="pel-001-execution-nav",
            type="primary" if st.session_state.get(page_key) == PAGE else "secondary",
            use_container_width=True,
        ):
            st.session_state[page_key] = PAGE
            st.rerun()
        return PAGE if st.session_state.get(page_key) == PAGE else active

    def render(shell: Any, page: str, **kwargs: Any) -> Any:
        if page == PAGE:
            return render_execution_center(
                principal=kwargs["principal"],
                engagement_id=kwargs["engagement_id"],
                core=kwargs["core"],
            )
        return original_render(shell, page, **kwargs)

    owner_runtime._owner_sidebar = sidebar
    owner_runtime._render_owner_page = render
    owner_runtime._pel_001_execution_center_patched = True
