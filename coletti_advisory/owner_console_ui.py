from __future__ import annotations

import html
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Mapping

import streamlit as st

from .analysis import build_analytical_issues, build_summary
from .mobile_mvp import prepare_dari_command
from .models import Permission
from .publication import PublicationStatus, published_reports
from .reporting import build_publication_gate
from .workspaces import workspace_environment, workspace_label
from .owner_console_style import OWNER_MAIN_NAV, OWNER_CONTROL_NAV


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _local_now() -> datetime:
    return datetime.now(ZoneInfo("America/Chicago"))


def _first_name(principal) -> str:
    name = (principal.display_name or "there").strip().split()[0]
    return "Owner" if name.lower() == "synthetic" else name


def _initials(principal) -> str:
    parts = [p for p in (principal.display_name or "Owner").split() if p]
    if not parts:
        return "OC"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _greeting() -> str:
    hour = _local_now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _owner_sidebar(shell, principal, engagement_id: str) -> str:
    page_key = f"_owner_reference_page:{principal.user_id}"
    active = st.session_state.get(page_key, "My Workspace")

    st.sidebar.caption("MY WORKSPACE")
    for label, icon in OWNER_MAIN_NAV:
        if st.sidebar.button(
            f"{icon}   {label}",
            key=f"owner-nav-main:{label}",
            type="primary" if active == label else "secondary",
            use_container_width=True,
        ):
            st.session_state[page_key] = label
            st.rerun()

    st.sidebar.divider()
    st.sidebar.caption("OWNER CONTROLS")
    for label, icon in OWNER_CONTROL_NAV:
        if st.sidebar.button(
            f"{icon}   {label}",
            key=f"owner-nav-control:{label}",
            type="primary" if active == label else "secondary",
            use_container_width=True,
        ):
            st.session_state[page_key] = label
            st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown(
        "<div style='font-family:var(--oc-serif);font-size:.8rem;line-height:1.35;color:#5f5c55;padding:.35rem .35rem .15rem'>"
        "A higher standard for a more confident tomorrow.</div>",
        unsafe_allow_html=True,
    )
    return active


