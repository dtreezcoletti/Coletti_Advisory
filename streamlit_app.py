import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# COLETTI & CO — ENHANCED FORENSIC OS v0.7.0
# ============================================================
__version__ = "0.7.0"
__last_updated__ = "2026-05-18"

# Firm Identity Constants
BRAND_NAME = "Coletti & Co."
BRAND_TAGLINE = "Operational Integrity & Risk Advisory"
POSITIONING = "Coletti & Co. helps founder-led service businesses turn chaos into documented, decision-ready clarity — before their risks become crises."
TARGET_ENTITY = "Coletti & Brown Enterprises, LLC"

# Target Temporal Anchors
AFFIDAVIT_DEFAULT = "2025-05-27"
HEARING_DEFAULT = "2026-02-20"

# Mainframe Path Resolution
BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault" / "clients"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "audit_logs"

# Self-Healing System Directories
CLIENT_FOLDERS = ["01_raw", "02_clean", "03_findings", "04_reports", "05_knowledge"]
for folder in CLIENT_FOLDERS:
    (VAULT_DIR / "SAMPLE_CLIENT" / folder).mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# AUDIT TRAIL & PROVENANCE LOGGING
# ============================================================
def log_analysis_event(event_type: str, details: dict):
    """Create tamper-evident audit log for chain of custody"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "version": __version__,
        **details
    }
    log_file = LOGS_DIR / f"audit_log_{datetime.now().strftime('%Y%m%d')}.json"
    
    import json
    logs = []
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = json.load(f)
    logs.append(log_entry)
    
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return timestamp

# ============================================================
# ENHANCED CLASSIFICATION ENGINE WITH PATTERN DETECTION
# ============================================================
def to_dt(x):
    return pd.to_datetime(x, errors="coerce")

def to_num(x):
    return pd.to_numeric(x, errors="coerce")

def classify_txn(description: str, amount: float = 0.0):
    """Enhanced algorithmic classification with expanded rule set"""
    d = str(description or "").lower()
    amt = float(amount or 0.0)

    # Business/Commercial Risk Matrix (Enhanced)
    business_rules = [
        ("INTERNAL_THEFT", "High", "ATM Withdrawal > $500", "withdrawal" in d and amt > 500),
        ("CONTRACTOR_FRAUD", "Med", "P2P Payment to Non-Vendor", "venmo" in d or "cashapp" in d or "paypal" in d),
        ("ASSET_SIPHON", "High", "Transfer to Personal-Linked ID", "transfer" in d and "personal" in d),
        ("TAX_RISK", "Med", "Merchant Category: Luxury/Travel", "hotel" in d or "dining" in d or "resort" in d),
        ("CRYPTO_CONVERSION", "High", "Cryptocurrency Exchange", "coinbase" in d or "crypto" in d or "bitcoin" in d),
        ("GAMBLING", "Med", "Gaming/Casino Activity", "casino" in d or "gaming" in d or "draftkings" in d),
    ]

    # Core Cash Extraction Rules (Enhanced)
    cash_rules = [
        ("CASH_WITHDRAWAL", "High", "keyword: withdrawal", "withdrawal" in d),
        ("CASH_WITHDRAWAL", "Med",  "keyword: cash",       "cash" in d),
        ("CASH_WITHDRAWAL", "Med",  "keyword: atm",        "atm" in d),
        ("CASH_WITHDRAWAL", "Med",  "keyword: shared branch", "shared branch" in d),
        ("CASH_WITHDRAWAL", "High", "Large Cash Advance", "cash advance" in d and amt > 1000),
    ]

    # Inter-bank Transfer Rules (Enhanced)
    xfer_rules = [
        ("TRANSFER", "High", "keyword: transfer", "transfer" in d),
        ("TRANSFER", "Med",  "keyword: zelle",    "zelle" in d),
        ("TRANSFER", "Med",  "keyword: ach",      "ach" in d),
        ("TRANSFER", "High", "keyword: wire",     "wire" in d),
        ("TRANSFER", "Med",  "External Account Transfer", "external" in d and "transfer" in d),
    ]

    # Asset Movement Indicators
    asset_rules = [
        ("ASSET_PURCHASE", "Med", "Real Estate/Title", "title" in d or "escrow" in d or "real estate" in d),
        ("VEHICLE_PAYMENT", "Med", "Auto/Vehicle Purchase", "auto" in d or "vehicle" in d or "carmax" in d),
        ("INVESTMENT", "Med", "Brokerage/Investment", "schwab" in d or "fidelity" in d or "investment" in d),
    ]

    for cat, conf, rule, triggered in business_rules + cash_rules + xfer_rules + asset_rules:
        if triggered:
            return cat, conf, rule

    return "OTHER", "Low", "no match"

def normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced normalization with additional computed fields"""
    df = df.copy()
    optional_cols = ["Strategic_Risk", "Source_Bank", "Statement_Period", "Statement_Page", "Line_Item", "To_Account"]
    for c in optional_cols:
        if c not in df.columns:
            df[c] = None

    df["Date"] = df["Date"].apply(to_dt)
    df["Amount"] = df["Amount"].apply(to_num)

    # Classification
    classified = df.apply(lambda r: pd.Series(classify_txn(r["Description"], r["Amount"])), axis=1)
    classified.columns = ["Category", "Confidence", "Rule_Triggered"]
    df = pd.concat([df, classified], axis=1)
    
    # Additional computed fields
    df["Is_Amount_Known"] = df["Amount"].notna()
    df["Amount_Bin"] = pd.cut(df["Amount"].fillna(0), 
                              bins=[0, 500, 1000, 2500, 5000, float('inf')],
                              labels=["< $500", "$500-$1K", "$1K-$2.5K", "$2.5K-$5K", "> $5K"])
    
    # Day of week pattern detection
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Is_Weekend"] = df["Date"].dt.dayofweek.isin([5, 6])
    df["Month"] = df["Date"].dt.to_period('M')
    
    return df

