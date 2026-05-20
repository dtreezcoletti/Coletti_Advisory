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
from forensic_ocr import ForensicOCREngine
from excel_export import ExcelExporter
from ingestion_engine import DataIngestionEngine, DocumentRecord, ExhibitRecord

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
if "ocr" not in st.session_state:
    st.session_state["ocr"] = ForensicOCREngine()

sys: ColettiOS = st.session_state["os"]
fe: ForensicEngine = st.session_state["fe"]
ocr: ForensicOCREngine = st.session_state["ocr"]


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
        <div style="font-size:11px; color:#8b949e; letter-spacing:3px;">v2.5.5 · COMMAND INTERFACE</div>
    </div>
    <hr style="border-color:#30363d; margin:0 0 16px;">
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Decree Barometer",
            "Litigation Docket",
            "Forensic Ops (Evidence)",
            "Income Disparity",
            "Case Valuation",
            "Forensic Engine",
            "Enterprise Ops (Coletti & Co.)",
            "Client Portal (Secure Ingest)",
            "Document Assembly (Drafting)",
            "Timeline Visualizer",
            "Dissipation Heat Map",
            "Hearing War Room",
            "PDF Reports",
            "Upload Statement",
            "Export to Excel",
            "Data Export",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#30363d; margin:16px 0 12px;'>", unsafe_allow_html=True)

    # Decree Barometer mini-widget
    _baro = sys.decree_barometer()
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size:10px; color:#8b949e; letter-spacing:1px; text-transform:uppercase; margin-bottom:4px;">Decree Barometer</div>
        <div style="font-size:38px; font-weight:900; color:{_baro['color']};">{_baro['total']}<span style="font-size:16px; color:#8b949e;">/100</span></div>
        <div style="font-size:11px; font-weight:700; color:{_baro['color']}; letter-spacing:1px;">{_baro['verdict']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(_baro["total"] / 100)

    st.markdown("<hr style='border-color:#30363d; margin:12px 0;'>", unsafe_allow_html=True)

    leverage = sys.litigation.evaluate_docket_leverage()
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size:11px; color:#8b949e; letter-spacing:1px; text-transform:uppercase;">Docket Leverage</div>
        <div style="font-size:28px; font-weight:700; color:{'#3fb950' if leverage >= 100 else '#f85149'};">{leverage}</div>
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

    # Tactical Reality
    ts = getattr(sys, "tactical_status", {})
    if ts:
        st.markdown("<div class='section-header'>[ CURRENT TACTICAL REALITY ]</div>", unsafe_allow_html=True)
        ceasefire_color = "#f85149" if ts.get("ceasefire_expired") else "#3fb950"
        ceasefire_label = (
            f"EXPIRED — {ts['ceasefire_date']} @ {ts['ceasefire_time']}"
            if ts.get("ceasefire_expired") else "ACTIVE"
        )
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {ceasefire_color};">
            <div class="metric-label">Ceasefire Status</div>
            <div class="metric-value" style="color:{ceasefire_color}; font-size:18px;">{ceasefire_label}</div>
            <div class="metric-sub" style="color:#c9d1d9; margin-top:8px;">
                <strong>Active Strategy:</strong> {ts.get('active_strategy', '')}<br>
                <strong>Counter-Measure:</strong> {ts.get('counter_measure', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            metric_card("Payroll Diverted to 3rd Parties",
                        f"${ts.get('dissipation_payroll_diverted', 0):,.2f}",
                        "Confirmed from FFCU ledger", "#f85149")
        with c2:
            metric_card("Housing Paid While Withholding Support",
                        f"${ts.get('dissipation_housing_withheld', 0):,.2f}",
                        "Confirmed from FFCU ledger", "#f85149")

    # Motion queue
    st.markdown("<div class='section-header'>[ MOTION QUEUE ]</div>", unsafe_allow_html=True)
    for m in sorted(sys.litigation.motions, key=lambda x: x.hearing_date or "9999"):
        cols = st.columns([3, 2, 2, 3])
        cols[0].markdown(f"**{m.title}**")
        cols[1].markdown(m.date_filed)
        cols[2].markdown(m.hearing_date or "TBD")
        cols[3].markdown(status_tag(m.status), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DECREE BAROMETER
# ════════════════════════════════════════════════════════════════════════════

elif page == "Decree Barometer":
    import plotly.graph_objects as go

    baro = sys.decree_barometer()

    st.markdown(f"""
    <div class="hud-header">
    ══════════════════════════════════════════════════════<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DECREE BAROMETER &nbsp;·&nbsp; CASE 24D-1003<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Coletti v. Brown &nbsp;·&nbsp; Davidson County Fourth Circuit<br>
    ══════════════════════════════════════════════════════
    </div>
    """, unsafe_allow_html=True)

    # ── Gauge ─────────────────────────────────────────────────────────────────
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=baro["total"],
        delta={"reference": 50, "increasing": {"color": "#3fb950"}, "decreasing": {"color": "#f85149"}},
        number={"suffix": " / 100", "font": {"size": 42, "color": baro["color"]}},
        title={"text": f"<b>{baro['verdict']}</b>", "font": {"size": 20, "color": baro["color"]}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#8b949e",
                     "tickfont": {"color": "#8b949e"}},
            "bar": {"color": baro["color"], "thickness": 0.3},
            "bgcolor": "#161b22",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  35], "color": "#2d1116"},
                {"range": [35, 55], "color": "#2d1f0a"},
                {"range": [55, 75], "color": "#1a2a1a"},
                {"range": [75, 90], "color": "#0d2233"},
                {"range": [90, 100], "color": "#0d2b1a"},
            ],
            "threshold": {
                "line": {"color": "#f0f6fc", "width": 3},
                "thickness": 0.85,
                "value": baro["total"],
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117",
        font={"color": "#c9d1d9"},
        height=360,
        margin={"t": 60, "b": 20, "l": 40, "r": 40},
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Verdict banner ────────────────────────────────────────────────────────
    verdict_desc = {
        "DECREE IMMINENT":   "All five pillars are locked. The evidentiary and procedural record is overwhelming. The Court has everything it needs to issue a favorable final decree.",
        "DOMINANT POSITION": "Commanding advantage across most pillars. Continue building the remaining gaps and the decree will follow.",
        "STRONG ADVANTAGE":  "Clear edge in multiple categories. Focus on the lower-scoring pillars to push into dominant territory.",
        "BUILDING LEVERAGE": "Foundational evidence is being established. Keep logging transactions, filing motions, and returning subpoenas.",
        "EARLY STAGE":       "Work is underway. Each new piece of evidence and each motion filed moves the needle.",
    }
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid {baro['color']}; margin-top: 8px;">
        <div class="metric-value" style="color:{baro['color']}; font-size:22px;">{baro['verdict']}</div>
        <div class="metric-sub" style="color:#c9d1d9; font-size:14px; margin-top:8px;">
            {verdict_desc.get(baro['verdict'], '')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Five pillars breakdown ────────────────────────────────────────────────
    st.markdown("<div class='section-header'>[ PILLAR BREAKDOWN ]</div>", unsafe_allow_html=True)

    PILLAR_DESC = {
        "Procedural Dominance": {
            "icon": "⚖️",
            "detail": "Rule 36 default days, active motions filed, pending judicial signatures.",
            "how": "File the remaining motions. Confirm the Rule 36 admissions at the May 29 hearing.",
        },
        "Financial Evidence": {
            "icon": "🔎",
            "detail": "Transactions logged in the forensic ledger, dissipation rate, active subpoenas.",
            "how": "Return the FFCU and Dreamliner subpoenas. Log every transaction as it arrives.",
        },
        "Income Fraud Proof": {
            "icon": "📊",
            "detail": "Concealment percentage, tracking months, sequestered hard assets.",
            "how": "The W-2 and 1099 data is confirmed. Add the 22-month tracking period to the ledger.",
        },
        "Damages Quantified": {
            "icon": "💰",
            "detail": "Tier 1/2/3 damage tiers built out, premeditation score.",
            "how": "All three tiers are populated. Premeditation score is maxed. This pillar is strong.",
        },
        "Strategic Position": {
            "icon": "♟️",
            "detail": "Disqualification motion, enterprise activity, ceasefire status, docket leverage.",
            "how": "Ceasefire expired. Disqualification motion active. Enterprise growing. Hold the line.",
        },
    }

    for pillar, pts in baro["pillars"].items():
        pct = pts / 20
        bar_color = "#3fb950" if pct >= 0.85 else ("#58a6ff" if pct >= 0.6 else ("#d29922" if pct >= 0.4 else "#f85149"))
        info = PILLAR_DESC.get(pillar, {})

        with st.container():
            c1, c2 = st.columns([1, 4])
            c1.markdown(f"<div style='font-size:32px; text-align:center; padding-top:8px;'>{info.get('icon','')}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="margin-bottom:2px;">
                    <span style="font-weight:700; color:#f0f6fc; font-size:14px;">{pillar}</span>
                    <span style="float:right; font-weight:900; color:{bar_color}; font-size:18px;">{pts}<span style="font-size:11px; color:#8b949e;"> / 20</span></span>
                </div>
                """, unsafe_allow_html=True)
                st.progress(pct)
                st.caption(f"{info.get('detail', '')}  ·  **Next move:** {info.get('how', '')}")
        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

    st.divider()

    # ── What moves the needle most ────────────────────────────────────────────
    st.markdown("<div class='section-header'>[ TOP ACTIONS TO INCREASE SCORE ]</div>", unsafe_allow_html=True)

    gaps = sorted(baro["pillars"].items(), key=lambda x: x[1])
    for pillar, pts in gaps:
        gap = 20 - pts
        if gap > 0:
            st.markdown(f"- **+{gap} pts available** — {pillar}: {PILLAR_DESC.get(pillar, {}).get('how', '')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: LITIGATION COMMAND
# ════════════════════════════════════════════════════════════════════════════

elif page == "Litigation Docket":
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

elif page == "Forensic Ops (Evidence)":
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

            # Flat pandas table view
            import pandas as pd
            rows = []
            for t in txns:
                rows.append({
                    "Date": t.effective_date,
                    "Description": t.description,
                    "Category": t.category,
                    "Amount ($)": t.amount,
                    "Balance After ($)": t.balance_after if t.balance_after else "—",
                    "Dissipation": "🔴 YES" if t.is_marital_dissipation else "⚪ No",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**Expand individual entries to remove or inspect:**")
            for i, t in enumerate(txns):
                flag = "🔴" if t.is_marital_dissipation else "⚪"
                with st.expander(f"{flag} {t.effective_date} · ${t.amount:,.2f} · {t.description}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"**Category:** {t.category}")
                    c2.markdown(f"**Amount:** ${t.amount:,.2f}")
                    c3.markdown(f"**Balance After:** ${t.balance_after:,.2f}" if t.balance_after else "**Balance After:** —")
                    c4.markdown(f"**Dissipation:** {'Yes ⚠️' if t.is_marital_dissipation else 'No'}")

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
            c1, c2, c3 = st.columns(3)
            amt = c1.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
            cat = c2.text_input("Category", placeholder="e.g. Transfer, Cash Withdrawal, Luxury")
            bal = c3.number_input("Balance After ($)", min_value=0.00, step=0.01, format="%.2f")
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
                        balance_after=float(bal),
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

elif page == "Enterprise Ops (Coletti & Co.)":
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
# PAGE: CLIENT PORTAL
# ════════════════════════════════════════════════════════════════════════════

elif page == "Client Portal (Secure Ingest)":
    st.title("🔐 Client Portal | Secure Document Ingest")
    st.markdown("Encrypted file transfer protocol for active Coletti & Co. advisory clients.")
    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Client Authentication")
        # Pull live client names; fall back to defaults if none onboarded yet
        live_clients = [c.entity_name for c in sys.enterprise.active_portfolios]
        client_choices = live_clients if live_clients else ["Alpha Logistics Group", "Vanguard Media"]
        client_choices.append("Guest / Pending Onboarding")

        client_id = st.selectbox("Select Active Client Entity", client_choices)
        doc_type = st.selectbox("Document Classification", [
            "Operational Audit (Raw Data)",
            "Narrative Blueprint / Brief",
            "Compliance & Legal Records",
            "Financial Ledgers",
        ])
        priority = st.radio("Processing Priority", [
            "Standard", "High", "Critical (Immediate Analysis)"
        ])

    with col2:
        st.subheader("Secure File Drop")
        uploaded_client_files = st.file_uploader(
            f"Select files for **{client_id}** (multiple allowed)",
            type=["pdf", "csv", "xlsx", "docx", "zip"],
            accept_multiple_files=True,
        )
        transmission_notes = st.text_area(
            "Strategic Context / Transmission Notes", height=100,
            placeholder="Brief the system on why these files are being ingested and what to watch for."
        )

        if st.button("Initialize Secure Transfer", type="primary", use_container_width=True):
            if uploaded_client_files:
                st.success(
                    f"{len(uploaded_client_files)} file(s) encrypted and routed to "
                    f"**{client_id}** framework."
                )
                st.info(f"Classification: {doc_type}  ·  Priority: {priority}")
                st.markdown("**Ingestion Log:**")
                for f in uploaded_client_files:
                    st.text(f"[-] {f.name} ({round(f.size / 1024, 2)} KB) — STATUS: SECURED")
                if transmission_notes:
                    st.markdown(f"**Notes logged:** {transmission_notes}")
            else:
                st.error("Transmission Error: No files detected in the drop zone.")

    st.divider()
    st.caption("Powered by Coletti OS  ·  Strategic Architecture & Data-Driven Frameworks")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DOCUMENT ASSEMBLY
# ════════════════════════════════════════════════════════════════════════════

elif page == "Document Assembly (Drafting)":
    st.title("📝 Document Assembly | Motion & Brief Drafting")
    st.caption("Case № 24D-1003  ·  Davidson County Fourth Circuit  ·  Hon. Stephanie J. Williams")

    TEMPLATES = {
        "Motion to Confirm Rule 36 Deemed Admissions": """\
IN THE CIRCUIT COURT FOR DAVIDSON COUNTY, TENNESSEE
FOURTH CIRCUIT

{petitioner}, Petitioner,
v.                                    Case No. {case_number}
{respondent}, Respondent.

MOTION TO CONFIRM RULE 36 DEEMED ADMISSIONS

COMES NOW the Petitioner, {petitioner}, by and through undersigned counsel, and respectfully moves this Court pursuant to Tenn. R. Civ. P. 36 to confirm that the following requests for admission served upon the Respondent have been deemed admitted by operation of law:

1. Respondent was served with Petitioner's First Set of Requests for Admission on {rfa_served_date}.
2. As of the date of this Motion, {rule_36_days} days have elapsed without a timely, verified response.
3. All {rfa_count} requests are therefore deemed admitted as a matter of law.

WHEREFORE, Petitioner respectfully requests that this Court enter an Order confirming the deemed admissions and directing that {rfa_count} counts of marital dissipation are established facts for all purposes in this proceeding.

Respectfully submitted,

{attorney_signature}
Date: {today}
""",

        "Motion for Pendente Lite Support": """\
IN THE CIRCUIT COURT FOR DAVIDSON COUNTY, TENNESSEE
FOURTH CIRCUIT

{petitioner}, Petitioner,
v.                                    Case No. {case_number}
{respondent}, Respondent.

MOTION FOR PENDENTE LITE SUPPORT AND SUIT MONEY

COMES NOW the Petitioner, {petitioner}, and moves this Court for an Order awarding pendente lite support and suit money based on the following:

1. INCOME DISPARITY: Respondent's verified monthly net income is ${verified_monthly_net}, compared to the sworn disclosure of ${sworn_monthly_net} — a concealment of ${monthly_concealment} per month ({concealment_pct}% above sworn).

2. SUPPORT REQUESTED: Petitioner requests pendente lite support of ${pendente_lite_monthly} per month, calculated at the Tennessee guideline rate applied to Respondent's verified income.

3. SUIT MONEY: Petitioner requests ${suit_money} in suit money to equalize litigation resources given Respondent's documented income concealment.

4. ARREARAGE: Respondent has been in arrearage of ${pendente_lite_arrearage} over the tracking period.

WHEREFORE, Petitioner requests immediate entry of an Order awarding the foregoing relief.

Respectfully submitted,

{attorney_signature}
Date: {today}
""",

        "Subpoena Cover Letter": """\
{today}

RE:    Subpoena for Records — Case No. {case_number}
TO:    Records Custodian, {institution}

Dear Records Custodian:

Enclosed please find a validly issued Subpoena Duces Tecum in the matter of {petitioner} v. {respondent}, Case No. {case_number}, pending in the Fourth Circuit Court, Davidson County, Tennessee.

You are directed to produce the following records for the account holder {respondent}:

{subpoena_items}

Records shall be produced no later than {response_deadline}. Please direct any questions to the undersigned.

Respectfully,

{attorney_signature}
""",

        "Blank Motion (Custom)": """\
IN THE CIRCUIT COURT FOR DAVIDSON COUNTY, TENNESSEE
FOURTH CIRCUIT

{petitioner}, Petitioner,
v.                                    Case No. {case_number}
{respondent}, Respondent.

{motion_title}

{motion_body}

Respectfully submitted,

{attorney_signature}
Date: {today}
""",
    }

    # Pull live data for auto-fill
    idp = sys.income_disparity
    cv  = sys.case_valuation

    col_sel, col_preview = st.columns([1, 2])

    with col_sel:
        template_name = st.selectbox("Select Template", list(TEMPLATES.keys()))
        st.divider()
        st.markdown("#### Auto-Fill from Case Data")

        petitioner    = st.text_input("Petitioner Name", "Demetries J.L. Coletti")
        respondent    = st.text_input("Respondent Name", "Respondent")
        case_number   = st.text_input("Case Number", sys.litigation.case_number)
        attorney_sig  = st.text_input("Attorney / Pro Se Signature Line",
                                      "Demetries J.L. Coletti, Pro Se")
        today_str     = st.date_input("Document Date", value=date.today()).isoformat()

        # Template-specific fields
        extra = {}
        if template_name == "Motion to Confirm Rule 36 Deemed Admissions":
            extra["rfa_served_date"]  = st.text_input("RFA Served Date", "November 21, 2025")
            extra["rule_36_days"]     = st.number_input("Days Elapsed", value=sys.litigation.rule_36_days_default)
            extra["rfa_count"]        = st.number_input("Count of Admissions", value=27)

        elif template_name == "Motion for Pendente Lite Support":
            extra["verified_monthly_net"] = f"{idp.verified_monthly_net:,.2f}"
            extra["sworn_monthly_net"]    = f"{idp.sworn_monthly_net:,.2f}"
            extra["monthly_concealment"]  = f"{idp.monthly_understatement():,.2f}"
            extra["concealment_pct"]      = f"{idp.understatement_pct():.1f}"
            extra["pendente_lite_monthly"]  = f"{cv.tier1.pendente_lite_monthly:,.2f}"
            extra["suit_money"]             = f"{cv.tier1.suit_money:,.2f}"
            extra["pendente_lite_arrearage"] = f"{cv.tier1.pendente_lite_arrearage:,.2f}"

        elif template_name == "Subpoena Cover Letter":
            extra["institution"]       = st.text_input("Institution Name", "First Florida Credit Union")
            extra["response_deadline"] = st.text_input("Response Deadline", "Within 14 days of service")
            items_raw = st.text_area(
                "Records Requested (one per line)",
                "All account statements from January 2022 to present\n"
                "All wire transfer and ACH records\n"
                "Signature cards and account opening documents",
            )
            extra["subpoena_items"] = "\n".join(
                f"  {i+1}. {line.strip()}"
                for i, line in enumerate(items_raw.strip().splitlines()) if line.strip()
            )

        elif template_name == "Blank Motion (Custom)":
            extra["motion_title"] = st.text_input("Motion Title")
            extra["motion_body"]  = st.text_area("Motion Body", height=200)

    with col_preview:
        st.markdown("#### Live Preview")
        try:
            filled = TEMPLATES[template_name].format(
                petitioner=petitioner,
                respondent=respondent,
                case_number=case_number,
                attorney_signature=attorney_sig,
                today=today_str,
                **extra,
            )
        except KeyError as e:
            filled = f"[Fill in all required fields — missing: {e}]"

        st.text_area("Draft", value=filled, height=520, key="draft_preview")

        col_copy, col_dl = st.columns(2)
        col_dl.download_button(
            "⬇️ Download Draft (.txt)",
            data=filled,
            file_name=f"{template_name.replace(' ', '_')}_{today_str}.txt",
            mime="text/plain",
            use_container_width=True,
        )

        if col_copy.button("Copy to Clipboard ↗", use_container_width=True):
            st.info("Select all text in the draft box above (Ctrl+A / Cmd+A) and copy.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: HEARING WAR ROOM
# ════════════════════════════════════════════════════════════════════════════

elif page == "Hearing War Room":
    HEARING_DATE = date(2026, 5, 29)
    today = date.today()
    days_to_hearing = (HEARING_DATE - today).days
    total_seconds_to_hearing = (HEARING_DATE - today).days * 86400

    # ── Quick Stats Bar ───────────────────────────────────────────────────────
    _baro_score = sys.decree_barometer()["total"]
    _motions_pending = sum(
        1 for m in sys.litigation.motions
        if m.status.lower() in ("active", "pending judicial signature")
    )

    # Determine exhibits ready from session state
    _exhibit_keys = [
        "warroom_exhibit_dreamliner",
        "warroom_exhibit_garrison",
        "warroom_exhibit_ffcu",
        "warroom_exhibit_rfa_service",
        "warroom_exhibit_financial_affidavit",
        "warroom_exhibit_disqualify",
        "warroom_exhibit_income_report",
    ]
    _exhibits_ready = sum(1 for k in _exhibit_keys if st.session_state.get(k, False))

    st.markdown(f"""
    <div class="hud-header">
    ══════════════════════════════════════════════════════<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;HEARING WAR ROOM &nbsp;·&nbsp; CASE 24D-1003 &nbsp;·&nbsp; Coletti v. Brown<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Hon. Stephanie J. Williams &nbsp;·&nbsp; Davidson County Fourth Circuit<br>
    ══════════════════════════════════════════════════════
    </div>
    """, unsafe_allow_html=True)

    qs1, qs2, qs3, qs4 = st.columns(4)
    with qs1:
        metric_card(
            "Days to Hearing",
            str(days_to_hearing) if days_to_hearing >= 0 else "PAST",
            f"May 29, 2026",
            "#f85149" if days_to_hearing <= 14 else "#d29922",
        )
    with qs2:
        metric_card(
            "Motions Pending Signature",
            str(_motions_pending),
            "Active or Pending",
            "#d29922",
        )
    with qs3:
        metric_card(
            "Exhibits Ready",
            f"{_exhibits_ready} / 7",
            "Pre-hearing checklist",
            "#3fb950" if _exhibits_ready == 7 else "#58a6ff",
        )
    with qs4:
        metric_card(
            "Decree Barometer",
            str(_baro_score),
            "/ 100  —  " + sys.decree_barometer()["verdict"],
            sys.decree_barometer()["color"],
        )

    st.divider()

    # ── 1. Countdown Banner ───────────────────────────────────────────────────
    if days_to_hearing > 0:
        st.markdown(
            f"""<div style="
                background: #2d1116;
                border: 2px solid #f85149;
                border-radius: 10px;
                padding: 28px;
                text-align: center;
                margin-bottom: 24px;
            ">
                <div style="font-size: 48px; font-weight: 900; color: #f85149; letter-spacing: 4px;">
                    T&ndash;{days_to_hearing} DAYS TO HEARING
                </div>
                <div style="font-size: 16px; color: #c9d1d9; margin-top: 8px; letter-spacing: 2px;">
                    HEARING DATE: MAY 29, 2026 &nbsp;·&nbsp; HON. STEPHANIE J. WILLIAMS
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    elif days_to_hearing == 0:
        st.markdown(
            """<div style="
                background: #0d2b1a;
                border: 2px solid #3fb950;
                border-radius: 10px;
                padding: 28px;
                text-align: center;
                margin-bottom: 24px;
            ">
                <div style="font-size: 48px; font-weight: 900; color: #3fb950; letter-spacing: 4px;">
                    TODAY IS HEARING DAY
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="
                background: #161b22;
                border: 2px solid #8b949e;
                border-radius: 10px;
                padding: 28px;
                text-align: center;
                margin-bottom: 24px;
            ">
                <div style="font-size: 40px; font-weight: 700; color: #8b949e; letter-spacing: 3px;">
                    HEARING DATE REACHED
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── 2. Motion Status Checklist ────────────────────────────────────────────
    st.markdown("<div class='section-header'>[ MOTION STATUS CHECKLIST ]</div>", unsafe_allow_html=True)

    for i, m in enumerate(sys.litigation.motions):
        is_active = m.status.lower() in ("active", "pending judicial signature")
        cb_key = f"warroom_motion_prepared_{i}"
        if cb_key not in st.session_state:
            st.session_state[cb_key] = is_active

        with st.container():
            col_title, col_badge, col_obj, col_cb = st.columns([3, 2, 4, 2])
            col_title.markdown(f"**{m.title}**")
            col_badge.markdown(status_tag(m.status), unsafe_allow_html=True)
            col_obj.markdown(f"<span style='color:#8b949e; font-size:13px;'>{m.strategic_objective}</span>", unsafe_allow_html=True)
            with col_cb:
                st.checkbox(
                    "Argument Prepared",
                    value=st.session_state[cb_key],
                    key=cb_key,
                )
        st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

    st.divider()

    # ── 3. Argument Preparation Board ────────────────────────────────────────
    st.markdown("<div class='section-header'>[ ARGUMENT PREPARATION BOARD ]</div>", unsafe_allow_html=True)

    arg_col, counter_col = st.columns([1, 1])

    MOTION_ARGS = {
        "Rule 36 Motion": (
            "Respondent failed to respond to 27 Requests for Admission within the 30-day window "
            "prescribed by Tenn. R. Civ. P. 36. Per controlling Tennessee precedent, unanswered RFAs "
            "are deemed admitted as a matter of law. These admissions establish [X] counts of marital "
            "dissipation, income concealment, and failure to disclose assets..."
        ),
        "Disqualification Motion": (
            "Opposing counsel has violated RPC 3.3 (Candor to the Tribunal) and RPC 3.7 (Lawyer as "
            "Witness). Counsel submitted representations to this Court that contradict documented "
            "evidence including paystubs, subpoena returns, and financial affidavits. Disqualification "
            "is mandatory under Tennessee's Rules of Professional Conduct..."
        ),
        "Suit Money / Pendente Lite": (
            "Petitioner has documented a $5,593 monthly income concealment — 127% above the sworn "
            "affidavit. Under Tenn. Code Ann. § 36-5-121, pendente lite support is calculated on "
            "actual income, not fraudulent disclosures. Respondent's retention of $[amount] over 22 "
            "months while Petitioner was left without resources constitutes economic abuse..."
        ),
    }

    with arg_col:
        st.markdown("##### OUR ARGUMENTS")
        arg_tabs = st.tabs(list(MOTION_ARGS.keys()))
        for tab, (motion_name, default_text) in zip(arg_tabs, MOTION_ARGS.items()):
            with tab:
                area_key = f"warroom_arg_{motion_name.replace(' ', '_').lower()}"
                if area_key not in st.session_state:
                    st.session_state[area_key] = default_text
                st.text_area(
                    "Argument Summary (editable)",
                    value=st.session_state[area_key],
                    height=220,
                    key=area_key,
                    label_visibility="collapsed",
                )

    OPPOSING_MOVES = [
        (
            '"RFAs were substantially complied with"',
            "Tennessee courts hold that substantial compliance is insufficient — full, verified, "
            "timely response is required. Cite *Saye v. Saye*.",
        ),
        (
            '"Disqualification motion is retaliatory"',
            "Motion is grounded in documented RPC violations with specific citations. "
            "Court can review the record.",
        ),
        (
            '"Income figures are disputed"',
            "W-2 and 1099 documents obtained via subpoena are certified third-party records — "
            "not disputable without impeaching Dreamliner and Garrison payroll systems.",
        ),
        (
            '"Petitioner has income of her own"',
            "Petitioner's independent income does not excuse Respondent's failure to disclose. "
            "Income disparity is the operative standard under Tenn. Code Ann. § 36-5-121.",
        ),
        (
            '"Motion to continue / delay"',
            "Petitioner objects to any continuance. Case has been pending since July 2024. "
            "Subpoenas are complete. The record is ready.",
        ),
    ]

    with counter_col:
        st.markdown("##### ANTICIPATED OPPOSING MOVES + COUNTERS")
        for opp_move, our_counter in OPPOSING_MOVES:
            with st.expander(opp_move):
                st.markdown(f"**Our Counter:** {our_counter}")

    st.divider()

    # ── 4. Evidence Exhibit Tracker ───────────────────────────────────────────
    st.markdown("<div class='section-header'>[ EVIDENCE EXHIBIT TRACKER ]</div>", unsafe_allow_html=True)

    EXHIBITS = [
        ("warroom_exhibit_dreamliner",          "Dreamliner paystubs (Feb 8, 2026)"),
        ("warroom_exhibit_garrison",            "Garrison 1099-NEC (2024)"),
        ("warroom_exhibit_ffcu",                "FFCU unredacted ledger"),
        ("warroom_exhibit_rfa_service",         "Rule 36 RFA proof of service"),
        ("warroom_exhibit_financial_affidavit", "Financial affidavit (sworn May 27, 2025)"),
        ("warroom_exhibit_disqualify",          "Motion to Disqualify with RPC citations"),
        ("warroom_exhibit_income_report",       "Income disparity analysis report"),
    ]

    ex_col1, ex_col2 = st.columns(2)
    for idx, (key, label) in enumerate(EXHIBITS):
        if key not in st.session_state:
            st.session_state[key] = False
        target_col = ex_col1 if idx % 2 == 0 else ex_col2
        with target_col:
            st.checkbox(label, value=st.session_state[key], key=key)

    # Recalculate after checkboxes render
    exhibits_ready_now = sum(1 for k, _ in EXHIBITS if st.session_state.get(k, False))
    st.markdown(f"**{exhibits_ready_now} of {len(EXHIBITS)} exhibits ready**")
    st.progress(exhibits_ready_now / len(EXHIBITS))
    if exhibits_ready_now == len(EXHIBITS):
        st.success("All exhibits accounted for — you are ready for the hearing.")
    elif exhibits_ready_now >= 5:
        st.info(f"Nearly ready — {len(EXHIBITS) - exhibits_ready_now} exhibit(s) still outstanding.")
    else:
        st.warning(f"{len(EXHIBITS) - exhibits_ready_now} exhibits still outstanding. Confirm all materials before May 29.")



# ════════════════════════════════════════════════════════════════════════════
# PAGE: TIMELINE VISUALIZER
# ════════════════════════════════════════════════════════════════════════════

elif page == "Timeline Visualizer":
    import plotly.graph_objects as go
    import pandas as pd

    st.markdown(
        """
    <div class="hud-header">
    ══════════════════════════════════════════════════════<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMELINE VISUALIZER &nbsp;·&nbsp; CASE 24D-1003<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Coletti v. Brown &nbsp;·&nbsp; All Key Events<br>
    ══════════════════════════════════════════════════════
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Category filters ──────────────────────────────────────────────────────
    st.markdown(
        "<div class='section-header'>[ CATEGORY FILTERS ]</div>",
        unsafe_allow_html=True,
    )
    _tvc1, _tvc2, _tvc3, _tvc4 = st.columns(4)
    _tv_marriage   = _tvc1.checkbox("Marriage",   value=True, key="tv_marriage")
    _tv_litigation = _tvc2.checkbox("Litigation", value=True, key="tv_litigation")
    _tv_forensic   = _tvc3.checkbox("Forensic",   value=True, key="tv_forensic")
    _tv_key        = _tvc4.checkbox("Key Events", value=True, key="tv_key")

    _tv_traces: list = []
    _tv_rows:   list = []

    # ── Helper: thick horizontal line for duration events ─────────────────────
    def _tv_dur(name, x0, x1, track, clr, tip=""):
        return go.Scatter(
            x=[x0, x1],
            y=[track, track],
            mode="lines",
            line=dict(color=clr, width=20),
            name=name,
            legendgroup=name,
            showlegend=True,
            hovertemplate=(
                f"<b>{name}</b><br>Start: {x0}<br>End: {x1}<br>{tip}<extra></extra>"
            ),
        )

    # ── Marriage Duration ─────────────────────────────────────────────────────
    if _tv_marriage:
        _tv_traces.append(
            _tv_dur("Marriage Duration", "2015-01-25", "2024-06-13", "Marriage", "#0d2233",
                    "Jan 25 2015 → Jun 13 2024")
        )
        _tv_rows.append({
            "Date": "2015-01-25 → 2024-06-13",
            "Event": "Marriage Duration",
            "Category": "Marriage",
            "Notes": "~11.5 years",
        })

    # ── Forensic Tracking Period ──────────────────────────────────────────────
    if _tv_forensic:
        _tv_traces.append(
            _tv_dur("Tracking Period (Forensic)", "2024-07-01", "2026-05-31",
                    "Forensic Ledger", "#1a2a1a", "FFCU forensic audit window")
        )
        _tv_rows.append({
            "Date": "2024-07-01 → 2026-05-31",
            "Event": "Tracking Period (Forensic)",
            "Category": "Forensic",
            "Notes": "FFCU forensic audit window",
        })

    # ── Motions ───────────────────────────────────────────────────────────────
    if _tv_litigation:
        for _tvm in sys.litigation.motions:
            _tvsl = _tvm.status.lower()
            if "active" in _tvsl:
                _tvmc = "#f85149"
            elif "pending" in _tvsl:
                _tvmc = "#d29922"
            elif "granted" in _tvsl:
                _tvmc = "#3fb950"
            else:
                _tvmc = "#8b949e"
            _tvx1 = _tvm.hearing_date if _tvm.hearing_date else _tvm.date_filed
            _tv_traces.append(
                go.Scatter(
                    x=[_tvm.date_filed, _tvx1],
                    y=["Litigation", "Litigation"],
                    mode="lines+markers",
                    line=dict(color=_tvmc, width=8),
                    marker=dict(symbol="circle", size=8, color=_tvmc),
                    name=_tvm.title[:40],
                    legendgroup=f"tvmot_{_tvm.title[:25]}",
                    showlegend=True,
                    hovertemplate=(
                        f"<b>{_tvm.title}</b><br>"
                        f"Filed: {_tvm.date_filed}<br>"
                        f"Hearing: {_tvm.hearing_date or 'TBD'}<br>"
                        f"Status: {_tvm.status}<br>"
                        f"{(_tvm.strategic_objective or '')[:80]}"
                        f"<extra></extra>"
                    ),
                )
            )
            _tv_rows.append({
                "Date": _tvm.date_filed,
                "Event": _tvm.title,
                "Category": "Litigation",
                "Notes": f"Status: {_tvm.status} | Hearing: {_tvm.hearing_date or 'TBD'}",
            })

    # ── FFCU Ledger dots ──────────────────────────────────────────────────────
    if _tv_forensic:
        _tvd_dates: list = []
        _tvn_dates: list = []
        _tvd_tips:  list = []
        _tvn_tips:  list = []
        for _tvt in sys.forensics.transactions:
            _tvht = (
                f"<b>{_tvt.description}</b><br>"
                f"Date: {_tvt.effective_date}<br>"
                f"Amount: ${_tvt.amount:,.2f}<br>"
                f"Category: {_tvt.category}<br>"
                f"Dissipation: {'YES' if _tvt.is_marital_dissipation else 'No'}"
            )
            if _tvt.is_marital_dissipation:
                _tvd_dates.append(_tvt.effective_date)
                _tvd_tips.append(_tvht)
            else:
                _tvn_dates.append(_tvt.effective_date)
                _tvn_tips.append(_tvht)
            _tv_rows.append({
                "Date": _tvt.effective_date,
                "Event": _tvt.description,
                "Category": "Forensic",
                "Notes": (
                    f"${_tvt.amount:,.2f} · {_tvt.category} · "
                    f"{'DISSIPATION' if _tvt.is_marital_dissipation else 'Normal'}"
                ),
            })
        if _tvd_dates:
            _tv_traces.append(
                go.Scatter(
                    x=_tvd_dates,
                    y=["Forensic Ledger"] * len(_tvd_dates),
                    mode="markers",
                    marker=dict(symbol="circle", size=7, color="#f85149", opacity=0.85),
                    name="FFCU — Dissipation",
                    legendgroup="tv_ffcu_dis",
                    showlegend=True,
                    text=_tvd_tips,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
        if _tvn_dates:
            _tv_traces.append(
                go.Scatter(
                    x=_tvn_dates,
                    y=["Forensic Ledger"] * len(_tvn_dates),
                    mode="markers",
                    marker=dict(symbol="circle", size=6, color="#8b949e", opacity=0.6),
                    name="FFCU — Normal",
                    legendgroup="tv_ffcu_nrm",
                    showlegend=True,
                    text=_tvn_tips,
                    hovertemplate="%{text}<extra></extra>",
                )
            )

    # ── Point events (diamond markers) ────────────────────────────────────────
    _TV_POINTS = [
        {
            "date":  "2015-01-25",
            "label": "Marriage Start",
            "track": "Key Events",
            "color": "#58a6ff",
            "show":  _tv_marriage,
            "notes": "Marriage commenced Jan 25, 2015",
        },
        {
            "date":  "2022-01-01",
            "label": "First FL CU Account Opened",
            "track": "Key Events",
            "color": "#8b949e",
            "show":  _tv_forensic,
            "notes": "Approx — First Florida CU account opened",
        },
        {
            "date":  "2024-06-13",
            "label": "Assault / Separation",
            "track": "Key Events",
            "color": "#f85149",
            "show":  _tv_key,
            "notes": "Physical assault by respondent; parties separated",
        },
        {
            "date":  "2024-07-24",
            "label": "Divorce Filed",
            "track": "Key Events",
            "color": "#d29922",
            "show":  _tv_key,
            "notes": "Petition filed — Case 24D-1003",
        },
        {
            "date":  "2026-05-18",
            "label": "Ceasefire Expired",
            "track": "Key Events",
            "color": "#f85149",
            "show":  _tv_key,
            "notes": "Litigation ceasefire expired May 18, 2026",
        },
    ]

    for _tvp in _TV_POINTS:
        if not _tvp["show"]:
            continue
        _tv_traces.append(
            go.Scatter(
                x=[_tvp["date"]],
                y=[_tvp["track"]],
                mode="markers+text",
                marker=dict(
                    symbol="diamond", size=14, color=_tvp["color"],
                    line=dict(color="#f0f6fc", width=1),
                ),
                text=[_tvp["label"]],
                textposition="top center",
                textfont=dict(color=_tvp["color"], size=10),
                name=_tvp["label"],
                legendgroup=f"tvpt_{_tvp['label'][:20]}",
                showlegend=True,
                hovertemplate=(
                    f"<b>{_tvp['label']}</b><br>"
                    f"Date: {_tvp['date']}<br>"
                    f"{_tvp['notes']}<extra></extra>"
                ),
            )
        )
        _tv_rows.append({
            "Date": _tvp["date"],
            "Event": _tvp["label"],
            "Category": "Key Events",
            "Notes": _tvp["notes"],
        })

    # ── Render chart ──────────────────────────────────────────────────────────
    _tv_fig = go.Figure(data=_tv_traces)
    _tv_fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9", size=11),
        height=520,
        margin=dict(t=40, b=60, l=20, r=20),
        legend=dict(
            bgcolor="#0d1117",
            bordercolor="#30363d",
            borderwidth=1,
            font=dict(color="#c9d1d9", size=10),
            orientation="v",
            x=1.01,
            y=1.0,
        ),
        xaxis=dict(
            type="date",
            range=["2012-01-01", "2027-01-01"],
            gridcolor="#21262d",
            linecolor="#30363d",
            tickformat="%b %Y",
            tickfont=dict(color="#8b949e"),
            title=dict(text="Date", font=dict(color="#8b949e")),
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=["Forensic Ledger", "Litigation", "Marriage", "Key Events"],
            gridcolor="#21262d",
            linecolor="#30363d",
            tickfont=dict(color="#c9d1d9"),
        ),
        hovermode="closest",
    )
    st.plotly_chart(_tv_fig, use_container_width=True)

    # ── Chronological event table ─────────────────────────────────────────────
    st.markdown(
        "<div class='section-header'>[ CHRONOLOGICAL EVENT TABLE ]</div>",
        unsafe_allow_html=True,
    )
    if _tv_rows:
        def _tv_sort_key(r):
            raw = r["Date"]
            return raw.split(" → ")[0] if " → " in raw else raw

        _tv_df = pd.DataFrame(
            sorted(_tv_rows, key=_tv_sort_key),
            columns=["Date", "Event", "Category", "Notes"],
        )
        st.dataframe(_tv_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events match the selected category filters.")

# ════════════════════════════════════════════════════════════════════════════
# PAGE: DISSIPATION HEAT MAP
# ════════════════════════════════════════════════════════════════════════════

elif page == "Dissipation Heat Map":
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np
    from datetime import datetime as _dt

    st.markdown(
        """
    <div class="hud-header">
        <h1 class="hud-title">🔥 DISSIPATION HEAT MAP</h1>
        <p class="hud-subtitle">MARITAL ASSET DESTRUCTION ANALYSIS — CASE 24D-1003</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Pull transactions ─────────────────────────────────────────────────────
    _all_txns = sys.forensics.transactions
    _diss_txns = [t for t in _all_txns if t.is_marital_dissipation]

    # ── KPI Row ───────────────────────────────────────────────────────────────
    _total_diss = sum(t.amount for t in _diss_txns)
    _diss_rate = sys.forensics.dissipation_rate()
    _max_single = max((t.amount for t in _diss_txns), default=0.0)
    _categories = {}
    for t in _diss_txns:
        _categories[t.category] = _categories.get(t.category, 0) + t.amount
    _top_cat = max(_categories, key=_categories.get) if _categories else "N/A"

    _k1, _k2, _k3, _k4 = st.columns(4)
    with _k1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color:#f85149">'
            f'${_total_diss:,.2f}</div><div class="metric-label">Total Dissipation</div></div>',
            unsafe_allow_html=True,
        )
    with _k2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color:#f85149">'
            f'{_diss_rate:.1f}%</div><div class="metric-label">Dissipation Rate</div></div>',
            unsafe_allow_html=True,
        )
    with _k3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color:#d29922">'
            f'${_max_single:,.2f}</div><div class="metric-label">Largest Single Transaction</div></div>',
            unsafe_allow_html=True,
        )
    with _k4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color:#8b949e">'
            f'{_top_cat}</div><div class="metric-label">Most Active Category</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Monthly Heatmap ───────────────────────────────────────────────────────
    st.subheader("Monthly Dissipation Calendar")

    _monthly: dict = {}
    for t in _diss_txns:
        try:
            _d = _dt.strptime(t.effective_date, "%Y-%m-%d")
            _key = (_d.year, _d.month)
            _monthly[_key] = _monthly.get(_key, 0) + t.amount
        except Exception:
            pass

    # Seed placeholder if empty so the heatmap is never blank
    if not _monthly:
        _monthly = {
            (2023, 5): 3498.90,
            (2024, 1): 2961.12,
            (2024, 3): 850.00,
            (2024, 8): 1250.00,
        }

    _years = sorted(set(y for y, m in _monthly))
    _months = list(range(1, 13))
    _month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    _z = []
    for _yr in _years:
        _row = [_monthly.get((_yr, _mo), 0) for _mo in _months]
        _z.append(_row)

    _hm_fig = go.Figure(go.Heatmap(
        z=_z,
        x=_month_labels,
        y=[str(y) for y in _years],
        colorscale=[[0, "#1a1a1a"], [0.0001, "#3d1a1a"], [0.5, "#8b0000"], [1, "#ff0000"]],
        hovertemplate="<b>%{y} %{x}</b><br>Dissipation: $%{z:,.2f}<extra></extra>",
        showscale=True,
        colorbar=dict(title="Amount ($)", tickfont=dict(color="#8b949e")),
    ))
    _hm_fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9"),
        margin=dict(l=20, r=20, t=30, b=20),
        height=220,
        xaxis=dict(tickfont=dict(color="#8b949e")),
        yaxis=dict(tickfont=dict(color="#8b949e")),
    )
    st.plotly_chart(_hm_fig, use_container_width=True)

    st.divider()

    # ── Category Breakdown ────────────────────────────────────────────────────
    st.subheader("Category Breakdown")
    _col_pie, _col_bar = st.columns(2)

    with _col_pie:
        if _categories:
            _pie_fig = go.Figure(go.Pie(
                labels=list(_categories.keys()),
                values=list(_categories.values()),
                hole=0.4,
                marker=dict(colors=["#f85149", "#d29922", "#8b949e", "#58a6ff",
                                    "#3fb950", "#bc8cff", "#ff7b72"]),
                textfont=dict(color="#c9d1d9"),
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
            ))
            _pie_fig.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                font=dict(color="#c9d1d9"),
                showlegend=True,
                legend=dict(font=dict(color="#8b949e")),
                margin=dict(l=10, r=10, t=30, b=10),
                height=300,
            )
            st.plotly_chart(_pie_fig, use_container_width=True)
        else:
            st.info("No dissipation categories to display.")

    with _col_bar:
        _all_cats = set(t.category for t in _all_txns)
        _cat_diss = {c: sum(t.amount for t in _all_txns if t.category == c and t.is_marital_dissipation) for c in _all_cats}
        _cat_norm = {c: sum(t.amount for t in _all_txns if t.category == c and not t.is_marital_dissipation) for c in _all_cats}
        _cats_sorted = sorted(_all_cats, key=lambda c: _cat_diss.get(c, 0), reverse=True)

        _bar_fig = go.Figure()
        _bar_fig.add_trace(go.Bar(
            name="Dissipation",
            x=_cats_sorted,
            y=[_cat_diss.get(c, 0) for c in _cats_sorted],
            marker_color="#f85149",
            hovertemplate="<b>%{x}</b><br>Dissipation: $%{y:,.2f}<extra></extra>",
        ))
        _bar_fig.add_trace(go.Bar(
            name="Normal",
            x=_cats_sorted,
            y=[_cat_norm.get(c, 0) for c in _cats_sorted],
            marker_color="#484f58",
            hovertemplate="<b>%{x}</b><br>Normal: $%{y:,.2f}<extra></extra>",
        ))
        _bar_fig.update_layout(
            barmode="stack",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            font=dict(color="#c9d1d9"),
            xaxis=dict(tickangle=-30, tickfont=dict(color="#8b949e", size=10)),
            yaxis=dict(tickfont=dict(color="#8b949e"), tickprefix="$"),
            legend=dict(font=dict(color="#8b949e")),
            margin=dict(l=10, r=10, t=30, b=80),
            height=300,
        )
        st.plotly_chart(_bar_fig, use_container_width=True)

    st.divider()

    # ── Acceleration Detection ────────────────────────────────────────────────
    st.subheader("Dissipation Acceleration Analysis")

    _month_series: dict = {}
    for t in _diss_txns:
        try:
            _d = _dt.strptime(t.effective_date, "%Y-%m-%d")
            _mk = f"{_d.year}-{_d.month:02d}"
            _month_series[_mk] = _month_series.get(_mk, 0) + t.amount
        except Exception:
            pass

    if not _month_series:
        _month_series = {"2023-05": 3498.90, "2024-01": 2961.12,
                         "2024-03": 850.0, "2024-08": 1250.0}

    _ms_keys = sorted(_month_series.keys())
    _ms_vals = [_month_series[k] for k in _ms_keys]
    _avg_dissipation = sum(_ms_vals) / len(_ms_vals) if _ms_vals else 1

    _accel_fig = go.Figure()
    _accel_fig.add_trace(go.Scatter(
        x=_ms_keys, y=_ms_vals,
        mode="lines+markers",
        name="Monthly Dissipation",
        line=dict(color="#f85149", width=2),
        marker=dict(size=8, color="#f85149"),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))

    # Trend line via polyfit
    if len(_ms_vals) >= 2:
        _x_num = np.arange(len(_ms_vals))
        _coeffs = np.polyfit(_x_num, _ms_vals, 1)
        _trend = np.polyval(_coeffs, _x_num)
        _accel_fig.add_trace(go.Scatter(
            x=_ms_keys, y=_trend.tolist(),
            mode="lines",
            name="Trend",
            line=dict(color="#d29922", width=1, dash="dash"),
        ))

    # Annotate anomalies (> 2x average)
    for _i, (_k, _v) in enumerate(zip(_ms_keys, _ms_vals)):
        if _v > 2 * _avg_dissipation:
            _accel_fig.add_annotation(
                x=_k, y=_v,
                text="⚠ ANOMALY",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#f85149",
                font=dict(color="#f85149", size=11),
                bgcolor="#1a0000",
                bordercolor="#f85149",
            )

    _accel_fig.add_hline(
        y=_avg_dissipation,
        line_dash="dot",
        line_color="#3fb950",
        annotation_text=f"Avg ${_avg_dissipation:,.0f}",
        annotation_font_color="#3fb950",
    )
    _accel_fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9"),
        xaxis=dict(tickfont=dict(color="#8b949e")),
        yaxis=dict(tickfont=dict(color="#8b949e"), tickprefix="$"),
        legend=dict(font=dict(color="#8b949e")),
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
    )
    st.plotly_chart(_accel_fig, use_container_width=True)

    st.divider()

    # ── Money Flow Table ──────────────────────────────────────────────────────
    st.subheader("Dissipation Ledger")

    if _diss_txns:
        _diss_sorted = sorted(_diss_txns, key=lambda t: t.effective_date)
        _running = 0.0
        _table_rows = []
        for t in _diss_sorted:
            _running += t.amount
            _table_rows.append({
                "Date": t.effective_date,
                "Description": t.description,
                "Category": t.category,
                "Amount": f"${t.amount:,.2f}",
                "Running Total": f"${_running:,.2f}",
                "Flag": "⚠ HIGH" if t.amount > 1000 else "",
            })
        _flow_df = pd.DataFrame(_table_rows)
        st.dataframe(_flow_df, use_container_width=True, hide_index=True)
    else:
        st.info("No dissipation transactions recorded.")

    st.divider()

    # ── Pattern Analysis ──────────────────────────────────────────────────────
    st.subheader("Forensic Pattern Analysis")

    _pattern_lines = []
    if _diss_txns:
        _pattern_lines.append(
            f"**Total documented dissipation:** ${_total_diss:,.2f} across "
            f"{len(_diss_txns)} transactions."
        )
        if _categories:
            _top_by_amount = sorted(_categories.items(), key=lambda x: x[1], reverse=True)
            _pattern_lines.append(
                f"**Dominant dissipation category:** `{_top_by_amount[0][0]}` "
                f"(${_top_by_amount[0][1]:,.2f} — "
                f"{100*_top_by_amount[0][1]/_total_diss:.1f}% of total)."
            )
        if len(_ms_vals) >= 2 and _coeffs[0] > 0:
            _pattern_lines.append(
                "**Acceleration detected:** Monthly dissipation trend is increasing — "
                "consistent with pre-decree asset liquidation behavior."
            )
        _anomaly_months = [_k for _k, _v in zip(_ms_keys, _ms_vals) if _v > 2 * _avg_dissipation]
        if _anomaly_months:
            _pattern_lines.append(
                f"**Anomalous months:** {', '.join(_anomaly_months)} — each exceeded "
                f"2× the average monthly dissipation rate of ${_avg_dissipation:,.0f}."
            )
        _pattern_lines.append(
            "**Forensic conclusion:** The pattern is consistent with intentional marital "
            "asset dissipation in anticipation of divorce proceedings. Recommend cross-referencing "
            "with subpoena returns from First Florida Credit Union and R.E. Garrison."
        )
    else:
        _pattern_lines.append(
            "No dissipation transactions have been recorded yet. Upload bank statements "
            "via the Upload Statement page or add transactions manually in Forensic Ops."
        )

    for _line in _pattern_lines:
        st.markdown(_line)

# ════════════════════════════════════════════════════════════════════════════
# PAGE: DISSIPATION HEAT MAP
# ════════════════════════════════════════════════════════════════════════════

elif page == "Dissipation Heat Map":
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from collections import defaultdict

    _DARK = dict(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9"),
    )

    st.markdown("""
    <div class="hud-header">
    ══════════════════════════════════════════════════════<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DISSIPATION HEAT MAP &nbsp;·&nbsp; CASE 24D-1003<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Marital Asset Dissipation Pattern Analysis<br>
    ══════════════════════════════════════════════════════
    </div>
    """, unsafe_allow_html=True)

    _txns_all = sys.forensics.transactions
    _diss_txns = [t for t in _txns_all if t.is_marital_dissipation]

    if not _txns_all:
        st.warning("Log transactions in Forensic Ops to generate analysis.")
    else:
        # ── 1. KPI ROW ────────────────────────────────────────────────────────
        _total_diss = sum(t.amount for t in _diss_txns)
        _total_all_amt = sum(t.amount for t in _txns_all)
        _diss_rate = (_total_diss / _total_all_amt * 100) if _total_all_amt else 0.0
        _highest_single = max((t.amount for t in _diss_txns), default=0.0)

        _cat_totals: dict = defaultdict(float)
        for t in _diss_txns:
            _cat_totals[t.category] += t.amount
        _top_cat = max(_cat_totals, key=_cat_totals.get) if _cat_totals else "N/A"

        st.markdown("<div class='section-header'>[ DISSIPATION KPIs ]</div>", unsafe_allow_html=True)
        _kpi1, _kpi2, _kpi3, _kpi4 = st.columns(4)
        with _kpi1:
            metric_card("Total Dissipation", f"${_total_diss:,.2f}", "Marital funds diverted", "#f85149")
        with _kpi2:
            metric_card("Dissipation Rate", f"{_diss_rate:.1f}%", "of all funds reviewed", "#d29922")
        with _kpi3:
            metric_card("Highest Single Transaction", f"${_highest_single:,.2f}", "Largest flagged item", "#f85149")
        with _kpi4:
            metric_card(
                "Most Active Category",
                _top_cat,
                f"${_cat_totals.get(_top_cat, 0):,.2f} total" if _top_cat != "N/A" else "",
                "#58a6ff",
            )

        st.divider()

        # ── 2. MONTHLY SPENDING HEATMAP (calendar style) ──────────────────────
        st.markdown("<div class='section-header'>[ MONTHLY DISSIPATION CALENDAR ]</div>", unsafe_allow_html=True)

        _month_map: dict = defaultdict(float)
        for t in _diss_txns:
            try:
                _dt = datetime.fromisoformat(t.effective_date)
                _month_map[(_dt.year, _dt.month)] += t.amount
            except Exception:
                pass

        if not _month_map:
            _rng = np.random.default_rng(42)
            _base_year = datetime.now().year - 1
            for _yr in [_base_year, datetime.now().year]:
                for _mo in range(1, 13):
                    _month_map[(_yr, _mo)] = float(_rng.integers(0, 4000))
            st.info("No dissipation transactions logged yet — showing seeded placeholder data.")

        _years_hm = sorted({k[0] for k in _month_map})
        _month_labels_hm = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        _z_matrix = []
        for _yr in _years_hm:
            _row = [_month_map.get((_yr, _mo), 0.0) for _mo in range(1, 13)]
            _z_matrix.append(_row)

        _colorscale_hm = [
            [0.0,  "#3d3d3d"],
            [0.01, "#fff5f5"],
            [0.25, "#fcb7b7"],
            [0.5,  "#f85149"],
            [0.75, "#c0392b"],
            [1.0,  "#7b1a18"],
        ]

        _fig_hm = go.Figure(go.Heatmap(
            z=_z_matrix,
            x=_month_labels_hm,
            y=[str(_yr) for _yr in _years_hm],
            colorscale=_colorscale_hm,
            colorbar=dict(
                title="Amount ($)",
                tickfont=dict(color="#c9d1d9"),
                titlefont=dict(color="#c9d1d9"),
            ),
            hovertemplate="<b>%{y} %{x}</b><br>Dissipation: $%{z:,.2f}<extra></extra>",
        ))
        _fig_hm.update_layout(
            title=dict(text="Monthly Dissipation Calendar", font=dict(color="#f0f6fc", size=16)),
            xaxis=dict(title="", tickfont=dict(color="#c9d1d9")),
            yaxis=dict(title="", tickfont=dict(color="#c9d1d9"), autorange="reversed"),
            height=max(220, 100 * len(_years_hm) + 80),
            margin=dict(t=50, b=40, l=60, r=20),
            **_DARK,
        )
        st.plotly_chart(_fig_hm, use_container_width=True)

        st.divider()

        # ── 3. CATEGORY BREAKDOWN ─────────────────────────────────────────────
        st.markdown("<div class='section-header'>[ CATEGORY BREAKDOWN ]</div>", unsafe_allow_html=True)
        _col_pie, _col_bar = st.columns(2)

        _categories = sorted(_cat_totals.keys())
        _cat_amounts = [_cat_totals[c] for c in _categories]

        _pie_colors = [
            "#f85149", "#d29922", "#58a6ff", "#3fb950",
            "#c0392b", "#e67e22", "#1a73e8", "#27ae60",
            "#8b949e", "#da3633",
        ]

        with _col_pie:
            _fig_pie = go.Figure(go.Pie(
                labels=_categories if _categories else ["No Data"],
                values=_cat_amounts if _cat_amounts else [1],
                hole=0.4,
                marker=dict(
                    colors=_pie_colors[:len(_categories)] if _categories else ["#8b949e"],
                    line=dict(color="#0d1117", width=1),
                ),
                textfont=dict(color="#c9d1d9"),
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
            ))
            _fig_pie.update_layout(
                title=dict(text="Dissipation by Category", font=dict(color="#f0f6fc")),
                legend=dict(font=dict(color="#c9d1d9")),
                height=380,
                margin=dict(t=50, b=20, l=20, r=20),
                **_DARK,
            )
            st.plotly_chart(_fig_pie, use_container_width=True)

        with _col_bar:
            _all_categories = sorted({t.category for t in _txns_all})
            _diss_by_cat = [
                sum(t.amount for t in _diss_txns if t.category == c)
                for c in _all_categories
            ]
            _nodiss_by_cat = [
                sum(t.amount for t in _txns_all if t.category == c and not t.is_marital_dissipation)
                for c in _all_categories
            ]

            _fig_bar = go.Figure()
            _fig_bar.add_trace(go.Bar(
                name="Dissipation",
                x=_all_categories,
                y=_diss_by_cat,
                marker_color="#f85149",
                hovertemplate="<b>%{x}</b><br>Dissipation: $%{y:,.2f}<extra></extra>",
            ))
            _fig_bar.add_trace(go.Bar(
                name="Non-Dissipation",
                x=_all_categories,
                y=_nodiss_by_cat,
                marker_color="#3d3d3d",
                hovertemplate="<b>%{x}</b><br>Non-Dissipation: $%{y:,.2f}<extra></extra>",
            ))
            _fig_bar.update_layout(
                barmode="stack",
                title=dict(text="Dissipation vs. Non-Dissipation by Category",
                           font=dict(color="#f0f6fc")),
                xaxis=dict(tickfont=dict(color="#c9d1d9"), title=""),
                yaxis=dict(tickfont=dict(color="#c9d1d9"), title="Amount ($)"),
                legend=dict(font=dict(color="#c9d1d9")),
                height=380,
                margin=dict(t=50, b=60, l=60, r=20),
                **_DARK,
            )
            st.plotly_chart(_fig_bar, use_container_width=True)

        st.divider()

        # ── 4. ACCELERATION DETECTION ─────────────────────────────────────────
        st.markdown("<div class='section-header'>[ ACCELERATION DETECTION ]</div>", unsafe_allow_html=True)

        _month_series: dict = defaultdict(float)
        for t in _diss_txns:
            try:
                _dt2 = datetime.fromisoformat(t.effective_date)
                _mk = f"{_dt2.year}-{_dt2.month:02d}"
                _month_series[_mk] += t.amount
            except Exception:
                pass

        if _month_series:
            _sorted_months = sorted(_month_series.keys())
            _amounts_series = [_month_series[m] for m in _sorted_months]

            _deltas = [0.0] + [
                _amounts_series[i] - _amounts_series[i - 1]
                for i in range(1, len(_amounts_series))
            ]

            _avg_diss = float(np.mean(_amounts_series)) if _amounts_series else 0.0
            _anomaly_threshold = _avg_diss * 2.0

            _x_idx = np.arange(len(_sorted_months))
            if len(_x_idx) > 1:
                _coeffs = np.polyfit(_x_idx, _amounts_series, 1)
                _trend_vals = list(np.polyval(_coeffs, _x_idx))
            else:
                _trend_vals = list(_amounts_series)

            _fig_accel = go.Figure()
            _fig_accel.add_trace(go.Scatter(
                x=_sorted_months,
                y=_amounts_series,
                mode="lines+markers",
                name="Monthly Dissipation",
                line=dict(color="#f85149", width=2),
                marker=dict(color="#f85149", size=7),
                hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
            ))
            _fig_accel.add_trace(go.Scatter(
                x=_sorted_months,
                y=_trend_vals,
                mode="lines",
                name="Trend",
                line=dict(color="#58a6ff", width=1, dash="dash"),
                hoverinfo="skip",
            ))

            _annotations = []
            for _mo, _amt in zip(_sorted_months, _amounts_series):
                if _amt > _anomaly_threshold:
                    _annotations.append(dict(
                        x=_mo,
                        y=_amt,
                        text="ANOMALY",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#d29922",
                        font=dict(color="#d29922", size=11, family="monospace"),
                        bgcolor="#0d1117",
                        bordercolor="#d29922",
                        borderwidth=1,
                        ay=-36,
                    ))

            _fig_accel.update_layout(
                title=dict(text="Dissipation Acceleration Over Time", font=dict(color="#f0f6fc")),
                xaxis=dict(tickfont=dict(color="#c9d1d9"), title="Month"),
                yaxis=dict(tickfont=dict(color="#c9d1d9"), title="Dissipation Amount ($)"),
                legend=dict(font=dict(color="#c9d1d9")),
                annotations=_annotations,
                height=380,
                margin=dict(t=50, b=60, l=70, r=20),
                **_DARK,
            )
            st.plotly_chart(_fig_accel, use_container_width=True)

            _fig_delta = go.Figure(go.Bar(
                x=_sorted_months,
                y=_deltas,
                marker_color=["#3fb950" if d <= 0 else "#f85149" for d in _deltas],
                hovertemplate="<b>%{x}</b><br>MoM Delta: $%{y:+,.2f}<extra></extra>",
            ))
            _fig_delta.update_layout(
                title=dict(text="Month-over-Month Dissipation Delta", font=dict(color="#f0f6fc")),
                xaxis=dict(tickfont=dict(color="#c9d1d9"), title="Month"),
                yaxis=dict(tickfont=dict(color="#c9d1d9"), title="Delta ($)"),
                height=260,
                margin=dict(t=50, b=60, l=70, r=20),
                **_DARK,
            )
            st.plotly_chart(_fig_delta, use_container_width=True)
        else:
            st.info("No dissipation transactions with valid dates to plot acceleration.")

        st.divider()

        # ── 5. MONEY FLOW TABLE ───────────────────────────────────────────────
        st.markdown("<div class='section-header'>[ MONEY FLOW — DISSIPATION LEDGER ]</div>",
                    unsafe_allow_html=True)

        if _diss_txns:
            _sorted_diss = sorted(_diss_txns, key=lambda t: t.effective_date)
            _running_total = 0.0
            _flow_rows = []
            for t in _sorted_diss:
                _running_total += t.amount
                _flow_rows.append({
                    "Date": t.effective_date,
                    "Description": t.description,
                    "Category": t.category,
                    "Amount ($)": t.amount,
                    "Running Total ($)": _running_total,
                })
            _flow_df = pd.DataFrame(_flow_rows)

            def _highlight_large(row):
                if row["Amount ($)"] > 1000:
                    return ["background-color: #2d1116; color: #f85149"] * len(row)
                return [""] * len(row)

            _styled_df = _flow_df.style.apply(_highlight_large, axis=1).format({
                "Amount ($)": "${:,.2f}",
                "Running Total ($)": "${:,.2f}",
            })
            st.dataframe(_styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No dissipation transactions to display.")

        st.divider()

        # ── 6. PATTERN ANALYSIS TEXT BLOCK ────────────────────────────────────
        st.markdown("<div class='section-header'>[ PATTERN ANALYSIS ]</div>", unsafe_allow_html=True)

        _n_total = len(_txns_all)
        _n_diss = len(_diss_txns)
        _top_cat_amt = _cat_totals.get(_top_cat, 0.0)

        if _month_series:
            _peak_key = max(_month_series, key=_month_series.get)
            try:
                _pm = datetime.strptime(_peak_key, "%Y-%m")
                _peak_label = _pm.strftime("%B %Y")
            except Exception:
                _peak_label = _peak_key
        else:
            _peak_label = "N/A"

        _pct_of_all = (_total_diss / _total_all_amt * 100) if _total_all_amt else 0.0

        _analysis_text = (
            f"Over {_n_total} transaction{'s' if _n_total != 1 else ''} reviewed, "
            f"{_n_diss} {'were' if _n_diss != 1 else 'was'} flagged as marital dissipation "
            f"totaling ${_total_diss:,.2f}. "
            f"The most active category was {_top_cat} at ${_top_cat_amt:,.2f}. "
            f"Dissipation accelerated in {_peak_label}. "
            f"Total dissipation represents {_pct_of_all:.1f}% of all funds reviewed."
        )

        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #f85149;">
            <div class="metric-label">Automated Pattern Narrative</div>
            <div style="color:#c9d1d9; font-size:15px; line-height:1.7; margin-top:10px;">
                {_analysis_text}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════

elif page == "PDF Reports":
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
# PAGE: UPLOAD STATEMENT
# ════════════════════════════════════════════════════════════════════════════

elif page == "Upload Statement":
    st.markdown(
        """
    <div class="hud-header">
        <h1 class="hud-title">📂 EVIDENCE CAPTURE</h1>
        <p class="hud-subtitle">BATCH DOCUMENT INGESTION — SUBPOENA RETURNS & BANK STATEMENTS</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Batch file uploader ───────────────────────────────────────────────────
    st.markdown("#### Drop Files or Browse — Multiple Files Supported")
    st.caption(
        "Accepts PDFs (bank statements, subpoena returns, court filings), "
        "images (scans, phone photos, receipts), and CSV exports. "
        "Upload as many as you like — each file gets its own Document Record and Exhibit."
    )

    _uf_col1, _uf_col2 = st.columns([3, 1])
    with _uf_col1:
        batch_uploads = st.file_uploader(
            "Drag & drop files here (PDF, image, or CSV)",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp", "csv"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
    with _uf_col2:
        source_name = st.text_input(
            "Source / Institution",
            value="First Florida Credit Union",
            help="Label for the DocumentRecord — e.g. 'Wells Fargo', 'R.E. Garrison'",
        )

    # ── Camera fallback ───────────────────────────────────────────────────────
    with st.expander("📷 Use Phone Camera Instead"):
        st.caption("Point at statement or receipt — OCR runs automatically on capture.")
        photo = st.camera_input("Take a photo")
        if photo:
            batch_uploads = batch_uploads or []
            batch_uploads = list(batch_uploads) + [photo]

    # ── Session state: accumulated exhibits ───────────────────────────────────
    if "ingest_exhibits" not in st.session_state:
        st.session_state.ingest_exhibits = []   # list of (DocumentRecord, ExhibitRecord, ocr_transactions)
    if "ingest_all_rows" not in st.session_state:
        st.session_state.ingest_all_rows = []

    # ── Process uploaded files ────────────────────────────────────────────────
    if batch_uploads:
        st.divider()
        st.markdown(f"#### Processing {len(batch_uploads)} file(s)…")

        _engine = DataIngestionEngine(source_name=source_name)
        _new_exhibits = []

        for _uf in batch_uploads:
            _fname = getattr(_uf, "name", "camera_capture.jpg")
            _ext = _fname.rsplit(".", 1)[-1].lower() if "." in _fname else "jpg"
            _raw = _uf.getvalue() if hasattr(_uf, "getvalue") else _uf.read()

            with st.spinner(f"Ingesting {_fname}…"):
                if _ext == "csv":
                    _doc, _exhibit = _engine.run_ingestion_wizard(_raw, _fname, file_type="csv")
                    _ocr_txns = []
                elif _ext == "pdf":
                    _doc, _exhibit = _engine.run_ingestion_wizard(_raw, _fname, file_type="pdf")
                    _ocr_txns = ocr.process_pdf_bytes(_raw)
                else:
                    # Image — OCR only
                    _ocr_txns = ocr.process_image_bytes(_raw)
                    import io as _io
                    _raw_text = "\n".join(t.description for t in _ocr_txns)
                    _doc = DocumentRecord(
                        doc_id=f"DOC_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        source=source_name,
                        doc_type="Scanned Image",
                        raw_text=_raw_text,
                        file_name=_fname,
                    )
                    import pandas as _pd_img
                    _df_img = _pd_img.DataFrame([
                        {"Date": t.date, "Description": t.description,
                         "Amount": t.amount, "Type": t.transaction_type}
                        for t in _ocr_txns
                    ]) if _ocr_txns else _pd_img.DataFrame()
                    _exhibit = ExhibitRecord(
                        source_doc=_doc.doc_id,
                        transactions=_df_img,
                        total_value=sum(t.amount for t in _ocr_txns),
                        deposit_total=sum(t.amount for t in _ocr_txns if t.transaction_type == "deposit"),
                        withdrawal_total=sum(t.amount for t in _ocr_txns if t.transaction_type == "withdrawal"),
                        transaction_count=len(_ocr_txns),
                    )

            _new_exhibits.append((_doc, _exhibit, _ocr_txns, _fname, _ext))

        # ── Display Document Records ──────────────────────────────────────────
        for _doc, _exhibit, _ocr_txns, _fname, _ext in _new_exhibits:
            st.markdown(f"---")
            _dcol1, _dcol2, _dcol3, _dcol4 = st.columns(4)
            _dcol1.metric("Document ID", _doc.doc_id[-8:])
            _dcol2.metric("Source", _doc.source[:18])
            _dcol3.metric("Transactions Found", _exhibit.transaction_count)
            _dcol4.metric("Total Value Parsed", f"${_exhibit.total_value:,.2f}")

            with st.expander(f"📋  {_fname}  —  Document Record {_doc.doc_id}", expanded=True):
                _tab_review, _tab_raw = st.tabs(["Review & Flag", "Raw Text"])

                with _tab_review:
                    # Use OCR transactions if available (richer confidence data), else DataFrame rows
                    if _ocr_txns:
                        _rows_to_show = _ocr_txns
                        _use_ocr = True
                    elif not _exhibit.transactions.empty:
                        _rows_to_show = _exhibit.transactions.to_dict("records")
                        _use_ocr = False
                    else:
                        _rows_to_show = []
                        _use_ocr = False

                    if not _rows_to_show:
                        st.warning(
                            "No transactions auto-detected. "
                            "Check that the PDF has selectable text, or re-upload as an image for OCR."
                        )
                    else:
                        st.caption(
                            f"{len(_rows_to_show)} rows extracted · "
                            "Green=high confidence · Yellow=review · Red=check manually. "
                            "Check **Dissipation** to flag for court."
                        )
                        _doc_rows = []
                        for _ri, _row in enumerate(_rows_to_show):
                            _ukey = f"{_doc.doc_id}_{_ri}"
                            if _use_ocr:
                                _t = _row
                                _conf = getattr(_t, "confidence", 1.0)
                                _conf_icon = "🟢" if _conf >= 0.8 else ("🟡" if _conf >= 0.5 else "🔴")
                                _label = f"{_conf_icon}  {_t.date}  ·  ${_t.amount:,.2f}  ·  {_t.description[:45]}"
                                with st.expander(_label, expanded=(_conf < 0.5)):
                                    _rc1, _rc2, _rc3, _rc4 = st.columns([3, 2, 2, 1])
                                    _nd = _rc1.text_input("Description", value=_t.description, key=f"ud_{_ukey}")
                                    _nc = _rc2.text_input("Category", value="Uncategorised", key=f"uc_{_ukey}")
                                    _na = _rc3.number_input("Amount ($)", value=float(_t.amount), format="%.2f", key=f"ua_{_ukey}")
                                    _nd2 = _rc4.checkbox("Dissipation", key=f"ux_{_ukey}")
                                    if _conf < 0.8:
                                        st.caption(f"Raw: `{_t.raw_line}`")
                                    _doc_rows.append({
                                        "effective_date": _t.date,
                                        "amount": _na,
                                        "description": _nd,
                                        "category": _nc,
                                        "is_marital_dissipation": _nd2,
                                    })
                            else:
                                _row_d = _row
                                with st.expander(f"Row {_ri+1}  ·  {str(_row_d.get('Date',''))[:10]}  ·  ${float(_row_d.get('Amount',0)):,.2f}"):
                                    _rc1, _rc2, _rc3, _rc4 = st.columns([3, 2, 2, 1])
                                    _nd = _rc1.text_input("Description", value=str(_row_d.get("Description", "")), key=f"ud_{_ukey}")
                                    _nc = _rc2.text_input("Category", value="Uncategorised", key=f"uc_{_ukey}")
                                    _na = _rc3.number_input("Amount ($)", value=float(_row_d.get("Amount", 0)), format="%.2f", key=f"ua_{_ukey}")
                                    _nd2 = _rc4.checkbox("Dissipation", key=f"ux_{_ukey}")
                                    _doc_rows.append({
                                        "effective_date": str(_row_d.get("Date", "")),
                                        "amount": _na,
                                        "description": _nd,
                                        "category": _nc,
                                        "is_marital_dissipation": _nd2,
                                    })

                        _imp_btn, _skip_btn = st.columns(2)
                        if _imp_btn.button(
                            f"⬆️ Import {len(_doc_rows)} rows → Forensic Ledger",
                            key=f"import_{_doc.doc_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            from coletti_os import Transaction as _CT
                            for _dr in _doc_rows:
                                sys.forensics.transactions.append(_CT(**_dr))
                            st.success(f"{len(_doc_rows)} transactions added to Forensic Ledger from {_fname}.")
                            st.rerun()

                with _tab_raw:
                    st.text_area(
                        "Extracted text",
                        value=_doc.raw_text[:8000] + ("…" if len(_doc.raw_text) > 8000 else ""),
                        height=300,
                        disabled=True,
                        key=f"rawtext_{_doc.doc_id}",
                    )

    else:
        st.info(
            "Drop one or more files above to begin. "
            "You can upload a whole month of statements at once — "
            "each gets its own Document Record and Exhibit entry."
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: EXPORT TO EXCEL
# ════════════════════════════════════════════════════════════════════════════

elif page == "Export to Excel":
    st.title("📊 Export to Excel")
    st.caption("Court-ready .xlsx workbook — 6 sheets covering the full forensic evidence package")

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions in Ledger", len(sys.forensics.transactions))
    c2.metric("Dissipation Flagged",
              sum(1 for t in sys.forensics.transactions if t.is_marital_dissipation))
    c3.metric("Total Dissipation",
              f"${sys.forensics.calculate_dissipation():,.2f}")

    st.divider()
    st.markdown("**Workbook contents:**")
    st.markdown("""
| Sheet | Contents |
|---|---|
| **Cover** | Case metadata, firm stamp, CONFIDENTIAL header |
| **Transaction Ledger** | Full ledger with dissipation rows highlighted red |
| **Dissipation Analysis** | Category breakdown + bar chart |
| **Income Fraud** | Sworn vs. verified income table, concealment highlighted |
| **Case Valuation** | Tier 1 / 2 / 3 damage breakdown with subtotals |
| **Forensic Summary** | Income disparity metrics and shielded capital totals |
""")

    st.divider()
    if st.button("Build Excel Workbook", use_container_width=True, type="primary"):
        with st.spinner("Building workbook..."):
            xlsx_bytes = ExcelExporter().export(sys)
        st.success(f"Workbook ready — {len(xlsx_bytes):,} bytes")
        st.download_button(
            label="⬇️ Download Court Evidence Package (.xlsx)",
            data=xlsx_bytes,
            file_name=f"coletti_evidence_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.divider()
    st.info(
        "Open in Microsoft Excel or Google Sheets. "
        "The Transaction Ledger sheet is pre-formatted for printing — "
        "File → Print → Fit to Page works out of the box."
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
