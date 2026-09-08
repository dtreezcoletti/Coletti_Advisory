from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from . import owner_console_ui as base
from .owner_console_live import OwnerControlPlaneClient, OwnerControlPlaneUnavailable
from .workspaces import workspace_label


def build_owner_notifications(snapshot: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build current-state notifications without inventing a second durable queue.

    The authoritative records remain Dispatcher/Registry objects. This function
    only projects them into the owner UI so the bell, DARI rail, approvals, and
    Dispatcher all reflect the same source state.
    """
    items: list[dict[str, str]] = []

    for approval in snapshot.get("approvals") or []:
        items.append(
            {
                "kind": "Decision",
                "title": str(approval.get("title") or approval.get("approval_key") or "Owner decision required"),
                "detail": "Protected human gate" if approval.get("protected_gate") else "Human decision required",
                "target": "Approvals",
            }
        )

    for task in snapshot.get("tasks") or []:
        if task.get("overdue"):
            items.append(
                {
                    "kind": "Overdue",
                    "title": str(task.get("title") or task.get("task_id") or "Dispatcher task"),
                    "detail": str(task.get("project") or "Dispatcher"),
                    "target": "Dispatcher",
                }
            )
        elif task.get("due_today"):
            items.append(
                {
                    "kind": "Due today",
                    "title": str(task.get("title") or task.get("task_id") or "Dispatcher task"),
                    "detail": str(task.get("project") or "Dispatcher"),
                    "target": "Dispatcher",
                }
            )

    for run in snapshot.get("reconciliations") or []:
        if str(run.get("status") or "").upper() in {"ATTENTION_REQUIRED", "FAILED"}:
            items.append(
                {
                    "kind": "Reconciliation",
                    "title": "State reconciliation needs attention",
                    "detail": f"{run.get('mismatch_count', 0)} mismatch(es) · {run.get('status', 'ATTENTION_REQUIRED')}",
                    "target": "Dispatcher",
                }
            )

    for command in snapshot.get("calendar_commands") or []:
        if str(command.get("approval_state") or "").upper() in {"PENDING", "REQUIRED"}:
            items.append(
                {
                    "kind": "Calendar",
                    "title": str(command.get("title") or command.get("natural_language") or "Calendar command waiting"),
                    "detail": "Approval required before calendar execution",
                    "target": "Dispatcher",
                }
            )

    # Keep the bell useful, not noisy. All full detail remains available in the
    # authoritative destination pages.
    return items[:20]


def _snapshot(core, principal, engagement_id: str) -> dict[str, Any]:
    try:
        client = OwnerControlPlaneClient(core)
        if not principal.authenticated:
            return {}
        return client.snapshot(principal, engagement_id)
    except OwnerControlPlaneUnavailable:
        return {}


def _route(principal, page: str) -> None:
    st.session_state[f"_owner_reference_page:{principal.user_id}"] = page
    st.rerun()


def _render_search(principal, manifest: Mapping[str, Any], engagement_ids, snapshot: Mapping[str, Any]) -> None:
    query = st.text_input(
        "Search",
        placeholder="Search cases, clients, documents, tasks, decisions, or help…",
        label_visibility="collapsed",
        key="owner_reference_search",
    ).strip().lower()
    if not query:
        return

    matches: list[tuple[str, str]] = []
    for eid in engagement_ids:
        label = workspace_label(eid)
        if query in str(eid).lower() or query in label.lower():
            matches.append((f"Case · {label} · {eid}", "Case Queue"))

    for source in (manifest.get("sources") or {}).values():
        meta = source.get("metadata") or {}
        filename = str(meta.get("filename") or source.get("source_id") or "")
        classification = str(meta.get("classification") or "")
        if query in filename.lower() or query in classification.lower():
            matches.append((f"Document · {filename}", "Evidence"))
        if len(matches) >= 8:
            break

    for task in snapshot.get("tasks") or []:
        title = str(task.get("title") or task.get("task_id") or "")
        project = str(task.get("project") or "")
        if query in title.lower() or query in project.lower():
            matches.append((f"Task · {title}", "Dispatcher"))
        if len(matches) >= 12:
            break

    for approval in snapshot.get("approvals") or []:
        title = str(approval.get("title") or approval.get("approval_key") or "")
        if query in title.lower():
            matches.append((f"Decision · {title}", "Approvals"))
        if len(matches) >= 15:
            break

    if not matches:
        st.caption("No match in your currently authorized owner workspace.")
        return

    with st.expander(f"Search results · {len(matches)}", expanded=True):
        for idx, (label, target) in enumerate(matches[:15]):
            cols = st.columns([4, 1], gap="small", vertical_alignment="center")
            cols[0].write(label)
            if cols[1].button("Open", key=f"owner-search-result-{idx}-{target}", use_container_width=True):
                _route(principal, target)


def render_live_owner_topbar(principal, manifest: Mapping[str, Any], engagement_ids, *, core, engagement_id: str) -> None:
    snapshot = _snapshot(core, principal, engagement_id)
    if not snapshot:
        base._owner_topbar(principal, manifest, engagement_ids)
        return

    notifications = build_owner_notifications(snapshot)
    left, search_col, bell_col, profile = st.columns([1.2, 2.25, .42, 1.2], gap="small", vertical_alignment="center")

    with left:
        st.markdown(
            "<div class='oc-topbrand'><strong>ColettiOS</strong><span>Owner Console</span></div>",
            unsafe_allow_html=True,
        )

    with search_col:
        st.markdown("<div class='oc-search-shell'>", unsafe_allow_html=True)
        _render_search(principal, manifest, engagement_ids, snapshot)
        st.markdown("</div>", unsafe_allow_html=True)

    with bell_col:
        label = f"🔔 {len(notifications)}" if notifications else "🔔"
        with st.popover(label, use_container_width=True):
            st.markdown("### Notifications")
            st.caption("Current in-app signals from Dispatcher and Registry. External delivery is a separate protected activation.")
            if not notifications:
                st.success("No current owner notification requires attention.")
            else:
                for idx, item in enumerate(notifications[:12]):
                    st.markdown(f"**{base._esc(item['kind'])} · {base._esc(item['title'])}**", unsafe_allow_html=True)
                    st.caption(item["detail"])
                    if st.button("Open", key=f"owner-notification-open-{idx}", use_container_width=True):
                        _route(principal, item["target"])
                    if idx < min(len(notifications), 12) - 1:
                        st.divider()

    with profile:
        st.markdown(
            f"<div class='oc-profile'><div class='oc-avatar'>{base._esc(base._initials(principal))}</div>"
            f"<div class='oc-profile-copy'><strong>{base._esc(principal.display_name)}</strong><span>Owner</span></div></div>",
            unsafe_allow_html=True,
        )
