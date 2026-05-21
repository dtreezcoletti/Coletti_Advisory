import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from collections import defaultdict

# Advanced Analytics Imports
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    st.warning("⚠️ scikit-learn not installed. Isolation Forest disabled. Install: pip install scikit-learn")

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    st.warning("⚠️ rapidfuzz not installed. Fuzzy matching disabled. Install: pip install rapidfuzz")

# ============================================================
# COLETTI & CO — HARDENED FORENSIC OS v2.7.0
# ============================================================
__version__ = "2.7.0"
__last_updated__ = "2026-05-20"

BRAND_NAME = "Coletti & Co."
BRAND_TAGLINE = "Operational Integrity & Risk Advisory"
POSITIONING = "Coletti & Co. helps founder-led service businesses turn chaos into documented, decision-ready clarity — before their risks become crises."
TARGET_ENTITY = "Coletti & Brown Enterprises, LLC"

AFFIDAVIT_DEFAULT = "2025-05-27"
HEARING_DEFAULT = "2026-02-20"

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault" / "clients"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "audit_logs"

CLIENT_FOLDERS = ["01_raw", "02_clean", "03_findings", "04_reports", "05_knowledge"]
for folder in CLIENT_FOLDERS:
    (VAULT_DIR / "SAMPLE_CLIENT" / folder).mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# ENHANCED PATTERN EXTRACTION ENGINES
# ============================================================

def extract_account_numbers(text: str) -> list:
    """Extract account numbers, routing numbers, and reference IDs"""
    if not text:
        return []
    
    patterns = [
        r'\b\d{4,17}\b',  # Account numbers (4-17 digits)
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Card numbers
        r'(?:ending|acct|account|#)\s*(?:in\s+)?(\d+)',  # "ending in 1234"
        r'[A-Z0-9]{8,}',  # Reference codes
    ]
    
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend(found)
    
    return list(set(matches))

def extract_crypto_indicators(text: str) -> list:
    """Detect cryptocurrency-related transactions"""
    if not text:
        return []
    
    crypto_keywords = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase',
        'binance', 'kraken', 'blockchain', 'wallet', 'metamask',
        'ledger', 'trezor', 'defi', 'nft', 'usdt', 'usdc'
    ]
    
    text_lower = text.lower()
    return [kw for kw in crypto_keywords if kw in text_lower]

def fuzzy_classify_vendor(description: str, known_vendors: list, threshold: int = 80) -> tuple:
    """Fuzzy match transaction descriptions against known vendor patterns"""
    if not FUZZY_AVAILABLE or not description or not known_vendors:
        return None, 0
    
    result = process.extractOne(description, known_vendors, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0], result[1]
    return None, 0

# ============================================================
# ADAPTIVE CLASSIFICATION ENGINE v2.7
# ============================================================

