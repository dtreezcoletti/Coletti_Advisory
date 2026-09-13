from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from . import supabase_auth
from .models import Role


LIFECYCLE_STATUSES = (
    "NOT_STARTED",
    "READY",
    "IN_PROGRESS",
    "WAITING",
    "BLOCKED",
    "AWAITING_HUMAN",
    "COMPLETE",
    "NOT_APPLICABLE",
)

OPERATIONAL_STAFF_CHECKPOINTS = {
    "RECORD_COLLECTION",
    "RECONSTRUCTION",
    "HUMAN_REVIEW",
    "REPORT_PREPARATION",
}


def _token() -> str:
    token = supabase_auth.current_access_token()
    if not token:
        raise PermissionError("A live Supabase Auth session is required for authoritative Case lifecycle data.")
    return token


def _rpc(name: str, payload: dict[str, Any]) -> Any:
    return supabase_auth._rpc(name, access_token=_token(), payload=payload)


def lifecycle_snapshot(case_id: str) -> dict[str, Any]:
    value = _rpc("case_lifecycle_snapshot_v1", {"p_case_id": case_id})
    return dict(value) if isinstance(value, dict) else {}


def transition_checkpoint(
    case_id: str,
    checkpoint_key: str,
    target_status: str,
    *,
    reason: str = "",
    public_note: str = "",
) -> dict[str, Any]:
    value = _rpc(
        "transition_case_checkpoint_v1",
        {
            "p_case_id": case_id,
            "p_checkpoint_key": checkpoint_key,
            "p_target_status": target_status,
            "p_reason": reason or None,
            "p_public_note": public_note or None,
        },
    )
    return dict(value) if isinstance(value, dict) else {}


def _rest_headers() -> dict[str, str]:
    return supabase_auth._headers(access_token=_token())


def _rest_url(table: str) -> str:
    return f"{supabase_auth._secret('SUPABASE_URL').rstrip('/')}/rest/v1/{table}"


def _rest_get(table: str, params: dict[str, str]) -> list[dict[str, Any]]:
    response = requests.get(_rest_url(table), headers=_rest_headers(), params=params, timeout=20)
    if response.status_code >= 400:
        raise PermissionError(f"Authorized {table} read failed")
    payload = response.json()
    return [dict(row) for row in payload] if isinstance(payload, list) else []


def _rest_post(table: str, payload: dict[str, Any]) -> None:
    headers = {**_rest_headers(), "Prefer": "return=minimal"}
    response = requests.post(_rest_url(table), headers=headers, json=payload, timeout=20)
    if response.status_code >= 400:
        raise PermissionError(f"Authorized {table} write failed")


def case_requests(case_id: str) -> list[dict[str, Any]]:
    return _rest_get(
        "document_requests",
        {
            "case_id": f"eq.{case_id}",
            "select": "id,title,description,status,due_date,client_visible,created_at,updated_at",
            "order": "created_at.desc",
        },
    )


def create_case_request(
    principal,
    case_id: str,
    *,
    title: str,
    description: str,
    due_date: str | None,
    client_visible: bool,
) -> None:
    _rest_post(
        "document_requests",
        {
            "case_id": case_id,
            "title": title.strip(),
            "description": description.strip() or None,
            "requested_by": principal.user_id,
            "due_date": due_date or None,
            "client_visible": bool(client_visible),
            "status": "OPEN",
        },
    )


def case_messages(case_id: str) -> list[dict[str, Any]]:
    return _rest_get(
        "portal_messages",
        {
            "case_id": f"eq.{case_id}",
            "select": "id,sender_id,body,thread_type,attachments,created_at",
            "order": "created_at.asc",
        },
    )


def send_message(principal, case_id: str, body: str, *, internal: bool = False) -> None:
    _rest_post(
        "portal_messages",
        {
            "case_id": case_id,
            "sender_id": principal.user_id,
            "body": body.strip(),
            "thread_type": "INTERNAL" if internal else "CLIENT",
            "attachments": [],
        },
    )


def page_heading(kicker: str, title: str, copy: str = "") -> None:
    st.markdown(
        "<section style='margin:.2rem 0 1.25rem'>"
        f"<div class='cc-kicker'>{_esc(kicker)}</div>"
        f"<h1 style='margin:.25rem 0 .35rem'>{_esc(title)}</h1>"
        + (f"<div style='max-width:880px;color:#6f6a62'>{_esc(copy)}</div>" if copy else "")
        + "</section>",
        unsafe_allow_html=True,
    )


def _esc(value: Any) -> str:
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _status_text(value: str) -> str:
    return value.replace("_", " ").title()


def _status_icon(value: str) -> str:
    return {
        "COMPLETE": "✓",
        "IN_PROGRESS": "◐",
        "READY": "→",
        "WAITING": "◷",
        "AWAITING_HUMAN": "!",
        "BLOCKED": "×",
        "NOT_APPLICABLE": "—",
    }.get(value, "○")