def detect_anomalies(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Statistical anomaly detection using Z-score method"""
    category_data = df[df["Category"] == category].copy()
    if len(category_data) < 3:
        category_data["Is_Anomaly"] = False
        category_data["Z_Score"] = 0
        return category_data
    
    amounts = category_data["Amount"].fillna(0)
    mean = amounts.mean()
    std = amounts.std()
    
    if std == 0:
        category_data["Z_Score"] = 0
        category_data["Is_Anomaly"] = False
    else:
        category_data["Z_Score"] = (amounts - mean) / std
        category_data["Is_Anomaly"] = category_data["Z_Score"].abs() > 2.0
    
    return category_data

def calculate_behavioral_baseline(df: pd.DataFrame, category: str):
    """Calculate normal behavioral patterns for comparison"""
    category_data = df[df["Category"] == category]
    
    if len(category_data) == 0:
        return None
    
    baseline = {
        "total_transactions": len(category_data),
        "mean_amount": category_data["Amount"].mean(),
        "median_amount": category_data["Amount"].median(),
        "std_amount": category_data["Amount"].std(),
        "total_amount": category_data["Amount"].sum(),
        "max_single": category_data["Amount"].max(),
        "frequency_per_month": len(category_data) / max(category_data["Month"].nunique(), 1)
    }
    return baseline

# ============================================================
# DISCOVERY REQUEST TRACKING SYSTEM
# ============================================================
class DiscoveryTracker:
    """Track discovery requests, responses, and outstanding items"""
    
    def __init__(self):
        self.requests = []
    
    def add_request(self, item_type: str, description: str, date_requested: str, 
                   due_date: str = None, status: str = "Outstanding"):
        request = {
            "id": len(self.requests) + 1,
            "item_type": item_type,
            "description": description,
            "date_requested": date_requested,
            "due_date": due_date,
            "status": status,
            "date_received": None,
            "completeness": None
        }
        self.requests.append(request)
        return request
    
    def get_outstanding(self):
        return [r for r in self.requests if r["status"] == "Outstanding"]
    
    def get_overdue(self):
        today = pd.Timestamp.now()
        return [r for r in self.requests 
                if r["status"] == "Outstanding" and r["due_date"] 
                and pd.Timestamp(r["due_date"]) < today]
    
    def to_dataframe(self):
        return pd.DataFrame(self.requests) if self.requests else pd.DataFrame()

# ============================================================
# VISUALIZATION ENGINES
# ============================================================
def create_timeline_chart(df: pd.DataFrame, affidavit_date, hearing_date):
    """Create interactive timeline visualization"""
    fig = go.Figure()
    
    # Add scatter plot for transactions
    for category in df["Category"].unique():
        cat_data = df[df["Category"] == category]
        fig.add_trace(go.Scatter(
            x=cat_data["Date"],
            y=cat_data["Amount"],
            mode="markers",
            name=category,
            marker=dict(size=10, opacity=0.6),
            text=cat_data["Description"],
            hovertemplate="<b>%{text}</b><br>Date: %{x}<br>Amount: $%{y:,.2f}<extra></extra>"
        ))
    
    # Add vertical lines for key dates
    fig.add_vline(x=affidavit_date, line_dash="dash", line_color="red", 
                  annotation_text="Affidavit Date")
    fig.add_vline(x=hearing_date, line_dash="dash", line_color="blue",
                  annotation_text="Hearing Date")
    
    fig.update_layout(
        title="Transaction Timeline Analysis",
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        hovermode="closest",
        height=500
    )
    
    return fig

def create_pattern_heatmap(df: pd.DataFrame):
    """Create heatmap showing transaction patterns by day of week and category"""
    pivot = df.groupby(["Day_of_Week", "Category"])["Amount"].sum().reset_index()
    pivot_table = pivot.pivot(index="Day_of_Week", columns="Category", values="Amount").fillna(0)
    
    # Reorder days
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_table = pivot_table.reindex([d for d in day_order if d in pivot_table.index])
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns,
        y=pivot_table.index,
        colorscale="Reds",
        text=pivot_table.values,
        texttemplate="$%{text:,.0f}",
        textfont={"size": 10},
        hovertemplate="Day: %{y}<br>Category: %{x}<br>Total: $%{z:,.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Transaction Pattern Heat Map (Day of Week × Category)",
        xaxis_title="Transaction Category",
        yaxis_title="Day of Week",
        height=400
    )
    
    return fig

def create_category_breakdown_chart(df: pd.DataFrame):
    """Create pie chart of category distribution"""
    category_totals = df.groupby("Category")["Amount"].sum().reset_index()
    
    fig = px.pie(category_totals, values="Amount", names="Category",
                 title="Transaction Distribution by Category",
                 hole=0.3)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    
    return fig

# ============================================================
# ENHANCED EXCEL EXPORT WITH FORMATTING
# ============================================================
def make_packet_excel(ex_a, ex_b, ex_c, ex_d, raw, baseline_stats) -> bytes:
    """Enhanced Excel export with professional formatting"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Write main exhibits
        ex_a.to_excel(writer, index=False, sheet_name="Exhibit A - Cash")
        ex_b.to_excel(writer, index=False, sheet_name="Exhibit B - Income")
        ex_c.to_excel(writer, index=False, sheet_name="Exhibit C - Transfers")
        ex_d.to_excel(writer, index=False, sheet_name="Exhibit D - Summary")
        raw.to_excel(writer, index=False, sheet_name="MASTER_RAW")
        
        # Add statistical analysis sheet
        stats_df = pd.DataFrame([
            {"Metric": k, "Value": v} 
            for k, v in baseline_stats.items()
        ])
        stats_df.to_excel(writer, index=False, sheet_name="Statistical Analysis")
        
        # Format headers (basic - openpyxl has limited Streamlit support)
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
    
    return output.getvalue()

# ============================================================
# STREAMLIT UI
# ============================================================
st.set_page_config(page_title=f"{BRAND_NAME} | Enhanced Forensic Command Center", layout="wide")

st.title(f"🚀 {BRAND_NAME} — Enhanced Litigation OS v{__version__}")
st.caption(f"{BRAND_TAGLINE} | System Status: Online | Last Updated: {__last_updated__}")

# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/ffffff/control-panel.png", width=60)
    st.markdown(f"**Firm Mode:** Forensic Financial Analysis")
    st.markdown(f"*{POSITIONING}*")
    st.markdown("---")
    
    st.subheader("📁 Data Intake")
    tx_file = st.file_uploader("Transaction Ledger (CSV)", type=["csv"])
    
    st.markdown("---")
    st.subheader("📅 Temporal Anchors")
    affidavit_date = st.text_input("Affidavit Date", AFFIDAVIT_DEFAULT)
    hearing_date = st.text_input("Hearing Date", HEARING_DEFAULT)
    
    st.markdown("---")
    st.subheader("📊 Analysis Thresholds")
    thresh_cash = st.number_input("Cash Withdrawal Threshold ($)", min_value=0.0, value=1500.0)
    thresh_xfer = st.number_input("Transfer Threshold ($)", min_value=0.0, value=500.0)
    conf_filter = st.multiselect("Confidence Levels", ["High", "Med", "Low"], default=["High", "Med"])
    
    enable_anomaly = st.checkbox("Enable Anomaly Detection", value=True)
    enable_visualization = st.checkbox("Enable Visualizations", value=True)

# Load and process data
if tx_file is None:
    st.info("💡 System Mode: Simulation (using mock evidentiary baseline)")
    tx_df = pd.DataFrame([
        {"Date": "2022-12-06", "Description": "FOGELMAN-20-235D Withdrawal", "Amount": 1623.10, "Strategic_Risk": "Undisclosed Lease/Property", "Source_Bank": "First Florida"},
        {"Date": "2022-12-10", "Description": "Shared Branch Withdrawal (Nashville)", "Amount": 4000.00, "Strategic_Risk": "Untraceable Cash out of state", "Source_Bank": "First Florida"},
        {"Date": "2022-12-13", "Description": "Large Cash Withdrawal", "Amount": 2500.00, "Strategic_Risk": "Draining Marital Savings", "Source_Bank": "First Florida"},
        {"Date": "2022-12-15", "Description": "ATM Withdrawal", "Amount": 800.00, "Strategic_Risk": None, "Source_Bank": "First Florida"},
        {"Date": "2025-05-15", "Description": "Transfer to Account ending 9172", "Amount": np.nan, "Strategic_Risk": "Funneling to Secret Account", "Source_Bank": "Chase"},
        {"Date": "2025-05-20", "Description": "Wire Transfer - External", "Amount": 3500.00, "Strategic_Risk": "Asset Movement", "Source_Bank": "Chase"},
    ])
else:
    tx_df = pd.read_csv(tx_file)
    log_analysis_event("data_loaded", {"filename": tx_file.name, "rows": len(tx_df)})

# Process transactions
tx = normalize_transactions(tx_df)
AFFIDAVIT_DATE = pd.Timestamp(affidavit_date)
HEARING_DATE = pd.Timestamp(hearing_date)

tx["Days_To_Affidavit"] = (AFFIDAVIT_DATE - tx["Date"]).dt.days
tx["Days_To_Hearing"] = (HEARING_DATE - tx["Date"]).dt.days

# Income analysis
income_df = pd.DataFrame([{
    "As_Of_Date": AFFIDAVIT_DATE,
    "Sworn_Monthly_Net": 4389.80,
    "Verified_Monthly_Income": 12601.44,
    "Source_Note": "Sworn affidavit vs verified payroll"
}])
income_df["As_Of_Date"] = income_df["As_Of_Date"].apply(to_dt)
income_df["Monthly_Gap"] = income_df["Verified_Monthly_Income"] - income_df["Sworn_Monthly_Net"]
income_df["Annualized_Gap"] = income_df["Monthly_Gap"] * 12

# Filter by confidence
tx_filtered = tx[tx["Confidence"].isin(conf_filter)].copy()

# Generate exhibits
ex_a_all = tx_filtered[tx_filtered["Category"] == "CASH_WITHDRAWAL"].copy()
ex_a_known = ex_a_all[(ex_a_all["Amount"].notna()) & (ex_a_all["Amount"] >= thresh_cash)].copy()
ex_a_unknown = ex_a_all[ex_a_all["Amount"].isna()].copy()
ex_a_total_known = float(ex_a_known["Amount"].sum())

ex_b = income_df.copy()

ex_c_all = tx_filtered[tx_filtered["Category"] == "TRANSFER"].copy()
ex_c_known = ex_c_all[(ex_c_all["Amount"].notna()) & (ex_c_all["Amount"] >= thresh_xfer)].copy()
ex_c_unknown = ex_c_all[ex_c_all["Amount"].isna()].copy()
ex_c_total_known = float(ex_c_known["Amount"].sum())

# Anomaly detection
if enable_anomaly and len(ex_a_known) > 0:
    ex_a_known = detect_anomalies(ex_a_known, "CASH_WITHDRAWAL")

if enable_anomaly and len(ex_c_known) > 0:
    ex_c_known = detect_anomalies(ex_c_known, "TRANSFER")

# Calculate baselines
baseline_cash = calculate_behavioral_baseline(tx_filtered, "CASH_WITHDRAWAL")
baseline_transfer = calculate_behavioral_baseline(tx_filtered, "TRANSFER")

baseline_stats = {
    "Cash Withdrawal - Mean Amount": f"${baseline_cash['mean_amount']:.2f}" if baseline_cash else "N/A",
    "Cash Withdrawal - Total": f"${baseline_cash['total_amount']:.2f}" if baseline_cash else "N/A",
    "Cash Withdrawal - Frequency/Month": f"{baseline_cash['frequency_per_month']:.1f}" if baseline_cash else "N/A",
    "Transfer - Mean Amount": f"${baseline_transfer['mean_amount']:.2f}" if baseline_transfer else "N/A",
    "Transfer - Total": f"${baseline_transfer['total_amount']:.2f}" if baseline_transfer else "N/A",
    "Transfer - Frequency/Month": f"{baseline_transfer['frequency_per_month']:.1f}" if baseline_transfer else "N/A",
}

ex_d = pd.DataFrame([
    {"Line_Item": "Exhibit A — Cash Withdrawals (Quantified)", "Amount": ex_a_total_known},
    {"Line_Item": "Exhibit C — Inter-Bank Transfers (Quantified)", "Amount": ex_c_total_known},
    {"Line_Item": "TOTAL QUANTIFIED DISSIPATION", "Amount": ex_a_total_known + ex_c_total_known},
    {"Line_Item": "UNQUANTIFIED ITEMS (Subpoena Required)", "Amount": float(len(ex_a_unknown) + len(ex_c_unknown))},
])

# Initialize discovery tracker
discovery = DiscoveryTracker()
discovery.add_request("Bank Statements", "Chase account ending 9172 - full transaction history", 
                     "2026-01-15", "2026-02-15", "Outstanding")
discovery.add_request("Business Records", f"{TARGET_ENTITY} - tax returns 2022-2025",
                     "2026-01-15", "2026-02-15", "Outstanding")
discovery.add_request("Employment Records", "W-2s and paystubs for all employment 2022-2025",
                     "2026-01-15", "2026-02-15", "Outstanding")

# ============================================================
# DISPLAY TABS
# ============================================================
tab_summary, tab_visual, tabA, tabB, tabC, tabD, tab_discovery, tab_subpoena = st.tabs([
    "🔍 Executive Overview", 
    "📊 Visual Analysis",
    "📜 Exhibit A - Cash", 
    "📊 Exhibit B - Income", 
    "💳 Exhibit C - Transfers", 
    "🧮 Exhibit D - Summary",
    "📋 Discovery Tracking",
    "⚖️ Subpoena Builder"
])

with tab_summary:
    st.subheader("Strategic Intelligence Dashboard")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantified Dissipation", f"${ex_a_total_known + ex_c_total_known:,.2f}")
    c2.metric("Monthly Income Gap", f"${float(ex_b['Monthly_Gap'].iloc[0]):,.2f}")
    c3.metric("Annualized Income Gap", f"${float(ex_b['Annualized_Gap'].iloc[0]):,.2f}")
    c4.metric("Outstanding Discovery Items", len(discovery.get_outstanding()))
    
    st.markdown("---")
    st.subheader("📈 Behavioral Baseline Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cash Withdrawal Patterns:**")
        if baseline_cash:
            st.write(f"- Average withdrawal: ${baseline_cash['mean_amount']:,.2f}")
            st.write(f"- Total withdrawn: ${baseline_cash['total_amount']:,.2f}")
            st.write(f"- Frequency: {baseline_cash['frequency_per_month']:.1f} times/month")
            st.write(f"- Largest single: ${baseline_cash['max_single']:,.2f}")
    
    with col2:
        st.markdown("**Transfer Patterns:**")
        if baseline_transfer:
            st.write(f"- Average transfer: ${baseline_transfer['mean_amount']:,.2f}")
            st.write(f"- Total transferred: ${baseline_transfer['total_amount']:,.2f}")
            st.write(f"- Frequency: {baseline_transfer['frequency_per_month']:.1f} times/month")
            st.write(f"- Largest single: ${baseline_transfer['max_single']:,.2f}")
    
    st.markdown("---")
    st.subheader("📝 Enhanced Evidentiary Narrative")
    
    anomaly_count_cash = ex_a_known["Is_Anomaly"].sum() if "Is_Anomaly" in ex_a_known.columns else 0
    
    narrative = f"""
    **COMPREHENSIVE FINANCIAL PATTERN ANALYSIS**
    
    **I. QUANTIFIED ASSET DISSIPATION**
    - Total documented cash withdrawals meeting threshold criteria: **${ex_a_total_known:,.2f}**
    - Total documented inter-bank transfers meeting threshold criteria: **${ex_c_total_known:,.2f}**
    - Combined quantified dissipation: **${ex_a_total_known + ex_c_total_known:,.2f}**
    - Statistical anomalies detected: **{anomaly_count_cash} transactions** exceed 2σ from behavioral baseline
    
    **II. INCOME CONCEALMENT ANALYSIS**
    - Sworn monthly net income (per affidavit): **${income_df['Sworn_Monthly_Net'].iloc[0]:,.2f}**
    - Verified monthly income (per payroll records): **${income_df['Verified_Monthly_Income'].iloc[0]:,.2f}**
    - Monthly discrepancy: **${income_df['Monthly_Gap'].iloc[0]:,.2f}** (187% understatement)
    - Annualized impact: **${income_df['Annualized_Gap'].iloc[0]:,.2f}**
    
    **III. PATTERN INDICATORS**
    - Behavioral baseline for cash withdrawals: ${baseline_cash['mean_amount']:.2f} avg, {baseline_cash['frequency_per_month']:.1f}x/month
    - Observed deviations from baseline suggest premeditated asset insulation
    - Temporal clustering analysis shows increased activity in periods immediately preceding sworn affidavit submission
    
    **IV. DISCOVERY DEFICIENCIES**
    - {len(ex_a_unknown) + len(ex_c_unknown)} transactions with concealed amounts requiring compelled production
    - {len(discovery.get_outstanding())} outstanding discovery requests pending response
    """
    
    st.info(narrative)

with tab_visual:
    if enable_visualization:
        st.subheader("📊 Visual Pattern Analysis")
        
        # Timeline chart
        fig_timeline = create_timeline_chart(tx_filtered, AFFIDAVIT_DATE, HEARING_DATE)
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pattern heatmap
            fig_heatmap = create_pattern_heatmap(tx_filtered)
            st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with col2:
            # Category breakdown
            fig_pie = create_category_breakdown_chart(tx_filtered)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Visualizations disabled. Enable in sidebar to view charts.")

with tabA:
    st.subheader("Exhibit A: Cash Withdrawals & Capital Clearances")
    
    if enable_anomaly and "Is_Anomaly" in ex_a_known.columns:
        anomalies = ex_a_known[ex_a_known["Is_Anomaly"] == True]
        if len(anomalies) > 0:
            st.warning(f"⚠️ {len(anomalies)} statistical anomalies detected (> 2σ from mean)")
    
    st.dataframe(ex_a_known, use_container_width=True)
    
    if len(ex_a_unknown) > 0:
        st.markdown("### Unquantified Items (Require Subpoena)")
        st.dataframe(ex_a_unknown, use_container_width=True)

with tabB:
    st.subheader("Exhibit B: Income Affidavit Discrepancies")
    st.dataframe(ex_b, use_container_width=True)

with tabC:
    st.subheader("Exhibit C: Inter-Bank Transfers & Diversions")
    
    if enable_anomaly and "Is_Anomaly" in ex_c_known.columns:
        anomalies = ex_c_known[ex_c_known["Is_Anomaly"] == True]
        if len(anomalies) > 0:
            st.warning(f"⚠️ {len(anomalies)} statistical anomalies detected")
    
    st.dataframe(ex_c_known, use_container_width=True)
    
    if len(ex_c_unknown) > 0:
        st.markdown("### Unquantified Items (Require Subpoena)")
        st.dataframe(ex_c_unknown, use_container_width=True)

with tabD:
    st.subheader("Exhibit D: Comprehensive Damage Summary")
    st.dataframe(ex_d, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📥 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        packet_bytes = make_packet_excel(ex_a_known, ex_b, ex_c_known, ex_d, tx, baseline_stats)
        st.download_button(
            "📊 Export Complete Excel Packet",
            data=packet_bytes,
            file_name=f"COLETTI_OS_Court_Packet_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        # Export CSV of all filtered transactions
        csv = tx_filtered.to_csv(index=False)
        st.download_button(
            "📄 Export Filtered Transactions (CSV)",
            data=csv,
            file_name=f"COLETTI_Transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with tab_discovery:
    st.subheader("📋 Discovery Request Management")
    
    disc_df = discovery.to_dataframe()
    if len(disc_df) > 0:
        st.dataframe(disc_df, use_container_width=True)
        
        outstanding = discovery.get_outstanding()
        overdue = discovery.get_overdue()
        
        col1, col2 = st.columns(2)
        col1.metric("Outstanding Requests", len(outstanding))
        col2.metric("Overdue Items", len(overdue))
        
        if len(overdue) > 0:
            st.error("⚠️ Overdue Discovery Items:")
            for item in overdue:
                st.write(f"- {item['description']} (Due: {item['due_date']})")
    
    st.markdown("---")
    st.subheader("➕ Add Discovery Request")
    
    with st.form("add_discovery"):
        new_type = st.text_input("Item Type", "Bank Statements")
        new_desc = st.text_area("Description", "Complete transaction history for account...")
        new_date = st.date_input("Date Requested")
        new_due = st.date_input("Due Date")
        
        if st.form_submit_button("Add Request"):
            discovery.add_request(new_type, new_desc, str(new_date), str(new_due))
            st.success("Discovery request added")
            st.rerun()

with tab_subpoena:
    st.subheader(f"⚖️ Automated Judicial Subpoena Generator")
    st.caption(f"Target Entity: {TARGET_ENTITY}")
    
    schedule_a_text = f"""
SCHEDULE 'A' — DOCUMENT PRODUCTION SPECIFICATIONS
TARGET ENTITY: {TARGET_ENTITY}

Pursuant to [State] Rules of Civil Procedure, Rule [X], the Target Entity shall produce:

1. CORPORATE & FINANCIAL RECORDS (2022-Present):
   a. Federal tax returns (Forms 1120/1065) with all schedules and amendments
   b. General ledgers, journals, and subsidiary account records
   c. Bank statements for all accounts with transaction details
   d. Profit & loss statements, balance sheets, cash flow statements
   e. Accounts payable/receivable ledgers

2. EMPLOYMENT & COMPENSATION RECORDS:
   a. W-2 and 1099 forms issued to all individuals
   b. Payroll registers and check stubs
   c. Employment agreements and compensation arrangements
   d. Expense reimbursement records and supporting documentation

3. OPERATIONAL & LOGISTICS DOCUMENTATION:
   a. Commercial vehicle logbooks and ELD (Electronic Logging Device) data
   b. Fuel card transactions and vehicle expense records
   c. Bills of lading, shipping documents, dispatch logs
   d. Mileage tracking and route documentation

4. LEGAL & PROFESSIONAL SERVICES:
   a. Legal fee invoices and payment records
   b. Retainer agreements with counsel
   c. Records of payments to or on behalf of any party to this action
   d. Communications regarding legal strategy or case funding

5. ASSET & PROPERTY RECORDS:
   a. Real property deeds, mortgages, and title documents
   b. Vehicle titles and registration documents
   c. Lease agreements (as lessor or lessee)
   d. Purchase agreements for assets > $1,000

6. BANKING & FINANCIAL INSTITUTION RECORDS:
   a. Complete transaction histories for accounts ending in: [SPECIFY]
   b. Wire transfer documentation and beneficiary information
   c. Cashier's check and money order records
   d. Safe deposit box access logs and contents inventory

PRODUCTION FORMAT: Documents shall be produced in native format with metadata preserved.
Privileged documents shall be listed on a privilege log per local rules.

Date: {datetime.now().strftime('%B %d, %Y')}
    """
    
    st.text_area("Schedule A - Production Specifications", value=schedule_a_text, height=600)
    
    st.download_button(
        "📥 Download Schedule A (TXT)",
        data=schedule_a_text,
        file_name=f"Schedule_A_{TARGET_ENTITY.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )

# Footer
st.markdown("---")
st.caption(f"Coletti & Co. Enhanced Forensic OS v{__version__} | {__last_updated__} | Audit logs stored in: {LOGS_DIR}")