def classify_txn_v2(description: str, amount: float = 0.0, known_accounts: list = None,
                    known_vendors: list = None) -> dict:
    """
    Enhanced classification with fuzzy matching and pattern extraction.
    Returns: dict with category, confidence, rule, and extracted metadata
    """
    d = str(description or "").lower()
    amt = float(amount or 0.0)
    
    # Extract metadata
    accounts = extract_account_numbers(description)
    crypto_signals = extract_crypto_indicators(description)
    
    result = {
        "category": "OTHER",
        "confidence": "Low",
        "rule": "no match",
        "extracted_accounts": accounts,
        "crypto_indicators": crypto_signals,
        "fuzzy_vendor": None,
        "fuzzy_score": 0
    }
    
    # Cryptocurrency detection (HIGH PRIORITY)
    if crypto_signals:
        result.update({
            "category": "CRYPTO_CONVERSION",
            "confidence": "High",
            "rule": f"Crypto indicators: {', '.join(crypto_signals)}"
        })
        return result
    
    # Business/Commercial Risk Matrix
    business_rules = [
        ("INTERNAL_THEFT", "High", "ATM Withdrawal > $500", "withdrawal" in d and amt > 500),
        ("CONTRACTOR_FRAUD", "Med", "P2P Payment", any(x in d for x in ["venmo", "cashapp", "paypal", "zelle"])),
        ("ASSET_SIPHON", "High", "Transfer to Personal Account", "transfer" in d and ("personal" in d or len(accounts) > 0)),
        ("TAX_RISK", "Med", "Luxury/Travel", any(x in d for x in ["hotel", "resort", "airline", "cruise"])),
        ("GAMBLING", "High", "Gaming Activity", any(x in d for x in ["casino", "gaming", "draftkings", "fanduel", "bet"])),
        ("OFFSHORE", "High", "International Wire", any(x in d for x in ["wire", "swift", "international", "foreign"])),
    ]
    
    # Cash Extraction Rules
    cash_rules = [
        ("CASH_WITHDRAWAL", "High", "keyword: withdrawal", "withdrawal" in d),
        ("CASH_WITHDRAWAL", "Med", "keyword: cash", "cash" in d and "cashback" not in d),
        ("CASH_WITHDRAWAL", "Med", "keyword: atm", "atm" in d),
        ("CASH_WITHDRAWAL", "Med", "keyword: shared branch", "shared branch" in d),
        ("CASH_WITHDRAWAL", "High", "Large Cash Advance", "cash advance" in d and amt > 1000),
    ]
    
    # Transfer Rules
    xfer_rules = [
        ("TRANSFER", "High", "keyword: transfer", "transfer" in d),
        ("TRANSFER", "High", "keyword: wire", "wire" in d),
        ("TRANSFER", "Med", "keyword: zelle", "zelle" in d),
        ("TRANSFER", "Med", "keyword: ach", "ach" in d),
        ("TRANSFER", "Med", "External Transfer", "external" in d),
    ]
    
    # Asset Movement
    asset_rules = [
        ("ASSET_PURCHASE", "High", "Real Estate Transaction", any(x in d for x in ["title", "escrow", "real estate", "closing"])),
        ("VEHICLE_PAYMENT", "Med", "Vehicle Purchase", any(x in d for x in ["auto", "vehicle", "carmax", "carvana"])),
        ("INVESTMENT", "Med", "Brokerage Transfer", any(x in d for x in ["schwab", "fidelity", "vanguard", "robinhood"])),
    ]
    
    # Check all rules
    for cat, conf, rule, triggered in business_rules + cash_rules + xfer_rules + asset_rules:
        if triggered:
            result.update({
                "category": cat,
                "confidence": conf,
                "rule": rule
            })
            break
    
    # Fuzzy vendor matching (if still unclassified)
    if result["category"] == "OTHER" and FUZZY_AVAILABLE and known_vendors:
        vendor, score = fuzzy_classify_vendor(description, known_vendors)
        if vendor:
            result.update({
                "fuzzy_vendor": vendor,
                "fuzzy_score": score,
                "confidence": "Med",
                "rule": f"Fuzzy match: {vendor} ({score}%)"
            })
    
    # Unknown account flag
    if known_accounts and accounts:
        unknown_accounts = [a for a in accounts if a not in known_accounts]
        if unknown_accounts:
            result["category"] = "UNKNOWN_ACCOUNT"
            result["confidence"] = "High"
            result["rule"] = f"Unrecognized accounts: {', '.join(unknown_accounts)}"
    
    return result

def normalize_transactions_v2(df: pd.DataFrame, known_accounts: list = None, 
                              known_vendors: list = None) -> pd.DataFrame:
    """Enhanced normalization with v2 classification"""
    df = df.copy()
    
    optional_cols = ["Strategic_Risk", "Source_Bank", "Statement_Period", "Statement_Page", "Line_Item", "To_Account"]
    for c in optional_cols:
        if c not in df.columns:
            df[c] = None
    
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    
    # V2 Classification
    classifications = df.apply(
        lambda r: pd.Series(classify_txn_v2(r["Description"], r["Amount"], known_accounts, known_vendors)),
        axis=1
    )
    
    # Flatten the nested dict columns
    df["Category"] = classifications["category"]
    df["Confidence"] = classifications["confidence"]
    df["Rule_Triggered"] = classifications["rule"]
    df["Extracted_Accounts"] = classifications["extracted_accounts"]
    df["Crypto_Indicators"] = classifications["crypto_indicators"]
    df["Fuzzy_Vendor"] = classifications["fuzzy_vendor"]
    df["Fuzzy_Score"] = classifications["fuzzy_score"]
    
    # Additional computed fields
    df["Is_Amount_Known"] = df["Amount"].notna()
    df["Amount_Bin"] = pd.cut(df["Amount"].fillna(0), 
                              bins=[0, 500, 1000, 2500, 5000, float('inf')],
                              labels=["< $500", "$500-$1K", "$1K-$2.5K", "$2.5K-$5K", "> $5K"])
    
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Is_Weekend"] = df["Date"].dt.dayofweek.isin([5, 6])
    df["Month"] = df["Date"].dt.to_period('M')
    df["Week"] = df["Date"].dt.to_period('W')
    
    return df