def _lifecycle_html(snapshot: dict[str, Any]) -> str:
    rows: list[str] = []
    for checkpoint in snapshot.get("checkpoints") or []:
        status = str(checkpoint.get("status") or "NOT_STARTED")
        protected = " · Protected gate" if checkpoint.get("protected_gate") else ""
        domain = f" · {checkpoint.get('domain')}" if checkpoint.get("domain") else ""
        note = checkpoint.get("public_note") or checkpoint.get("description") or ""
        rows.append(
            "<div style='display:grid;grid-template-columns:32px minmax(180px,1fr) minmax(110px,.45fr);gap:12px;"
            "padding:12px 0;border-bottom:1px solid #e9e2d6;align-items:start'>"
            f"<div style='font-weight:700'>{_esc(_status_icon(status))}</div>"
            f"<div><div style='font-weight:700'>{_esc(checkpoint.get('label'))}</div>"
            f"<div style='font-size:.78rem;color:#7d756b'>{_esc(note)}</div>"
            f"<div style='font-size:.69rem;color:#9a8e7d;margin-top:4px'>{_esc(domain + protected)}</div></div>"
            f"<div style='font-size:.72rem;letter-spacing:.06em;text-transform:uppercase'>{_esc(_status_text(status))}</div>"
            "</div>"
        )
    return "".join(rows) or "<div style='padding:1rem'>No lifecycle checkpoints are available.</div>"


def render_lifecycle(principal, case_id: str, *, controls: bool = False, title: str = "Case Lifecycle") -> dict[str, Any]:
    try:
        snapshot = lifecycle_snapshot(case_id)
    except (PermissionError, requests.RequestException) as exc:
        st.warning(str(exc) or "Authoritative Case lifecycle is unavailable in this session.")
        return {}

    current = (snapshot.get("case") or {}).get("current_checkpoint") or "Complete"
    page_heading("Case Control", title, f"One authoritative checkpoint sequence · Current checkpoint: {_status_text(str(current))}")
    st.markdown(
        f"<section class='cc-panel' style='padding:0 1.1rem'>{_lifecycle_html(snapshot)}</section>",
        unsafe_allow_html=True,
    )

    if controls and principal.role in {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER}:
        _transition_controls(principal, case_id, snapshot)
    return snapshot


def _transition_controls(principal, case_id: str, snapshot: dict[str, Any]) -> None:
    checkpoints = list(snapshot.get("checkpoints") or [])
    if principal.role in {Role.ANALYST, Role.REVIEWER}:
        checkpoints = [item for item in checkpoints if item.get("key") in OPERATIONAL_STAFF_CHECKPOINTS]
    if not checkpoints:
        return

    with st.expander("Checkpoint control", expanded=False):
        st.caption(
            "Transitions write to the institutional lifecycle ledger. Protected gates remain Owner/Admin-only, and completion fails closed when a required earlier checkpoint is unresolved."
        )
        by_key = {str(item["key"]): item for item in checkpoints}
        key = st.selectbox(
            "Checkpoint",
            list(by_key),
            format_func=lambda value: f"{by_key[value].get('label')} · {_status_text(str(by_key[value].get('status')))}",
            key=f"lifecycle-checkpoint:{case_id}",
        )
        target = st.selectbox("Target state", LIFECYCLE_STATUSES, key=f"lifecycle-target:{case_id}")
        reason = st.text_area(
            "Reason / human rationale",
            placeholder="Required for completion, blocked, or not-applicable transitions.",
            key=f"lifecycle-reason:{case_id}",
        )
        public_note = st.text_input(
            "Client-visible note (optional)",
            placeholder="Keep this factual and suitable for the Client portal.",
            key=f"lifecycle-public-note:{case_id}",
        )
        if st.button("Record checkpoint transition", type="primary", key=f"lifecycle-transition:{case_id}"):
            try:
                transition_checkpoint(case_id, key, target, reason=reason, public_note=public_note)
                st.success("Lifecycle checkpoint recorded and audited.")
                st.rerun()
            except Exception as exc:
                message = str(exc)
                if "prior lifecycle checkpoint incomplete" in message.lower():
                    st.error("This checkpoint cannot be completed yet because a required earlier checkpoint is unresolved.")
                elif "not authorized" in message.lower() or "protected" in message.lower():
                    st.error("Your role is not authorized for that checkpoint transition.")
                else:
                    st.error(message or "The lifecycle transition was rejected.")


