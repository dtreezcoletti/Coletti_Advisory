from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import streamlit as st

from .analysis import build_analytical_issues
from .owner_console_live import OwnerControlPlaneClient, OwnerControlPlaneUnavailable
from . import owner_console_ui as base
from .publication import PublicationStatus


LOCAL_TZ = ZoneInfo("America/Chicago")
TASK_STATES = (
    "CONCEPT",
    "SCOPED",
    "SCHEDULED",
    "IN PROGRESS",
    "DRAFT/BUILD",
    "REVIEW",
    "TEST/VALIDATION",
    "DEBUG/REWORK",
    "BLOCKED",
    "AWAITING HUMAN DECISION",
    "READY FOR APPROVAL",
    "COMPLETE",
    "CLOSED",
    "CANCELLED/SUPERSEDED",
)


def _client(core) -> OwnerControlPlaneClient | None:
    try:
        return OwnerControlPlaneClient(core)
    except OwnerControlPlaneUnavailable:
        return None


def _live_snapshot(core, principal, engagement_id: str) -> tuple[dict[str, Any], str | None]:
    client = _client(core)
    if client is None or not principal.authenticated:
        return {}, "Live Dispatcher data is unavailable in this session."
    try:
        return client.snapshot(principal, engagement_id), None
    except OwnerControlPlaneUnavailable:
        return {}, "The private ColettiOS owner service is not reachable right now."


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    return parsed.astimezone(LOCAL_TZ)


def _relative_time(value: Any) -> str:
    parsed = _parse_time(value)
    if parsed is None:
        return "Current"
    now = datetime.now(LOCAL_TZ)
    delta = now - parsed
    if delta < timedelta(minutes=2):
        return "Now"
    if delta < timedelta(hours=1):
        return f"{max(1, int(delta.total_seconds() // 60))}m ago"
    if delta < timedelta(days=1):
        return f"{max(1, int(delta.total_seconds() // 3600))}h ago"
    if delta < timedelta(days=2):
        return "Yesterday"
    return parsed.strftime("%b %-d")