# ============================================================
# ADVANCED ANOMALY DETECTION: ISOLATION FOREST
# ============================================================

def detect_anomalies_isolation_forest(df: pd.DataFrame, category: str = None) -> pd.DataFrame:
    """
    Isolation Forest-based anomaly detection.
    Does NOT assume normal distribution. Handles skewed financial data correctly.
    """
    if not SKLEARN_AVAILABLE:
        st.warning("Isolation Forest unavailable. Install scikit-learn.")
        df["Is_Anomaly_IF"] = False
        df["Anomaly_Score"] = 0.0
        return df
    
    work_df = df.copy()
    
    # Filter by category if specified
    if category:
        work_df = work_df[work_df["Category"] == category].copy()
    
    # Need at least 10 samples for meaningful IF analysis
    if len(work_df) < 10:
        work_df["Is_Anomaly_IF"] = False
        work_df["Anomaly_Score"] = 0.0
        return work_df
    
    # Prepare features
    features = []
    if "Amount" in work_df.columns:
        features.append("Amount")
    
    # Add temporal features
    work_df["DayOfYear"] = work_df["Date"].dt.dayofyear
    work_df["DaysSinceFirst"] = (work_df["Date"] - work_df["Date"].min()).dt.days
    features.extend(["DayOfYear", "DaysSinceFirst"])
    
    # Remove rows with missing features
    feature_data = work_df[features].fillna(0)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feature_data)
    
    # Isolation Forest
    iso_forest = IsolationForest(
        contamination=0.1,  # Expect ~10% anomalies
        random_state=42,
        n_estimators=100
    )
    
    work_df["Is_Anomaly_IF"] = iso_forest.fit_predict(X_scaled) == -1
    work_df["Anomaly_Score"] = iso_forest.score_samples(X_scaled)
    
    return work_df

# ============================================================
# TEMPORAL VELOCITY & CLUSTERING DETECTION
# ============================================================

def detect_structuring(df: pd.DataFrame, window_days: int = 7, 
                       amount_threshold: float = 10000, proximity_threshold: float = 0.9) -> pd.DataFrame:
    """
    Detects structuring: multiple sub-threshold transactions that cluster temporally
    and sum to exceed threshold within a rolling window.
    
    Classic evasion: Instead of 1x $10,000 transfer, do 11x $900 over 10 days.
    """
    df = df.copy()
    df = df.sort_values("Date").reset_index(drop=True)
    
    df["Is_Structured"] = False
    df["Structured_Cluster_ID"] = None
    df["Cluster_Total"] = 0.0
    df["Cluster_Count"] = 0
    
    cluster_id = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row["Amount"]) or row["Amount"] >= amount_threshold:
            continue
        
        # Look at window around this transaction
        date_min = row["Date"] - timedelta(days=window_days)
        date_max = row["Date"] + timedelta(days=window_days)
        
        window = df[
            (df["Date"] >= date_min) & 
            (df["Date"] <= date_max) &
            (df["Category"] == row["Category"]) &
            (df["Amount"] < amount_threshold) &
            (df["Amount"].notna())
        ].copy()
        
        if len(window) < 2:
            continue
        
        cluster_total = window["Amount"].sum()
        
        # If cluster exceeds threshold, flag it
        if cluster_total >= amount_threshold:
            cluster_id += 1
            for widx in window.index:
                df.at[widx, "Is_Structured"] = True
                df.at[widx, "Structured_Cluster_ID"] = f"CLUSTER_{cluster_id}"
                df.at[widx, "Cluster_Total"] = cluster_total
                df.at[widx, "Cluster_Count"] = len(window)
    
    return df