def render_requests(principal, case_id: str, *, allow_create: bool = False) -> None:
    page_heading("Records · Client Coordination", "Requests & To-Do", "Case-scoped record requests are shared without exposing internal analysis.")
    try:
        rows = case_requests(case_id)
    except Exception as exc:
        st.error(str(exc) or "Document requests could not be loaded.")
        return
    visible = rows if principal.role in {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER} else [r for r in rows if r.get("client_visible")]
    if visible:
        st.dataframe(
            [{
                "Request": r.get("title"),
                "Status": _status_text(str(r.get("status") or "OPEN")),
                "Due": r.get("due_date"),
                "Description": r.get("description"),
            } for r in visible],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No open record request is currently surfaced for this Case.")

    if allow_create and principal.role in {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER}:
        with st.expander("Create record request", expanded=False):
            with st.form(f"case-request:{case_id}"):
                title = st.text_input("Request title")
                description = st.text_area("Description")
                due = st.date_input("Due date", value=None)
                client_visible = st.checkbox("Show in Client portal", value=True)
                submit = st.form_submit_button("Create request", type="primary")
            if submit:
                if not title.strip():
                    st.error("A request title is required.")
                else:
                    try:
                        create_case_request(
                            principal,
                            case_id,
                            title=title,
                            description=description,
                            due_date=due.isoformat() if due else None,
                            client_visible=client_visible,
                        )
                        st.success("Case-scoped request created.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc) or "The request could not be created.")


def render_messages(principal, case_id: str, *, allow_internal: bool = False) -> None:
    page_heading("Communications", "Case Messages", "Messages remain Case-scoped and permission-controlled.")
    try:
        rows = case_messages(case_id)
    except Exception as exc:
        st.error(str(exc) or "Messages could not be loaded.")
        return

    internal_user = principal.role in {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER}
    tabs = st.tabs(("Client Thread", "Internal Thread")) if internal_user and allow_internal else (st.container(),)
    with tabs[0]:
        client_rows = [r for r in rows if r.get("thread_type") == "CLIENT"]
        if client_rows:
            for row in client_rows:
                st.markdown(f"**{_esc(row.get('sender_id'))}** · {_esc(row.get('created_at'))}")
                st.write(row.get("body") or "")
                st.divider()
        else:
            st.info("No Client-thread messages are recorded for this Case.")
        body = st.text_area("New message", key=f"client-thread-message:{case_id}")
        if st.button("Send message", type="primary", disabled=not body.strip(), key=f"send-client-message:{case_id}"):
            try:
                send_message(principal, case_id, body, internal=False)
                st.success("Message recorded in the Case thread.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc) or "Message could not be recorded.")

    if internal_user and allow_internal:
        with tabs[1]:
            internal_rows = [r for r in rows if r.get("thread_type") == "INTERNAL"]
            if internal_rows:
                for row in internal_rows:
                    st.markdown(f"**{_esc(row.get('sender_id'))}** · {_esc(row.get('created_at'))}")
                    st.write(row.get("body") or "")
                    st.divider()
            else:
                st.info("No internal Case-thread messages are recorded.")
            internal_body = st.text_area("Internal message", key=f"internal-thread-message:{case_id}")
            if st.button("Record internal message", disabled=not internal_body.strip(), key=f"send-internal-message:{case_id}"):
                try:
                    send_message(principal, case_id, internal_body, internal=True)
                    st.success("Internal Case message recorded.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc) or "Internal message could not be recorded.")


def render_client_dashboard(shell, principal, case_id: str, manifest: dict, records: dict) -> None:
    first_name = (principal.display_name or "Client").strip().split()[0]
    page_heading("Client Portal · Case Overview", f"Welcome, {first_name}.", "Your Case status, requests, records, and published deliverables are controlled from the same Case record.")
    snapshot = render_lifecycle(principal, case_id, controls=False, title="Your Case Progress")
    counts = snapshot or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Case", case_id)
    c2.metric("Records submitted", len(manifest.get("sources") or {}))
    c3.metric("Open requests", (counts.get("open_requests") if counts else 0) or 0)
    c4.metric("Published reports", (counts.get("published_reports") if counts else 0) or 0)
    st.caption("Internal reviewer notes, draft conclusions, and protected professional interpretation are not exposed in the Client portal.")


def render_employee_dashboard(shell, principal, case_id: str, manifest: dict, records: dict, reports: dict) -> None:
    page_heading("Team Workspace · Case Operations", "Work the Case through the controlled lifecycle.", "Records, reconstruction, human review, report preparation, and handoff are tied to explicit checkpoints.")
    render_lifecycle(principal, case_id, controls=True, title="Assigned Case Lifecycle")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sources", len(manifest.get("sources") or {}))
    c2.metric("Contradictions", len(manifest.get("contradictions") or {}))
    c3.metric("Draft report bundles", len(reports or {}))
    render_requests(principal, case_id, allow_create=True)


def render_admin_dashboard(shell, principal, case_id: str, manifest: dict, records: dict, reports: dict) -> None:
    page_heading("Administration · Lifecycle Control", "Admin Operations", "Control Client onboarding, Case checkpoints, access, assignments, and operational handoffs without replacing Owner-only governance.")
    render_lifecycle(principal, case_id, controls=True, title="Case Lifecycle Control")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Authorized Case", case_id)
    c2.metric("Sources", len(manifest.get("sources") or {}))
    c3.metric("Reports in workspace", len(reports or {}))
    c4.metric("Role", "Admin")
    render_requests(principal, case_id, allow_create=True)
