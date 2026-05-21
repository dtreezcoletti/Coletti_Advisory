"""
Coletti OS v2.0 — Streamlit Command Interface
"""

import json
import streamlit as st
from datetime import date, datetime

from coletti_os import (
    ColettiOS, Transaction, LegalMotion, AdvisoryClient, ProjectPhase, IncomeDisparity
)
from document_engine import (
    build_docket_summary, build_forensic_report, build_client_brief, build_master_report
)
from forensic_engine import ForensicEngine

import numpy as np
import pandas as pd
from advanced_detection import (
    normalize_transactions_v2, detect_anomalies_isolation_forest,
    detect_structuring, calculate_velocity_metrics,
    generate_schedule_a_v2, make_packet_excel_v2,
    SKLEARN_AVAILABLE, FUZZY_AVAILABLE, TARGET_ENTITY,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Coletti OS v2.0",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0d1117; }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .metric-label { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #f0f6fc; font-size: 28px; font-weight: 700; }
    .metric-sub   { color: #58a6ff; font-size: 13px; margin-top: 4px; }

    .tag-critical { background:#da3633; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
    .tag-active   { background:#388bfd22; color:#58a6ff; border:1px solid #388bfd; padding:2px 8px; border-radius:4px; font-size:11px; }
    .tag-pending  { background:#d29922; color:#0d1117; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
    .tag-archived { background:#21262d; color:#8b949e; padding:2px 8px; border-radius:4px; font-size:11px; }

    .section-header {
        border-left: 3px solid #58a6ff;
        padding-left: 10px;
        margin: 20px 0 12px;
        font-size: 15px;
        font-weight: 600;
        color: #f0f6fc;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .hud-header {
        font-family: monospace;
        color: #58a6ff;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state bootstrap ───────────────────────────────────────────────────

if "os" not in st.session_state:
    st.session_state["os"] = ColettiOS()
if "fe" not in st.session_state:
    st.session_state["fe"] = ForensicEngine()

sys: ColettiOS = st.session_state["os"]
fe: ForensicEngine = st.session_state["fe"]

if "adv_tx" not in st.session_state:
    st.session_state["adv_tx"] = None
if "adv_raw" not in st.session_state:
    st.session_state["adv_raw"] = None
if "adv_crypto_detected" not in st.session_state:
    st.session_state["adv_crypto_detected"] = False
if "adv_config" not in st.session_state:
    st.session_state["adv_config"] = {
        "known_accounts": ["9172", "5431", "8765"],
        "known_vendors": ["First Florida Credit Union", "Chase Bank", "Wells Fargo"],
        "affidavit_date": "2025-05-27",
        "hearing_date": "2026-02-20",
        "thresh_cash": 1500.0,
        "thresh_xfer": 500.0,
        "conf_filter": ["High", "Med"],
        "enable_if": SKLEARN_AVAILABLE,
        "enable_structuring": True,
        "structuring_window": 7,
        "structuring_threshold": 10000.0,
        "entity_config": {
            "card_endings": {},
            "geographic_rules": {},
            "behavioral_tags": {},
            "p2p_identifiers": {},
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def metric_card(label: str, value: str, sub: str = "", color: str = "#58a6ff"):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color:{color}">{value}</div>
        {"<div class='metric-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)


def status_tag(status: str) -> str:
    s = status.lower()
    if "critical" in s or "immediate" in s or "active" in s:
        return f'<span class="tag-critical">{status}</span>'
    if "pending" in s:
        return f'<span class="tag-pending">{status}</span>'
    if "archived" in s or "completed" in s:
        return f'<span class="tag-archived">{status}</span>'
    return f'<span class="tag-active">{status}</span>'


def days_until(iso_date: str) -> int:
    try:
        return (date.fromisoformat(iso_date) - date.today()).days
    except Exception:
        return 0


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:20px 0 10px;">
        <div style="font-size:28px">⚖️</div>
        <div style="font-size:16px; font-weight:700; color:#f0f6fc; letter-spacing:2px;">COLETTI OS</div>
        <div style="font-size:11px; color:#8b949e; letter-spacing:3px;">v2.0 · COMMAND INTERFACE</div>
    </div>
    <hr style="border-color:#30363d; margin:0 0 16px;">
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Dashboard", "Litigation Command", "Forensic Accounting", "Income Disparity",
         "Case Valuation", "Forensic Engine", "Enterprise Ops", "Documents", "Data Export",
         "Transaction Import", "Advanced Detection", "Exhibits", "Enhanced Subpoena"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#30363d; margin:16px 0 12px;'>", unsafe_allow_html=True)
    leverage = sys.litigation.evaluate_docket_leverage()
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size:11px; color:#8b949e; letter-spacing:1px; text-transform:uppercase;">Docket Leverage</div>
        <div style="font-size:36px; font-weight:700; color:{'#3fb950' if leverage >= 100 else '#f85149'};">{leverage}</div>
        <div style="font-size:11px; color:#8b949e;">/ 260 max score</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#30363d; margin:12px 0;'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:10px; color:#8b949e; text-align:center;">
        Case № {sys.litigation.case_number}<br>
        {sys.litigation.jurisdiction}<br>
        <em>{sys.litigation.judge}</em>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

if page == "Dashboard":
    st.markdown(f"""
    <div class="hud-header">
    ══════════════════════════════════════════════════════<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;COLETTI OS v2.0 &nbsp;·&nbsp; STRATEGIC COMMAND HUD<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; SYSTEM STATUS: <span style="color:#3fb950">ONLINE</span><br>
    ══════════════════════════════════════════════════════
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>[ LITIGATION OPS ]</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Rule 36 Default", f"{sys.litigation.rule_36_days_default} Days",
                    "CRITICAL LEVERAGE", "#f85149")
    with c2:
        nh = sys.litigation.next_hearing()
        if nh:
            d = days_until(nh)
            metric_card("Next Hearing", date.fromisoformat(nh).strftime("%b %d, %Y"),
                        f"T–{d} days", "#d29922" if d <= 30 else "#58a6ff")
        else:
            metric_card("Next Hearing", "None Scheduled", color="#8b949e")
    with c3:
        metric_card("Active Motions",
                    str(sum(1 for m in sys.litigation.motions if m.status.lower() in ("active", "pending judicial signature"))),
                    "Filed & Pending")
    with c4:
        metric_card("Subpoenas Active", str(len(sys.litigation.active_subpoenas)),
                    "Evidence Hunts Open", "#3fb950")

    st.markdown("<div class='section-header'>[ FORENSIC OPS ]</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Institution", sys.forensics.institution, sys.forensics.target_account)
    with c2:
        metric_card("Total Dissipation",
                    f"${sys.forensics.calculate_dissipation():,.2f}",
                    f"{sys.forensics.dissipation_rate():.1f}% of logged funds", "#f85149")
    with c3:
        metric_card("Transactions Logged",
                    str(len(sys.forensics.transactions)),
                    f"${sys.forensics.calculate_total():,.2f} total reviewed")
    with c4:
        metric_card("Known Balance", f"${sys.forensics.known_balance:,.2f}",
                    "Last verified on record")

    st.markdown("<div class='section-header'>[ ENTERPRISE OPS ]</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Firm", sys.enterprise.firm_name, sys.enterprise.founder)
    with c2:
        metric_card("Active Portfolios", str(len(sys.enterprise.active_portfolios)),
                    "Total client engagements")
    with c3:
        metric_card("Retainers Active", str(sys.enterprise.retainer_count()),
                    "Contracted engagements", "#3fb950")

    # Active subpoenas quick view
    if sys.litigation.active_subpoenas:
        st.markdown("<div class='section-header'>[ ACTIVE SUBPOENAS ]</div>", unsafe_allow_html=True)
        for s in sys.litigation.active_subpoenas:
            st.markdown(f"&nbsp;&nbsp;`▶` {s}")

    # Income disparity highlight
    idp = sys.income_disparity
    st.markdown("<div class='section-header'>[ INCOME DISPARITY ]</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Sworn Net/Month", f"${idp.sworn_monthly_net:,.2f}", "Opposing disclosure")
    with c2:
        metric_card("Verified Net/Month", f"${idp.verified_monthly_net:,.2f}", "Forensic finding", "#f85149")
    with c3:
        metric_card("Monthly Understatement",
                    f"${idp.monthly_understatement():,.2f}",
                    f"{idp.understatement_pct():.0f}% above sworn", "#f85149")
    with c4:
        metric_card("Total Concealed Value",
                    f"${idp.total_concealed_value():,.2f}",
                    f"Over {idp.tracking_months} months + hard assets", "#f85149")

    # Upcoming motions
    st.markdown("<div class='section-header'>[ MOTION QUEUE ]</div>", unsafe_allow_html=True)
    for m in sorted(sys.litigation.motions, key=lambda x: x.hearing_date or "9999"):
        cols = st.columns([3, 2, 2, 3])
        cols[0].markdown(f"**{m.title}**")
        cols[1].markdown(m.date_filed)
        cols[2].markdown(m.hearing_date or "TBD")
        cols[3].markdown(status_tag(m.status), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: LITIGATION COMMAND
# ════════════════════════════════════════════════════════════════════════════

elif page == "Litigation Command":
    st.title("⚖️ Litigation Command Center")
    st.caption(f"Case № {sys.litigation.case_number} · {sys.litigation.jurisdiction}")

    tab_motions, tab_subpoenas, tab_meta = st.tabs(["Motions", "Subpoenas", "Case Meta"])

    # ── Motions ──────────────────────────────────────────────────────────────
    with tab_motions:
        st.markdown("<div class='section-header'>Filed Motions</div>", unsafe_allow_html=True)

        for i, m in enumerate(sys.litigation.motions):
            with st.expander(f"{status_tag(m.status)} &nbsp; {m.title}", expanded=True):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Filed:** {m.date_filed}")
                c2.markdown(f"**Hearing:** {m.hearing_date or 'TBD'}")
                st.markdown(f"**Strategic Objective:** {m.strategic_objective}")
                new_status = st.selectbox(
                    "Update Status",
                    ["Active", "Pending Judicial Signature", "Granted", "Denied", "Withdrawn", "Archived"],
                    index=["Active", "Pending Judicial Signature", "Granted", "Denied", "Withdrawn", "Archived"].index(m.status)
                    if m.status in ["Active", "Pending Judicial Signature", "Granted", "Denied", "Withdrawn", "Archived"]
                    else 0,
                    key=f"status_{i}",
                )
                if st.button("Save Status", key=f"save_{i}"):
                    sys.litigation.motions[i].status = new_status
                    st.success("Status updated.")

        st.divider()
        st.markdown("#### File New Motion")
        with st.form("new_motion"):
            title = st.text_input("Motion Title")
            col1, col2 = st.columns(2)
            filed = col1.date_input("Date Filed", value=date.today())
            hearing = col2.date_input("Hearing Date", value=date.today())
            objective = st.text_area("Strategic Objective")
            submitted = st.form_submit_button("Add Motion")
            if submitted and title:
                sys.litigation.motions.append(LegalMotion(
                    title=title,
                    date_filed=filed.isoformat(),
                    hearing_date=hearing.isoformat(),
                    status="Active",
                    strategic_objective=objective,
                ))
                st.success(f"Motion '{title}' added to docket.")
                st.rerun()

    # ── Subpoenas ─────────────────────────────────────────────────────────────
    with tab_subpoenas:
        st.markdown("<div class='section-header'>Active Subpoenas</div>", unsafe_allow_html=True)

        for i, s in enumerate(sys.litigation.active_subpoenas):
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"🔍 **{s}**")
            if c2.button("Remove", key=f"del_sub_{i}"):
                sys.litigation.active_subpoenas.pop(i)
                st.rerun()

        st.divider()
        with st.form("new_sub"):
            new_sub = st.text_input("New Subpoena Target")
            if st.form_submit_button("Issue Subpoena") and new_sub:
                sys.litigation.active_subpoenas.append(new_sub)
                st.success(f"Subpoena issued: {new_sub}")
                st.rerun()

    # ── Case Meta ─────────────────────────────────────────────────────────────
    with tab_meta:
        st.markdown("#### Docket Configuration")
        with st.form("meta_form"):
            cn = st.text_input("Case Number", value=sys.litigation.case_number)
            jx = st.text_input("Jurisdiction", value=sys.litigation.jurisdiction)
            jg = st.text_input("Judge", value=sys.litigation.judge)
            r36 = st.number_input("Rule 36 Days Default", value=sys.litigation.rule_36_days_default, step=1)
            if st.form_submit_button("Update Case Meta"):
                sys.litigation.case_number = cn
                sys.litigation.jurisdiction = jx
                sys.litigation.judge = jg
                sys.litigation.rule_36_days_default = int(r36)
                st.success("Case meta updated.")

        st.divider()
        leverage = sys.litigation.evaluate_docket_leverage()
        st.markdown(f"### Docket Leverage Score: `{leverage}`")
        progress = min(leverage / 260, 1.0)
        st.progress(progress)
        if leverage >= 200:
            st.success("DOMINANT — Procedural position is overwhelming.")
        elif leverage >= 100:
            st.info("STRONG — Significant advantages secured.")
        else:
            st.warning("BUILDING — Continue filing and discovery pressure.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: FORENSIC ACCOUNTING
# ════════════════════════════════════════════════════════════════════════════

elif page == "Forensic Accounting":
    st.title("🔎 Forensic Accounting Engine")
    st.caption(f"{sys.forensics.institution} · Account {sys.forensics.target_account}")

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Transactions", len(sys.forensics.transactions))
    c2.metric("Total Funds Reviewed", f"${sys.forensics.calculate_total():,.2f}")
    c3.metric("Marital Dissipation", f"${sys.forensics.calculate_dissipation():,.2f}")
    c4.metric("Dissipation Rate", f"{sys.forensics.dissipation_rate():.1f}%")

    st.divider()

    tab_ledger, tab_add, tab_config = st.tabs(["Transaction Ledger", "Log Transaction", "Account Config"])

    # ── Ledger ────────────────────────────────────────────────────────────────
    with tab_ledger:
        if not sys.forensics.transactions:
            st.info("No transactions logged. Use 'Log Transaction' to begin building the evidentiary ledger.")
        else:
            # Filter controls
            fc1, fc2 = st.columns(2)
            show_dissipation_only = fc1.checkbox("Show Dissipation Only")
            category_filter = fc2.selectbox(
                "Filter by Category",
                ["All"] + sorted({t.category for t in sys.forensics.transactions})
            )

            txns = sys.forensics.transactions
            if show_dissipation_only:
                txns = [t for t in txns if t.is_marital_dissipation]
            if category_filter != "All":
                txns = [t for t in txns if t.category == category_filter]

            st.markdown(f"**{len(txns)} records displayed**")

            for i, t in enumerate(txns):
                flag = "🔴" if t.is_marital_dissipation else "⚪"
                with st.expander(f"{flag} {t.effective_date} · ${t.amount:,.2f} · {t.description}"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Category:** {t.category}")
                    c2.markdown(f"**Amount:** ${t.amount:,.2f}")
                    c3.markdown(f"**Dissipation:** {'Yes ⚠️' if t.is_marital_dissipation else 'No'}")

                    if st.button("Remove Entry", key=f"del_txn_{i}"):
                        sys.forensics.transactions.pop(
                            sys.forensics.transactions.index(t)
                        )
                        st.rerun()

    # ── Add Transaction ────────────────────────────────────────────────────────
    with tab_add:
        st.markdown("#### Log New Transaction")
        with st.form("add_txn"):
            d = st.date_input("Effective Date", value=date.today())
            c1, c2 = st.columns(2)
            amt = c1.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
            cat = c2.text_input("Category", placeholder="e.g. Transfer, Cash Withdrawal, Luxury")
            desc = st.text_input("Description")
            is_dis = st.checkbox("Flag as Marital Dissipation")

            if st.form_submit_button("Log Transaction"):
                if desc and cat:
                    sys.forensics.transactions.append(Transaction(
                        effective_date=d.isoformat(),
                        amount=float(amt),
                        description=desc,
                        category=cat,
                        is_marital_dissipation=is_dis,
                    ))
                    st.success(f"Transaction logged: ${amt:,.2f} — {desc}")
                    st.rerun()
                else:
                    st.error("Description and Category are required.")

    # ── Account Config ─────────────────────────────────────────────────────────
    with tab_config:
        with st.form("acct_config"):
            inst = st.text_input("Institution", value=sys.forensics.institution)
            acct = st.text_input("Target Account", value=sys.forensics.target_account)
            bal = st.number_input("Known Balance ($)", value=sys.forensics.known_balance, format="%.2f")
            if st.form_submit_button("Update"):
                sys.forensics.institution = inst
                sys.forensics.target_account = acct
                sys.forensics.known_balance = float(bal)
                st.success("Account configuration updated.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: ENTERPRISE OPS
# ════════════════════════════════════════════════════════════════════════════

elif page == "Enterprise Ops":
    st.title("🏢 Coletti & Co. — Enterprise Operations")
    st.caption(f"Chief Executive: {sys.enterprise.founder}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Portfolios", len(sys.enterprise.active_portfolios))
    c2.metric("Active Retainers", sys.enterprise.retainer_count())
    c3.metric("Firm", sys.enterprise.firm_name)

    st.divider()
    tab_clients, tab_add = st.tabs(["Client Portfolios", "Onboard Client"])

    # ── Client List ───────────────────────────────────────────────────────────
    with tab_clients:
        if not sys.enterprise.active_portfolios:
            st.info("No clients onboarded yet.")
        else:
            phase_filter = st.selectbox(
                "Filter by Phase",
                ["All"] + [p.value for p in ProjectPhase]
            )
            clients = sys.enterprise.active_portfolios
            if phase_filter != "All":
                clients = [c for c in clients if c.phase == phase_filter]

            for i, client in enumerate(clients):
                retainer_badge = "🟢 Retainer Active" if client.retainer_active else "⚪ No Retainer"
                with st.expander(f"**{client.entity_name}** · {client.phase} · {retainer_badge}"):
                    st.markdown(f"**Primary Objective:** {client.primary_objective}")
                    c1, c2 = st.columns(2)
                    new_phase = c1.selectbox(
                        "Phase",
                        [p.value for p in ProjectPhase],
                        index=[p.value for p in ProjectPhase].index(client.phase)
                        if client.phase in [p.value for p in ProjectPhase] else 0,
                        key=f"phase_{i}",
                    )
                    new_retainer = c2.checkbox("Retainer Active", value=client.retainer_active, key=f"ret_{i}")
                    if st.button("Update", key=f"upd_{i}"):
                        sys.enterprise.active_portfolios[
                            sys.enterprise.active_portfolios.index(client)
                        ].phase = new_phase
                        sys.enterprise.active_portfolios[
                            sys.enterprise.active_portfolios.index(client)
                        ].retainer_active = new_retainer
                        st.success("Client record updated.")
                        st.rerun()
                    if st.button("Remove Client", key=f"rem_{i}"):
                        sys.enterprise.active_portfolios.remove(client)
                        st.rerun()

    # ── Onboard ───────────────────────────────────────────────────────────────
    with tab_add:
        st.markdown("#### Onboard New Client")
        with st.form("new_client"):
            name = st.text_input("Entity / Client Name")
            obj = st.text_area("Primary Objective")
            phase = st.selectbox("Initial Phase", [p.value for p in ProjectPhase])
            retainer = st.checkbox("Retainer Active at Onboarding")
            if st.form_submit_button("Onboard"):
                if name:
                    sys.enterprise.add_client(AdvisoryClient(
                        entity_name=name,
                        primary_objective=obj,
                        phase=phase,
                        retainer_active=retainer,
                    ))
                    st.success(f"'{name}' added to portfolio.")
                    st.rerun()
                else:
                    st.error("Entity name is required.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: INCOME DISPARITY
# ════════════════════════════════════════════════════════════════════════════

elif page == "Income Disparity":
    st.title("📊 Income Disparity Analysis")
    st.caption("Sworn disclosure vs. forensic verification — evidentiary summary")

    idp = sys.income_disparity

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='section-header'>Sworn Disclosure</div>", unsafe_allow_html=True)
        metric_card("Sworn Monthly Net", f"${idp.sworn_monthly_net:,.2f}", "Opposing party's filed affidavit")
    with c2:
        st.markdown("<div class='section-header'>Forensic Finding</div>", unsafe_allow_html=True)
        metric_card("Verified Monthly Net", f"${idp.verified_monthly_net:,.2f}",
                    "Confirmed via subpoena returns", "#f85149")

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly Understatement", f"${idp.monthly_understatement():,.2f}")
    c2.metric("Understatement %", f"{idp.understatement_pct():.1f}%")
    c3.metric("Tracking Period", f"{idp.tracking_months} Months")
    c4.metric("Cumulative Understatement", f"${idp.cumulative_understatement():,.2f}")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        metric_card("Sequestered Hard Assets", f"${idp.sequestered_hard_assets:,.2f}",
                    "Physical & financial assets concealed", "#f85149")
    with c2:
        metric_card("Total Concealed Value", f"${idp.total_concealed_value():,.2f}",
                    f"Cumulative understatement + hard assets", "#f85149")

    # Bar chart comparison
    st.markdown("<div class='section-header'>Monthly Net Comparison</div>", unsafe_allow_html=True)
    import pandas as pd
    chart_data = pd.DataFrame({
        "Source": ["Sworn (Opponent)", "Verified (Forensic)"],
        "Monthly Net ($)": [idp.sworn_monthly_net, idp.verified_monthly_net],
    })
    st.bar_chart(chart_data.set_index("Source"))

    st.divider()
    st.markdown("#### Update Disparity Parameters")
    with st.form("idp_form"):
        fc1, fc2 = st.columns(2)
        new_sworn = fc1.number_input("Sworn Monthly Net ($)", value=idp.sworn_monthly_net, format="%.2f")
        new_verified = fc2.number_input("Verified Monthly Net ($)", value=idp.verified_monthly_net, format="%.2f")
        fc3, fc4 = st.columns(2)
        new_months = fc3.number_input("Tracking Months", value=idp.tracking_months, step=1)
        new_assets = fc4.number_input("Sequestered Hard Assets ($)", value=idp.sequestered_hard_assets, format="%.2f")
        if st.form_submit_button("Update Parameters"):
            sys.income_disparity.sworn_monthly_net = float(new_sworn)
            sys.income_disparity.verified_monthly_net = float(new_verified)
            sys.income_disparity.tracking_months = int(new_months)
            sys.income_disparity.sequestered_hard_assets = float(new_assets)
            st.success("Income disparity parameters updated.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: CASE VALUATION
# ════════════════════════════════════════════════════════════════════════════

elif page == "Case Valuation":
    st.title("💰 Case Valuation — 24D-1003")
    st.caption("Coletti v. Brown · Davidson County Fourth Circuit")

    cv = sys.case_valuation

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Case Value (Capped)", f"${cv.total_capped:,.2f}")
    c2.metric("Income Fraud Concealment", f"${cv.income_fraud.concealment_amount:,.2f}",
              f"{cv.income_fraud.concealment_pct:.1f}% above sworn")
    c3.metric("Premeditation", cv.premeditation_assessment,
              f"Score: {cv.premeditation_score:.1f}  |  {cv.premeditation_event_count} events")

    tab_t1, tab_t2, tab_t3, tab_fraud, tab_sabotage, tab_dates = st.tabs(
        ["Tier 1 – Motion Relief", "Tier 2 – Trial Damages",
         "Tier 3 – Punitive", "Income Fraud", "Business Sabotage", "Key Dates"]
    )

    with tab_t1:
        t1 = cv.tier1
        st.markdown("#### Immediate Motion Relief")
        data = {
            "Line Item": ["Suit Money", "Income Concealment (Proven)", "Income Concealment (Suspected)",
                          "Income Concealment Total", "Animal Equalization",
                          "Pendente Lite Monthly", "Pendente Lite Arrearage", "King Personal Sanctions"],
            "Amount": [
                f"${t1.suit_money:,.2f}", f"${t1.income_concealment_proven:,.2f}",
                f"${t1.income_concealment_suspected:,.2f}", f"${t1.income_concealment_total:,.2f}",
                f"${t1.animal_equalization:,.2f}", f"${t1.pendente_lite_monthly:,.2f}",
                f"${t1.pendente_lite_arrearage:,.2f}", f"${t1.king_personal_sanctions:,.2f}",
            ],
        }
        import pandas as pd
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("**Tier 1 Subtotal**", f"${t1.subtotal:,.2f}")

    with tab_t2:
        t2 = cv.tier2
        st.markdown("#### Trial-Level Damages")
        data = {
            "Damage Category": ["Homemaker Contributions", "Human Capital Loss",
                                "Business Sabotage", "Property Division",
                                "Alimony in Solido", "Marital Fault Damages"],
            "Amount": [
                f"${t2.homemaker_contributions:,.2f}", f"${t2.human_capital_loss:,.2f}",
                f"${t2.business_sabotage:,.2f}", f"${t2.property_division:,.2f}",
                f"${t2.alimony_in_solido:,.2f}", f"${t2.marital_fault_damages:,.2f}",
            ],
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("**Tier 2 Subtotal**", f"${t2.subtotal:,.2f}")

    with tab_t3:
        t3 = cv.tier3
        st.markdown("#### Punitive Damages")
        c1, c2 = st.columns(2)
        c1.metric("Assault Punitive", f"${t3.assault_punitive:,.2f}")
        c2.metric("Economic Destruction Punitive", f"${t3.economic_destruction_punitive:,.2f}")
        st.metric("**Tier 3 Total**", f"${t3.total:,.2f}")

    with tab_fraud:
        fi = cv.income_fraud
        st.markdown("#### Respondent's Income Fraud (Coletti v. Brown)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sworn Annual Income", f"${fi.sworn_annual:,.2f}")
        c2.metric("Verified W-2 (Dreamliner)", f"${fi.verified_w2:,.2f}")
        c3.metric("Verified 1099 (Garrison)", f"${fi.verified_1099:,.2f}")
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Total Verified Income", f"${fi.verified_total:,.2f}")
        c2.metric("Concealment Amount", f"${fi.concealment_amount:,.2f}", f"{fi.concealment_pct:.1f}% above sworn")

    with tab_sabotage:
        sb = cv.sabotage
        st.markdown("#### Business Sabotage Breakdown")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Modeling Career**")
            st.metric("Immediate Recovery", f"${sb.modeling_immediate_recovery:,.2f}")
            st.metric("Forced Leave (23 mo)", f"${sb.modeling_forced_leave_23mo:,.2f}")
            st.metric("SLAM Contract Loss", f"${sb.modeling_slam_contract_loss:,.2f}")
            st.metric("Future Trajectory (5yr)", f"${sb.modeling_future_5yr:,.2f}")
            st.metric("Modeling Total", f"${sb.modeling_total:,.2f}")
        with c2:
            st.markdown("**Coletti & Co.**")
            st.metric("Base Revenue/Year", f"${sb.coletti_co_base_annual:,.2f}")
            st.metric("Years Closed", f"{sb.coletti_co_years_closed:.2f}")
            st.metric("Lost Revenue", f"${sb.coletti_co_lost_revenue:,.2f}")
            st.metric("Growth Adjustment", f"${sb.coletti_co_growth_adj:,.2f}")
            st.metric("Coletti & Co. Total", f"${sb.coletti_co_total:,.2f}")
        st.divider()
        st.metric("Physical Property Damage", f"${sb.physical_property:,.2f}")
        st.metric("**Grand Total — Business Sabotage**", f"${sb.grand_total:,.2f}")

    with tab_dates:
        cd = cv.case_dates
        st.markdown("#### Key Case Dates")
        c1, c2 = st.columns(2)
        c1.metric("Marriage Start", cd.marriage_start)
        c2.metric("Marriage Duration", f"{cd.marriage_years():.1f} years")
        c1.metric("Assault / Separation Date", cd.assault_date)
        c2.metric("Filing Date", cd.filing_date)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: FORENSIC ENGINE
# ════════════════════════════════════════════════════════════════════════════

elif page == "Forensic Engine":
    st.title("🔬 Forensic Financial Analysis Engine")
    st.caption(f"{fe.SYSTEM_ID}  ·  {fe.case_name}  ·  {fe.analyst_attribution}")

    tab_overview, tab_income, tab_assets, tab_variance, tab_impact, tab_disparity, tab_report = st.tabs([
        "Overview", "Income Sources", "Asset Discovery",
        "Variance Analysis", "Cumulative Impact", "Economic Disparity", "Text Report"
    ])

    with tab_overview:
        manifest = fe.generate_court_manifest()
        va = fe.variance_analysis
        ci = fe.cumulative_impact
        ad = fe.asset_summary()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Income Sources", len(fe.income_sources))
        c2.metric("Monthly Concealment", f"${va.get('monthly_concealment_delta', 0):,.2f}")
        c3.metric("Concealment Rate", f"{va.get('concealment_percentage', 0):.1f}%")
        c4.metric("Total Shielded Capital", f"${ci.get('total_shielded_capital', 0):,.2f}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Assets Discovered", ad["total_count"])
        c2.metric("Concealed Assets", ad["concealed_count"])
        c3.metric("Concealed Equity", f"${ad['concealed_equity_value']:,.2f}")
        c4.metric("Audit Hash", manifest["METADATA"]["audit_hash"])

    with tab_income:
        st.markdown("#### Discovered Income Sources")
        recon = fe.reconstruct_total_income()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Annual Gross", f"${recon['total_annual_gross']:,.2f}")
        c2.metric("Total Monthly Gross", f"${recon['total_monthly_gross']:,.2f}")
        c3.metric("Sources Count", recon["source_count"])
        st.divider()
        for sid, src in recon["sources_breakdown"].items():
            with st.expander(f"**{src['name']}** — ${src['annual']:,.2f}/yr"):
                st.markdown(f"- **Type:** {src['type']}")
                st.markdown(f"- **Annual Gross:** ${src['annual']:,.2f}")
                st.markdown(f"- **Monthly Gross:** ${src['monthly']:,.2f}")
                st.markdown(f"- **Documentation:** {src['documentation']}")

        st.divider()
        st.markdown("#### Add Income Source")
        with st.form("fe_add_source"):
            fc1, fc2 = st.columns(2)
            sname = fc1.text_input("Source Name")
            stype = fc2.selectbox("Type", ["W2", "1099", "Cash", "Investment", "Other"])
            fc3, fc4 = st.columns(2)
            sannual = fc3.number_input("Annual Amount ($)", min_value=0.01, format="%.2f")
            sdoc = fc4.text_input("Documentation Reference")
            sdate = st.date_input("Discovery Date", value=date.today())
            if st.form_submit_button("Ingest Source"):
                if sname:
                    fe.ingest_income_source(sname, float(sannual), stype, sdoc, sdate.isoformat())
                    fe.calculate_variance(actual_monthly_net=fe.variance_analysis.get("actual_monthly_net", 9983.18))
                    fe.calculate_cumulative_impact()
                    st.success(f"Source '{sname}' ingested.")
                    st.rerun()

    with tab_assets:
        st.markdown("#### Discovered Assets")
        asumm = fe.asset_summary()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Market Value", f"${asumm['total_market_value']:,.2f}")
        c2.metric("Total Equity Value", f"${asumm['total_equity_value']:,.2f}")
        c3.metric("Concealed Equity", f"${asumm['concealed_equity_value']:,.2f}")
        st.divider()
        for aid, asset in fe.assets_discovered.items():
            flag = "🔴 CONCEALED" if asset["concealed"] else "🟢 Disclosed"
            with st.expander(f"**{asset['name']}** — {flag} — ${asset['equity_value']:,.2f}"):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Type:** {asset['type']}")
                c2.markdown(f"**Market Value:** ${asset['market_value']:,.2f}")
                st.markdown(f"**Documentation:** {asset['documentation']}")

        st.divider()
        st.markdown("#### Add Asset")
        with st.form("fe_add_asset"):
            fc1, fc2 = st.columns(2)
            aname = fc1.text_input("Asset Name")
            atype = fc2.selectbox("Asset Type", ["Real Estate", "Retirement", "LLC", "Account", "Vehicle", "Other"])
            fc3, fc4 = st.columns(2)
            amv = fc3.number_input("Market Value ($)", min_value=0.01, format="%.2f")
            aev = fc4.number_input("Equity Value ($)", min_value=0.01, format="%.2f")
            adoc = st.text_input("Documentation Reference")
            adisclosed = st.checkbox("Disclosed in Affidavit")
            if st.form_submit_button("Ingest Asset"):
                if aname:
                    fe.ingest_asset(aname, atype, float(amv), float(aev), adoc, adisclosed)
                    fe.calculate_cumulative_impact()
                    st.success(f"Asset '{aname}' ingested.")
                    st.rerun()

    with tab_variance:
        va = fe.variance_analysis
        st.markdown("#### Income Variance Analysis")
        c1, c2 = st.columns(2)
        with c1:
            metric_card("Sworn Monthly Net", f"${va.get('sworn_monthly_net', 0):,.2f}",
                        "Opposing affidavit May 27, 2025")
        with c2:
            metric_card("Verified Monthly Net", f"${va.get('actual_monthly_net', 0):,.2f}",
                        "Forensic reconstruction", "#f85149")
        c1, c2, c3 = st.columns(3)
        c1.metric("Monthly Concealment", f"${va.get('monthly_concealment_delta', 0):,.2f}")
        c2.metric("Concealment Rate", f"{va.get('concealment_percentage', 0):.1f}%")
        c3.metric("Annual Concealment", f"${va.get('annual_concealment_delta', 0):,.2f}")

        st.divider()
        st.markdown("#### Update Verified Net")
        with st.form("update_variance"):
            new_net = st.number_input(
                "Verified Monthly Net ($)",
                value=fe.variance_analysis.get("actual_monthly_net", 9983.18),
                format="%.2f"
            )
            if st.form_submit_button("Recalculate"):
                fe.calculate_variance(float(new_net))
                fe.calculate_cumulative_impact()
                st.success("Variance recalculated.")
                st.rerun()

    with tab_impact:
        ci = fe.cumulative_impact
        st.markdown("#### Cumulative Impact Analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Tracking Period", f"{ci.get('tracking_period_months', 0)} months")
        c2.metric("Monthly Concealment", f"${ci.get('monthly_concealment', 0):,.2f}")
        c3.metric("Total Concealed Income", f"${ci.get('total_concealed_income', 0):,.2f}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Proper Monthly Support", f"${ci.get('proper_monthly_support', 0):,.2f}")
        c2.metric("Court-Ordered Support", f"${ci.get('court_ordered_support', 0):,.2f}")
        c3.metric("Monthly Shortfall", f"${ci.get('monthly_support_shortfall', 0):,.2f}")

        c1, c2 = st.columns(2)
        c1.metric("Total Support Arrearage", f"${ci.get('total_support_arrearage', 0):,.2f}")
        c2.metric("Concealed Assets Value", f"${ci.get('concealed_assets_value', 0):,.2f}")

        st.divider()
        metric_card("TOTAL SHIELDED CAPITAL",
                    f"${ci.get('total_shielded_capital', 0):,.2f}",
                    "Concealed income + concealed assets", "#f85149")

    with tab_disparity:
        ce = fe.comparative_economics
        if ce:
            pb = ce["petitioner_business"]
            ri = ce["respondent_income"]
            da = ce["disparity"]
            st.markdown("#### Economic Disparity Analysis")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{pb['name']}**")
                st.metric("Operation Period", f"{pb['total_months']} months")
                st.metric("Total Revenue", f"${pb['total_net_revenue']:,.2f}")
                st.metric("Monthly Average", f"${pb['monthly_average']:,.2f}")
            with c2:
                st.markdown("**Respondent**")
                st.metric("Monthly Net Income", f"${ri['monthly_net']:,.2f}")
                st.metric("Annual Net Income", f"${ri['annual_net']:,.2f}")
                st.metric("Equiv. Period Earnings", f"${ri['equiv_period_net']:,.2f}")
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Monthly Ratio", f"{da['monthly_ratio']:.2f}x")
            c2.metric("Annual Ratio", f"{da['annual_ratio']:.2f}x")
            c3.metric("Months to Match Business", f"{da['months_to_match']:.1f}")
        else:
            st.info("No disparity analysis yet.")

    with tab_report:
        st.markdown("#### Full Forensic Text Report")
        report_text = fe.generate_text_report()
        st.code(report_text, language="text")
        st.download_button(
            "⬇️ Download Text Report",
            data=report_text,
            file_name=f"forensic_report_{date.today().isoformat()}.txt",
            mime="text/plain",
        )
        manifest_json = json.dumps(fe.generate_court_manifest(), indent=2, default=str)
        st.download_button(
            "⬇️ Download Court Manifest (JSON)",
            data=manifest_json,
            file_name=f"court_manifest_{date.today().isoformat()}.json",
            mime="application/json",
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════

elif page == "Documents":
    st.title("🖨️ Document Generation")
    st.markdown(
        "Generate print-ready PDF reports from live Coletti OS data. "
        "Download and print for court filings, briefings, and physical recordkeeping."
    )

    st.divider()

    doc_col1, doc_col2 = st.columns(2)

    with doc_col1:
        st.markdown("#### Docket Summary Sheet")
        st.markdown("Full litigation docket: case info, all motions, active subpoenas, leverage analysis.")
        if st.button("Generate Docket PDF", use_container_width=True):
            with st.spinner("Building PDF..."):
                pdf_bytes = build_docket_summary(sys.litigation)
            st.download_button(
                label="⬇️ Download Docket Summary",
                data=pdf_bytes,
                file_name=f"docket_summary_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### Forensic Accounting Report")
        st.markdown("Full transaction ledger with dissipation analysis and evidentiary narrative.")
        if st.button("Generate Forensic PDF", use_container_width=True):
            with st.spinner("Building PDF..."):
                pdf_bytes = build_forensic_report(sys.forensics)
            st.download_button(
                label="⬇️ Download Forensic Report",
                data=pdf_bytes,
                file_name=f"forensic_report_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    with doc_col2:
        st.markdown("#### Client Portfolio Brief")
        st.markdown("Enterprise client roster with objectives, phases, and retainer status.")
        if st.button("Generate Portfolio PDF", use_container_width=True):
            with st.spinner("Building PDF..."):
                pdf_bytes = build_client_brief(sys.enterprise)
            st.download_button(
                label="⬇️ Download Portfolio Brief",
                data=pdf_bytes,
                file_name=f"portfolio_brief_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### Master Operational Report")
        st.markdown("Combined: litigation + forensic + enterprise — full picture for counsel or review.")
        if st.button("Generate Master Report", use_container_width=True):
            with st.spinner("Building PDF..."):
                pdf_bytes = build_master_report(sys)
            st.download_button(
                label="⬇️ Download Master Report",
                data=pdf_bytes,
                file_name=f"master_report_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.divider()
    st.info(
        "All documents are stamped CONFIDENTIAL — ATTORNEY WORK PRODUCT and include page numbers, "
        "firm header, and generation timestamp. Print via your browser's PDF viewer for best results."
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DATA EXPORT
# ════════════════════════════════════════════════════════════════════════════

elif page == "Data Export":
    st.title("📦 Data Export & Backup")
    st.markdown(
        "Export the full Coletti OS state as JSON for backup, transfer, or offline analysis. "
        "Paste a previously exported JSON below to restore state."
    )

    # Export
    payload = json.dumps(sys.to_dict(), indent=2)
    st.download_button(
        label="⬇️ Download Full State (JSON)",
        data=payload,
        file_name=f"coletti_os_export_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
    )
    st.code(payload, language="json")

    st.divider()

    # Import
    st.markdown("#### Restore from JSON")
    uploaded = st.file_uploader("Upload exported JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            sys.load_dict(data)
            st.success("State restored successfully. Navigate to any page to see updated data.")
        except Exception as e:
            st.error(f"Failed to parse JSON: {e}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSACTION IMPORT
# ════════════════════════════════════════════════════════════════════════════

elif page == "Transaction Import":
    st.title("📥 Transaction Import & Analysis Config")
    st.caption("Upload a CSV ledger to run advanced forensic detection across all exhibit channels.")

    cfg = st.session_state["adv_config"]

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Data Source")
        tx_file = st.file_uploader("Transaction Ledger (CSV)", type=["csv"])

        st.markdown("#### Temporal Anchors")
        cfg["affidavit_date"] = st.text_input("Affidavit Date", cfg["affidavit_date"])
        cfg["hearing_date"]   = st.text_input("Hearing Date",   cfg["hearing_date"])

        st.markdown("#### Thresholds")
        cfg["thresh_cash"] = st.number_input("Cash Threshold ($)",     min_value=0.0, value=cfg["thresh_cash"])
        cfg["thresh_xfer"] = st.number_input("Transfer Threshold ($)", min_value=0.0, value=cfg["thresh_xfer"])
        cfg["conf_filter"] = st.multiselect("Confidence Levels", ["High", "Med", "Low"], default=cfg["conf_filter"])

    with col_right:
        st.markdown("#### Known Entities")
        known_accounts_raw = st.text_area(
            "Known Account Numbers (one per line)",
            "\n".join(cfg["known_accounts"]),
            height=100,
        )
        cfg["known_accounts"] = [a.strip() for a in known_accounts_raw.split("\n") if a.strip()]

        known_vendors_raw = st.text_area(
            "Known Vendors (fuzzy matching)",
            "\n".join(cfg["known_vendors"]),
            height=100,
        )
        cfg["known_vendors"] = [v.strip() for v in known_vendors_raw.split("\n") if v.strip()]

        st.markdown("#### Detection Modules")
        cfg["enable_if"] = st.checkbox(
            "Isolation Forest Anomaly Detection",
            value=cfg["enable_if"],
            disabled=not SKLEARN_AVAILABLE,
            help="Requires scikit-learn." if not SKLEARN_AVAILABLE else "",
        )
        cfg["enable_structuring"]     = st.checkbox("Structuring Detection", value=cfg["enable_structuring"])
        cfg["structuring_window"]     = int(st.number_input("Structuring Window (days)", min_value=1, value=cfg["structuring_window"]))
        cfg["structuring_threshold"]  = st.number_input("Structuring Threshold ($)", min_value=0.0, value=cfg["structuring_threshold"])

    st.divider()

    # ── Entity Attribution Config ─────────────────────────────────────────────
    st.markdown("### 🎯 Entity Attribution Engine")
    st.caption("Tag transactions to specific individuals using 4 mechanical proof methods.")

    ec = cfg.setdefault("entity_config", {"card_endings": {}, "geographic_rules": {}, "behavioral_tags": {}, "p2p_identifiers": {}})

    ea_col1, ea_col2 = st.columns(2)

    with ea_col1:
        with st.expander("① Card Ending Filter — Definitive Proof", expanded=True):
            st.caption("Each physical debit card has unique last-4 digits. Any POS swipe is mechanically attributed to the cardholder.")
            card_raw = st.text_area(
                "card_ending → Entity (one per line, e.g. `5431 → Robert`)",
                "\n".join(f"{k} → {v}" for k, v in ec.get("card_endings", {}).items()) or "5431 → Robert",
                height=90, key="card_raw",
            )
            ec["card_endings"] = {}
            for line in card_raw.splitlines():
                if "→" in line:
                    k, _, v = line.partition("→")
                    k, v = k.strip(), v.strip()
                    if k and v:
                        ec["card_endings"][k] = v

        with st.expander("③ Behavioral Vendor Tagging — Spending Baseline", expanded=True):
            st.caption("Merchants exclusive to one party's lifestyle: kennel fees, specific streaming, auto shops, etc.")
            beh_raw = st.text_area(
                "keyword → Entity (one per line, e.g. `kennel → Robert`)",
                "\n".join(f"{k} → {v}" for k, v in ec.get("behavioral_tags", {}).items())
                or "kennel → Robert\npetco → Robert\npetsmart → Robert",
                height=120, key="beh_raw",
            )
            ec["behavioral_tags"] = {}
            for line in beh_raw.splitlines():
                if "→" in line:
                    k, _, v = line.partition("→")
                    k, v = k.strip(), v.strip()
                    if k and v:
                        ec["behavioral_tags"][k] = v

    with ea_col2:
        with st.expander("② Geographic Isolation — Tour Bus Advantage", expanded=True):
            st.caption("Transactions in states where one party was physically present (e.g. Robert on tour) can't belong to the other.")
            geo_raw = st.text_area(
                "Entity → locations (one per line, e.g. `Robert → Ohio`)",
                "\n".join(f"{entity} → {loc}" for entity, locs in ec.get("geographic_rules", {}).items() for loc in locs)
                or "Robert → Ohio\nRobert → Florida\nRobert → California\nPetitioner → Tennessee\nPetitioner → Texas",
                height=120, key="geo_raw",
            )
            geo_map: dict = {}
            for line in geo_raw.splitlines():
                if "→" in line:
                    entity_name, _, loc = line.partition("→")
                    entity_name, loc = entity_name.strip(), loc.strip()
                    if entity_name and loc:
                        geo_map.setdefault(entity_name, []).append(loc)
            ec["geographic_rules"] = geo_map

        with st.expander("④ P2P Transfer Tracing — Digital Wallet Diversion", expanded=True):
            st.caption("Venmo handles, CashApp tags, and phone numbers in transfer descriptions reveal the recipient.")
            p2p_raw = st.text_area(
                "identifier → Entity (one per line, e.g. `cashapp*robert → Robert`)",
                "\n".join(f"{k} → {v}" for k, v in ec.get("p2p_identifiers", {}).items())
                or "cashapp*robert → Robert\nvenmo*robert → Robert",
                height=90, key="p2p_raw",
            )
            ec["p2p_identifiers"] = {}
            for line in p2p_raw.splitlines():
                if "→" in line:
                    k, _, v = line.partition("→")
                    k, v = k.strip(), v.strip()
                    if k and v:
                        ec["p2p_identifiers"][k] = v

    st.divider()

    if tx_file is not None:
        raw_df = pd.read_csv(tx_file)
    else:
        st.info("No file uploaded — using simulation baseline.")
        raw_df = pd.DataFrame([
            {"Date": "2022-12-06", "Description": "FOGELMAN-20-235D Withdrawal",          "Amount": 1623.10},
            {"Date": "2022-12-10", "Description": "Shared Branch Withdrawal (Nashville)",  "Amount": 4000.00},
            {"Date": "2022-12-13", "Description": "Large Cash Withdrawal",                 "Amount": 2500.00},
            {"Date": "2022-12-15", "Description": "ATM Withdrawal",                        "Amount":  800.00},
            {"Date": "2022-12-16", "Description": "Cash Withdrawal",                       "Amount":  850.00},
            {"Date": "2022-12-17", "Description": "ATM Cash",                              "Amount":  900.00},
            {"Date": "2022-12-18", "Description": "Withdrawal ATM",                        "Amount":  920.00},
            {"Date": "2022-12-19", "Description": "Cash ATM",                              "Amount":  880.00},
            {"Date": "2025-05-15", "Description": "Transfer to Account ending 9172",       "Amount": np.nan},
            {"Date": "2025-05-20", "Description": "Wire Transfer - External",              "Amount": 3500.00},
            {"Date": "2025-05-21", "Description": "Coinbase Pro Purchase",                 "Amount": 5000.00},
        ])

    if st.button("▶ Process Transactions", type="primary", use_container_width=True):
        with st.spinner("Classifying and analyzing..."):
            tx_norm = normalize_transactions_v2(
                raw_df, cfg["known_accounts"], cfg["known_vendors"],
                entity_config=cfg.get("entity_config"),
            )

            aff_ts  = pd.Timestamp(cfg["affidavit_date"])
            hear_ts = pd.Timestamp(cfg["hearing_date"])
            tx_norm["Days_To_Affidavit"] = (aff_ts  - tx_norm["Date"]).dt.days
            tx_norm["Days_To_Hearing"]   = (hear_ts - tx_norm["Date"]).dt.days

            tx_filt = tx_norm[tx_norm["Confidence"].isin(cfg["conf_filter"])].copy()

            if cfg["enable_structuring"]:
                tx_filt = detect_structuring(
                    tx_filt,
                    window_days=cfg["structuring_window"],
                    amount_threshold=cfg["structuring_threshold"],
                )
            else:
                tx_filt["Is_Structured"]        = False
                tx_filt["Structured_Cluster_ID"] = None
                tx_filt["Cluster_Total"]         = 0.0
                tx_filt["Cluster_Count"]         = 0

            if cfg["enable_if"] and SKLEARN_AVAILABLE:
                tx_filt = detect_anomalies_isolation_forest(tx_filt)
            else:
                tx_filt["Is_Anomaly_IF"]  = False
                tx_filt["Anomaly_Score"]  = 0.0

            crypto_detected = tx_filt["Crypto_Indicators"].apply(len).gt(0).any()

            st.session_state["adv_tx"]             = tx_filt
            st.session_state["adv_raw"]            = tx_norm
            st.session_state["adv_crypto_detected"] = bool(crypto_detected)

        st.success(f"✓ {len(tx_filt)} transactions processed. Navigate to Advanced Detection or Exhibits.")
        st.dataframe(
            tx_filt[["Date", "Description", "Amount", "Category", "Confidence", "Rule_Triggered"]].head(20),
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: ADVANCED DETECTION
# ════════════════════════════════════════════════════════════════════════════

elif page == "Advanced Detection":
    st.title("🔍 Advanced Pattern Detection")

    if st.session_state["adv_tx"] is None:
        st.warning("No transaction data loaded. Go to **Transaction Import** first.")
        st.stop()

    tx_filt = st.session_state["adv_tx"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Fuzzy Matching",       "✓ Online" if FUZZY_AVAILABLE   else "✗ Offline")
    c2.metric("Isolation Forest",     "✓ Online" if SKLEARN_AVAILABLE else "✗ Offline")
    c3.metric("Structuring Detection","✓ Online")

    st.divider()

    # Velocity
    st.subheader("Velocity Analysis")
    v_cash  = calculate_velocity_metrics(tx_filt, "CASH_WITHDRAWAL")
    v_xfer  = calculate_velocity_metrics(tx_filt, "TRANSFER")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cash Withdrawal Velocity**")
        if v_cash:
            st.metric("Transactions / week", f"{v_cash.get('velocity_transactions_per_week', 0):.2f}")
            st.metric("Avg interval (days)",  f"{v_cash.get('avg_interval_days', 0):.1f}")
            accel = v_cash.get("velocity_acceleration", 0)
            st.metric("Acceleration", f"{accel:.0%}")
        else:
            st.info("Insufficient data.")
    with col2:
        st.markdown("**Transfer Velocity**")
        if v_xfer:
            st.metric("Transactions / week", f"{v_xfer.get('velocity_transactions_per_week', 0):.2f}")
            st.metric("Avg interval (days)",  f"{v_xfer.get('avg_interval_days', 0):.1f}")
            accel = v_xfer.get("velocity_acceleration", 0)
            st.metric("Acceleration", f"{accel:.0%}")
        else:
            st.info("Insufficient data.")

    st.divider()

    # Structuring
    st.subheader("Structuring Analysis")
    structured = tx_filt[tx_filt["Is_Structured"] == True]
    if len(structured) > 0:
        st.error(f"⚠️ STRUCTURING DETECTED: {len(structured)} transactions in {structured['Structured_Cluster_ID'].nunique()} cluster(s)")
        for cid in structured["Structured_Cluster_ID"].unique():
            cdata = structured[structured["Structured_Cluster_ID"] == cid]
            total = cdata["Cluster_Total"].iloc[0]
            dr    = f"{cdata['Date'].min().date()} to {cdata['Date'].max().date()}"
            with st.expander(f"**{cid}** — ${total:,.2f} across {len(cdata)} transactions ({dr})"):
                st.dataframe(cdata[["Date", "Description", "Amount", "Category"]], use_container_width=True)
    else:
        st.success("No structuring patterns detected.")

    st.divider()

    # Isolation Forest
    st.subheader("Isolation Forest Anomalies")
    anomalies = tx_filt[tx_filt["Is_Anomaly_IF"] == True]
    if len(anomalies) > 0:
        st.warning(f"⚠️ {len(anomalies)} statistical anomalies detected")
        st.dataframe(
            anomalies[["Date", "Description", "Amount", "Category", "Anomaly_Score"]].sort_values("Anomaly_Score"),
            use_container_width=True,
        )
    else:
        st.success("No statistical anomalies detected.")

    st.divider()

    # Crypto
    st.subheader("Cryptocurrency Activity")
    crypto_txns = tx_filt[tx_filt["Crypto_Indicators"].apply(len) > 0]
    if len(crypto_txns) > 0:
        st.error(f"🚨 {len(crypto_txns)} cryptocurrency-related transactions detected")
        st.dataframe(crypto_txns[["Date", "Description", "Amount", "Crypto_Indicators"]], use_container_width=True)
    else:
        st.success("No cryptocurrency activity detected.")

    st.divider()

    st.subheader("🎯 Entity Attribution")
    if "Entity" in tx_filt.columns:
        attributed = tx_filt[tx_filt["Entity"].notna()]
        if len(attributed) > 0:
            # Per-entity summary
            by_entity = attributed.groupby("Entity").agg(
                Transactions=("Amount", "count"),
                Total_Amount=("Amount", "sum"),
            ).reset_index()
            st.dataframe(by_entity, use_container_width=True)

            # Method breakdown
            for entity in attributed["Entity"].unique():
                ent_df = attributed[attributed["Entity"] == entity]
                with st.expander(f"**{entity}** — {len(ent_df)} transactions  |  ${ent_df['Amount'].sum():,.2f}"):
                    st.dataframe(
                        ent_df[["Date", "Description", "Amount", "Category", "Entity_Method", "Entity_Confidence"]],
                        use_container_width=True,
                    )
        else:
            st.info("No transactions attributed yet. Configure entity rules in Transaction Import.")
    else:
        st.info("Re-process transactions to enable entity attribution.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: EXHIBITS
# ════════════════════════════════════════════════════════════════════════════

elif page == "Exhibits":
    st.title("📊 Forensic Exhibits — A / B / C / D")

    if st.session_state["adv_tx"] is None:
        st.warning("No transaction data loaded. Go to **Transaction Import** first.")
        st.stop()

    tx_filt = st.session_state["adv_tx"]
    raw_df  = st.session_state.get("adv_raw", tx_filt)
    cfg     = st.session_state["adv_config"]

    # Build exhibits
    ex_a_all   = tx_filt[tx_filt["Category"] == "CASH_WITHDRAWAL"].copy()
    ex_a_known = ex_a_all[ex_a_all["Amount"].notna() & (ex_a_all["Amount"] >= cfg["thresh_cash"])].copy()
    ex_a_unk   = ex_a_all[ex_a_all["Amount"].isna()].copy()
    ex_a_total = float(ex_a_known["Amount"].sum())

    income_df = pd.DataFrame([{
        "As_Of_Date":              cfg["affidavit_date"],
        "Sworn_Monthly_Net":       4389.80,
        "Verified_Monthly_Income": 12601.44,
    }])
    income_df["Monthly_Gap"]    = income_df["Verified_Monthly_Income"] - income_df["Sworn_Monthly_Net"]
    income_df["Annualized_Gap"] = income_df["Monthly_Gap"] * 12

    ex_c_all   = tx_filt[tx_filt["Category"] == "TRANSFER"].copy()
    ex_c_known = ex_c_all[ex_c_all["Amount"].notna() & (ex_c_all["Amount"] >= cfg["thresh_xfer"])].copy()
    ex_c_unk   = ex_c_all[ex_c_all["Amount"].isna()].copy()
    ex_c_total = float(ex_c_known["Amount"].sum())

    crypto_txns    = tx_filt[tx_filt["Crypto_Indicators"].apply(len) > 0]
    structured_txns = tx_filt[tx_filt["Is_Structured"] == True]
    anomaly_txns    = tx_filt[tx_filt["Is_Anomaly_IF"]  == True]

    ex_d = pd.DataFrame([
        {"Line_Item": "Exhibit A — Cash Withdrawals",    "Amount": ex_a_total},
        {"Line_Item": "Exhibit C — Transfers",           "Amount": ex_c_total},
        {"Line_Item": "Structuring Clusters Detected",   "Amount": float(structured_txns["Structured_Cluster_ID"].nunique() if len(structured_txns) > 0 else 0)},
        {"Line_Item": "Isolation Forest Anomalies",      "Amount": float(len(anomaly_txns))},
        {"Line_Item": "Cryptocurrency Transactions",     "Amount": float(len(crypto_txns))},
        {"Line_Item": "TOTAL QUANTIFIED DISSIPATION",    "Amount": ex_a_total + ex_c_total},
    ])

    tab_a, tab_b, tab_c, tab_d, tab_export = st.tabs(
        ["Exhibit A — Cash", "Exhibit B — Income", "Exhibit C — Transfers", "Exhibit D — Summary", "Export"]
    )

    with tab_a:
        st.markdown(f"#### Cash Withdrawals ≥ ${cfg['thresh_cash']:,.0f}")
        st.metric("Total Quantified", f"${ex_a_total:,.2f}", f"{len(ex_a_known)} transactions")
        st.dataframe(ex_a_known[["Date", "Description", "Amount", "Confidence", "Rule_Triggered"]], use_container_width=True)
        if len(ex_a_unk) > 0:
            st.markdown("#### Unquantified — Require Subpoena")
            st.dataframe(ex_a_unk[["Date", "Description", "Confidence"]], use_container_width=True)

    with tab_b:
        st.markdown("#### Income Discrepancy Summary")
        st.dataframe(income_df, use_container_width=True)
        st.metric("Annualized Gap", f"${float(income_df['Annualized_Gap'].iloc[0]):,.2f}")

    with tab_c:
        st.markdown(f"#### Transfers ≥ ${cfg['thresh_xfer']:,.0f}")
        st.metric("Total Quantified", f"${ex_c_total:,.2f}", f"{len(ex_c_known)} transactions")
        st.dataframe(ex_c_known[["Date", "Description", "Amount", "Confidence", "Rule_Triggered"]], use_container_width=True)
        if len(ex_c_unk) > 0:
            st.markdown("#### Unquantified — Require Subpoena")
            st.dataframe(ex_c_unk[["Date", "Description", "Confidence"]], use_container_width=True)

    with tab_d:
        st.markdown("#### Comprehensive Dissipation Summary")
        st.dataframe(ex_d, use_container_width=True)
        st.metric("Total Quantified Dissipation", f"${ex_a_total + ex_c_total:,.2f}")

    with tab_export:
        st.markdown("#### Export Complete Forensic Packet")
        v_cash = calculate_velocity_metrics(tx_filt, "CASH_WITHDRAWAL")
        v_xfer = calculate_velocity_metrics(tx_filt, "TRANSFER")

        structuring_summary = None
        if len(structured_txns) > 0:
            structuring_summary = structured_txns.groupby("Structured_Cluster_ID").agg(
                Date_Min=("Date", "min"),
                Date_Max=("Date", "max"),
                Amount_Sum=("Amount", "sum"),
                Count=("Amount", "count"),
            ).reset_index()

        packet_bytes = make_packet_excel_v2(
            ex_a_known, income_df, ex_c_known, ex_d, raw_df,
            {**v_cash, **v_xfer},
            structuring_summary,
        )
        st.download_button(
            "📊 Download Complete Forensic Packet (XLSX)",
            data=packet_bytes,
            file_name=f"COLETTI_Forensic_Packet_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: ENHANCED SUBPOENA
# ════════════════════════════════════════════════════════════════════════════

elif page == "Enhanced Subpoena":
    st.title("⚖️ Enhanced Schedule A Generator")
    st.caption("Digital-asset-aware subpoena template with automatic crypto section injection.")

    cfg             = st.session_state["adv_config"]
    crypto_detected = st.session_state.get("adv_crypto_detected", False)

    col1, col2 = st.columns([2, 1])
    with col1:
        target = st.text_input("Target Entity", TARGET_ENTITY)
    with col2:
        force_crypto = st.checkbox(
            "Include Crypto Section",
            value=crypto_detected,
            help="Auto-enabled when cryptocurrency transactions are detected in loaded data.",
        )

    if crypto_detected:
        st.warning("🚨 Cryptocurrency transactions detected in loaded data — crypto section auto-enabled.")

    schedule_a = generate_schedule_a_v2(target, cfg["known_accounts"], force_crypto)

    st.text_area("Schedule A — Enhanced Digital Asset Discovery", value=schedule_a, height=500)

    st.download_button(
        "📥 Download Schedule A (TXT)",
        data=schedule_a,
        file_name=f"Schedule_A_Enhanced_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )
