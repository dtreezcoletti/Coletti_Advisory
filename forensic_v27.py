"""
=============================================================================
              COLETTI OS v2.7.0 — HARDENED FORENSIC DETECTION ENGINE
              ACC (Coletti & Co.) | Case Reference: 24D1003
=============================================================================
Modules:
  1. Adaptive Classification Engine v2.7
  2. Isolation Forest Anomaly Detection
  3. Structuring / Layering Detection
  4. Transaction Velocity & Acceleration Analysis
  5. Cryptocurrency Indicator Extraction
  6. Enhanced Schedule A Generator (digital assets, crypto, offshore)
=============================================================================
"""

import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


# ── Pattern Extraction ────────────────────────────────────────────────────────

def extract_account_numbers(text: str) -> list:
    if not text:
        return []
    patterns = [
        r'\b\d{4,17}\b',
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        r'(?:ending|acct|account|#)\s*(?:in\s+)?(\d+)',
        r'[A-Z0-9]{8,}',
    ]
    matches = []
    for pat in patterns:
        matches.extend(re.findall(pat, text, re.IGNORECASE))
    return list(set(matches))


def extract_crypto_indicators(text: str) -> list:
    if not text:
        return []
    keywords = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase',
        'binance', 'kraken', 'blockchain', 'wallet', 'metamask',
        'ledger', 'trezor', 'defi', 'nft', 'usdt', 'usdc',
    ]
    t = text.lower()
    return [kw for kw in keywords if kw in t]


def fuzzy_classify_vendor(description: str, known_vendors: list, threshold: int = 80):
    if not FUZZY_AVAILABLE or not description or not known_vendors:
        return None, 0
    result = process.extractOne(description, known_vendors, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0], result[1]
    return None, 0


# ── Classification Engine v2.7 ────────────────────────────────────────────────

def classify_txn_v27(
    description: str,
    amount: float = 0.0,
    known_accounts: list = None,
    known_vendors: list = None,
) -> dict:
    d = str(description or "").lower()
    amt = float(amount or 0.0)
    accounts = extract_account_numbers(description or "")
    crypto_signals = extract_crypto_indicators(description or "")

    result = {
        "category": "OTHER",
        "confidence": "Low",
        "rule": "no match",
        "extracted_accounts": accounts,
        "crypto_indicators": crypto_signals,
        "fuzzy_vendor": None,
        "fuzzy_score": 0,
    }

    if crypto_signals:
        result.update({
            "category": "CRYPTO_CONVERSION",
            "confidence": "High",
            "rule": f"Crypto indicators: {', '.join(crypto_signals)}",
        })
        return result

    all_rules = [
        ("INTERNAL_THEFT",    "High", "ATM Withdrawal > $500",          "withdrawal" in d and amt > 500),
        ("CONTRACTOR_FRAUD",  "Med",  "P2P Payment",                    any(x in d for x in ["venmo", "cashapp", "paypal", "zelle"])),
        ("ASSET_SIPHON",      "High", "Transfer to Personal Account",   "transfer" in d and ("personal" in d or len(accounts) > 0)),
        ("TAX_RISK",          "Med",  "Luxury/Travel",                  any(x in d for x in ["hotel", "resort", "airline", "cruise"])),
        ("GAMBLING",          "High", "Gaming Activity",                any(x in d for x in ["casino", "gaming", "draftkings", "fanduel", "bet"])),
        ("OFFSHORE",          "High", "International Wire",             any(x in d for x in ["wire", "swift", "international", "foreign"])),
        ("CASH_WITHDRAWAL",   "High", "keyword: withdrawal",            "withdrawal" in d),
        ("CASH_WITHDRAWAL",   "Med",  "keyword: cash",                  "cash" in d and "cashback" not in d),
        ("CASH_WITHDRAWAL",   "Med",  "keyword: atm",                   "atm" in d),
        ("CASH_WITHDRAWAL",   "Med",  "keyword: shared branch",         "shared branch" in d),
        ("CASH_WITHDRAWAL",   "High", "Large Cash Advance",             "cash advance" in d and amt > 1000),
        ("TRANSFER",          "High", "keyword: transfer",              "transfer" in d),
        ("TRANSFER",          "High", "keyword: wire",                  "wire" in d),
        ("TRANSFER",          "Med",  "keyword: zelle",                 "zelle" in d),
        ("TRANSFER",          "Med",  "keyword: ach",                   "ach" in d),
        ("TRANSFER",          "Med",  "External Transfer",              "external" in d),
        ("ASSET_PURCHASE",    "High", "Real Estate Transaction",        any(x in d for x in ["title", "escrow", "real estate", "closing"])),
        ("VEHICLE_PAYMENT",   "Med",  "Vehicle Purchase",               any(x in d for x in ["auto", "vehicle", "carmax", "carvana"])),
        ("INVESTMENT",        "Med",  "Brokerage Transfer",             any(x in d for x in ["schwab", "fidelity", "vanguard", "robinhood"])),
    ]

    for cat, conf, rule, triggered in all_rules:
        if triggered:
            result.update({"category": cat, "confidence": conf, "rule": rule})
            break

    if result["category"] == "OTHER" and FUZZY_AVAILABLE and known_vendors:
        vendor, score = fuzzy_classify_vendor(description, known_vendors)
        if vendor:
            result.update({
                "fuzzy_vendor": vendor,
                "fuzzy_score": score,
                "confidence": "Med",
                "rule": f"Fuzzy match: {vendor} ({score}%)",
            })

    if known_accounts and accounts:
        unknown = [a for a in accounts if a not in known_accounts]
        if unknown:
            result["category"] = "UNKNOWN_ACCOUNT"
            result["confidence"] = "High"
            result["rule"] = f"Unrecognized accounts: {', '.join(unknown)}"

    return result


