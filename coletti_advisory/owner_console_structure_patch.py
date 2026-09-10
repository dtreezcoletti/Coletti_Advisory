from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

import streamlit as st

from .analysis import build_summary
from .models import Role
from .owner_console_structure import (
    BACKEND_REQUIRED_PAGES,
    MORNING_CARD_TITLES,
    OPERATING_ZONES,
    OWNER_PREVIEW_OPTIONS,
    OWNER_SIDEBAR_GROUPS,
    canonical_owner_page,
)
from .publication import published_reports


def _page_key(principal) -> str:
    return f"_owner_reference_page:{principal.user_id}"


def _preview_key(principal) -> str:
    return f"_owner_nonmutating_preview:{principal.user_id}"


def _goto(principal, page: str) -> None:
    st.session_state[_page_key(principal)] = page
    st.rerun()


def _inject_structure_css() -> None:
    st.markdown(
        """
        <style>
        .oc-day-grid { grid-template-columns:repeat(4,minmax(0,1fr)) !important; }
        .oc-day-block { min-height:122px; }
        .oc-run-divider {
            display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:.8rem;
            margin:1.3rem 0 .9rem; color:#8a8174; font-size:.59rem; letter-spacing:.20em;
            text-transform:uppercase;
        }
        .oc-run-divider:before,.oc-run-divider:after { content:""; height:1px; background:#d8d0c4; }
        .oc-zone-title { font-family:var(--oc-serif); font-size:1.05rem; margin-bottom:.15rem; }
        .oc-zone-sub { font-size:.64rem; color:#807a71; margin-bottom:.55rem; }
        .oc-preview-banner {
            border:1px solid #cda96e; background:#fbf3e5; border-radius:6px; padding:.7rem .85rem;
            margin:.4rem 0 1rem; font-size:.72rem; color:#665334;
        }
        @media (max-width:1100px) { .oc-day-grid { grid-template-columns:repeat(2,minmax(0,1fr)) !important; } }
        @media (max-width:700px) { .oc-day-grid { grid-template-columns:1fr !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _structured_sidebar(owner_ui, principal, engagement_id: str) -> str:
    page_key = _page_key(principal)
    default_page = "Start My Day" if owner_ui._needs_start_my_day(principal) else "My Workspace"
    active = st.session_state.get(page_key, default_page)
    valid = {label for _group, items in OWNER_SIDEBAR_GROUPS for label, _icon in items}
    if active not in valid:
        active = default_page
        st.session_state[page_key] = active

    for group_index, (group, items) in enumerate(OWNER_SIDEBAR_GROUPS):
        if group_index:
            st.sidebar.divider()
        st.sidebar.caption(group)
        for label, icon in items:
            if st.sidebar.button(
                f"{icon}   {label}",
                key=f"owner-nav:{group}:{label}",
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


def _fallback_morning_cards(owner_ui, principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> list[tuple[str, str]]:
    summary = build_summary(dict(manifest))
    decisions = owner_ui._decision_items(manifest, records)
    real_decisions = [item for item in decisions if item.get("status") != "Clear"]
    gate = owner_ui.build_publication_gate(dict(manifest))
    return [
        ("Since Yesterday", f"Current workspace: {summary['sources']} source(s), {summary['propositions']} record statement(s), and {summary['inconsistencies']} inconsistency item(s)."),
        ("Due Today", "Dispatcher due-today data is not available in this fallback session; no due item is invented."),
        ("Decisions", f"{len(real_decisions)} owner-facing decision item(s) are surfaced from current review/publication state."),
        ("Carryover", f"{gate.get('review_required_count', 0)} review-required item(s) remain unresolved in the publication gate."),
        ("Blockers", f"{summary['inconsistencies']} inconsistency item(s) are recorded; unresolved items remain explicit until reviewed."),
        ("Capacity", "Use the owner queue as the limiting surface: protected decisions first, then due work, then unblocked case progression."),
        ("Success Definition", "Make ready decisions, explicitly disposition blocked work, and leave no silent ambiguity in the operating record."),
    ]


def _live_morning_cards(owner_live_ui, snapshot: Mapping[str, Any]) -> list[tuple[str, str]]:
    counts = snapshot.get("counts") or {}
    changes = owner_live_ui._changes_since_yesterday(snapshot)
    problems = len((snapshot.get("for_human") or {}).get("Problems / Conflicts") or [])
    return [
        ("Since Yesterday", f"{changes} material implementation change(s) were recorded in the last 24 hours."),
        ("Due Today", f"{counts.get('tasks_due_today', 0)} Dispatcher task(s) are due today."),
        ("Decisions", f"{counts.get('approvals', 0)} owner decision(s) are waiting for review."),
        ("Carryover", f"{counts.get('tasks_overdue', 0)} open task(s) are overdue and need an explicit disposition."),
        ("Blockers", f"{problems} Registry conflict item(s), {counts.get('task_blockers', 0)} task blocker(s), and {counts.get('reconciliation_attention', 0)} reconciliation attention item(s) are surfaced."),
        ("Capacity", owner_live_ui._capacity_text(snapshot)),
        ("Success Definition", "Make the protected decisions that are actually ready, clear or explicitly disposition due work, and leave no silent blocker in today’s operating state."),
    ]


def _render_morning(owner_ui, principal, cards: list[tuple[str, str]], *, start_page: bool) -> None:
    # Contract guard: the execution zone must contain exactly the seven approved cards in order.
    if tuple(title for title, _body in cards) != MORNING_CARD_TITLES:
        raise RuntimeError("Owner morning brief structure drifted from the approved seven-card contract")

    blocks = "".join(
        f"<div class='oc-day-block'><strong>{owner_ui._esc(title)}</strong><p>{owner_ui._esc(body)}</p></div>"
        for title, body in cards
    )
    st.markdown(
        f"<section class='oc-day'><div class='oc-kicker'>{'Start My Day' if start_page else 'My Workspace'}</div>"
        f"<h1>{owner_ui._esc(owner_ui._greeting())}, {owner_ui._esc(owner_ui._first_name(principal))}.</h1>"
        "<div style='font-family:var(--oc-serif);font-size:1.08rem'>What needs me today.</div>"
        f"<div class='oc-day-grid'>{blocks}</div></section>",
        unsafe_allow_html=True,
    )

    if start_page:
        if st.button("Acknowledge & enter My Workspace →", type="primary", use_container_width=True, key="ack_start_my_day_structured"):
            st.session_state[owner_ui._start_my_day_key(principal)] = True
            st.session_state[_page_key(principal)] = "My Workspace"
            st.rerun()


def _render_operating_zones(principal) -> None:
    st.markdown("<div class='oc-run-divider'><span></span><span>Run the company</span><span></span></div>", unsafe_allow_html=True)
    for zone_name, destinations in OPERATING_ZONES:
        with st.container(border=True):
            st.markdown(f"<div class='oc-zone-title'>{zone_name}</div>", unsafe_allow_html=True)
            if zone_name == "Start My Day":
                st.markdown("<div class='oc-zone-sub'>Daily execution, decisions, and signals.</div>", unsafe_allow_html=True)
            elif zone_name == "Back Office":
                st.markdown("<div class='oc-zone-sub'>Administrative operating work sits below the daily execution zone by design.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='oc-zone-sub'>Open a connected operating surface.</div>", unsafe_allow_html=True)
            columns = st.columns(min(3, len(destinations)))
            for idx, destination in enumerate(destinations):
                if columns[idx % len(columns)].button(
                    destination,
                    key=f"owner-zone:{zone_name}:{destination}",
                    use_container_width=True,
                ):
                    _goto(principal, destination)


def _render_structured_workspace(owner_ui, owner_live_ui, principal, manifest, records, core, *, start_page: bool) -> None:
    _inject_structure_css()
    snapshot, _error = owner_live_ui._live_snapshot(core, principal, next(iter(principal.engagement_ids), ""))
    if snapshot:
        cards = _live_morning_cards(owner_live_ui, snapshot)
    else:
        cards = _fallback_morning_cards(owner_ui, principal, manifest, records)
    _render_morning(owner_ui, principal, cards, start_page=start_page)
    _render_operating_zones(principal)


def _render_notifications(owner_notifications, principal, core, engagement_id: str) -> None:
    st.title("Notifications")
    st.caption("Personal owner signals projected from authoritative Dispatcher and Registry state.")
    snapshot = owner_notifications._snapshot(core, principal, engagement_id)
    items = owner_notifications.build_owner_notifications(snapshot) if snapshot else []
    if not items:
        st.info("No live owner notification is available in this session.")
        return
    for idx, item in enumerate(items):
        with st.container(border=True):
            left, right = st.columns([4, 1], vertical_alignment="center")
            left.markdown(f"**{item['kind']} · {item['title']}**")
            left.caption(item["detail"])
            target = {"Approvals": "Decisions"}.get(item["target"], item["target"])
            if right.button("Open", key=f"owner-notification-page:{idx}", use_container_width=True):
                _goto(principal, target)


def _render_records_hub(original_render, shell, **kwargs) -> None:
    st.title("Records")
    st.caption("One records workspace: intake/registration and records intelligence stay connected to the same selected case.")
    mode = st.radio("Records workspace", ("Ingest Records", "Review Records"), horizontal=True, label_visibility="collapsed", key="owner-records-mode")
    if mode == "Ingest Records":
        original_render(shell, "Record Ingestion", **kwargs)
    else:
        original_render(shell, "Evidence", **kwargs)


def _render_backend_surface(principal, page: str, message: str) -> None:
    st.title(page)
    st.info(message)
    st.caption("The Owner Console surface is wired and intentionally does not fabricate an authoritative backend.")
    related = {
        "Referrals": ("Clients",),
        "Billing": ("Finance",),
        "Contracts": ("Documents", "Docket"),
        "Pricing": ("Finance",),
        "Documents": ("Knowledge", "Docket"),
        "Capacity": ("Team", "Dispatcher"),
        "Assignments": ("Team", "Dispatcher"),
        "Docket": ("Knowledge", "System Health"),
        "Implementation": ("Dispatcher", "System Health"),
        "Fix Center": ("System Health", "System Lab"),
        "Integrations": ("System Health", "System Lab"),
        "Deployments": ("System Health", "System Lab"),
    }.get(page, ())
    if related:
        cols = st.columns(len(related))
        for idx, target in enumerate(related):
            if cols[idx].button(f"Open {target}", key=f"backend-surface:{page}:{target}", use_container_width=True):
                _goto(principal, target)


def _render_dari_page(owner_live_ui, owner_runtime, principal, engagement_id: str, manifest, records, core) -> None:
    st.title("DARI")
    snapshot, _error = owner_live_ui._live_snapshot(core, principal, engagement_id)
    if snapshot:
        owner_live_ui._render_dari_live(core, principal, engagement_id, snapshot)
        return
    owner_runtime.render_owner_dari(
        principal,
        engagement_id,
        owner_runtime.owner_ui._decision_items(manifest, records),
        manifest,
    )


def _render_system_health(owner_page_integration, principal) -> None:
    st.title("System Health")
    st.caption("Owner-facing integration truth: connected surfaces are distinguished from backend-required surfaces.")
    owner_page_integration._integration_health()
    if st.button("Open System Lab", key="system-health-open-lab", type="primary"):
        _goto(principal, "System Lab")


def _render_nonmutating_preview(shell, owner_ui, principal, engagement_id: str, manifest, records, reports, preview: str) -> None:
    st.markdown(
        f"<div class='oc-preview-banner'><strong>READ-ONLY OWNER PREVIEW · View as {owner_ui._esc(preview)}</strong><br>"
        "Your authenticated Owner principal has not changed. This preview does not call role-impersonation or protected write actions.</div>",
        unsafe_allow_html=True,
    )
    if st.button("Return to Owner", key="owner-preview-return", use_container_width=True):
        st.session_state[_preview_key(principal)] = "Owner"
        st.rerun()

    if preview == "Client":
        st.caption("Client dashboard presentation using data already authorized to the Owner account; mutation controls are omitted from preview mode.")
        shell._client_dashboard(principal, engagement_id, manifest, records)
    else:
        st.caption(f"{preview} dashboard presentation using Owner-authorized data; administrative/write controls are omitted from preview mode.")
        shell._employee_dashboard(principal, engagement_id, manifest, records, reports)


def _patch_profile_preview(profile_menu_patch) -> None:
    original = profile_menu_patch.render_profile_menu
    if getattr(original, "_owner_preview_wrapped", False):
        return

    def wrapped(principal, **kwargs):
        original(principal, **kwargs)
        if principal.role != Role.OWNER or not principal.authenticated:
            return
        with st.popover("View as…  ▾", use_container_width=True):
            st.markdown("### Owner preview")
            st.caption("Controlled presentation preview only. Your Owner identity and permissions are not replaced or delegated.")
            key = _preview_key(principal)
            current = st.session_state.get(key, "Owner")
            if current not in OWNER_PREVIEW_OPTIONS:
                current = "Owner"
                st.session_state[key] = current
            st.selectbox("Preview experience", OWNER_PREVIEW_OPTIONS, index=OWNER_PREVIEW_OPTIONS.index(current), key=key)
            st.info("Client / Employee / Admin previews are non-mutating. Return to Owner to perform authorized actions.")

    wrapped._owner_preview_wrapped = True
    profile_menu_patch.render_profile_menu = wrapped


def patch_owner_console_structure(
    owner_ui,
    owner_live_ui,
    owner_runtime,
    owner_notifications,
    owner_page_integration,
    profile_menu_patch,
) -> None:
    """Install the approved Owner Console information architecture."""
    if getattr(owner_runtime, "_approved_owner_structure_patched", False):
        return

    _patch_profile_preview(profile_menu_patch)

    def sidebar(shell, principal, engagement_id: str) -> str:
        return _structured_sidebar(owner_ui, principal, engagement_id)

    owner_ui._owner_sidebar = sidebar
    owner_runtime._owner_sidebar = sidebar

    def structured_dashboard(shell, principal, engagement_id, manifest, records, reports, core):
        _render_structured_workspace(owner_ui, owner_live_ui, principal, manifest, records, core, start_page=False)

    owner_ui.render_owner_dashboard = structured_dashboard
    owner_live_ui.render_live_owner_dashboard = structured_dashboard
    owner_runtime.render_live_owner_dashboard = structured_dashboard

    original_render = owner_runtime._render_owner_page

    def render(shell, page: str, **kwargs):
        principal = kwargs["principal"]
        preview = st.session_state.get(_preview_key(principal), "Owner")
        if principal.role == Role.OWNER and principal.authenticated and preview != "Owner":
            return _render_nonmutating_preview(
                shell,
                owner_ui,
                principal,
                kwargs["engagement_id"],
                kwargs["manifest"],
                kwargs["records"],
                kwargs["reports"],
                preview,
            )

        if page == "Start My Day":
            return _render_structured_workspace(
                owner_ui,
                owner_live_ui,
                principal,
                kwargs["manifest"],
                kwargs["records"],
                kwargs["core"],
                start_page=True,
            )
        if page == "My Workspace":
            return structured_dashboard(
                shell,
                principal,
                kwargs["engagement_id"],
                kwargs["manifest"],
                kwargs["records"],
                kwargs["reports"],
                kwargs["core"],
            )
        if page == "Notifications":
            return _render_notifications(owner_notifications, principal, kwargs["core"], kwargs["engagement_id"])
        if page == "Records":
            return _render_records_hub(original_render, shell, **kwargs)
        if page == "DARI":
            return _render_dari_page(
                owner_live_ui,
                owner_runtime,
                principal,
                kwargs["engagement_id"],
                kwargs["manifest"],
                kwargs["records"],
                kwargs["core"],
            )
        if page == "System Health":
            return _render_system_health(owner_page_integration, principal)
        if page in BACKEND_REQUIRED_PAGES:
            return _render_backend_surface(principal, page, BACKEND_REQUIRED_PAGES[page])

        canonical = canonical_owner_page(page)
        return original_render(shell, canonical, **kwargs)

    owner_runtime._render_owner_page = render
    owner_runtime._approved_owner_structure_patched = True
