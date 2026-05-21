"""
Coletti OS — Advanced Detection Module v2.7
Isolation Forest anomaly detection, structuring analysis, velocity metrics,
fuzzy classification, and enhanced subpoena generation.
"""

import re
from collections import deque
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd

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


TARGET_ENTITY = "Coletti & Brown Enterprises, LLC"


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
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(set(matches))


def extract_crypto_indicators(text: str) -> list:
    if not text:
        return []
    keywords = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase',
        'binance', 'kraken', 'blockchain', 'wallet', 'metamask',
        'ledger', 'trezor', 'defi', 'nft', 'usdt', 'usdc',
    ]
    tl = text.lower()
    return [kw for kw in keywords if kw in tl]


def extract_card_ending(text: str) -> str | None:
    """Extract the 4-digit card ending from a POS transaction description.
    Handles formats like: 'POS DEBIT 4582 WALMART', 'XXXX-4582', 'CARD ENDING 4582'.
    """
    if not text:
        return None
    patterns = [
        r'(?:pos|debit|card|visa|mc|ending|xxxx[-\s]?)(\d{4})\b',
        r'\b(\d{4})\s+(?:pos|visa|mc|purchase|debit)\b',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def attribute_entity(description: str, entity_config: dict) -> dict:
    """
    Attribute a transaction to a named entity using 4 cascading methods:
      1. Card ending filter  — Definitive (mechanical proof)
      2. P2P identifier      — High (specific handle/phone)
      3. Geographic isolation — High (location in description)
      4. Behavioral tagging  — High (vendor keyword)
    Returns the first match in priority order.
    """
    result = {"entity": None, "entity_method": None, "entity_confidence": None}
    if not entity_config:
        return result

    d_lower = str(description or "").lower()

    # 1. Card ending — most definitive
    card_map = entity_config.get("card_endings", {})
    card = extract_card_ending(description)
    if card and card in card_map:
        return {
            "entity": card_map[card],
            "entity_method": f"Card ×{card}",
            "entity_confidence": "Definitive",
        }

    # 2. P2P identifier — specific handle or phone in description
    for identifier, entity in entity_config.get("p2p_identifiers", {}).items():
        if identifier.lower() in d_lower:
            return {
                "entity": entity,
                "entity_method": f"P2P: {identifier}",
                "entity_confidence": "High",
            }

    # 3. Geographic isolation — location keyword in description
    for entity, locations in entity_config.get("geographic_rules", {}).items():
        for loc in locations:
            if loc.lower() in d_lower:
                return {
                    "entity": entity,
                    "entity_method": f"Geographic: {loc}",
                    "entity_confidence": "High",
                }

    # 4. Behavioral tagging — merchant/vendor keyword
    for keyword, entity in entity_config.get("behavioral_tags", {}).items():
        if keyword.lower() in d_lower:
            return {
                "entity": entity,
                "entity_method": f"Behavioral: {keyword}",
                "entity_confidence": "High",
            }

    return result


def fuzzy_classify_vendor(description: str, known_vendors: list, threshold: int = 80) -> tuple:
    if not FUZZY_AVAILABLE or not description or not known_vendors:
        return None, 0
    result = process.extractOne(description, known_vendors, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0], result[1]
    return None, 0


def classify_txn_v2(description: str, amount: float = 0.0,
                    known_accounts: list = None, known_vendors: list = None,
                    entity_config: dict = None) -> dict:
    d = str(description or "").lower()
    amt = float(amount or 0.0)
    accounts = extract_account_numbers(description)
    crypto_signals = extract_crypto_indicators(description)
    entity_attr = attribute_entity(description, entity_config or {})

    result = {
        "category": "OTHER",
        "confidence": "Low",
        "rule": "no match",
        "extracted_accounts": accounts,
        "crypto_indicators": crypto_signals,
        "fuzzy_vendor": None,
        "fuzzy_score": 0,
        "entity": entity_attr["entity"],
        "entity_method": entity_attr["entity_method"],
        "entity_confidence": entity_attr["entity_confidence"],
    }

    if crypto_signals:
        result.update({
            "category": "CRYPTO_CONVERSION",
            "confidence": "High",
            "rule": f"Crypto indicators: {', '.join(crypto_signals)}",
        })
        return result

    all_rules = [
        ("INTERNAL_THEFT",   "High", "ATM Withdrawal > $500",     "withdrawal" in d and amt > 500),
        ("CONTRACTOR_FRAUD", "Med",  "P2P Payment",                any(x in d for x in ["venmo", "cashapp", "paypal", "zelle"])),
        ("ASSET_SIPHON",     "High", "Transfer to Personal Acct",  "transfer" in d and ("personal" in d or len(accounts) > 0)),
        ("TAX_RISK",         "Med",  "Luxury/Travel",              any(x in d for x in ["hotel", "resort", "airline", "cruise"])),
        ("GAMBLING",         "High", "Gaming Activity",            any(x in d for x in ["casino", "gaming", "draftkings", "fanduel", "bet"])),
        ("OFFSHORE",         "High", "International Wire",         any(x in d for x in ["wire", "swift", "international", "foreign"])),
        ("CASH_WITHDRAWAL",  "High", "keyword: withdrawal",        "withdrawal" in d),
        ("CASH_WITHDRAWAL",  "Med",  "keyword: cash",              "cash" in d and "cashback" not in d),
        ("CASH_WITHDRAWAL",  "Med",  "keyword: atm",               "atm" in d),
        ("CASH_WITHDRAWAL",  "Med",  "keyword: shared branch",     "shared branch" in d),
        ("CASH_WITHDRAWAL",  "High", "Large Cash Advance",         "cash advance" in d and amt > 1000),
        ("TRANSFER",         "High", "keyword: transfer",          "transfer" in d),
        ("TRANSFER",         "High", "keyword: wire",              "wire" in d),
        ("TRANSFER",         "Med",  "keyword: zelle",             "zelle" in d),
        ("TRANSFER",         "Med",  "keyword: ach",               "ach" in d),
        ("TRANSFER",         "Med",  "External Transfer",          "external" in d),
        ("ASSET_PURCHASE",   "High", "Real Estate Transaction",    any(x in d for x in ["title", "escrow", "real estate", "closing"])),
        ("VEHICLE_PAYMENT",  "Med",  "Vehicle Purchase",           any(x in d for x in ["auto", "vehicle", "carmax", "carvana"])),
        ("INVESTMENT",       "Med",  "Brokerage Transfer",         any(x in d for x in ["schwab", "fidelity", "vanguard", "robinhood"])),
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
            result.update({
                "category": "UNKNOWN_ACCOUNT",
                "confidence": "High",
                "rule": f"Unrecognized accounts: {', '.join(unknown)}",
            })

    return result


def normalize_transactions_v2(df: pd.DataFrame, known_accounts: list = None,
                               known_vendors: list = None,
                               entity_config: dict = None) -> pd.DataFrame:
    df = df.copy()
    for c in ["Strategic_Risk", "Source_Bank", "Statement_Period", "Statement_Page", "Line_Item", "To_Account"]:
        if c not in df.columns:
            df[c] = None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    classifications = df.apply(
        lambda r: pd.Series(classify_txn_v2(r["Description"], r["Amount"],
                                            known_accounts, known_vendors, entity_config)),
        axis=1,
    )

    df["Category"]           = classifications["category"]
    df["Confidence"]         = classifications["confidence"]
    df["Rule_Triggered"]     = classifications["rule"]
    df["Extracted_Accounts"] = classifications["extracted_accounts"]
    df["Crypto_Indicators"]  = classifications["crypto_indicators"]
    df["Fuzzy_Vendor"]       = classifications["fuzzy_vendor"]
    df["Fuzzy_Score"]        = classifications["fuzzy_score"]
    df["Entity"]             = classifications["entity"]
    df["Entity_Method"]      = classifications["entity_method"]
    df["Entity_Confidence"]  = classifications["entity_confidence"]

    df["Is_Amount_Known"] = df["Amount"].notna()
    df["Amount_Bin"] = pd.cut(
        df["Amount"].fillna(0),
        bins=[0, 500, 1000, 2500, 5000, float("inf")],
        labels=["< $500", "$500-$1K", "$1K-$2.5K", "$2.5K-$5K", "> $5K"],
    )
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Is_Weekend"]  = df["Date"].dt.dayofweek.isin([5, 6])
    df["Month"]       = df["Date"].dt.to_period("M")
    df["Week"]        = df["Date"].dt.to_period("W")

    return df


def detect_anomalies_isolation_forest(df: pd.DataFrame, category: str = None) -> pd.DataFrame:
    work = df.copy()
    if category:
        work = work[work["Category"] == category].copy()

    if not SKLEARN_AVAILABLE or len(work) < 10:
        work["Is_Anomaly_IF"] = False
        work["Anomaly_Score"] = 0.0
        return work

    features = ["Amount"] if "Amount" in work.columns else []
    work["DayOfYear"]      = work["Date"].dt.dayofyear
    work["DaysSinceFirst"] = (work["Date"] - work["Date"].min()).dt.days
    features += ["DayOfYear", "DaysSinceFirst"]

    X = StandardScaler().fit_transform(work[features].fillna(0))
    iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    work["Is_Anomaly_IF"] = iso.fit_predict(X) == -1
    work["Anomaly_Score"] = iso.score_samples(X)
    return work


def detect_structuring(df: pd.DataFrame, window_days: int = 7,
                       amount_threshold: float = 10000) -> pd.DataFrame:
    df = df.copy().sort_values("Date").reset_index(drop=True)
    df["Is_Structured"]       = False
    df["Structured_Cluster_ID"] = None
    df["Cluster_Total"]       = 0.0
    df["Cluster_Count"]       = 0

    cluster_id = 0
    for idx, row in df.iterrows():
        if pd.isna(row["Amount"]) or row["Amount"] >= amount_threshold:
            continue
        window = df[
            (df["Date"] >= row["Date"] - timedelta(days=window_days)) &
            (df["Date"] <= row["Date"] + timedelta(days=window_days)) &
            (df["Category"] == row["Category"]) &
            (df["Amount"] < amount_threshold) &
            df["Amount"].notna()
        ]
        if len(window) < 2 or window["Amount"].sum() < amount_threshold:
            continue
        cluster_id += 1
        total = window["Amount"].sum()
        for widx in window.index:
            df.at[widx, "Is_Structured"]         = True
            df.at[widx, "Structured_Cluster_ID"] = f"CLUSTER_{cluster_id}"
            df.at[widx, "Cluster_Total"]         = total
            df.at[widx, "Cluster_Count"]         = len(window)
    return df


def calculate_velocity_metrics(df: pd.DataFrame, category: str = None) -> dict:
    work = df.copy()
    if category:
        work = work[work["Category"] == category]
    if len(work) < 2:
        return {}

    work = work.sort_values("Date")
    work["Days_Since_Last"] = work["Date"].diff().dt.days
    date_range = (work["Date"].max() - work["Date"].min()).days

    metrics = {
        "total_transactions":           len(work),
        "date_range_days":              date_range,
        "avg_interval_days":            work["Days_Since_Last"].mean(),
        "min_interval_days":            work["Days_Since_Last"].min(),
        "max_interval_days":            work["Days_Since_Last"].max(),
        "velocity_transactions_per_week": len(work) / max(date_range / 7, 1),
    }

    midpoint   = work["Date"].min() + (work["Date"].max() - work["Date"].min()) / 2
    first_half = work[work["Date"] <= midpoint]
    second_half = work[work["Date"] > midpoint]

    if len(first_half) > 0 and len(second_half) > 0:
        v1 = len(first_half)  / max((first_half["Date"].max()  - first_half["Date"].min()).days  / 7, 1)
        v2 = len(second_half) / max((second_half["Date"].max() - second_half["Date"].min()).days / 7, 1)
        metrics["velocity_acceleration"] = (v2 - v1) / max(v1, 0.1)
    else:
        metrics["velocity_acceleration"] = 0.0

    return metrics


def cluster_entity_aliases(descriptions: list, threshold: int = 75) -> dict[str, list]:
    """
    Group messy transaction descriptions that refer to the same entity.
    Example: 'VENMO*MARY E BRWN', 'CASHAPP MARYB', 'P2P TRANSFER M BROWN'
    all cluster together under a representative label.

    Returns dict: {representative_string: [matching_descriptions]}
    """
    if not FUZZY_AVAILABLE:
        return {}

    remaining = deque(set(descriptions))
    clusters: dict[str, list] = {}

    while remaining:
        seed = remaining.popleft()
        cluster = [seed]
        still_remaining = []
        for candidate in remaining:
            score = fuzz.token_sort_ratio(seed, candidate)
            if score >= threshold:
                cluster.append(candidate)
            else:
                still_remaining.append(candidate)
        remaining = still_remaining
        clusters[seed] = cluster

    return clusters


def score_entity_attribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a per-entity breakdown: transaction count, total amount,
    and method confidence distribution. Returns a summary DataFrame.
    """
    if 'Entity' not in df.columns or df['Entity'].isna().all():
        return pd.DataFrame()

    attributed = df[df['Entity'].notna()].copy()
    if attributed.empty:
        return pd.DataFrame()

    summary = attributed.groupby('Entity').agg(
        Transactions=('Amount', 'count'),
        Total_Amount=('Amount', 'sum'),
        Definitive=('Entity_Confidence', lambda x: (x == 'Definitive').sum()),
        High=('Entity_Confidence', lambda x: (x == 'High').sum()),
    ).reset_index()
    summary['Pct_Definitive'] = (summary['Definitive'] / summary['Transactions'] * 100).round(1)
    return summary


def generate_schedule_a_v2(target_entity: str, known_accounts: list = None,
                           crypto_detected: bool = False) -> str:
    account_section = ""
    if known_accounts:
        account_section = (
            "\n   g. Complete transaction histories for accounts identified in discovery:\n"
            f"      {', '.join(known_accounts[:10])}\n"
        )

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

    return f"""SCHEDULE 'A' — COMPREHENSIVE DOCUMENT PRODUCTION SPECIFICATIONS
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

8. DIGITAL PAYMENT PLATFORM RECORDS:
   a. Venmo account statements and transaction histories
   b. PayPal and PayPal Credit account records
   c. Cash App transaction histories and Bitcoin wallet records
   d. Zelle transfer records and linked bank accounts
   e. Apple Pay and Google Pay transaction histories
   f. Wise (TransferWise) international transfer records
   g. Any other peer-to-peer payment applications

9. OFFSHORE & ALTERNATIVE BANKING RECORDS:
   a. Neo-bank accounts (Chime, Revolut, N26, etc.)
   b. Offshore bank accounts in any jurisdiction
   c. Foreign investment accounts and brokerage records
   d. International wire transfer documentation (SWIFT codes, beneficiary info)
   e. Correspondent banking relationships
   f. Safe deposit box access logs and content inventories
{crypto_section}
10. METADATA & ELECTRONIC EVIDENCE:
    a. Email communications related to financial transactions
    b. Text messages and encrypted messaging app contents (Signal, WhatsApp, Telegram)
    c. Cloud storage contents (Google Drive, Dropbox, iCloud, OneDrive)
    d. Financial planning software data (Quicken, QuickBooks, Mint)
    e. Digital calendar entries related to financial meetings or transactions

PRODUCTION REQUIREMENTS:
- Native format with full metadata preserved
- Searchable text (OCR for scanned documents)
- Privilege log for any withheld documents per [Local Rule X]
- Rolling production for voluminous records (prioritize last 12 months)
- Certification of completeness by custodian of records

DEADLINE FOR PRODUCTION: [30/60 days from service]

Date: {datetime.now().strftime('%B %d, %Y')}

NOTICE: Failure to produce responsive documents may result in sanctions including adverse
inference instructions, monetary penalties, and preclusion of evidence at trial.
"""


def make_packet_excel_v2(ex_a, ex_b, ex_c, ex_d, raw,
                         velocity_metrics: dict, structuring_summary) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        ex_a.to_excel(writer, index=False, sheet_name="Exhibit A - Cash")
        ex_b.to_excel(writer, index=False, sheet_name="Exhibit B - Income")
        ex_c.to_excel(writer, index=False, sheet_name="Exhibit C - Transfers")
        ex_d.to_excel(writer, index=False, sheet_name="Exhibit D - Summary")
        raw.to_excel(writer, index=False, sheet_name="MASTER_RAW")
        if velocity_metrics:
            pd.DataFrame(
                [{"Metric": k, "Value": v} for k, v in velocity_metrics.items()]
            ).to_excel(writer, index=False, sheet_name="Velocity Analysis")
        if structuring_summary is not None and len(structuring_summary) > 0:
            structuring_summary.to_excel(writer, index=False, sheet_name="Structuring Detected")
        # Entity attribution sheet — only rows that were attributed
        if "Entity" in raw.columns:
            attributed = raw[raw["Entity"].notna()][
                ["Date", "Description", "Amount", "Category", "Entity", "Entity_Method", "Entity_Confidence"]
            ]
            if len(attributed) > 0:
                attributed.to_excel(writer, index=False, sheet_name="Entity Attribution")
    return output.getvalue()