def normalize_transactions_v27(
    df: pd.DataFrame,
    known_accounts: list = None,
    known_vendors: list = None,
) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    clsf = df.apply(
        lambda r: pd.Series(classify_txn_v27(r.get("Description", ""), r.get("Amount", 0), known_accounts, known_vendors)),
        axis=1,
    )
    df["Category"]          = clsf["category"]
    df["Confidence"]        = clsf["confidence"]
    df["Rule_Triggered"]    = clsf["rule"]
    df["Extracted_Accounts"]= clsf["extracted_accounts"]
    df["Crypto_Indicators"] = clsf["crypto_indicators"]
    df["Fuzzy_Vendor"]      = clsf["fuzzy_vendor"]
    df["Fuzzy_Score"]       = clsf["fuzzy_score"]

    df["Amount_Bin"] = pd.cut(
        df["Amount"].fillna(0),
        bins=[0, 500, 1000, 2500, 5000, float("inf")],
        labels=["< $500", "$500-$1K", "$1K-$2.5K", "$2.5K-$5K", "> $5K"],
    )
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Is_Weekend"]  = df["Date"].dt.dayofweek.isin([5, 6])
    df["Month"]       = df["Date"].dt.to_period("M").astype(str)

    return df


# ── Isolation Forest ──────────────────────────────────────────────────────────

def detect_anomalies_isolation_forest(df: pd.DataFrame, category: str = None) -> pd.DataFrame:
    df = df.copy()
    work = df[df["Category"] == category].copy() if category else df.copy()

    if not SKLEARN_AVAILABLE or len(work) < 10:
        df["Is_Anomaly_IF"] = False
        df["Anomaly_Score"] = 0.0
        return df

    work["DayOfYear"]      = work["Date"].dt.dayofyear
    work["DaysSinceFirst"] = (work["Date"] - work["Date"].min()).dt.days
    feature_data = work[["Amount", "DayOfYear", "DaysSinceFirst"]].fillna(0)

    scaler = StandardScaler()
    X = scaler.fit_transform(feature_data)

    iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    work["Is_Anomaly_IF"] = iso.fit_predict(X) == -1
    work["Anomaly_Score"] = iso.score_samples(X)

    df = df.merge(
        work[["Is_Anomaly_IF", "Anomaly_Score"]],
        left_index=True, right_index=True, how="left",
    )
    df["Is_Anomaly_IF"] = df["Is_Anomaly_IF"].fillna(False)
    df["Anomaly_Score"] = df["Anomaly_Score"].fillna(0.0)
    return df