def _owner_topbar(principal, manifest: Mapping[str, Any], engagement_ids: tuple[str, ...] | list[str]) -> None:
    left, search_col, profile = st.columns([1.25, 2.2, 1.25], gap="small", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='oc-topbrand'><strong>ColettiOS</strong><span>Owner Console</span></div>",
            unsafe_allow_html=True,
        )
    with search_col:
        st.markdown("<div class='oc-search-shell'>", unsafe_allow_html=True)
        query = st.text_input(
            "Search",
            placeholder="Search cases, clients, documents, team members, or help…",
            label_visibility="collapsed",
            key="owner_reference_search",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with profile:
        st.markdown(
            f"<div class='oc-profile'><span class='oc-bell'>●</span><div class='oc-avatar'>{_esc(_initials(principal))}</div>"
            f"<div class='oc-profile-copy'><strong>{_esc(principal.display_name)}</strong><span>Owner</span></div></div>",
            unsafe_allow_html=True,
        )

    query = query.strip().lower()
    if not query:
        return

    matches: list[str] = []
    for eid in engagement_ids:
        label = workspace_label(eid)
        if query in eid.lower() or query in label.lower():
            matches.append(f"Case · {label} · {eid}")
    for source in (manifest.get("sources") or {}).values():
        meta = source.get("metadata") or {}
        filename = str(meta.get("filename") or source.get("source_id") or "")
        classification = str(meta.get("classification") or "")
        if query in filename.lower() or query in classification.lower():
            matches.append(f"Document · {filename}")
        if len(matches) >= 8:
            break
    if matches:
        with st.expander(f"Search results · {len(matches)}", expanded=True):
            for match in matches[:8]:
                st.write(match)
    else:
        st.caption("No match in the currently authorized Streamlit workspace data.")


def _decision_items(manifest: Mapping[str, Any], records: Mapping[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for report_name, record in records.items():
        status = getattr(record, "status", None)
        if status == PublicationStatus.IN_REVIEW:
            items.append(
                {
                    "icon": "▤",
                    "title": str(report_name).replace("_", " ").title(),
                    "kind": "Report sign-off",
                    "status": "Ready for Approval",
                    "tone": "warn",
                    "time": "Now",
                }
            )
        elif status == PublicationStatus.APPROVED:
            items.append(
                {
                    "icon": "◫",
                    "title": str(report_name).replace("_", " ").title(),
                    "kind": "Publication decision",
                    "status": "Needs Approval",
                    "tone": "alert",
                    "time": "Now",
                }
            )

    contradictions = manifest.get("contradictions") or {}
    for key in list(contradictions.keys())[:3]:
        items.append(
            {
                "icon": "!",
                "title": f"Contradiction {key}",
                "kind": "Human review",
                "status": "Requires Review",
                "tone": "alert",
                "time": "Open",
            }
        )

    if not items:
        items.append(
            {
                "icon": "✓",
                "title": "No protected owner decision is currently recorded",
                "kind": "Current workspace",
                "status": "Clear",
                "tone": "ok",
                "time": "Current",
            }
        )
    return items[:5]


def _kpis(principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> list[tuple[str, str, str, str]]:
    gate = build_publication_gate(dict(manifest))
    in_review = sum(1 for record in records.values() if getattr(record, "status", None) == PublicationStatus.IN_REVIEW)
    approved = sum(1 for record in records.values() if getattr(record, "status", None) == PublicationStatus.APPROVED)
    return [
        ("✓", str(gate.get("review_required_count", 0)), "My Approvals", "Human decisions required"),
        ("▤", str(len(build_analytical_issues(dict(manifest)))), "Pending Reviews", "Human review queue"),
        ("▣", str(len(principal.engagement_ids)), "Active Cases", "Authorized workspaces"),
        ("⌁", str(in_review + approved), "Reports Awaiting Sign-off", "Review / publication gate"),
    ]


def _render_kpis(items: list[tuple[str, str, str, str]]) -> None:
    cards = []
    for icon, value, label, sub in items:
        cards.append(
            f"<div class='oc-kpi'><div class='oc-kpi-row'><div class='oc-kpi-icon'>{_esc(icon)}</div>"
            f"<div><div class='oc-kpi-value'>{_esc(value)}</div><div class='oc-kpi-label'>{_esc(label)}</div>"
            f"<div class='oc-kpi-sub'>{_esc(sub)}</div></div></div></div>"
        )
    st.markdown(f"<div class='oc-kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _render_decisions(items: list[dict[str, str]]) -> None:
    rows = []
    for item in items:
        rows.append(
            "<div class='oc-row'>"
            f"<div class='oc-row-icon'>{_esc(item['icon'])}</div>"
            f"<div class='oc-row-title'>{_esc(item['title'])}</div>"
            f"<div class='oc-row-sub'>{_esc(item['kind'])}</div>"
            f"<div class='oc-status {_esc(item['tone'])}'>{_esc(item['status'])}</div>"
            f"<div class='oc-time'>{_esc(item['time'])}</div>"
            "</div>"
        )
    st.markdown(
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>Needs Your Decision</div>"
        "<div class='oc-tabs'><span>All</span><span>Reports</span><span>Publications</span><span>Client Requests</span></div>"
        "<div class='oc-link'>View All →</div></div>"
        + "".join(rows)
        + "</section>",
        unsafe_allow_html=True,
    )


def _manifest_stage(manifest: Mapping[str, Any]) -> tuple[str, str]:
    sources = len(manifest.get("sources") or {})
    propositions = len(manifest.get("propositions") or {})
    contradictions = len(manifest.get("contradictions") or {})
    if contradictions:
        return "Human Review", "High"
    if propositions:
        return "Analysis", "Normal"
    if sources:
        return "Evidence", "Normal"
    return "Intake", "Low"


def _case_rows(core, principal, selected_engagement: str) -> str:
    rows = []
    for eid in list(principal.engagement_ids)[:6]:
        try:
            manifest = core.manifest(eid)
        except Exception:
            manifest = {}
        stage, priority = _manifest_stage(manifest)
        badge = "alert" if priority == "High" else ("ok" if priority == "Low" else "warn")
        rows.append(
            "<div class='oc-mini-row'><div>"
            f"<div class='oc-mini-title'>{_esc(workspace_label(eid))}</div>"
            f"<div class='oc-mini-sub'>{_esc(eid)} · {_esc(stage)} · <span class='oc-status {badge}'>{_esc(priority)}</span></div>"
            f"</div><div class='oc-mini-meta'>{'Current' if eid == selected_engagement else 'Authorized'}</div></div>"
        )
    if not rows:
        rows.append("<div class='oc-mini-row'><div class='oc-mini-title'>No authorized cases</div></div>")
    return "".join(rows)


def _task_rows(decisions: list[dict[str, str]]) -> str:
    rows = []
    for item in decisions[:4]:
        rows.append(
            "<div class='oc-mini-row'><div>"
            f"<div class='oc-mini-title'>{_esc(item['title'])}</div>"
            f"<div class='oc-mini-sub'>{_esc(item['kind'])}</div></div>"
            f"<div class='oc-mini-meta'>{_esc(item['time'])}</div></div>"
        )
    return "".join(rows)


def _activity_rows(manifest: Mapping[str, Any]) -> str:
    audit = list(manifest.get("audit_log") or [])[-4:]
    rows: list[str] = []
    for entry in reversed(audit):
        if isinstance(entry, Mapping):
            title = entry.get("action") or entry.get("event") or entry.get("type") or "Workspace activity"
            sub = entry.get("actor") or entry.get("user_id") or entry.get("subject_id") or "Audit record"
            when = entry.get("timestamp") or entry.get("created_at") or entry.get("at") or "Recorded"
        else:
            title, sub, when = str(entry), "Audit record", "Recorded"
        rows.append(
            "<div class='oc-mini-row'><div>"
            f"<div class='oc-mini-title'>{_esc(title)}</div>"
            f"<div class='oc-mini-sub'>{_esc(sub)}</div></div>"
            f"<div class='oc-mini-meta'>{_esc(str(when)[:16])}</div></div>"
        )
    if not rows:
        rows.append(
            "<div class='oc-mini-row'><div><div class='oc-mini-title'>No recent durable activity in this manifest</div>"
            "<div class='oc-mini-sub'>Activity will appear here when the audit log records it.</div></div><div class='oc-mini-meta'>Current</div></div>"
        )
    return "".join(rows)


def _render_lower_grid(core, principal, engagement_id: str, manifest: Mapping[str, Any], decisions: list[dict[str, str]]) -> None:
    st.markdown(
        "<div class='oc-three'>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>My Cases</div><div class='oc-link'>View All →</div></div>"
        + _case_rows(core, principal, engagement_id)
        + "</section>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>My Tasks</div><div class='oc-link'>Today</div></div>"
        + _task_rows(decisions)
        + "</section>"
        "<section class='oc-card'><div class='oc-card-head'><div class='oc-card-title'>Recent Activity</div><div class='oc-link'>View All →</div></div>"
        + _activity_rows(manifest)
        + "</section></div>",
        unsafe_allow_html=True,
    )


def _dari_queue(principal, engagement_id: str) -> list[dict[str, Any]]:
    queues = st.session_state.setdefault("_desktop_dari_command_queues", {})
    return queues.setdefault(f"{principal.user_id}:{engagement_id}", [])


def _render_dari(principal, engagement_id: str, decisions: list[dict[str, str]], manifest: Mapping[str, Any]) -> None:
    contradictions = len(manifest.get("contradictions") or {})
    st.markdown(
        "<section class='oc-card'><div class='oc-dari-header'><div class='oc-dari-orb'></div>"
        "<div><span class='oc-dari-title'>DARI</span><span class='oc-dari-sub'>Your AI Assistant</span></div></div>"
        f"<div class='oc-dari-copy'><strong>{_esc(_greeting())}, {_esc(_first_name(principal))}.</strong>"
        "<span>Here are a few things that need your attention.</span></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>!</div><div>{len(decisions)} decision item(s) surfaced</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>⌁</div><div>{contradictions} recorded contradiction(s)</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>▣</div><div>{len(principal.engagement_ids)} authorized case workspace(s)</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )
    command = st.text_input(
        "Ask DARI",
        placeholder="Ask DARI a question…",
        label_visibility="collapsed",
        key="owner_dari_command",
    )
    if st.button("Ask DARI →", type="primary", use_container_width=True, disabled=not command.strip(), key="owner_dari_submit"):
        envelope = prepare_dari_command(
            principal,
            engagement_id,
            command,
            case_id=engagement_id,
            protected_action=False,
        )
        _dari_queue(principal, engagement_id).append(asdict(envelope))
        st.success("DARI command staged for the authorized backend.")


def _render_action_center(decisions: list[dict[str, str]], manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    contradictions = len(manifest.get("contradictions") or {})
    published = len(published_reports(dict(records)))
    actions = [
        ("✓", "Approval Queue", f"{len(decisions)} surfaced decision item(s)"),
        ("⌘", "Dispatcher", "Command / scheduling authority remains separately controlled"),
        ("♙", "Team Management", "Administration and role controls"),
        ("$", "Financial Review", "Financial ledger feed not connected to this Streamlit surface"),
        ("◔", "Firm Overview", f"{contradictions} contradiction(s) · {published} published report(s)"),
    ]
    rows = []
    for icon, title, sub in actions:
        rows.append(
            "<div class='oc-action-row'>"
            f"<div class='oc-action-icon'>{_esc(icon)}</div><div><div class='oc-action-title'>{_esc(title)}</div>"
            f"<div class='oc-action-sub'>{_esc(sub)}</div></div><div class='oc-chevron'>›</div></div>"
        )
    st.markdown(
        "<section class='oc-card' style='margin-top:.7rem'><div class='oc-card-head'><div class='oc-card-title'>Owner Action Center</div>"
        "<div class='oc-link'>View All →</div></div>" + "".join(rows) + "</section>",
        unsafe_allow_html=True,
    )


def _start_my_day_key(principal) -> str:
    return f"_start_my_day_ack:{principal.user_id}:{_local_now().date().isoformat()}"


def _needs_start_my_day(principal) -> bool:
    now = _local_now()
    return now.weekday() < 5 and 5 <= now.hour < 13 and not st.session_state.get(_start_my_day_key(principal), False)


def _render_start_my_day(principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    decisions = _decision_items(manifest, records)
    summary = build_summary(dict(manifest))
    gate = build_publication_gate(dict(manifest))
    st.markdown(
        f"<section class='oc-day'><div class='oc-kicker'>Start My Day</div><h1>{_esc(_greeting())}, {_esc(_first_name(principal))}.</h1>"
        "<div style='font-family:var(--oc-serif);font-size:1.08rem'>Review what changed, what needs you, and what a successful day looks like.</div>"
        "<div class='oc-day-grid'>"
        f"<div class='oc-day-block'><strong>Since yesterday</strong><p>{summary['sources']} source(s), {summary['propositions']} proposition(s), and {summary['inconsistencies']} inconsistency item(s) are currently recorded in this workspace.</p></div>"
        f"<div class='oc-day-block'><strong>Due / decisions</strong><p>{len(decisions)} owner-facing decision item(s) are surfaced from the current review and publication state.</p></div>"
        f"<div class='oc-day-block'><strong>Carryover</strong><p>{gate.get('review_required_count', 0)} review-required item(s) remain unresolved in the publication gate.</p></div>"
        f"<div class='oc-day-block'><strong>Blockers</strong><p>{summary['inconsistencies']} inconsistency item(s) are recorded. Dispatcher and Calendar due-today feeds remain separate until their controlled integration is activated.</p></div>"
        "<div class='oc-day-block'><strong>Capacity</strong><p>Use the owner queue as the limiting work surface: protected decisions first, then reviews, then case progression.</p></div>"
        "<div class='oc-day-block'><strong>Success definition</strong><p>Clear the protected decisions that are actually ready, move blocked items to an explicit next action, and leave no silent ambiguity in the record.</p></div>"
        "</div></section>",
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("Acknowledge & enter My Workspace →", type="primary", use_container_width=True, key="ack_start_my_day"):
        st.session_state[_start_my_day_key(principal)] = True
        st.rerun()


def render_owner_dashboard(shell, principal, engagement_id: str, manifest: Mapping[str, Any], records: Mapping[str, Any], reports: Mapping[str, Any], core) -> None:
    if _needs_start_my_day(principal):
        _render_start_my_day(principal, manifest, records)
        return

    decisions = _decision_items(manifest, records)
    left, right = st.columns([4.35, 1.28], gap="medium")
    with left:
        st.markdown(
            f"<section class='oc-hero'><div class='oc-hero-copy'><div class='oc-kicker'>My Workspace</div>"
            f"<h1>{_esc(_greeting())}, {_esc(_first_name(principal))}.</h1>"
            "<div class='oc-hero-sub'>People. Process. Performance.</div>"
            "<div class='oc-hero-body'>Everything you need to move the firm forward — your work, your team, and the bigger picture, in one place.</div>"
            "</div><div class='oc-hero-art'></div><div class='oc-hero-quote'>Evidence<br>Clarity<br>People<br>Progress<br>A Stronger<br>Tomorrow</div></section>",
            unsafe_allow_html=True,
        )
        _render_kpis(_kpis(principal, manifest, records))
        _render_decisions(decisions)
        _render_lower_grid(core, principal, engagement_id, manifest, decisions)
    with right:
        _render_dari(principal, engagement_id, decisions, manifest)
        _render_action_center(decisions, manifest, records)


def _render_clients(principal) -> None:
    st.title("Clients")
    st.caption("Authorized client/case workspaces visible to this owner account.")
    rows = [{"Workspace": workspace_label(eid), "ID": eid, "Environment": workspace_environment(eid)} for eid in principal.engagement_ids]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_owner_messages() -> None:
    st.title("Messages")
    st.info("The reference owner surface is in place. Durable inbound/outbound communications are not yet connected to this Streamlit workspace.")
    st.caption("No synthetic client message is shown as real communication.")


def _render_knowledge_base() -> None:
    st.title("Knowledge Base")
    st.markdown("**Operating method** · source-traceable reconstruction → contradiction review → human judgment → controlled publication")
    st.markdown("**Evidence principle** · no proposition without a source; no silent promotion of unresolved material.")
    st.markdown("**Publication principle** · human review and approval remain mandatory before client publication.")


def _render_dispatcher() -> None:
    st.title("Dispatcher")
    st.info("Dispatcher is the governing operational control plane. This Streamlit owner surface does not create a second scheduling or execution authority.")
    st.caption("The visual command surface is reserved here; live cross-system execution remains subject to the controlled Dispatcher integration path.")


def _render_financials() -> None:
    st.title("Financials")
    st.info("The owner navigation and visual surface are ready, but no authoritative financial ledger is connected to this Streamlit deployment yet.")
    st.caption("Financial values are intentionally not fabricated for presentation.")


def _render_firm_overview(core, principal) -> None:
    st.title("Firm Overview")
    total_sources = total_propositions = total_inconsistencies = 0
    rows = []
    for eid in principal.engagement_ids:
        try:
            manifest = core.manifest(eid)
        except Exception:
            manifest = {}
        summary = build_summary(manifest)
        total_sources += summary["sources"]
        total_propositions += summary["propositions"]
        total_inconsistencies += summary["inconsistencies"]
        rows.append({"Case": workspace_label(eid), "Sources": summary["sources"], "Propositions": summary["propositions"], "Inconsistencies": summary["inconsistencies"]})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Authorized cases", len(principal.engagement_ids))
    c2.metric("Sources", total_sources)
    c3.metric("Propositions", total_propositions)
    c4.metric("Inconsistencies", total_inconsistencies)
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_owner_settings(shell, app_mode: str, storage_backend: str, core_backend: str, manifest: Mapping[str, Any], principal, engagement_id: str) -> None:
    shell._render_administration(app_mode, storage_backend, core_backend, dict(manifest), principal)
    st.divider()
    if st.button("Open System Lab", use_container_width=True, key="open_system_lab"):
        st.session_state[f"_owner_reference_page:{principal.user_id}"] = "System Lab"
        st.rerun()


def _render_owner_page(shell, page: str, *, principal, engagement_id: str, manifest: Mapping[str, Any], records: Mapping[str, Any], reports: Mapping[str, Any], core, storage, publication_store, app_mode: str, storage_backend: str, core_backend: str) -> None:
    if page == "My Workspace":
        render_owner_dashboard(shell, principal, engagement_id, manifest, records, reports, core)
    elif page == "Case Queue":
        shell._render_engagements(principal)
    elif page == "Evidence":
        shell.legacy._render_evidence_workspace(principal=principal, engagement_id=engagement_id, core=core, manifest=dict(manifest))
    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        shell.app._render_analysis(dict(manifest))
    elif page in {"Human Review", "Approvals"}:
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        shell.app._render_review_center(dict(manifest), dict(reports), dict(records), publication_store, principal, engagement_id)
    elif page == "Reports":
        shell.app._render_internal_reports(dict(manifest), dict(reports), dict(records))
    elif page == "Clients":
        _render_clients(principal)
    elif page == "Messages":
        _render_owner_messages()
    elif page == "Knowledge Base":
        _render_knowledge_base()
    elif page == "Dispatcher":
        _render_dispatcher()
    elif page == "Team":
        shell._render_administration(app_mode, storage_backend, core_backend, dict(manifest), principal)
    elif page == "Financials":
        _render_financials()
    elif page == "Firm Overview":
        _render_firm_overview(core, principal)
    elif page == "Settings":
        _render_owner_settings(shell, app_mode, storage_backend, core_backend, manifest, principal, engagement_id)
    elif page == "System Lab":
        shell.render_system_lab(principal=principal, manifest=dict(manifest), app_mode=app_mode, storage_backend=storage_backend, core_backend=core_backend, engagement_id=engagement_id)
    else:
        st.error("Unknown owner page.")

