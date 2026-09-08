from __future__ import annotations

import html
from datetime import date, datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import streamlit as st

from .analysis import build_analytical_issues, build_summary
from .models import Permission, Role
from .publication import published_reports
from .reporting import build_publication_gate
from .workspaces import live_workspace_gate_errors, workspace_environment, workspace_label


CENTRAL_TIME = ZoneInfo("America/Chicago")
PRIMARY_DARI_COMMANDS = (
    "What needs my decision?",
    "What should I work on next?",
    "Find anything",
)
SECONDARY_DARI_COMMANDS = (
    "Show production blockers",
    "Continue where I left off",
)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _first_name(display_name: str | None) -> str:
    value = (display_name or "there").strip()
    return value.split()[0] if value else "there"


def _local_now() -> datetime:
    return datetime.now(CENTRAL_TIME)


def _ack_key(principal, day: date | None = None) -> str:
    day = day or _local_now().date()
    user_key = getattr(principal, "user_id", None) or getattr(principal, "email", None) or "internal-user"
    return f"cc_start_my_day_ack::{user_key}::{day.isoformat()}"


def _is_internal(principal) -> bool:
    return principal.role not in {Role.CLIENT, Role.READ_ONLY}


def classify_dari_command(command: str) -> str:
    text = (command or "").strip().lower()
    if not text:
        return "empty"
    if "decision" in text or "approval" in text:
        return "decisions"
    if "work on next" in text or "next priority" in text or text == "next":
        return "next"
    if text.startswith("find") or "search" in text or "look up" in text:
        return "find"
    if "blocker" in text or "production" in text and "block" in text:
        return "blockers"
    if "continue" in text or "left off" in text or "resume" in text:
        return "continue"
    return "general"


def _status_value(record: Any) -> str:
    status = getattr(record, "status", "")
    return str(getattr(status, "value", status)).lower()