def calculate_velocity_metrics(df: pd.DataFrame, category: str = None) -> dict:
    """
    Calculate transaction velocity: frequency, acceleration, temporal clustering.
    Detects sudden changes in behavioral patterns.
    """
    work_df = df.copy()
    if category:
        work_df = work_df[work_df["Category"] == category]
    
    if len(work_df) < 2:
        return {}
    
    work_df = work_df.sort_values("Date")
    
    # Calculate inter-transaction intervals
    work_df["Days_Since_Last"] = work_df["Date"].diff().dt.days
    
    metrics = {
        "total_transactions": len(work_df),
        "date_range_days": (work_df["Date"].max() - work_df["Date"].min()).days,
        "avg_interval_days": work_df["Days_Since_Last"].mean(),
        "min_interval_days": work_df["Days_Since_Last"].min(),
        "max_interval_days": work_df["Days_Since_Last"].max(),
        "velocity_transactions_per_week": len(work_df) / max((work_df["Date"].max() - work_df["Date"].min()).days / 7, 1),
    }
    
    # Detect acceleration (second half vs first half)
    midpoint = work_df["Date"].min() + (work_df["Date"].max() - work_df["Date"].min()) / 2
    first_half = work_df[work_df["Date"] <= midpoint]
    second_half = work_df[work_df["Date"] > midpoint]
    
    if len(first_half) > 0 and len(second_half) > 0:
        velocity_first = len(first_half) / max((first_half["Date"].max() - first_half["Date"].min()).days / 7, 1)
        velocity_second = len(second_half) / max((second_half["Date"].max() - second_half["Date"].min()).days / 7, 1)
        metrics["velocity_acceleration"] = (velocity_second - velocity_first) / max(velocity_first, 0.1)
    else:
        metrics["velocity_acceleration"] = 0
    
    return metrics

# ============================================================
# ENHANCED SUBPOENA GENERATOR WITH DIGITAL ASSETS
# ============================================================

