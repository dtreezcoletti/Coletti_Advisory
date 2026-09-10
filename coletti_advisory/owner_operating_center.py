from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

import streamlit as st

from .analysis import build_analytical_issues, build_summary
from .mobile_mvp import prepare_dari_command
from .models import Permission, Role
from .publication import PublicationStatus, published_reports
from .reporting import build_publication_gate
from .workspaces import workspace_environment, workspace_label


OWNER_NAV_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("TODAY", (("Start My Day", "☀"), ("My Workspace", "⌂"), ("Decisions", "✓"), ("Notifications", "●"))),
    ("BUSINESS", (("Clients", "♙"), ("Cases", "▣"), ("Records", "◇"), ("Reports", "▤"), ("Referrals", "↗"), ("Communications", "◫"))),
    ("BACK OFFICE", (("Finance", "$"), ("Billing", "¤"), ("Contracts", "§"), ("Pricing", "⌁"), ("Documents", "▱"))),
    ("PEOPLE", (("Team", "♙"), ("Capacity", "◔"), ("Assignments", "⇄"), ("Access", "⌘"))),
    ("CONTROL", (("DARI", "◉"), ("Dispatcher", "⌘"), ("Knowledge", "◧"), ("Docket", "▦"), ("Implementation", "✓"), ("System Health", "◈"))),
    ("BUILD & FIX", (("Fix Center", "⚒"), ("Integrations", "∞"), ("Deployments", "⇧"), ("System Lab", "◈"))),
)

START_DAY_CARDS = (
    "Since Yesterday",
    "Due Today",
    "Decisions",
    "Carryover",
    "Blockers",
    "Capacity",
    "Success Definition",
)

OPERATING_ZONES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Start My Day", "☀", ("overnight changes", "today's priorities", "approvals and decisions", "blockers", "overdue work", "team/case issues", "cash/billing alerts", "contracts awaiting action", "system problems", "success definition")),
    ("Business Operations", "▣", ("clients", "cases", "intake", "records", "analysis/reconciliation", "human review", "reports", "publication", "referrals", "client communications")),
    ("Back Office", "$", ("finances", "revenue", "expenses", "invoices", "payments", "receivables", "billing", "pricing", "contracts", "proposals", "engagement agreements", "templates", "vendors", "subscriptions", "insurance", "tax/accounting handoff", "company documents")),
    ("People & Administration", "♙", ("employees", "assignments", "workload", "permissions", "onboarding", "training", "performance", "capacity", "admin teams", "individual case progress", "scheduling", "staff policies")),
    ("Company Control", "⌘", ("DARI", "Dispatcher", "Constitution", "Judiciary / Docket", "Knowledge", "Implementation Matrix", "policies", "Executive Orders", "approvals", "system health", "integrations", "security", "backups", "deployment state", "production blockers")),
    ("Build & Fix", "⚒", ("broken", "degraded", "incomplete", "policy drift", "failed tests", "needs approval", "auto-repairable", "code change", "database change", "human decision")),
)

OWNER_OPERATING_CENTER_CSS = r"""
<style>
.oc-exec-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.62rem;margin:.8rem 0 .9rem;}
.oc-exec-card {background:var(--oc-card);border:1px solid var(--oc-line);border-radius:6px;padding:.82rem .86rem;min-height:108px;box-shadow:var(--oc-shadow);}
.oc-exec-card strong {display:block;font-family:var(--oc-serif);font-size:.92rem;font-weight:400;margin-bottom:.35rem;}
.oc-exec-card span {font-size:.64rem;line-height:1.45;color:var(--oc-muted);}
.oc-zone-divider {display:flex;align-items:center;gap:.8rem;margin:1.15rem 0 .85rem;color:#9b7845;text-transform:uppercase;letter-spacing:.26em;font-size:.57rem;font-weight:700;}
.oc-zone-divider:before,.oc-zone-divider:after {content:"";height:1px;background:linear-gradient(90deg,transparent,#b79056);flex:1;}
.oc-zone-divider:after {background:linear-gradient(90deg,#b79056,transparent);}
.oc-zone-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin-bottom:1rem;}
.oc-zone {background:#fffefa;border:1px solid var(--oc-line);border-radius:6px;padding:.9rem;box-shadow:var(--oc-shadow);min-height:190px;}
.oc-zone-head {display:flex;align-items:center;gap:.55rem;margin-bottom:.55rem;}
.oc-zone-icon {width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--oc-gold-soft);color:var(--oc-gold-deep);font-size:.74rem;}
.oc-zone-title {font-family:var(--oc-serif);font-size:1rem;}
.oc-zone-items {font-size:.63rem;color:#747168;line-height:1.58;}
.oc-zone-items span:not(:last-child):after {content:" · ";color:#b18a52;}
.oc-preview-banner {border:1px solid #d5c6ae;background:#faf4e8;padding:.65rem .8rem;border-radius:6px;margin:.35rem 0 .8rem;font-size:.66rem;color:#6b6257;}
.oc-health-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin:.7rem 0;}
.oc-health-card {background:#fffefa;border:1px solid var(--oc-line);border-radius:6px;padding:.75rem;}
.oc-health-card strong {display:block;font-family:var(--oc-serif);font-size:1.1rem;font-weight:400;}
.oc-health-card span {font-size:.61rem;color:var(--oc-muted);}
@media (max-width:1100px){.oc-exec-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.oc-zone-grid{grid-template-columns:1fr 1fr;}.oc-health-grid{grid-template-columns:1fr 1fr;}}
@media (max-width:720px){.oc-exec-grid,.oc-zone-grid,.oc-health-grid{grid-template-columns:1fr;}}
</style>
"""