def _audit_event_label(row: Any) -> str:
    if isinstance(row, dict):
        for key in ("message", "event", "action", "event_type", "type", "operation"):
            value = row.get(key)
            if value:
                return str(value)
        for key in ("source_id", "record_id", "id"):
            value = row.get(key)
            if value:
                return f"Updated {value}"
        return "Workspace record updated"
    return str(row)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _collect_due_today(value: Any, today: date, *, limit: int = 12) -> list[str]:
    found: list[str] = []
    due_keys = ("due_date", "due_at", "deadline", "deadline_at", "scheduled_for")
    label_keys = ("title", "name", "task", "description", "label", "case_id", "source_id", "id")

    def visit(node: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            due_value = next((node.get(key) for key in due_keys if node.get(key)), None)
            if _parse_date(due_value) == today:
                label = next((node.get(key) for key in label_keys if node.get(key)), "Scheduled item")
                label_text = str(label)
                if label_text not in found:
                    found.append(label_text)
            for child in node.values():
                visit(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child)

    visit(value)
    return found


def build_start_my_day_brief(
    *,
    manifest: dict,
    records: dict,
    reports: dict,
    gate_errors: Iterable[str] = (),
    owner: bool = False,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or _local_now().date()
    summary = build_summary(manifest)
    gate = build_publication_gate(manifest)
    issues = build_analytical_issues(manifest)
    audit = list(manifest.get("audit_log") or [])
    recent = [_audit_event_label(row) for row in audit[-5:]]
    explicit_due = _collect_due_today(manifest, today)

    review_count = int(gate.get("review_required_count") or 0)
    published_count = len(published_reports(records))
    draft_count = len(reports)
    unresolved_count = len(issues)

    decisions: list[str] = []
    if review_count:
        decisions.append(f"{review_count} item(s) require human review before they can advance.")
    waiting_statuses = [
        _status_value(record)
        for record in records.values()
        if _status_value(record) in {"draft", "in_review", "approved"}
    ]
    if waiting_statuses:
        decisions.append(f"{len(waiting_statuses)} report publication record(s) remain inside the human approval path.")
    if owner and not decisions:
        decisions.append("No owner-only approval is deterministically pending in the connected workspace data.")
    elif not owner and not decisions:
        decisions.append("No explicit human-review decision is pending in the connected workspace data.")

    blockers = list(gate_errors)
    if unresolved_count:
        blockers.append(f"{unresolved_count} analytical issue(s) remain unresolved or require review.")
    if not blockers:
        blockers.append("No deterministic production blocker is visible in the connected workspace data.")

    if not recent:
        recent = ["No prior-day audit entries are available in this workspace yet."]

    if not explicit_due:
        explicit_due = [
            "No explicit due-date record is connected for today. Dispatcher/Calendar due-today wiring is still required for a complete cross-system brief."
        ]

    success = (
        f"Advance {workspace_label(manifest.get('engagement_id', 'current workspace'))} by clearing the highest-priority review or blocker without bypassing a human gate."
        if manifest.get("engagement_id")
        else "Clear the highest-priority review or blocker and leave the workspace in a verified, handoff-ready state."
    )

    return {
        "recent": recent,
        "due_today": explicit_due,
        "decisions": decisions,
        "blockers": blockers,
        "capacity": "Capacity signal is not inferred here until the protected Chapter 2 / Dispatcher capacity adapter is connected.",
        "success": success,
        "sources": int(summary.get("sources") or 0),
        "inconsistencies": int(summary.get("inconsistencies") or 0),
        "review_required": review_count,
        "draft_reports": draft_count,
        "published_reports": published_count,
    }


def _inject_workspace_css() -> None:
    st.markdown(
        """
        <style>
        .cc-v2-page { max-width: 1260px; margin: 0 auto; }
        .cc-v2-kicker { color:#a16f28; text-transform:uppercase; letter-spacing:.24em; font-size:.66rem; font-weight:700; }
        .cc-v2-heading { font-family:Georgia,'Times New Roman',serif; font-size:clamp(2.3rem,4vw,4.7rem); font-weight:500; letter-spacing:-.035em; line-height:.98; margin:.35rem 0 .5rem; color:#181a1b; }
        .cc-v2-sub { color:#74716b; font-size:.96rem; line-height:1.55; }
        .cc-v2-card { background:#fff; border:1px solid #e8e1d7; border-radius:16px; box-shadow:0 12px 36px rgba(35,31,25,.055); padding:1.15rem 1.2rem; }
        .cc-v2-card h3 { margin:.05rem 0 .55rem !important; }
        .cc-v2-dari { background:linear-gradient(135deg,#fff 0%,#fbf7ef 64%,#f5ead7 100%); border:1px solid #e3d3bb; border-radius:20px; box-shadow:0 18px 48px rgba(95,69,31,.08); padding:1.35rem; margin:.85rem 0 1.15rem; position:relative; overflow:hidden; }
        .cc-v2-dari:after { content:'DARI'; position:absolute; right:1rem; top:.7rem; color:rgba(159,111,40,.10); font-family:Georgia,'Times New Roman',serif; font-size:4.2rem; letter-spacing:.08em; }
        .cc-v2-dari-title { font-family:Georgia,'Times New Roman',serif; font-size:1.55rem; margin-bottom:.2rem; position:relative; z-index:1; }
        .cc-v2-dari-sub { color:#77726b; font-size:.82rem; position:relative; z-index:1; max-width:720px; }
        .cc-v2-section-label { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:1.35rem 0 .55rem; }
        .cc-v2-section-title { font-family:Georgia,'Times New Roman',serif; font-size:1.35rem; }
        .cc-v2-section-note { color:#8a857d; font-size:.72rem; }
        .cc-v2-list { display:grid; gap:.55rem; }
        .cc-v2-row { display:grid; grid-template-columns:34px minmax(0,1fr) auto; gap:.7rem; align-items:center; padding:.72rem 0; border-bottom:1px solid #f0ece5; }
        .cc-v2-row:last-child { border-bottom:0; }
        .cc-v2-icon { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f4ecdf; color:#9b6c2b; font-weight:700; }
        .cc-v2-row-title { font-weight:700; font-size:.84rem; }
        .cc-v2-row-sub { color:#87827a; font-size:.72rem; margin-top:.12rem; }
        .cc-v2-badge { font-size:.66rem; padding:.27rem .55rem; border-radius:999px; background:#edf3ef; color:#50725f; white-space:nowrap; }
        .cc-v2-owner { border-left:3px solid #b88435; background:#fffdf9; }
        .cc-v2-answer { border-left:3px solid #b88435; background:#fff; padding:.85rem 1rem; border-radius:0 10px 10px 0; margin:.75rem 0; color:#383a39; }
        .cc-v2-start-grid { display:grid; grid-template-columns:1.05fr .95fr; gap:1rem; margin:1rem 0; }
        .cc-v2-start-card { min-height:180px; }
        .cc-v2-start-card ul { margin:.55rem 0 0 1.05rem; padding:0; }
        .cc-v2-start-card li { margin:.38rem 0; color:#55534f; line-height:1.4; }
        .cc-v2-mobile-dock { display:none; }
        @media (max-width: 800px) {
          .cc-v2-start-grid { grid-template-columns:1fr; }
          .cc-v2-heading { font-size:2.6rem; }
          .cc-v2-dari { border-radius:16px; padding:1.05rem; }
          .cc-v2-dari:after { font-size:3.2rem; }
          .cc-v2-mobile-dock { display:flex; position:fixed; left:10px; right:10px; bottom:10px; z-index:9999; background:rgba(255,253,248,.96); backdrop-filter:blur(16px); border:1px solid #e4d9c8; border-radius:20px; box-shadow:0 16px 50px rgba(30,25,18,.16); align-items:flex-end; justify-content:space-around; padding:.5rem .3rem calc(.5rem + env(safe-area-inset-bottom)); }
          .cc-v2-mobile-dock a { flex:1; text-decoration:none; text-align:center; color:#69645d; font-size:.62rem; line-height:1.15; padding:.2rem; }
          .cc-v2-mobile-dock a span { display:block; font-size:1.05rem; margin-bottom:.18rem; }
          .cc-v2-mobile-dock a.cc-v2-dari-button { color:#fff; background:linear-gradient(180deg,#b98437,#95631f); width:58px; min-width:58px; max-width:58px; height:58px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; margin-top:-24px; box-shadow:0 8px 22px rgba(149,99,31,.28); }
          .cc-v2-mobile-dock a.cc-v2-dari-button span { margin:0; font-size:1.15rem; }
          .block-container { padding-bottom:6.5rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_mobile_dock(owner: bool) -> None:
    more_anchor = "owner-control" if owner else "continue-work"
    st.markdown(
        f"""
        <nav class="cc-v2-mobile-dock" aria-label="Mobile workspace shortcuts">
          <a href="#workspace-home"><span>⌂</span>Home</a>
          <a href="#continue-work"><span>▦</span>Work</a>
          <a class="cc-v2-dari-button" href="#dari"><span>✦</span>DARI</a>
          <a href="#decisions"><span>✓</span>Decisions</a>
          <a href="#{more_anchor}"><span>•••</span>More</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def _render_start_my_day(shell, principal, engagement_id: str, manifest: dict, records: dict, reports: dict, gate_errors: list[str]) -> None:
    _inject_workspace_css()
    now = _local_now()
    owner = principal.role == Role.OWNER
    brief = build_start_my_day_brief(
        manifest=manifest,
        records=records,
        reports=reports,
        gate_errors=gate_errors,
        owner=owner,
        today=now.date(),
    )
    role = "Owner" if owner else principal.role.value.replace("_", " ").title()
    first = _first_name(principal.display_name)

    st.markdown("<div id='workspace-home' class='cc-v2-page'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='cc-v2-kicker'>Start My Day · {now.strftime('%A, %B %-d')}</div>"
        f"<div class='cc-v2-heading'>Good morning, {_esc(first)}.</div>"
        f"<div class='cc-v2-sub'>Your daily execution brief is ready. Review the handoff from yesterday, today's obligations, decisions, blockers, capacity, and the definition of a successful day before entering the workspace.</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"{principal.display_name} · {role} · {workspace_label(engagement_id)}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources", brief["sources"])
    c2.metric("Review required", brief["review_required"])
    c3.metric("Inconsistencies", brief["inconsistencies"])
    c4.metric("Draft reports", brief["draft_reports"])

    def card(title: str, items: list[str]) -> str:
        lis = "".join(f"<li>{_esc(item)}</li>" for item in items)
        return f"<section class='cc-v2-card cc-v2-start-card'><h3>{_esc(title)}</h3><ul>{lis}</ul></section>"

    st.markdown(
        "<div class='cc-v2-start-grid'>"
        + card("Update from yesterday", brief["recent"])
        + card("Everything due today", brief["due_today"])
        + card("Decisions & approvals", brief["decisions"])
        + card("Blockers & dependency warnings", brief["blockers"])
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<section class='cc-v2-card'><h3>Capacity & success definition</h3>"
        f"<p class='cc-v2-sub'>{_esc(brief['capacity'])}</p>"
        f"<p><strong>Today is successful when:</strong> {_esc(brief['success'])}</p></section>",
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("Acknowledge brief & enter workspace", type="primary", use_container_width=True):
        st.session_state[_ack_key(principal, now.date())] = True
        st.session_state["cc_navigation"] = "Dashboard"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _recent_sources(manifest: dict, limit: int = 3) -> list[dict[str, str]]:
    sources = list((manifest.get("sources") or {}).values())[-limit:]
    rows: list[dict[str, str]] = []
    for source in reversed(sources):
        meta = source.get("metadata") or {}
        rows.append(
            {
                "id": str(source.get("source_id") or "Source"),
                "name": str(meta.get("filename") or meta.get("title") or source.get("source_id") or "Source record"),
                "kind": str(meta.get("classification") or "Record"),
            }
        )
    return rows


def _dari_answer(command: str, *, engagement_id: str, manifest: dict, records: dict, reports: dict, gate_errors: list[str], owner: bool) -> str:
    kind = classify_dari_command(command)
    gate = build_publication_gate(manifest)
    issues = build_analytical_issues(manifest)
    review_count = int(gate.get("review_required_count") or 0)
    recent = _recent_sources(manifest, 5)

    if kind == "empty":
        return "Ask DARI about decisions, next work, a client/case/source, production blockers, or where you left off."
    if kind == "decisions":
        if review_count:
            return f"There are {review_count} item(s) requiring human review in {workspace_label(engagement_id)}. Publication remains gated; DARI will not bypass that decision path."
        return "No explicit review decision is pending in the connected workspace data right now."
    if kind == "next":
        if review_count:
            return f"Work the human-review queue first: {review_count} item(s) are blocking advancement."
        if issues:
            return f"Resolve the analytical issue queue next. {len(issues)} issue(s) are currently surfaced."
        if recent:
            return f"Continue from the most recent source: {recent[0]['name']}."
        return "There is no deterministic queued work in this engagement yet. Secure intake is the next available step."
    if kind == "blockers":
        blockers = list(gate_errors)
        if issues:
            blockers.append(f"{len(issues)} analytical issue(s) remain surfaced.")
        if blockers:
            return "Current blocker signal: " + " ".join(blockers[:4])
        return "No deterministic production blocker is visible in the connected workspace data."
    if kind == "continue":
        if recent:
            return f"Resume {workspace_label(engagement_id)} from {recent[0]['name']}. The current report bundle contains {len(reports)} draft report(s)."
        return f"Resume {workspace_label(engagement_id)} from its dashboard; no recent source is available yet."
    if kind == "find":
        text = command.strip()
        term = text[4:].strip(" :") if text.lower().startswith("find") else ""
        if not term or term.lower() == "anything":
            return "Type an identifier, client/case label, source ID, or filename after Find. DARI's deterministic lookup path will search the current authorized workspace first."
        needle = term.lower()
        matches = []
        if needle in engagement_id.lower() or needle in workspace_label(engagement_id).lower():
            matches.append(workspace_label(engagement_id))
        for row in recent:
            if needle in row["id"].lower() or needle in row["name"].lower():
                matches.append(f"{row['id']} · {row['name']}")
        if matches:
            return "Found: " + "; ".join(matches[:5])
        return f"No match for '{term}' was found in the currently loaded authorized workspace. Cross-client registry lookup remains a separate governed lookup path."
    return "DARI chat entry is active in deterministic mode. The next wiring step is provider-routed reasoning for commands that cannot be answered safely from system state alone."


def _render_command_buttons() -> str | None:
    selected: str | None = None
    primary = st.columns(3)
    for idx, command in enumerate(PRIMARY_DARI_COMMANDS):
        if primary[idx].button(command, key=f"cc_dari_primary_{idx}", use_container_width=True):
            selected = command
    secondary = st.columns(2)
    for idx, command in enumerate(SECONDARY_DARI_COMMANDS):
        if secondary[idx].button(command, key=f"cc_dari_secondary_{idx}", use_container_width=True):
            selected = command
    return selected


def _render_internal_workspace(shell, principal, engagement_id: str, manifest: dict, records: dict, reports: dict, app_mode: str, storage_backend: str, core_backend: str) -> None:
    _inject_workspace_css()
    owner = principal.role == Role.OWNER
    now = _local_now()
    first = _first_name(principal.display_name)
    gate = build_publication_gate(manifest)
    issues = build_analytical_issues(manifest)
    summary = build_summary(manifest)
    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    review_count = int(gate.get("review_required_count") or 0)
    recent = _recent_sources(manifest, 3)

    st.markdown("<div id='workspace-home' class='cc-v2-page'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='cc-v2-kicker'>{'Owner' if owner else 'Team'} Workspace · {now.strftime('%A')}</div>"
        f"<div class='cc-v2-heading'>Good morning, {_esc(first)}.</div>"
        f"<div class='cc-v2-sub'>DARI is your primary operating surface. Ask for a decision, the next priority, a case or source, a blocker, or the work you were last touching.</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<section id='dari' class='cc-v2-dari'><div class='cc-v2-dari-title'>Ask DARI</div>"
        "<div class='cc-v2-dari-sub'>Search and command ColettiOS from one place. Deterministic system state is used before any generated reasoning path.</div></section>",
        unsafe_allow_html=True,
    )

    chosen = _render_command_buttons()
    with st.form("cc_dari_command_form", clear_on_submit=True):
        typed = st.text_input(
            "DARI command",
            placeholder="Find C26-92, what needs my decision, show production blockers…",
            label_visibility="collapsed",
        )
        asked = st.form_submit_button("Ask DARI", type="primary", use_container_width=True)
    if chosen:
        st.session_state["cc_dari_last_command"] = chosen
    if asked and typed.strip():
        st.session_state["cc_dari_last_command"] = typed.strip()
    active_command = st.session_state.get("cc_dari_last_command")
    if active_command:
        answer = _dari_answer(
            active_command,
            engagement_id=engagement_id,
            manifest=manifest,
            records=records,
            reports=reports,
            gate_errors=list(gate_errors),
            owner=owner,
        )
        st.markdown(
            f"<div class='cc-v2-answer'><strong>DARI</strong><br>{_esc(answer)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div id='decisions' class='cc-v2-section-label'><div class='cc-v2-section-title'>"
        + ("Needs Your Decision" if owner else "Needs Your Review")
        + "</div><div class='cc-v2-section-note'>Action before analytics</div></div>",
        unsafe_allow_html=True,
    )
    d1, d2, d3 = st.columns(3)
    d1.metric("Human review", review_count)
    d2.metric("Analytical issues", len(issues))
    d3.metric("Draft reports", len(reports))
    if review_count == 0 and not issues:
        st.success("No immediate deterministic review decision is waiting in this engagement.")
    else:
        st.caption("Human review and publication controls remain authoritative. DARI may surface the queue but cannot approve or publish for you.")

    st.markdown(
        "<div id='continue-work' class='cc-v2-section-label'><div class='cc-v2-section-title'>Continue Working</div><div class='cc-v2-section-note'>Resume context instead of hunting for it</div></div>",
        unsafe_allow_html=True,
    )
    work_cols = st.columns(3)
    work_cols[0].markdown(
        f"<div class='cc-v2-card'><div class='cc-v2-kicker'>Current workspace</div><h3>{_esc(workspace_label(engagement_id))}</h3><div class='cc-v2-sub'>{_esc(workspace_environment(engagement_id))} · active</div></div>",
        unsafe_allow_html=True,
    )
    if recent:
        work_cols[1].markdown(
            f"<div class='cc-v2-card'><div class='cc-v2-kicker'>Recent source</div><h3>{_esc(recent[0]['name'])}</h3><div class='cc-v2-sub'>{_esc(recent[0]['id'])} · {_esc(recent[0]['kind'])}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        work_cols[1].markdown("<div class='cc-v2-card'><div class='cc-v2-kicker'>Recent source</div><h3>No recent source</h3><div class='cc-v2-sub'>Secure intake is ready when authorized.</div></div>", unsafe_allow_html=True)
    work_cols[2].markdown(
        f"<div class='cc-v2-card'><div class='cc-v2-kicker'>Reports</div><h3>{len(reports)} draft · {len(published_reports(records))} published</h3><div class='cc-v2-sub'>Controlled publication path</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='cc-v2-section-label'><div class='cc-v2-section-title'>Workspace Pulse</div><div class='cc-v2-section-note'>Context, not the primary operating surface</div></div>", unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Sources", int(summary.get("sources") or 0))
    p2.metric("Propositions", int(summary.get("propositions") or 0))
    p3.metric("Inconsistencies", int(summary.get("inconsistencies") or 0))
    p4.metric("Published", len(published_reports(records)))

    if owner:
        st.markdown("<div id='owner-control' class='cc-v2-section-label'><div class='cc-v2-section-title'>Owner Control</div><div class='cc-v2-section-note'>Employee workspace + owner powers</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='cc-v2-card cc-v2-owner'><strong>Owner capabilities are layered on this same workspace.</strong><div class='cc-v2-sub'>System Lab, administration/security, publication controls, production readiness, and firm-level oversight stay available without replacing your normal employee workflow.</div></div>", unsafe_allow_html=True)
        o1, o2, o3 = st.columns(3)
        if o1.button("Open System Lab", use_container_width=True):
            st.session_state["cc_nav_request"] = "System Lab"
            st.rerun()
        if o2.button("Administration & Security", use_container_width=True):
            st.session_state["cc_nav_request"] = "Administration"
            st.rerun()
        if o3.button("Open Review Center", use_container_width=True):
            st.session_state["cc_nav_request"] = "Review Center"
            st.rerun()
        st.caption(f"Runtime: {app_mode.upper()} · Storage: {storage_backend} · Core adapter: {core_backend}")

    _render_mobile_dock(owner)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_topbar(principal, experience: str) -> None:
    if experience == "client":
        title = "Client Portal"
        role = principal.role.value.replace("_", " ").title()
    else:
        title = "Coletti Workspace"
        role = "Owner" if principal.role == Role.OWNER else principal.role.value.replace("_", " ").title()
    st.markdown(
        f"<div class='cc-topline'><div class='cc-topline-title'>{_esc(title)}</div>"
        f"<div class='cc-pill'>{_esc(principal.display_name)} &nbsp;·&nbsp; {_esc(role)}</div></div>",
        unsafe_allow_html=True,
    )


def _run_v2(shell) -> None:
    st.set_page_config(
        page_title="Coletti & Co. | Workspace",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    shell._apply_brand_theme()

    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = shell.app._runtime()
    shell._sidebar_brand()
    shell._sidebar_identity(principal, principal.engagement_ids[0])
    engagement_id = shell._select_engagement(principal)

    experience = shell._experience(principal)
    manifest = core.manifest(engagement_id)
    internal_user = experience in {"employee", "owner"}
    reports = shell.app.build_report_bundle(manifest) if internal_user else {}
    records = shell.app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = shell.app.sync_drafts(records, reports)
        shell.app._save_publication_records(publication_store, principal, engagement_id, records)

    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )

    if principal.authenticated and internal_user and not st.session_state.get(_ack_key(principal), False):
        if principal.authenticated:
            st.sidebar.divider()
            if st.sidebar.button("Log out", use_container_width=True, key="cc_start_day_logout"):
                st.logout()
        _render_topbar(principal, experience)
        _render_start_my_day(shell, principal, engagement_id, manifest, records, reports, list(gate_errors))
        return

    if gate_errors:
        st.error("Coletti & Co. Live is configured but locked until the production gate is open.")
        for error in gate_errors:
            st.write(f"• {error}")
        return

    pages = shell._visible_pages(principal)
    requested = st.session_state.pop("cc_nav_request", None)
    if requested in pages:
        st.session_state["cc_navigation"] = requested
    if st.session_state.get("cc_navigation") not in pages:
        st.session_state["cc_navigation"] = "Dashboard"

    def nav_label(value: str) -> str:
        if internal_user and value == "Dashboard":
            return "✦   DARI Workspace"
        return f"{shell._PAGE_ICONS.get(value, '•')}   {value}"

    page = st.sidebar.radio(
        "Navigation",
        pages,
        format_func=nav_label,
        label_visibility="collapsed",
        key="cc_navigation",
    )
    if principal.authenticated:
        st.sidebar.divider()
        if st.sidebar.button("Log out", use_container_width=True, key="cc_workspace_logout"):
            st.logout()

    _render_topbar(principal, experience)

    if page == "Dashboard":
        if experience == "client":
            shell._client_dashboard(principal, engagement_id, manifest, records)
        else:
            _render_internal_workspace(
                shell,
                principal,
                engagement_id,
                manifest,
                records,
                reports,
                app_mode,
                storage_backend,
                core_backend,
            )
    elif page == "My Case":
        shell._render_client_case(engagement_id, manifest, records)
    elif page == "Upload Documents":
        shell.legacy._render_secure_intake(app_mode=app_mode, principal=principal, engagement_id=engagement_id, storage=storage, core=core)
    elif page == "Requests & To-Do":
        shell._render_client_requests()
    elif page == "Progress":
        st.title("Progress")
        shell._progress_panel(records, manifest)
        st.caption("Progress is deliberately client-safe and does not expose internal review notes or draft conclusions.")
    elif page == "Messages":
        shell._render_client_messages()
    elif page == "My Account":
        shell._render_account(principal, engagement_id)
    elif page == "Help & Support":
        shell._render_help()
    elif page == "Engagements":
        shell._render_engagements(principal)
    elif page == "Secure Intake":
        shell.legacy._render_secure_intake(app_mode=app_mode, principal=principal, engagement_id=engagement_id, storage=storage, core=core)
    elif page == "Evidence":
        shell.legacy._render_evidence_workspace(principal=principal, engagement_id=engagement_id, core=core, manifest=manifest)
    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            return
        shell.app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)
    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            return
        shell.app._render_analysis(manifest)
    elif page == "Reports":
        if internal_user:
            shell.app._render_internal_reports(manifest, reports, records)
        else:
            shell.app._render_client_reports(records)
    elif page == "System Lab":
        if principal.role != Role.OWNER:
            st.error("System Lab is owner-only.")
            return
        shell.render_system_lab(
            principal=principal,
            manifest=manifest,
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
            engagement_id=engagement_id,
        )
    elif page == "Administration":
        shell._render_administration(app_mode, storage_backend, core_backend, manifest, principal)


def patch_workspace_v2(experience_shell) -> None:
    """Install the DARI-first unified internal workspace without changing core evidence or authorization rules."""
    experience_shell._topbar = _render_topbar
    experience_shell.run = lambda: _run_v2(experience_shell)