def _decision_items(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in snapshot.get("approvals") or []:
        protected = bool(raw.get("protected_gate"))
        items.append(
            {
                "icon": "!" if protected else "✓",
                "title": str(raw.get("title") or raw.get("approval_key") or "Owner decision"),
                "kind": f"{str(raw.get('owning_domain') or 'dispatcher').replace('_', ' ').title()} · {str(raw.get('source_type') or 'Decision').replace('_', ' ').title()}",
                "status": "Protected Approval" if protected else "Needs Approval",
                "tone": "alert" if protected else "warn",
                "time": _relative_time(raw.get("created_at")),
                "approval_key": str(raw.get("approval_key") or ""),
                "source_type": str(raw.get("source_type") or ""),
                "source_id": str(raw.get("source_id") or ""),
                "protected_gate": protected,
                "current_state": str(raw.get("current_state") or ""),
                "detail": raw.get("detail") if isinstance(raw.get("detail"), Mapping) else {},
                "owning_domain": str(raw.get("owning_domain") or "dispatcher"),
            }
        )
    return items


def _goto_owner_page(principal, page: str) -> None:
    st.session_state[f"_owner_reference_page:{principal.user_id}"] = page
    st.rerun()


def _render_live_kpis(principal, snapshot: Mapping[str, Any], manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    counts = snapshot.get("counts") or {}
    review_tasks = sum(
        1
        for task in snapshot.get("tasks") or []
        if str(task.get("lifecycle_state") or "").upper() in {"REVIEW", "AWAITING HUMAN DECISION", "READY FOR APPROVAL"}
    )
    local_reviews = len(build_analytical_issues(dict(manifest)))
    active_cases = int((snapshot.get("case_counts") or {}).get("active_cases") or 0)
    if active_cases == 0:
        active_cases = len(principal.engagement_ids)
    report_signoffs = sum(
        1
        for record in records.values()
        if getattr(record, "status", None) in {PublicationStatus.IN_REVIEW, PublicationStatus.APPROVED}
    )
    items = [
        ("✓", str(counts.get("approvals", 0)), "My Approvals", "Protected and owner decisions"),
        ("▤", str(review_tasks + local_reviews), "Pending Reviews", "Human review queue"),
        ("▣", str(active_cases), "Active Cases", "Authoritative / authorized cases"),
        ("⌁", str(report_signoffs), "Reports Awaiting Sign-off", "Review / publication gate"),
    ]
    base._render_kpis(items)


def _render_live_decisions(principal, decisions: list[dict[str, Any]]) -> None:
    st.markdown(
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>Needs Your Decision</div>"
        "<div class='oc-tabs'><span>All</span><span>Reports</span><span>Publications</span><span>Client Requests</span></div>"
        "<div class='oc-link'>Live queue</div></div></section>",
        unsafe_allow_html=True,
    )
    if not decisions:
        st.success("No owner decision is waiting right now.")
        return

    for idx, item in enumerate(decisions[:7]):
        cols = st.columns([0.35, 3.25, 1.65, 1.35, 0.8], gap="small", vertical_alignment="center")
        cols[0].markdown(f"**{base._esc(item['icon'])}**")
        cols[1].markdown(f"**{base._esc(item['title'])}**  \n<span style='font-size:.72rem;color:#827d74'>{base._esc(item['kind'])}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span class='oc-status {base._esc(item['tone'])}'>{base._esc(item['status'])}</span>", unsafe_allow_html=True)
        cols[3].caption(item["time"])
        if cols[4].button("Review →", key=f"owner-review-{idx}-{item['approval_key']}", use_container_width=True):
            st.session_state["_owner_focus_approval"] = item["approval_key"]
            _goto_owner_page(principal, "Approvals")
        st.markdown("<div style='border-bottom:1px solid #ece8e0;margin:.1rem 0 .25rem'></div>", unsafe_allow_html=True)


def _task_rows(snapshot: Mapping[str, Any]) -> str:
    tasks = list(snapshot.get("tasks") or [])[:5]
    rows: list[str] = []
    for task in tasks:
        due = "Overdue" if task.get("overdue") else ("Today" if task.get("due_today") else str(task.get("assigned_date") or "Queued"))
        sub = " · ".join(
            value
            for value in (
                str(task.get("project") or ""),
                str(task.get("lifecycle_state") or ""),
                str(task.get("priority") or ""),
            )
            if value
        )
        rows.append(
            "<div class='oc-mini-row'><div>"
            f"<div class='oc-mini-title'>{base._esc(task.get('title') or task.get('task_id') or 'Task')}</div>"
            f"<div class='oc-mini-sub'>{base._esc(sub)}</div></div>"
            f"<div class='oc-mini-meta'>{base._esc(due)}</div></div>"
        )
    if not rows:
        rows.append("<div class='oc-mini-row'><div class='oc-mini-title'>No open Dispatcher tasks</div><div class='oc-mini-meta'>Clear</div></div>")
    return "".join(rows)


def _activity_rows(snapshot: Mapping[str, Any]) -> str:
    changes = list((snapshot.get("for_human") or {}).get("Important Changes") or [])[:5]
    rows: list[str] = []
    for change in changes:
        rows.append(
            "<div class='oc-mini-row'><div>"
            f"<div class='oc-mini-title'>{base._esc(change.get('title') or change.get('implementation_id') or 'Material change')}</div>"
            f"<div class='oc-mini-sub'>{base._esc(change.get('owner') or 'Registry')} · {base._esc(change.get('state') or '')}</div></div>"
            f"<div class='oc-mini-meta'>{base._esc(_relative_time(change.get('updated_at')))}</div></div>"
        )
    if not rows:
        rows.append("<div class='oc-mini-row'><div class='oc-mini-title'>No recent material changes</div><div class='oc-mini-meta'>Current</div></div>")
    return "".join(rows)


def _render_lower_grid_live(core, principal, engagement_id: str, snapshot: Mapping[str, Any]) -> None:
    st.markdown(
        "<div class='oc-three'>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>My Cases</div><div class='oc-link'>Authorized</div></div>"
        + base._case_rows(core, principal, engagement_id)
        + "</section>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>My Tasks</div><div class='oc-link'>Dispatcher live</div></div>"
        + _task_rows(snapshot)
        + "</section>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>Recent Activity</div><div class='oc-link'>Registry live</div></div>"
        + _activity_rows(snapshot)
        + "</section></div>",
        unsafe_allow_html=True,
    )


def _deterministic_dari_answer(prompt: str, snapshot: Mapping[str, Any]) -> str | None:
    q = prompt.strip().lower()
    if not q:
        return None
    approvals = list(snapshot.get("approvals") or [])
    tasks = list(snapshot.get("tasks") or [])
    problems = list((snapshot.get("for_human") or {}).get("Problems / Conflicts") or [])
    next_items = list((snapshot.get("for_human") or {}).get("What Matters Next") or [])

    if "decision" in q or "approval" in q or "need me" in q:
        if not approvals:
            return "Your live owner approval queue is clear."
        titles = "; ".join(str(item.get("title") or item.get("approval_key")) for item in approvals[:4])
        return f"You have {len(approvals)} live owner decision item(s): {titles}."
    if "work on next" in q or "priority" in q or "start" in q:
        due = [item for item in tasks if item.get("overdue") or item.get("due_today")]
        if due:
            item = due[0]
            return f"Start with {item.get('title') or item.get('task_id')}. It is {'overdue' if item.get('overdue') else 'due today'} in {item.get('project') or 'Dispatcher'}. Next action: {item.get('next_action') or 'review the task record and move it to an explicit next state'}."
        if next_items:
            item = next_items[0]
            return f"Next material item: {item.get('title')}. Next action: {item.get('next_action') or 'review its current implementation state'}."
        return "No due-today Dispatcher task is currently surfaced."
    if "blocker" in q or "problem" in q or "conflict" in q:
        if not problems:
            return "No active Registry problem/conflict is surfaced in the current For Human snapshot."
        first = problems[0]
        return f"There are {len(problems)} surfaced problem/conflict item(s). First: {first.get('title') or first.get('type') or first.get('id')}. {first.get('blocker') or first.get('notes') or ''}".strip()
    if "changed" in q or "yesterday" in q or "update" in q:
        changes = list((snapshot.get("for_human") or {}).get("Important Changes") or [])
        if not changes:
            return "No material implementation changes are surfaced in the current live window."
        first = changes[0]
        return f"{len(changes)} material change(s) are surfaced in the current window. Most recent: {first.get('title')} — {first.get('state')}."
    return None


def _render_dari_live(core, principal, engagement_id: str, snapshot: Mapping[str, Any]) -> None:
    counts = snapshot.get("counts") or {}
    attention = int(counts.get("approvals", 0)) + int(counts.get("tasks_overdue", 0)) + int(counts.get("reconciliation_attention", 0))
    st.markdown(
        "<section class='oc-card'><div class='oc-dari-header'><div class='oc-dari-orb'></div>"
        "<div><span class='oc-dari-title'>DARI</span><span class='oc-dari-sub'>Your AI Assistant</span></div></div>"
        f"<div class='oc-dari-copy'><strong>{base._esc(base._greeting())}, {base._esc(base._first_name(principal))}.</strong>"
        "<span>Live owner state is connected through ColettiOS.</span></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>!</div><div>{counts.get('approvals', 0)} approval(s) waiting</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>▤</div><div>{counts.get('tasks_due_today', 0)} task(s) due today · {counts.get('tasks_overdue', 0)} overdue</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>◌</div><div>{attention} attention signal(s)</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )

    quicks = [
        "What needs my decision?",
        "What should I work on next?",
        "Show production blockers",
        "What changed since yesterday?",
    ]
    qcols = st.columns(2, gap="small")
    for idx, prompt in enumerate(quicks):
        if qcols[idx % 2].button(prompt, key=f"owner-dari-quick-{idx}", use_container_width=True):
            st.session_state["_owner_dari_live_answer"] = _deterministic_dari_answer(prompt, snapshot)

    command = st.text_input(
        "Ask DARI",
        placeholder="Ask DARI a question or give a command…",
        label_visibility="collapsed",
        key="owner_dari_live_command",
    )
    if st.button("Ask DARI →", type="primary", use_container_width=True, disabled=not command.strip(), key="owner_dari_live_submit"):
        deterministic = _deterministic_dari_answer(command, snapshot)
        if deterministic is not None:
            st.session_state["_owner_dari_live_answer"] = deterministic
        else:
            client = _client(core)
            if client is None:
                st.session_state["_owner_dari_live_answer"] = "The live command router is unavailable in this session."
            else:
                try:
                    result = client.route_command(
                        principal,
                        engagement_id,
                        command,
                        context={"requested_capability": "owner_console_dari"},
                    )
                    targets = ", ".join(result.get("targets") or []) or "human routing"
                    gate = " Human approval is required before execution." if result.get("requires_human_approval") else ""
                    st.session_state["_owner_dari_live_answer"] = f"Routed through Dispatcher to {targets}. State: {result.get('routing_state', 'ROUTED')}.{gate}"
                except OwnerControlPlaneUnavailable:
                    st.session_state["_owner_dari_live_answer"] = "The private ColettiOS command router is not reachable right now."

    answer = st.session_state.get("_owner_dari_live_answer")
    if answer:
        st.info(answer)


def _render_action_center_live(principal, snapshot: Mapping[str, Any], manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    counts = snapshot.get("counts") or {}
    st.markdown("<section class='oc-card' style='margin-top:.7rem'><div class='oc-card-head'><div class='oc-card-title'>Owner Action Center</div><div class='oc-link'>Live</div></div></section>", unsafe_allow_html=True)
    actions = [
        ("✓", "Approval Queue", f"{counts.get('approvals', 0)} decision item(s)", "Approvals"),
        ("⌘", "Dispatcher", f"{counts.get('tasks_due_today', 0)} due today · {counts.get('tasks_overdue', 0)} overdue", "Dispatcher"),
        ("♙", "Team Management", "Roles, users, and administration", "Team"),
        ("$", "Financial Review", "Financial ledger remains a separate authoritative feed", "Financials"),
        ("◔", "Firm Overview", f"{counts.get('reconciliation_attention', 0)} reconciliation attention item(s)", "Firm Overview"),
    ]
    for idx, (icon, title, sub, page) in enumerate(actions):
        cols = st.columns([0.42, 2.7, 0.55], gap="small", vertical_alignment="center")
        cols[0].markdown(f"**{icon}**")
        cols[1].markdown(f"**{title}**  \n<span style='font-size:.7rem;color:#827d74'>{base._esc(sub)}</span>", unsafe_allow_html=True)
        if cols[2].button("›", key=f"owner-action-{idx}", use_container_width=True):
            _goto_owner_page(principal, page)


def _changes_since_yesterday(snapshot: Mapping[str, Any]) -> int:
    cutoff = datetime.now(LOCAL_TZ) - timedelta(days=1)
    return sum(
        1
        for item in (snapshot.get("for_human") or {}).get("Important Changes") or []
        if (_parse_time(item.get("updated_at")) or datetime.min.replace(tzinfo=LOCAL_TZ)) >= cutoff
    )


def _capacity_text(snapshot: Mapping[str, Any]) -> str:
    projects = list(snapshot.get("projects") or [])
    postures = [str(item.get("capacity_posture") or "").strip() for item in projects if str(item.get("capacity_posture") or "").strip()]
    if postures:
        return postures[0]
    return "Use the owner queue as the limiting surface: protected decisions first, then due work, then unblocked progression."


def _render_start_my_day_live(principal, snapshot: Mapping[str, Any]) -> None:
    counts = snapshot.get("counts") or {}
    changes = _changes_since_yesterday(snapshot)
    problems = len((snapshot.get("for_human") or {}).get("Problems / Conflicts") or [])
    st.markdown(
        f"<section class='oc-day'><div class='oc-kicker'>Start My Day</div><h1>{base._esc(base._greeting())}, {base._esc(base._first_name(principal))}.</h1>"
        "<div style='font-family:var(--oc-serif);font-size:1.08rem'>This brief is generated from the authoritative Dispatcher and Registry state.</div>"
        "<div class='oc-day-grid'>"
        f"<div class='oc-day-block'><strong>Since yesterday</strong><p>{changes} material implementation change(s) were recorded in the last 24 hours.</p></div>"
        f"<div class='oc-day-block'><strong>Due / decisions</strong><p>{counts.get('approvals', 0)} owner decision(s) and {counts.get('tasks_due_today', 0)} task(s) are due today.</p></div>"
        f"<div class='oc-day-block'><strong>Carryover</strong><p>{counts.get('tasks_overdue', 0)} open task(s) are overdue and should be explicitly resolved, rescheduled, or blocked.</p></div>"
        f"<div class='oc-day-block'><strong>Blockers</strong><p>{problems} Registry problem/conflict item(s), {counts.get('task_blockers', 0)} task blocker(s), and {counts.get('reconciliation_attention', 0)} reconciliation attention item(s) are surfaced.</p></div>"
        f"<div class='oc-day-block'><strong>Capacity</strong><p>{base._esc(_capacity_text(snapshot))}</p></div>"
        f"<div class='oc-day-block'><strong>Success definition</strong><p>Make the protected decisions that are actually ready, clear or explicitly disposition due work, and leave no silent blocker in today’s operating state.</p></div>"
        "</div></section>",
        unsafe_allow_html=True,
    )
    if st.button("Acknowledge & enter My Workspace →", type="primary", use_container_width=True, key="ack_start_my_day_live"):
        st.session_state[base._start_my_day_key(principal)] = True
        st.rerun()


def render_live_owner_dashboard(shell, principal, engagement_id: str, manifest: Mapping[str, Any], records: Mapping[str, Any], reports: Mapping[str, Any], core) -> None:
    snapshot, error = _live_snapshot(core, principal, engagement_id)
    if not snapshot:
        if error:
            st.caption(error)
        return base.render_owner_dashboard(shell, principal, engagement_id, manifest, records, reports, core)

    if base._needs_start_my_day(principal):
        _render_start_my_day_live(principal, snapshot)
        return

    decisions = _decision_items(snapshot)
    left, right = st.columns([4.35, 1.28], gap="medium")
    with left:
        st.markdown(
            f"<section class='oc-hero'><div class='oc-hero-copy'><div class='oc-kicker'>My Workspace</div>"
            f"<h1>{base._esc(base._greeting())}, {base._esc(base._first_name(principal))}.</h1>"
            "<div class='oc-hero-sub'>People. Process. Performance.</div>"
            "<div class='oc-hero-body'>Everything you need to move the firm forward — your work, your team, and the bigger picture, in one place.</div>"
            "</div><div class='oc-hero-art'></div><div class='oc-hero-quote'>Evidence<br>Clarity<br>People<br>Progress<br>A Stronger<br>Tomorrow</div></section>",
            unsafe_allow_html=True,
        )
        _render_live_kpis(principal, snapshot, manifest, records)
        _render_live_decisions(principal, decisions)
        _render_lower_grid_live(core, principal, engagement_id, snapshot)
    with right:
        _render_dari_live(core, principal, engagement_id, snapshot)
        _render_action_center_live(principal, snapshot, manifest, records)


def _detail_text(detail: Mapping[str, Any]) -> str:
    if not detail:
        return "No additional detail was supplied by the authoritative queue."
    ordered = []
    for key, value in detail.items():
        if value in (None, ""):
            continue
        ordered.append(f"**{str(key).replace('_', ' ').title()}:** {value}")
    return "  \n".join(ordered) or "No additional detail was supplied by the authoritative queue."


def _decision_domain_payload(item: Mapping[str, Any], decision: str, key_prefix: str) -> dict[str, Any]:
    source_type = str(item.get("source_type") or "")
    if source_type == "TASK":
        state = st.selectbox("New task state", TASK_STATES, index=3, key=f"{key_prefix}:task-state")
        blocker = st.text_input("Blocker (optional)", key=f"{key_prefix}:task-blocker")
        next_action = st.text_input("Next action (optional)", key=f"{key_prefix}:task-next")
        payload: dict[str, Any] = {"new_lifecycle_state": state}
        if blocker.strip():
            payload["blocker"] = blocker.strip()
        if next_action.strip():
            payload["next_action"] = next_action.strip()
        return payload
    if source_type == "RELEASE_MANIFEST":
        if decision == "REJECT":
            return {"release_outcome": "REJECTED"}
        if decision == "DEFER":
            return {}
        outcome = st.selectbox(
            "Release outcome",
            ("ACCEPTED", "PRODUCTION_AUTHORIZED"),
            key=f"{key_prefix}:release-outcome",
            help="Production authorization is a stronger protected action than accepting a pre-production release.",
        )
        return {"release_outcome": outcome}
    return {}


def render_live_approvals(core, principal, engagement_id: str) -> None:
    st.title("Approvals")
    st.caption("One authoritative queue for protected owner decisions. No approval is auto-executed by this screen.")
    snapshot, error = _live_snapshot(core, principal, engagement_id)
    if not snapshot:
        st.warning(error or "Live approval queue is unavailable.")
        return

    approvals = _decision_items(snapshot)
    flash = st.session_state.pop("_owner_approval_flash", None)
    if flash:
        st.success(flash)
    if not approvals:
        st.success("The owner approval queue is clear.")
        return

    focus = st.session_state.pop("_owner_focus_approval", None)
    if focus:
        approvals.sort(key=lambda item: 0 if item["approval_key"] == focus else 1)

    client = _client(core)
    for idx, item in enumerate(approvals):
        key_prefix = f"approval:{idx}:{item['approval_key']}"
        label = f"{item['title']} · {item['status']}"
        with st.expander(label, expanded=bool(focus and item["approval_key"] == focus)):
            meta1, meta2, meta3 = st.columns(3)
            meta1.metric("Owner", item["owning_domain"].replace("_", " ").title())
            meta2.metric("Current state", item["current_state"] or "Pending")
            meta3.metric("Gate", "Protected" if item["protected_gate"] else "Human")
            st.markdown(_detail_text(item["detail"]))
            st.divider()

            decision = st.radio("Decision", ("APPROVE", "REJECT", "DEFER"), horizontal=True, key=f"{key_prefix}:decision")
            reason = st.text_area("Decision reason", key=f"{key_prefix}:reason", placeholder="State the basis for this decision…")
            domain_payload = _decision_domain_payload(item, decision, key_prefix)
            confirm = False
            if item["protected_gate"] and decision == "APPROVE":
                confirm = st.checkbox(
                    "I explicitly confirm this protected human gate and authorize the source-aware write-through described above.",
                    key=f"{key_prefix}:confirm",
                )
            disabled = client is None or (item["protected_gate"] and decision == "APPROVE" and not confirm)
            if st.button("Record decision", type="primary", disabled=disabled, key=f"{key_prefix}:submit"):
                try:
                    result = client.decide(
                        principal,
                        engagement_id,
                        approval_key=item["approval_key"],
                        decision=decision,
                        reason=reason.strip() or None,
                        domain_payload=domain_payload,
                        confirm_protected_gate=confirm,
                    )
                except OwnerControlPlaneUnavailable:
                    st.error("The private owner decision service is not reachable right now.")
                else:
                    st.session_state["_owner_approval_flash"] = f"{result.get('decision', decision)} recorded for {item['title']}."
                    st.rerun()


def render_live_dispatcher(core, principal, engagement_id: str) -> None:
    st.title("Dispatcher")
    st.caption("Command, task, schedule, approval, and reconciliation state — read from the authoritative Dispatcher/Registry control plane.")
    snapshot, error = _live_snapshot(core, principal, engagement_id)
    if not snapshot:
        st.warning(error or "Live Dispatcher state is unavailable.")
        return

    counts = snapshot.get("counts") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Due today", counts.get("tasks_due_today", 0))
    c2.metric("Overdue", counts.get("tasks_overdue", 0))
    c3.metric("Approvals", counts.get("approvals", 0))
    c4.metric("Reconciliation attention", counts.get("reconciliation_attention", 0))

    with st.container(border=True):
        st.subheader("Command Dispatcher")
        command = st.text_area("Command", placeholder="Reconcile today’s priorities and show me what needs my decision.", key="dispatcher-live-command")
        protected = st.checkbox("This command may involve a protected action", key="dispatcher-live-protected")
        if st.button("Route command", type="primary", disabled=not command.strip(), key="dispatcher-live-submit"):
            client = _client(core)
            if client is None:
                st.error("Live command routing is unavailable in this session.")
            else:
                try:
                    result = client.route_command(
                        principal,
                        engagement_id,
                        command,
                        origin_domain="dispatcher",
                        context={"requested_capability": "owner_dispatcher", "protected_gate": protected},
                    )
                except OwnerControlPlaneUnavailable:
                    st.error("The private Dispatcher command router is not reachable right now.")
                else:
                    targets = ", ".join(result.get("targets") or []) or "human routing"
                    st.success(f"Command {result.get('routing_state', 'ROUTED')} → {targets}")
                    if result.get("requires_human_approval"):
                        st.warning("This command is blocked behind a human approval gate before execution.")

    tabs = st.tabs(("Tasks", "Project Control", "Calendar", "Reconciliation", "For Human"))
    with tabs[0]:
        tasks = snapshot.get("tasks") or []
        if tasks:
            st.dataframe(tasks, use_container_width=True, hide_index=True)
        else:
            st.success("No open Dispatcher tasks.")
    with tabs[1]:
        projects = snapshot.get("projects") or []
        if projects:
            st.dataframe(projects, use_container_width=True, hide_index=True)
        else:
            st.info("No project-control rows were returned.")
    with tabs[2]:
        commands = snapshot.get("calendar_commands") or []
        if commands:
            st.dataframe(commands, use_container_width=True, hide_index=True)
        else:
            st.success("No open Calendar command is waiting in Dispatcher.")
    with tabs[3]:
        reconciliations = snapshot.get("reconciliations") or []
        if reconciliations:
            st.dataframe(reconciliations, use_container_width=True, hide_index=True)
        else:
            st.info("No reconciliation runs were returned.")
    with tabs[4]:
        for_human = snapshot.get("for_human") or {}
        for section in ("Needs My Approval", "What Matters Next", "Problems / Conflicts", "Important Changes"):
            st.subheader(section)
            values = for_human.get(section) or []
            if values:
                st.dataframe(values, use_container_width=True, hide_index=True)
            else:
                st.caption("No items.")


def render_owner_page_live(original_page, shell, page: str, **kwargs) -> None:
    if page == "Approvals":
        return render_live_approvals(kwargs["core"], kwargs["principal"], kwargs["engagement_id"])
    if page == "Dispatcher":
        return render_live_dispatcher(kwargs["core"], kwargs["principal"], kwargs["engagement_id"])
    return original_page(shell, page, **kwargs)