def _safe_summary(manifest: Mapping[str, Any]) -> dict[str, int]:
    try:
        return build_summary(dict(manifest))
    except Exception:
        return {"sources": 0, "propositions": 0, "inconsistencies": 0}


def _decision_count(records: Mapping[str, Any], manifest: Mapping[str, Any]) -> int:
    review = sum(1 for record in records.values() if getattr(record, "status", None) in {PublicationStatus.IN_REVIEW, PublicationStatus.APPROVED})
    return review + len(manifest.get("contradictions") or {})


def _start_day_values(principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> dict[str, str]:
    summary = _safe_summary(manifest)
    gate = build_publication_gate(dict(manifest))
    decisions = _decision_count(records, manifest)
    contradictions = summary.get("inconsistencies", 0)
    return {
        "Since Yesterday": f"{summary.get('sources', 0)} source(s), {summary.get('propositions', 0)} proposition(s), {contradictions} inconsistency item(s) are currently recorded.",
        "Due Today": "Dispatcher/Calendar due-today feed will populate here when the controlled integration is active; no due items are fabricated.",
        "Decisions": f"{decisions} owner decision/review item(s) are currently surfaced.",
        "Carryover": f"{gate.get('review_required_count', 0)} review-required item(s) remain open in the publication gate.",
        "Blockers": f"{contradictions} inconsistency item(s) are recorded; unresolved protected actions remain human-gated.",
        "Capacity": f"{len(principal.engagement_ids)} authorized case workspace(s). Use protected decisions first, then review, then case progression.",
        "Success Definition": "Clear ready decisions, assign explicit next actions to blocked work, and leave no silent ambiguity in the record.",
    }


def _render_execution_cards(principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    values = _start_day_values(principal, manifest, records)
    html = "".join(
        f"<div class='oc-exec-card'><strong>{title}</strong><span>{values[title]}</span></div>"
        for title in START_DAY_CARDS
    )
    st.markdown(f"<div class='oc-exec-grid'>{html}</div>", unsafe_allow_html=True)


def _render_operating_zones() -> None:
    cards = []
    for title, icon, items in OPERATING_ZONES:
        item_html = "".join(f"<span>{item}</span>" for item in items)
        cards.append(
            f"<section class='oc-zone'><div class='oc-zone-head'><div class='oc-zone-icon'>{icon}</div>"
            f"<div class='oc-zone-title'>{title}</div></div><div class='oc-zone-items'>{item_html}</div></section>"
        )
    st.markdown("<div class='oc-zone-divider'>Run the Business</div>" + f"<div class='oc-zone-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _render_preview_selector(principal) -> str:
    if not principal.authenticated or principal.role != Role.OWNER:
        return "Owner"
    options = ["Owner", "Client", "Employee", "Admin"]
    selected = st.sidebar.selectbox(
        "Preview interface",
        options,
        key=f"_owner_preview_interface:{principal.user_id}",
        help="Read-only owner preview. This does not impersonate another user or change authorization.",
    )
    if selected != "Owner":
        st.sidebar.caption(f"Preview only · {selected} interface · owner authority unchanged")
    return selected


def _render_preview_banner(selected: str) -> None:
    if selected == "Owner":
        return
    st.markdown(
        f"<div class='oc-preview-banner'><strong>Read-only {selected} preview</strong> · You remain authenticated as Owner. "
        "This view does not change the principal, role, permissions, case memberships, or publication authority.</div>",
        unsafe_allow_html=True,
    )


def grouped_owner_sidebar(shell, principal, engagement_id: str) -> str:
    page_key = f"_owner_reference_page:{principal.user_id}"
    active = st.session_state.get(page_key, "My Workspace")
    for group, items in OWNER_NAV_GROUPS:
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
    _render_preview_selector(principal)
    st.sidebar.markdown(
        "<div style='font-family:var(--oc-serif);font-size:.8rem;line-height:1.35;color:#5f5c55;padding:.55rem .35rem .15rem'>"
        "A higher standard for a more confident tomorrow.</div>",
        unsafe_allow_html=True,
    )
    return active


def render_owner_operating_dashboard(base, principal, engagement_id: str, manifest: Mapping[str, Any], records: Mapping[str, Any], reports: Mapping[str, Any], core) -> None:
    st.markdown(OWNER_OPERATING_CENTER_CSS, unsafe_allow_html=True)
    selected_preview = st.session_state.get(f"_owner_preview_interface:{principal.user_id}", "Owner")
    _render_preview_banner(selected_preview)
    st.markdown(
        f"<section class='oc-hero'><div class='oc-hero-copy'><div class='oc-kicker'>Owner Console · Full Access</div>"
        f"<h1>{base._esc(base._greeting())}, {base._esc(base._first_name(principal))}.</h1>"
        "<div class='oc-hero-sub'>What needs you today.</div>"
        "<div class='oc-hero-body'>Decisions, continuity, capacity, back office, people, company control, and repair work in one operating surface.</div>"
        "</div><div class='oc-hero-art'></div><div class='oc-hero-quote'>Records<br>Clarity<br>People<br>Process<br>Forward</div></section>",
        unsafe_allow_html=True,
    )
    _render_execution_cards(principal, manifest, records)
    _render_operating_zones()
    decisions = base._decision_items(manifest, records)
    left, right = st.columns([4.35, 1.28], gap="medium")
    with left:
        base._render_decisions(decisions)
        base._render_lower_grid(core, principal, engagement_id, manifest, decisions)
    with right:
        base._render_dari(principal, engagement_id, decisions, manifest)
        base._render_action_center(decisions, manifest, records)


def render_start_my_day(base, principal, manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    st.markdown(OWNER_OPERATING_CENTER_CSS, unsafe_allow_html=True)
    st.markdown(
        f"<section class='oc-day'><div class='oc-kicker'>Start My Day</div><h1>{base._esc(base._greeting())}, {base._esc(base._first_name(principal))}.</h1>"
        "<div style='font-family:var(--oc-serif);font-size:1.08rem'>Review what changed, what is due, what needs your decision, and what a successful day looks like.</div></section>",
        unsafe_allow_html=True,
    )
    _render_execution_cards(principal, manifest, records)


def _render_finance(base) -> None:
    st.title("Finance")
    st.caption("Owner back office · cash, revenue, expenses, receivables, profitability, and planning.")
    st.info("Supabase now has protected owner/admin back-office tables for expenses, vendors, subscriptions, invoices, and payments. The Streamlit owner runtime still needs its authenticated Supabase adapter before live values can be rendered here without fabrication.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", "Not connected")
    c2.metric("Revenue", "Not connected")
    c3.metric("Receivables", "Not connected")
    c4.metric("Expenses", "Not connected")


def _render_billing() -> None:
    st.title("Billing")
    st.caption("Invoices, payments, receivables, overdue balances, and payment follow-up.")
    st.info("Authoritative invoice/payment tables exist in Supabase. This owner surface will remain blank rather than invent billing values until the runtime adapter is connected.")


def _render_contracts(principal) -> None:
    st.title("Contracts")
    st.caption("Draft → review → owner approval → execution. AI drafting never equals approval.")
    contract_type = st.selectbox("Document type", ["Client engagement agreement", "Referral agreement", "Contractor agreement", "Vendor agreement", "NDA", "Internal policy", "Custom document"], key="owner_contract_type")
    title = st.text_input("Working title", key="owner_contract_title")
    draft = st.text_area("Draft workspace", height=280, key="owner_contract_draft", placeholder="Draft content stays a working draft until reviewed and approved.")
    if st.button("Stage working draft", type="primary", disabled=not title.strip() or not draft.strip(), key="owner_contract_stage"):
        queue = st.session_state.setdefault("_owner_contract_drafts", [])
        queue.append({"type": contract_type, "title": title, "draft": draft, "status": "DRAFT", "created_by": principal.user_id})
        st.success("Working draft staged in this session. No contract was approved, signed, or published.")


def _render_knowledge() -> None:
    st.title("Knowledge")
    st.caption("Institutional knowledge is a usable layer; the Docket remains the authoritative governance register.")
    tabs = st.tabs(["Ask DARI", "Browse", "Recently Changed", "Saved", "Governance"])
    with tabs[0]:
        st.text_input("Ask DARI about company knowledge…", placeholder="What policy governs publication?", key="owner_knowledge_query")
        st.caption("Authoritative source → approved knowledge article → case-specific record → draft/reference material.")
    with tabs[1]:
        st.write("Policies · Procedures · Methodology · Templates · Training · System Documentation")
    with tabs[2]:
        st.info("Recent-change feed will populate from the Supabase knowledge_items and Docket adapters.")
    with tabs[3]:
        st.info("Saved owner references will appear here.")
    with tabs[4]:
        st.write("Constitution · First Truth Law · Docket · Executive Orders · Implementation Matrix · Policy-to-System Parity")
    st.markdown("**Knowledge item metadata standard:** state · version · effective date · owner · last review · supersedes · governed by · implements · related systems")


def _render_docket() -> None:
    st.title("Docket")
    st.caption("Authoritative controlled register of policies, governance artifacts, versions, approvals, dependencies, and health.")
    st.info("The Docket remains distinct from the Knowledge layer. Knowledge may explain a rule; the Docket controls which rule is authoritative.")


def _render_implementation() -> None:
    st.title("Implementation")
    st.caption("Proposed → Approved → Implementing → Verified → Operational")
    st.info("Use this area for implementation status, parity checks, acceptance evidence, and unresolved promotion gates.")


def _render_fix_center(manifest: Mapping[str, Any], records: Mapping[str, Any]) -> None:
    st.title("Fix Center")
    st.caption("What is broken, degraded, incomplete, drifting, failed, or waiting on a human decision.")
    summary = _safe_summary(manifest)
    pending = _decision_count(records, manifest)
    cards = [
        ("Broken", "No runtime outage asserted from this local manifest."),
        ("Degraded", "Use System Health for verified component degradation."),
        ("Incomplete", "Back-office Supabase adapter and some cross-system integrations remain incomplete."),
        ("Policy drift", "Use Implementation / parity controls for verified drift."),
        ("Failed tests", "Deployment/CI adapter required for live failures."),
        ("Needs approval", f"{pending} decision/review item(s) currently surfaced."),
        ("Database change", "Schema changes remain migration-controlled."),
        ("Human decision", f"{summary.get('inconsistencies', 0)} inconsistency item(s) may require human review."),
    ]
    cols = st.columns(2)
    for index, (title, body) in enumerate(cards):
        with cols[index % 2]:
            st.markdown(f"**{title}**")
            st.caption(body)


def _render_team_overview(shell, app_mode: str, storage_backend: str, core_backend: str, manifest: Mapping[str, Any], principal) -> None:
    st.title("Team")
    st.caption("Admin/owner team oversight: individual case position plus group workload and exceptions.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Authorized cases", len(principal.engagement_ids))
    c2.metric("Current inconsistencies", _safe_summary(manifest).get("inconsistencies", 0))
    c3.metric("Role", principal.role.value.title())
    c4.metric("Team health", "Awaiting staff feed")
    st.markdown("### Team Overview")
    st.write("Active staff · active cases · workload distribution · cases by stage · overdue work · review queue · blocked cases · capacity pressure")
    st.markdown("### Individual Team Member")
    st.write("Assigned cases · current stage · outstanding tasks · deadlines · review status · workload · recent activity · blockers")
    st.markdown("### Group Performance")
    st.write("Throughput · review completion · overdue rate · rework · publication readiness · cycle time · capacity utilization")
    st.markdown("### Needs Admin Attention")
    st.write("Overloaded staff · unassigned work · stale cases · deadlines at risk · QA failures · review bottlenecks · missing ownership")
    st.divider()
    shell._render_administration(app_mode, storage_backend, core_backend, dict(manifest), principal)


def _render_communications() -> None:
    st.title("Communications")
    st.caption("Inbox · Client Messages · Email · Internal Team · Referral Partners · Drafts · Templates · Follow-ups")
    st.info("Client portal messages already have a durable Supabase store. Gmail/team/referral aggregation remains integration-controlled; this surface does not claim messages that have not been connected.")


def _render_system_status(title: str, body: str) -> None:
    st.title(title)
    st.info(body)


def install_owner_operating_center(owner_ui, owner_runtime, shell) -> None:
    if getattr(owner_runtime, "_owner_operating_center_installed", False):
        return

    original_page = owner_runtime._render_owner_page
    owner_runtime._owner_sidebar = grouped_owner_sidebar
    owner_ui._owner_sidebar = grouped_owner_sidebar

    def render_page(shell_obj, page: str, **kwargs) -> None:
        principal = kwargs["principal"]
        manifest = kwargs["manifest"]
        records = kwargs["records"]
        reports = kwargs["reports"]
        core = kwargs["core"]
        if page == "Start My Day":
            return render_start_my_day(owner_ui, principal, manifest, records)
        if page == "My Workspace":
            return render_owner_operating_dashboard(owner_ui, principal, kwargs["engagement_id"], manifest, records, reports, core)
        if page == "Decisions":
            return shell_obj.app._render_review_center(dict(manifest), dict(reports), dict(records), kwargs["publication_store"], principal, kwargs["engagement_id"])
        if page == "Notifications":
            return _render_system_status("Notifications", "Owner decision, Dispatcher, case, billing, contract, system-health, and integration notifications converge here as their authoritative feeds are connected.")
        if page == "Clients":
            return owner_ui._render_clients(principal)
        if page == "Cases":
            return shell_obj._render_engagements(principal)
        if page == "Records":
            return shell_obj.legacy._render_evidence_workspace(principal=principal, engagement_id=kwargs["engagement_id"], core=core, manifest=dict(manifest))
        if page == "Reports":
            return shell_obj.app._render_internal_reports(dict(manifest), dict(reports), dict(records))
        if page == "Referrals":
            return _render_system_status("Referrals", "Referral partner and opportunity records are authoritative in Supabase; the Streamlit adapter is the remaining wiring step.")
        if page == "Communications":
            return _render_communications()
        if page == "Finance":
            return _render_finance(owner_ui)
        if page == "Billing":
            return _render_billing()
        if page == "Contracts":
            return _render_contracts(principal)
        if page == "Pricing":
            return _render_system_status("Pricing", "Pricing configuration remains controlled. Review and edit service pricing only through an authorized admin data path.")
        if page == "Documents":
            return _render_system_status("Company Documents", "Templates, engagement documents, policies, proposals, and controlled company documents belong here. Publication and execution remain separately approved states.")
        if page == "Team":
            return _render_team_overview(shell_obj, kwargs["app_mode"], kwargs["storage_backend"], kwargs["core_backend"], manifest, principal)
        if page == "Capacity":
            return _render_system_status("Capacity", "Capacity combines case load, review queue, deadlines, blocked work, and staff availability. No utilization number is fabricated until the team feed is connected.")
        if page == "Assignments":
            return shell_obj._render_administration(kwargs["app_mode"], kwargs["storage_backend"], kwargs["core_backend"], dict(manifest), principal)
        if page == "Access":
            return shell_obj._render_administration(kwargs["app_mode"], kwargs["storage_backend"], kwargs["core_backend"], dict(manifest), principal)
        if page == "DARI":
            decisions = owner_ui._decision_items(manifest, records)
            return owner_ui._render_dari(principal, kwargs["engagement_id"], decisions, manifest)
        if page == "Dispatcher":
            return owner_ui._render_dispatcher()
        if page == "Knowledge":
            return _render_knowledge()
        if page == "Docket":
            return _render_docket()
        if page == "Implementation":
            return _render_implementation()
        if page == "System Health":
            return shell_obj.render_system_lab(principal=principal, manifest=dict(manifest), app_mode=kwargs["app_mode"], storage_backend=kwargs["storage_backend"], core_backend=kwargs["core_backend"], engagement_id=kwargs["engagement_id"])
        if page == "Fix Center":
            return _render_fix_center(manifest, records)
        if page == "Integrations":
            return _render_system_status("Integrations", "Supabase, GitHub, Google services, email, calendar, storage, and provider integrations are tracked here by verified connection state—not by planned status.")
        if page == "Deployments":
            return _render_system_status("Deployments", "Deployment state belongs here once CI/deployment telemetry is connected to the owner runtime. Production authorization remains separately controlled.")
        if page == "System Lab":
            return shell_obj.render_system_lab(principal=principal, manifest=dict(manifest), app_mode=kwargs["app_mode"], storage_backend=kwargs["storage_backend"], core_backend=kwargs["core_backend"], engagement_id=kwargs["engagement_id"])
        return original_page(shell_obj, page, **kwargs)

    owner_runtime._render_owner_page = render_page
    owner_runtime._owner_operating_center_installed = True