def generate_schedule_a_v2(target_entity: str, known_accounts: list = None, 
                          crypto_detected: bool = False) -> str:
    """
    Enhanced Schedule A with explicit digital asset discovery language
    """
    
    account_section = ""
    if known_accounts and len(known_accounts) > 0:
        account_list = ", ".join(known_accounts[:10])  # List up to 10
        account_section = f"""
   g. Complete transaction histories for accounts identified in discovery:
      {account_list}
"""
    
    crypto_section = ""
    if crypto_detected:
        crypto_section = """
7. DIGITAL ASSET & CRYPTOCURRENCY RECORDS:
   a. All cryptocurrency exchange accounts (Coinbase, Binance, Kraken, etc.)
   b. Blockchain wallet addresses and associated private keys or seed phrases
   c. Non-fungible token (NFT) holdings and transaction histories  
   d. Decentralized finance (DeFi) protocol interactions and liquidity positions
   e. Stablecoin holdings (USDT, USDC, DAI, etc.)
   f. Records of cryptocurrency mining activities
   g. Peer-to-peer cryptocurrency transactions (LocalBitcoins, Paxful, etc.)
   h. Cold storage wallet inventories (Ledger, Trezor, etc.)
   i. Cryptocurrency tax reporting documents (Form 8949, Schedule D)
"""
    
    p2p_section = """
8. DIGITAL PAYMENT PLATFORM RECORDS:
   a. Venmo account statements and transaction histories
   b. PayPal and PayPal Credit account records
   c. Cash App transaction histories and Bitcoin wallet records
   d. Zelle transfer records and linked bank accounts
   e. Apple Pay and Google Pay transaction histories
   f. Wise (TransferWise) international transfer records
   g. Any other peer-to-peer payment applications
"""
    
    offshore_section = """
9. OFFSHORE & ALTERNATIVE BANKING RECORDS:
   a. Neo-bank accounts (Chime, Revolut, N26, etc.)
   b. Offshore bank accounts in any jurisdiction
   c. Foreign investment accounts and brokerage records
   d. International wire transfer documentation (SWIFT codes, beneficiary info)
   e. Correspondent banking relationships
   f. Safe deposit box access logs and content inventories (domestic and foreign)
"""
    
    template = f"""
SCHEDULE 'A' — COMPREHENSIVE DOCUMENT PRODUCTION SPECIFICATIONS
TARGET ENTITY: {target_entity}

Pursuant to [State] Rules of Civil Procedure, Rule [X], the Target Entity and all 
related parties shall produce the following records and documents:

1. CORPORATE & FINANCIAL RECORDS (2022-Present):
   a. Federal tax returns (Forms 1120/1065/1040 Schedule C) with ALL schedules
   b. State tax returns and business license filings
   c. General ledgers, journals, and subsidiary account records
   d. Bank statements for ALL accounts (personal and business) with full transaction detail
   e. Profit & loss statements, balance sheets, cash flow statements
   f. Accounts payable/receivable ledgers with vendor/customer detail
{account_section}

2. EMPLOYMENT & COMPENSATION RECORDS:
   a. W-2 and 1099 forms issued to and received by all individuals
   b. Payroll registers, check stubs, and direct deposit authorizations
   c. Employment agreements, independent contractor agreements
   d. Expense reimbursement records with supporting receipts
   e. Company credit card statements and usage policies
   f. Mileage reimbursement logs and vehicle use records

3. ASSET & PROPERTY DOCUMENTATION:
   a. Real property deeds, mortgages, promissory notes, title policies
   b. Vehicle titles, registrations, loan documents, lease agreements
   c. Personal property asset inventories and appraisals
   d. Life insurance policies with cash value and beneficiary designations
   e. Retirement account statements (401k, IRA, pension, etc.)
   f. Investment and brokerage account statements (all institutions)

4. OPERATIONAL & LOGISTICS RECORDS:
   a. Commercial vehicle logbooks and ELD (Electronic Logging Device) data
   b. Fuel card transactions (Fleet cards, gas station accounts)
   c. Bills of lading, shipping manifests, delivery records
   d. Dispatch logs, route planning documentation
   e. Vehicle maintenance and repair records

5. LEGAL & PROFESSIONAL SERVICES:
   a. Legal fee invoices, retainer agreements, and payment records
   b. Attorney-client communications (non-privileged business communications)
   c. Accounting and tax preparation service records
   d. Consulting agreements and payments to third parties
   e. Records of litigation funding or third-party financing

6. BUSINESS RELATIONSHIP DOCUMENTATION:
   a. Partnership agreements, operating agreements, bylaws
   b. Shareholder agreements and stock certificates
   c. Buy-sell agreements and succession plans
   d. Joint venture agreements and profit-sharing arrangements
   e. Franchise agreements or licensing contracts

{p2p_section}
{offshore_section}
{crypto_section}

10. METADATA & ELECTRONIC EVIDENCE:
    a. Email communications related to financial transactions
    b. Text messages and encrypted messaging app contents (Signal, WhatsApp, Telegram)
    c. Cloud storage contents (Google Drive, Dropbox, iCloud, OneDrive)
    d. Financial planning software data (Quicken, QuickBooks, Mint)
    e. Digital calendar entries related to financial meetings or transactions

PRODUCTION REQUIREMENTS:
- Native format with full metadata preserved (modified dates, author, etc.)
- Searchable text (OCR for scanned documents)
- Privilege log for any withheld documents per [Local Rule X]
- Rolling production for voluminous records (prioritize last 12 months)
- Certification of completeness by custodian of records

DEADLINE FOR PRODUCTION: [30/60 days from service]

Date: {datetime.now().strftime('%B %d, %Y')}

NOTICE: Failure to produce responsive documents may result in sanctions including adverse 
inference instructions, monetary penalties, and preclusion of evidence at trial.
"""
    
    return template

# ============================================================
# EXCEL EXPORT WITH ENHANCED SHEETS
# ============================================================