# ── Structuring Detection ─────────────────────────────────────────────────────

def detect_structuring(
    df: pd.DataFrame,
    window_days: int = 7,
    amount_threshold: float = 10000.0,
) -> pd.DataFrame:
    df = df.copy().sort_values("Date").reset_index(drop=True)
    df["Is_Structured"]         = False
    df["Structured_Cluster_ID"] = None
    df["Cluster_Total"]         = 0.0
    df["Cluster_Count"]         = 0

    cluster_id = 0
    for idx, row in df.iterrows():
        if pd.isna(row["Amount"]) or row["Amount"] >= amount_threshold:
            continue
        d_min = row["Date"] - timedelta(days=window_days)
        d_max = row["Date"] + timedelta(days=window_days)
        window = df[
            (df["Date"] >= d_min) &
            (df["Date"] <= d_max) &
            (df["Category"] == row["Category"]) &
            (df["Amount"] < amount_threshold) &
            df["Amount"].notna()
        ]
        if len(window) < 2:
            continue
        cluster_total = window["Amount"].sum()
        if cluster_total >= amount_threshold:
            cluster_id += 1
            for wi in window.index:
                df.at[wi, "Is_Structured"]         = True
                df.at[wi, "Structured_Cluster_ID"] = f"CLUSTER_{cluster_id}"
                df.at[wi, "Cluster_Total"]         = cluster_total
                df.at[wi, "Cluster_Count"]         = len(window)
    return df


# ── Velocity Analysis ─────────────────────────────────────────────────────────

def calculate_velocity_metrics(df: pd.DataFrame, category: str = None) -> dict:
    work = df[df["Category"] == category].copy() if category else df.copy()
    if len(work) < 2:
        return {}

    work = work.sort_values("Date")
    work["Days_Since_Last"] = work["Date"].diff().dt.days
    span_days = max((work["Date"].max() - work["Date"].min()).days, 1)

    metrics = {
        "total_transactions": len(work),
        "date_span_days": span_days,
        "avg_interval_days": float(work["Days_Since_Last"].mean()),
        "min_interval_days": float(work["Days_Since_Last"].min()),
        "transactions_per_week": len(work) / max(span_days / 7, 1),
    }

    mid = work["Date"].min() + (work["Date"].max() - work["Date"].min()) / 2
    first = work[work["Date"] <= mid]
    second = work[work["Date"] > mid]

    if len(first) > 0 and len(second) > 0:
        v1 = len(first) / max((first["Date"].max() - first["Date"].min()).days / 7, 1)
        v2 = len(second) / max((second["Date"].max() - second["Date"].min()).days / 7, 1)
        metrics["velocity_acceleration"] = (v2 - v1) / max(v1, 0.1)
    else:
        metrics["velocity_acceleration"] = 0.0

    return metrics


# ── Enhanced Schedule A ───────────────────────────────────────────────────────

def generate_schedule_a_v27(
    target_entity: str,
    known_accounts: list = None,
    crypto_detected: bool = False,
) -> str:
    account_section = ""
    if known_accounts:
        acct_list = ", ".join(known_accounts[:10])
        account_section = f"\n   g. Complete transaction histories for identified accounts: {acct_list}\n"

    crypto_section = ""
    if crypto_detected:
        crypto_section = """
7. DIGITAL ASSET & CRYPTOCURRENCY RECORDS:
   a. All cryptocurrency exchange accounts (Coinbase, Binance, Kraken, etc.)
   b. Blockchain wallet addresses and transaction histories
   c. Non-fungible token (NFT) holdings and transaction histories
   d. Decentralized finance (DeFi) protocol interactions
   e. Stablecoin holdings (USDT, USDC, DAI, etc.)
   f. Cryptocurrency mining activity records
   g. Peer-to-peer cryptocurrency transactions
   h. Cold storage wallet inventories (Ledger, Trezor, etc.)
   i. Cryptocurrency tax reporting documents (Form 8949, Schedule D)
"""

    return f"""
SCHEDULE 'A' — COMPREHENSIVE DOCUMENT PRODUCTION SPECIFICATIONS
TARGET ENTITY: {target_entity}
GENERATED: {datetime.now().strftime('%B %d, %Y')}
CASE: 24D1003 — Coletti-Brown v. Brown

1. CORPORATE & FINANCIAL RECORDS (2022–Present):
   a. Federal tax returns (Forms 1120/1065/1040 Schedule C) with ALL schedules
   b. State tax returns and business license filings
   c. General ledgers, journals, and subsidiary account records
   d. Bank statements for ALL accounts (personal and business)
   e. Profit & loss statements, balance sheets, cash flow statements
   f. Accounts payable/receivable ledgers with vendor/customer detail
{account_section}

2. EMPLOYMENT & COMPENSATION RECORDS:
   a. W-2 and 1099 forms issued to and received by all individuals
   b. Payroll registers, check stubs, and direct deposit authorizations
   c. Employment agreements, independent contractor agreements
   d. Expense reimbursement records with supporting receipts
   e. Company credit card statements and usage policies

3. ASSET & PROPERTY DOCUMENTATION:
   a. Real property deeds, mortgages, promissory notes, title policies
   b. Vehicle titles, registrations, loan documents, lease agreements
   c. Personal property asset inventories and appraisals
   d. Life insurance policies with cash value and beneficiary designations
   e. Retirement account statements (401k, IRA, pension, etc.)
   f. Investment and brokerage account statements (all institutions)

4. OPERATIONAL RECORDS:
   a. Commercial vehicle logbooks and ELD data
   b. Fuel card transactions (Fleet cards, gas station accounts)
   c. Bills of lading, shipping manifests, delivery records
   d. Dispatch logs and route planning documentation

5. LEGAL & PROFESSIONAL SERVICES:
   a. Legal fee invoices, retainer agreements, and payment records
   b. Accounting and tax preparation service records
   c. Consulting agreements and payments to third parties

6. DIGITAL PAYMENT PLATFORM RECORDS:
   a. Venmo account statements and transaction histories
   b. PayPal and PayPal Credit account records
   c. Cash App transaction histories and Bitcoin wallet records
   d. Zelle transfer records and linked bank accounts
   e. Apple Pay and Google Pay transaction histories
   f. Wise (TransferWise) international transfer records
{crypto_section}
8. OFFSHORE & ALTERNATIVE BANKING RECORDS:
   a. Neo-bank accounts (Chime, Revolut, N26, etc.)
   b. Offshore bank accounts in any jurisdiction
   c. Foreign investment accounts and brokerage records
   d. International wire transfer documentation (SWIFT codes, beneficiary info)
   e. Safe deposit box access logs and content inventories

9. METADATA & ELECTRONIC EVIDENCE:
   a. Email communications related to financial transactions
   b. Text messages and encrypted messaging app contents
   c. Cloud storage contents (Google Drive, Dropbox, iCloud, OneDrive)
   d. Financial planning software data (QuickBooks, Mint, etc.)
   e. Digital calendar entries related to financial meetings or transactions

PRODUCTION REQUIREMENTS:
  - Native format with full metadata preserved
  - Searchable text (OCR for scanned documents)
  - Privilege log for any withheld documents
  - Rolling production for voluminous records (prioritize last 12 months)
  - Certification of completeness by custodian of records

NOTICE: Failure to produce responsive documents may result in sanctions including
adverse inference instructions, monetary penalties, and preclusion of evidence at trial.
"""