def make_packet_excel_v2(ex_a, ex_b, ex_c, ex_d, raw, velocity_metrics, 
                         structuring_summary) -> bytes:
    """Enhanced Excel export with velocity and structuring analysis"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        ex_a.to_excel(writer, index=False, sheet_name="Exhibit A - Cash")
        ex_b.to_excel(writer, index=False, sheet_name="Exhibit B - Income")
        ex_c.to_excel(writer, index=False, sheet_name="Exhibit C - Transfers")
        ex_d.to_excel(writer, index=False, sheet_name="Exhibit D - Summary")
        raw.to_excel(writer, index=False, sheet_name="MASTER_RAW")
        
        # Velocity metrics
        if velocity_metrics:
            velocity_df = pd.DataFrame([
                {"Metric": k, "Value": v}
                for k, v in velocity_metrics.items()
            ])
            velocity_df.to_excel(writer, index=False, sheet_name="Velocity Analysis")
        
        # Structuring summary
        if structuring_summary is not None and len(structuring_summary) > 0:
            structuring_summary.to_excel(writer, index=False, sheet_name="Structuring Detected")
    
    return output.getvalue()

# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(page_title=f"{BRAND_NAME} | Hardened Forensic Platform", layout="wide")

st.title(f"🛡️ {BRAND_NAME} — Hardened Litigation OS v{__version__}")
st.caption(f"{BRAND_TAGLINE} | Adversarial-Resistant Architecture | {__last_updated__}")

# Display capability status
col1, col2, col3 = st.columns(3)
col1.metric("Fuzzy Matching", "✓ Online" if FUZZY_AVAILABLE else "✗ Offline")
col2.metric("Isolation Forest", "✓ Online" if SKLEARN_AVAILABLE else "✗ Offline")
col3.metric("Structuring Detection", "✓ Online")

st.markdown("---")

# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/ffffff/shield.png", width=60)
    st.markdown(f"**Mode:** Advanced Forensic Analysis")
    st.markdown("---")
    
    st.subheader("📁 Data Intake")
    tx_file = st.file_uploader("Transaction Ledger (CSV)", type=["csv"])
    
    st.markdown("---")
    st.subheader("📅 Temporal Anchors")
    affidavit_date = st.text_input("Affidavit Date", AFFIDAVIT_DEFAULT)
    hearing_date = st.text_input("Hearing Date", HEARING_DEFAULT)
    
    st.markdown("---")
    st.subheader("🎯 Known Entities")
    known_accounts_input = st.text_area(
        "Known Account Numbers (one per line)",
        "9172\n5431\n8765",
        height=100
    )
    known_accounts = [a.strip() for a in known_accounts_input.split("\n") if a.strip()]
    
    known_vendors_input = st.text_area(
        "Known Vendors (for fuzzy matching)",
        "First Florida Credit Union\nChase Bank\nWells Fargo",
        height=100
    )
    known_vendors = [v.strip() for v in known_vendors_input.split("\n") if v.strip()]
    
    st.markdown("---")
    st.subheader("📊 Analysis Configuration")
    thresh_cash = st.number_input("Cash Threshold ($)", min_value=0.0, value=1500.0)
    thresh_xfer = st.number_input("Transfer Threshold ($)", min_value=0.0, value=500.0)
    conf_filter = st.multiselect("Confidence", ["High", "Med", "Low"], default=["High", "Med"])
    
    enable_if = st.checkbox("Isolation Forest Anomaly Detection", value=SKLEARN_AVAILABLE)
    enable_structuring = st.checkbox("Structuring Detection", value=True)
    structuring_window = st.number_input("Structuring Window (days)", min_value=1, value=7)
    structuring_threshold = st.number_input("Structuring Threshold ($)", min_value=0.0, value=10000.0)

# Load data
if tx_file is None:
    st.info("💡 Simulation Mode: Using mock evidentiary baseline")
    tx_df = pd.DataFrame([
        {"Date": "2022-12-06", "Description": "FOGELMAN-20-235D Withdrawal", "Amount": 1623.10},
        {"Date": "2022-12-10", "Description": "Shared Branch Withdrawal (Nashville)", "Amount": 4000.00},
        {"Date": "2022-12-13", "Description": "Large Cash Withdrawal", "Amount": 2500.00},
        {"Date": "2022-12-15", "Description": "ATM Withdrawal", "Amount": 800.00},
        {"Date": "2022-12-16", "Description": "Cash Withdrawal", "Amount": 850.00},
        {"Date": "2022-12-17", "Description": "ATM Cash", "Amount": 900.00},
        {"Date": "2022-12-18", "Description": "Withdrawal ATM", "Amount": 920.00},
        {"Date": "2022-12-19", "Description": "Cash ATM", "Amount": 880.00},
        {"Date": "2025-05-15", "Description": "Transfer to Account ending 9172", "Amount": np.nan},
        {"Date": "2025-05-20", "Description": "Wire Transfer - External", "Amount": 3500.00},
        {"Date": "2025-05-21", "Description": "Coinbase Pro Purchase", "Amount": 5000.00},
    ])
else:
    tx_df = pd.read_csv(tx_file)

# Process
tx = normalize_transactions_v2(tx_df, known_accounts, known_vendors)
AFFIDAVIT_DATE = pd.Timestamp(affidavit_date)
HEARING_DATE = pd.Timestamp(hearing_date)

tx["Days_To_Affidavit"] = (AFFIDAVIT_DATE - tx["Date"]).dt.days
tx["Days_To_Hearing"] = (HEARING_DATE - tx["Date"]).dt.days

# Income analysis
income_df = pd.DataFrame([{
    "As_Of_Date": AFFIDAVIT_DATE,
    "Sworn_Monthly_Net": 4389.80,
    "Verified_Monthly_Income": 12601.44,
}])
income_df["As_Of_Date"] = pd.to_datetime(income_df["As_Of_Date"])
income_df["Monthly_Gap"] = income_df["Verified_Monthly_Income"] - income_df["Sworn_Monthly_Net"]
income_df["Annualized_Gap"] = income_df["Monthly_Gap"] * 12

# Filter
tx_filtered = tx[tx["Confidence"].isin(conf_filter)].copy()

# Structuring detection
if enable_structuring:
    tx_filtered = detect_structuring(
        tx_filtered, 
        window_days=structuring_window,
        amount_threshold=structuring_threshold
    )
    structuring_detected = tx_filtered[tx_filtered["Is_Structured"] == True].copy()
else:
    structuring_detected = pd.DataFrame()

# Isolation Forest
if enable_if and SKLEARN_AVAILABLE:
    tx_filtered = detect_anomalies_isolation_forest(tx_filtered)
    if_anomalies = tx_filtered[tx_filtered["Is_Anomaly_IF"] == True]
else:
    if_anomalies = pd.DataFrame()

# Velocity metrics
velocity_cash = calculate_velocity_metrics(tx_filtered, "CASH_WITHDRAWAL")
velocity_transfer = calculate_velocity_metrics(tx_filtered, "TRANSFER")

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

# Crypto detection
crypto_transactions = tx_filtered[tx_filtered["Crypto_Indicators"].apply(len) > 0]
crypto_detected = len(crypto_transactions) > 0

ex_d = pd.DataFrame([
    {"Line_Item": "Exhibit A — Cash Withdrawals", "Amount": ex_a_total_known},
    {"Line_Item": "Exhibit C — Transfers", "Amount": ex_c_total_known},
    {"Line_Item": "Structuring Clusters Detected", "Amount": float(structuring_detected["Structured_Cluster_ID"].nunique() if len(structuring_detected) > 0 else 0)},
    {"Line_Item": "Isolation Forest Anomalies", "Amount": float(len(if_anomalies))},
    {"Line_Item": "Cryptocurrency Transactions", "Amount": float(len(crypto_transactions))},
    {"Line_Item": "TOTAL QUANTIFIED DISSIPATION", "Amount": ex_a_total_known + ex_c_total_known},
])

# ============================================================
# DISPLAY TABS
# ============================================================

tabs = st.tabs([
    "🎯 Executive Dashboard",
    "🔍 Advanced Detection",
    "📜 Exhibit A",
    "📊 Exhibit B", 
    "💳 Exhibit C",
    "🧮 Exhibit D",
    "⚖️ Enhanced Subpoena"
])

with tabs[0]:
    st.subheader("Executive Intelligence Dashboard")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantified Dissipation", f"${ex_a_total_known + ex_c_total_known:,.2f}")
    c2.metric("Income Gap (Annual)", f"${float(ex_b['Annualized_Gap'].iloc[0]):,.2f}")
    c3.metric("Structuring Clusters", len(structuring_detected["Structured_Cluster_ID"].unique()) if len(structuring_detected) > 0 else 0)
    c4.metric("IF Anomalies", len(if_anomalies))
    
    if crypto_detected:
        st.error(f"🚨 CRYPTO ALERT: {len(crypto_transactions)} cryptocurrency transactions detected")
    
    st.markdown("---")
    st.subheader("Velocity Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cash Withdrawal Velocity:**")
        if velocity_cash:
            st.write(f"- Transactions/week: {velocity_cash.get('velocity_transactions_per_week', 0):.2f}")
            st.write(f"- Avg interval: {velocity_cash.get('avg_interval_days', 0):.1f} days")
            st.write(f"- Acceleration factor: {velocity_cash.get('velocity_acceleration', 0):.2%}")
    
    with col2:
        st.markdown("**Transfer Velocity:**")
        if velocity_transfer:
            st.write(f"- Transactions/week: {velocity_transfer.get('velocity_transactions_per_week', 0):.2f}")
            st.write(f"- Avg interval: {velocity_transfer.get('avg_interval_days', 0):.1f} days")
            st.write(f"- Acceleration factor: {velocity_transfer.get('velocity_acceleration', 0):.2%}")

with tabs[1]:
    st.subheader("🔍 Advanced Pattern Detection")
    
    st.markdown("### Structuring Analysis")
    if len(structuring_detected) > 0:
        st.error(f"⚠️ STRUCTURING DETECTED: {len(structuring_detected)} transactions in {structuring_detected['Structured_Cluster_ID'].nunique()} clusters")
        
        for cluster_id in structuring_detected["Structured_Cluster_ID"].unique():
            cluster_data = structuring_detected[structuring_detected["Structured_Cluster_ID"] == cluster_id]
            cluster_total = cluster_data["Cluster_Total"].iloc[0]
            date_range = f"{cluster_data['Date'].min().date()} to {cluster_data['Date'].max().date()}"
            
            st.warning(f"**{cluster_id}**: ${cluster_total:,.2f} across {len(cluster_data)} transactions ({date_range})")
            st.dataframe(cluster_data[["Date", "Description", "Amount", "Category"]], use_container_width=True)
    else:
        st.success("No structuring patterns detected")
    
    st.markdown("---")
    st.markdown("### Isolation Forest Anomalies")
    if len(if_anomalies) > 0:
        st.warning(f"⚠️ {len(if_anomalies)} anomalies detected by Isolation Forest")
        st.dataframe(if_anomalies[["Date", "Description", "Amount", "Category", "Anomaly_Score"]], use_container_width=True)
    else:
        st.success("No statistical anomalies detected")
    
    st.markdown("---")
    st.markdown("### Cryptocurrency Transactions")
    if crypto_detected:
        st.error(f"🚨 {len(crypto_transactions)} crypto-related transactions")
        st.dataframe(crypto_transactions[["Date", "Description", "Amount", "Crypto_Indicators"]], use_container_width=True)
    else:
        st.success("No cryptocurrency activity detected")

with tabs[2]:
    st.subheader("Exhibit A: Cash Withdrawals")
    st.dataframe(ex_a_known, use_container_width=True)
    if len(ex_a_unknown) > 0:
        st.markdown("### Unquantified (Require Subpoena)")
        st.dataframe(ex_a_unknown, use_container_width=True)

with tabs[3]:
    st.subheader("Exhibit B: Income Discrepancies")
    st.dataframe(ex_b, use_container_width=True)

with tabs[4]:
    st.subheader("Exhibit C: Transfers")
    st.dataframe(ex_c_known, use_container_width=True)
    if len(ex_c_unknown) > 0:
        st.markdown("### Unquantified (Require Subpoena)")
        st.dataframe(ex_c_unknown, use_container_width=True)

with tabs[5]:
    st.subheader("Exhibit D: Comprehensive Summary")
    st.dataframe(ex_d, use_container_width=True)
    
    st.markdown("---")
    
    # Prepare structuring summary for export
    structuring_summary = None
    if len(structuring_detected) > 0:
        structuring_summary = structuring_detected.groupby("Structured_Cluster_ID").agg({
            "Date": ["min", "max"],
            "Amount": ["sum", "count"],
        }).reset_index()
    
    packet_bytes = make_packet_excel_v2(
        ex_a_known, ex_b, ex_c_known, ex_d, tx,
        {**velocity_cash, **velocity_transfer},
        structuring_summary
    )
    
    st.download_button(
        "📊 Export Complete Forensic Packet (XLSX)",
        data=packet_bytes,
        file_name=f"COLETTI_Hardened_Packet_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with tabs[6]:
    st.subheader("⚖️ Enhanced Schedule A Generator")
    
    schedule_a = generate_schedule_a_v2(TARGET_ENTITY, known_accounts, crypto_detected)
    
    st.text_area("Schedule A - Enhanced Digital Asset Discovery", value=schedule_a, height=600)
    
    st.download_button(
        "📥 Download Schedule A (TXT)",
        data=schedule_a,
        file_name=f"Schedule_A_Enhanced_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )

st.markdown("---")
st.caption(f"{BRAND_NAME} Hardened Forensic OS v{__version__} | Adversarial-Resistant Architecture | {__last_updated__}")
