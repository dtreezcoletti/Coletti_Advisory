"""
=============================================================================
                    COLETTI OS v2.6.0 — ELITE FORENSIC LITIGATION SUITE
                    ACC (Coletti & Co.) | Case Reference: 24D1003
=============================================================================
Modules:
  1. OCR Evidence Intake: TRANSCRIPT + FINANCIAL
  2. Evidence Chain-of-Custody Engine
  3. Court-Safe Translation Layer
  4. Dynamic Financial Reconstruction Engine
  5. Procedural Litigation Dashboard

Court-safe design:
  - Uses detected / possible / review needed / subject to proof
  - Avoids unsupported fraud, motive, or intent conclusions
  - Treats calculations as working forensic estimates pending verification

Adaptation notes for server/Streamlit environment:
  - cv2 (OpenCV) used for image preprocessing — headless build
  - Tesseract binary installed via packages.txt (no Windows path needed)
  - All I/O works on bytes (Streamlit file_uploader) as well as file paths
=============================================================================
"""

import re
import json
import hashlib
import numpy as np
import pandas as pd
import cv2
import pytesseract
from io import BytesIO
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from typing import List, Optional


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class EvidenceRecord:
    evidence_id: str
    case_number: str
    source_file: str
    sha256: str
    imported_at_utc: str
    file_size_bytes: int
    file_extension: str
    module: str
    review_status: str = "Preserved in custody ledger; verify against original before court use"


@dataclass
class LitigationEvent:
    event_id: str
    title: str
    event_date: str
    category: str
    rule_or_basis: str = ""
    status: str = "Active"
    notes: str = ""
    priority: str = "Medium"


@dataclass
class FinancialObservation:
    source: str
    observation_date: str
    observed_monthly_net: float = float("nan")
    observed_gross: float = float("nan")
    ytd_income: float = float("nan")
    employer_or_source: str = ""
    notes: str = ""
    confidence: str = "Review Needed"


# ── Core Class ────────────────────────────────────────────────────────────────

class ColettiOSCore:
    VERSION = "2.6.0"

    def __init__(self):
        self.system_id = "ColettiOS_v2.6.0_ELITE_PROD"
        self.case_number = "24D1003"
        self.case_name = "Coletti-Brown v. Brown"
        self.attribution = "ACC (Coletti & Co.)"

        # Core financial constants
        self.sworn_monthly_net = 4389.80
        self.verified_monthly_net = 9983.18
        self.tracking_months = 22
        self.sequestered_hard_assets = 205642.80
        self.coletti_co_lifetime_net = 23011.04

        self.evidence_ledger: List[EvidenceRecord] = []
        self.litigation_events: List[LitigationEvent] = []
        self.financial_observations: List[FinancialObservation] = []

    # ── OCR Evidence Intake ───────────────────────────────────────────────────

    def ocr_image_bytes(self, image_bytes: bytes) -> str:
        """
        Accepts raw image bytes (Streamlit file_uploader / camera_input).
        Applies OpenCV preprocessing before Tesseract OCR.
        Returns raw text string.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return ""
        return self._preprocess_and_ocr(img)

    def ocr_image_file(self, file_path) -> str:
        """Accepts a file path. Reads and preprocesses with OpenCV."""
        img = cv2.imread(str(file_path))
        if img is None:
            return ""
        return self._preprocess_and_ocr(img)

    def _preprocess_and_ocr(self, img) -> str:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        if w < 1200:
            scale = 1200 / max(w, 1)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.medianBlur(gray, 3)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return pytesseract.image_to_string(thresh, config=r"--oem 3 --psm 6")

    def parse_financial_ocr(self, text: str, filename: str = "upload", evidence_id: str = "") -> list:
        """Parse raw OCR text into structured financial records."""
        records = []
        doc_type = self._classify_financial_document(text)
        detected_periods = self._extract_dates(text)

        for line_no, line in enumerate(text.splitlines(), start=1):
            clean = self._clean_line(line)
            if not clean:
                continue

            money_values = self._extract_money_values(clean)
            date_values = self._extract_dates(clean)
            field_type = self._classify_financial_field(clean)
            confidence = self._confidence_score(clean, money_values, field_type, doc_type)

            if money_values or field_type != "Unclassified" or date_values:
                records.append({
                    "Case": self.case_number,
                    "Evidence_ID": evidence_id,
                    "File": filename,
                    "Line_No": line_no,
                    "Document_Type": doc_type,
                    "Field_Type": field_type,
                    "Observed_Text": clean,
                    "Court_Safe_Summary": self.translate_to_court_safe(clean, mode="Judge"),
                    "Money_Values": "; ".join([f"${v:,.2f}" for v in money_values]),
                    "Primary_Amount": money_values[0] if money_values else None,
                    "Date_Values": "; ".join(date_values),
                    "Document_Periods": "; ".join(detected_periods),
                    "Confidence": confidence,
                    "Review_Status": self._review_status(confidence),
                })

        return records

    def parse_transcript_ocr(self, text: str, filename: str = "upload", evidence_id: str = "") -> list:
        """Parse raw OCR text as a message transcript / timeline."""
        records = []
        time_pattern = r"\b((1[0-2]|0?[1-9]):([0-5][0-9])\s*([AaPp][Mm]))\b"

        for line_no, line in enumerate(text.splitlines(), start=1):
            clean = self._clean_line(line)
            if not clean or len(clean) < 5:
                continue

            time_match = re.search(time_pattern, clean)
            timestamp = time_match.group(0) if time_match else "Unknown"
            msg = clean.replace(timestamp, "").strip()

            if len(msg) > 4 and not any(n in msg for n in ["4G", "LTE", "Wi-Fi", "5G"]):
                records.append({
                    "Case": self.case_number,
                    "Evidence_ID": evidence_id,
                    "File": filename,
                    "Line_No": line_no,
                    "Timestamp": timestamp,
                    "Data": msg,
                    "Court_Safe_Summary": self.translate_to_court_safe(msg, mode="Timeline"),
                    "Review_Status": "OCR extracted; verify against original image",
                })

        return records

    # ── Chain-of-Custody Engine ───────────────────────────────────────────────

    def register_evidence_bytes(self, file_bytes: bytes, filename: str, module: str = "Upload") -> EvidenceRecord:
        sha = hashlib.sha256(file_bytes).hexdigest()
        ext = Path(filename).suffix.lower()
        base = Path(filename).stem[:12].upper().replace(" ", "_")
        evidence_id = f"EXH-{datetime.utcnow().strftime('%Y%m%d')}-{base}-{sha[:8]}"

        record = EvidenceRecord(
            evidence_id=evidence_id,
            case_number=self.case_number,
            source_file=filename,
            sha256=sha,
            imported_at_utc=datetime.utcnow().isoformat() + "Z",
            file_size_bytes=len(file_bytes),
            file_extension=ext,
            module=module,
        )
        self.evidence_ledger.append(record)
        return record

    def get_custody_ledger_df(self) -> pd.DataFrame:
        if not self.evidence_ledger:
            return pd.DataFrame()
        return pd.DataFrame([asdict(r) for r in self.evidence_ledger])

    # ── Court-Safe Translation Layer ─────────────────────────────────────────

    _REPLACEMENTS = {
        r"\bfraud\b": "material discrepancy",
        r"\bfraudulent\b": "materially inconsistent",
        r"\blie\b": "inconsistent statement",
        r"\blied\b": "made a statement that appears inconsistent with the record",
        r"\bperjury\b": "sworn statement requiring judicial review",
        r"\bhidden\b": "not yet verified or disclosed",
        r"\bhiding\b": "not yet verified or disclosed",
        r"\bstole\b": "retained or transferred value requiring verification",
        r"\btheft\b": "asset transfer issue requiring verification",
        r"\babuse\b": "coercive or destabilizing conduct alleged",
        r"\bfinancial abuse\b": "financial instability and control-related concerns",
        r"\bstrangled\b": "substantially restricted",
        r"\bdestroyed\b": "materially impaired",
        r"\bweaponized\b": "used in a manner that affected litigation stability",
        r"\bpunish\b": "impose consequences authorized by rule or statute",
        r"\bpanic\b": "time-sensitive procedural response",
        r"\bcornered\b": "procedurally constrained",
        r"\bdead to rights\b": "subject to evidentiary challenge",
        r"\bslam dunk\b": "strong record-supported argument",
        r"\bnuclear\b": "significant procedural remedy",
        r"\bcareer threat\b": "professional-conduct issue requiring review",
    }

    def translate_to_court_safe(self, raw_statement: str, mode: str = "Judge") -> str:
        """
        Replaces inflammatory language with court-appropriate equivalents.
        mode: "Judge" | "Settlement" | "Advisory" | "Timeline"
        """
        if not raw_statement:
            return ""

        safe = raw_statement.strip()
        for pattern, replacement in self._REPLACEMENTS.items():
            safe = re.sub(pattern, replacement, safe, flags=re.IGNORECASE)
        safe = re.sub(r"!+", ".", safe)
        safe = re.sub(r"\s+", " ", safe).strip()

        m = mode.lower()
        if m == "judge":
            return (
                "Petitioner respectfully submits that the record reflects the following "
                f"issue requiring review: {safe}"
            )
        if m == "settlement":
            return (
                "For settlement purposes only, this issue is framed as a documented "
                f"risk requiring resolution: {safe}"
            )
        if m == "advisory":
            return (
                f"Operational risk indicator: {safe}. "
                "Recommended action: verify source documents and preserve the record."
            )
        if m == "timeline":
            return f"Record note: {safe}"
        return safe

    def translate_batch(self, statements: list, mode: str = "Judge") -> pd.DataFrame:
        rows = []
        for i, stmt in enumerate(statements, start=1):
            rows.append({
                "Item": i,
                "Raw_Statement": stmt,
                "Mode": mode,
                "Court_Safe_Output": self.translate_to_court_safe(stmt, mode=mode),
            })
        return pd.DataFrame(rows)

    # ── Dynamic Financial Reconstruction ─────────────────────────────────────

    def add_financial_observation(
        self,
        source: str,
        observation_date: str,
        observed_monthly_net: float = float("nan"),
        observed_gross: float = float("nan"),
        ytd_income: float = float("nan"),
        employer_or_source: str = "",
        notes: str = "",
        confidence: str = "Review Needed",
    ) -> FinancialObservation:
        obs = FinancialObservation(
            source=source,
            observation_date=observation_date,
            observed_monthly_net=float(observed_monthly_net) if not _isnan(observed_monthly_net) else float("nan"),
            observed_gross=float(observed_gross) if not _isnan(observed_gross) else float("nan"),
            ytd_income=float(ytd_income) if not _isnan(ytd_income) else float("nan"),
            employer_or_source=employer_or_source,
            notes=notes,
            confidence=confidence,
        )
        self.financial_observations.append(obs)
        return obs

    def reconstruct_financial_position(self) -> dict:
        obs_df = pd.DataFrame([asdict(o) for o in self.financial_observations])

        if obs_df.empty or obs_df["observed_monthly_net"].dropna().empty:
            avg_net = self.verified_monthly_net
            avg_gross = float("nan")
            confidence = "Baseline Constants Only"
        else:
            avg_net = obs_df["observed_monthly_net"].dropna().mean()
            avg_gross = obs_df["observed_gross"].dropna().mean() if not obs_df["observed_gross"].dropna().empty else float("nan")
            confidence = self._financial_confidence(obs_df)

        monthly_delta = avg_net - self.sworn_monthly_net
        pct_variance = (monthly_delta / self.sworn_monthly_net * 100) if self.sworn_monthly_net else float("nan")
        cash_variance = monthly_delta * self.tracking_months
        total_at_issue = cash_variance + self.sequestered_hard_assets
        asymmetry = (avg_net * 12 / self.coletti_co_lifetime_net) if self.coletti_co_lifetime_net else float("nan")

        return {
            "system_id": self.system_id,
            "case_number": self.case_number,
            "sworn_monthly_net": self.sworn_monthly_net,
            "observed_avg_monthly_net": avg_net,
            "observed_avg_gross": avg_gross,
            "monthly_delta": monthly_delta,
            "pct_variance_from_sworn": pct_variance,
            "tracking_months": self.tracking_months,
            "tracking_period_cash_variance": cash_variance,
            "sequestered_hard_assets": self.sequestered_hard_assets,
            "total_capital_at_issue": total_at_issue,
            "economic_asymmetry_factor": asymmetry,
            "confidence": confidence,
            "court_safe_summary": (
                "The working reconstruction identifies a variance between the sworn monthly "
                "net figure and observed or verified monthly income indicators. This calculation "
                "should be treated as subject to proof and source-document verification."
            ),
        }

    def _financial_confidence(self, df: pd.DataFrame) -> str:
        score = (df["observed_monthly_net"].dropna().shape[0] * 2
                 + df["observed_gross"].dropna().shape[0]
                 + df["ytd_income"].dropna().shape[0])
        if score >= 6:
            return "High - Multiple Observations"
        if score >= 3:
            return "Medium - Some Observations"
        return "Low - Limited Observations"

    # ── Procedural Litigation Dashboard ──────────────────────────────────────

    def add_litigation_event(
        self,
        title: str,
        event_date: str,
        category: str,
        rule_or_basis: str = "",
        status: str = "Active",
        notes: str = "",
        priority: str = "Medium",
    ) -> LitigationEvent:
        evt = LitigationEvent(
            event_id=f"EVT-{len(self.litigation_events) + 1:04d}",
            title=title,
            event_date=event_date,
            category=category,
            rule_or_basis=rule_or_basis,
            status=status,
            notes=notes,
            priority=priority,
        )
        self.litigation_events.append(evt)
        return evt

    def seed_case_24d1003_dashboard(self):
        """Pre-loads confirmed upcoming procedural dates and action items."""
        self.add_litigation_event(
            title="Discovery response due date / production tracking",
            event_date="2026-06-08",
            category="Discovery",
            rule_or_basis="Tenn. R. Civ. P. 26, 33, 34, 37",
            notes="Track whether requested written discovery and production are acknowledged and answered.",
            priority="High",
        )
        self.add_litigation_event(
            title="Status conference",
            event_date="2026-06-18",
            category="Court Date",
            rule_or_basis="Court scheduling / case management",
            notes="Procedural checkpoint for discovery status, pending motions, and trial readiness.",
            priority="High",
        )
        self.add_litigation_event(
            title="Evidentiary hearing target window",
            event_date="2026-06-26",
            category="Hearing",
            rule_or_basis="Support / equitable distribution / discovery compliance",
            notes="Prepare exhibit list, financial variance table, custody ledger, and court-safe summaries.",
            priority="High",
        )
        self.add_litigation_event(
            title="Vehicle maintenance / stabilization issue",
            event_date="2026-05-20",
            category="Stabilization",
            rule_or_basis="Tenn. Code Ann. § 36-4-106(d); marital property preservation",
            notes="Track registration, maintenance, insurance, inspection, and repair status.",
            priority="Medium",
        )
        self.add_litigation_event(
            title="Service animal / kennel-related expenditure tracking",
            event_date="2026-05-20",
            category="Injunction / Property",
            rule_or_basis="Tenn. Code Ann. § 36-4-106(d)",
            notes="Track alleged noncompliance period, kennel costs, and proof-of-condition requests.",
            priority="Medium",
        )

    def get_dashboard_df(self) -> pd.DataFrame:
        if not self.litigation_events:
            self.seed_case_24d1003_dashboard()

        today = date.today()
        rows = []
        for evt in self.litigation_events:
            try:
                evt_date = datetime.strptime(evt.event_date, "%Y-%m-%d").date()
                days_until = (evt_date - today).days
            except Exception:
                days_until = None

            rows.append({
                **asdict(evt),
                "days_until": days_until,
                "risk_level": self._risk_level(days_until, evt.priority, evt.status),
                "next_action": self._next_action(evt, days_until),
            })

        return pd.DataFrame(rows)

    def _risk_level(self, days_until, priority: str, status: str) -> str:
        if status.lower() not in ["active", "pending", "open"]:
            return "Low / Closed"
        if days_until is None:
            return "Review Needed"
        if days_until < 0:
            return "Past Due / Verify Status"
        if days_until <= 7 and priority.lower() == "high":
            return "Critical"
        if days_until <= 14:
            return "High"
        if priority.lower() == "high":
            return "Medium-High"
        return "Medium"

    def _next_action(self, evt: LitigationEvent, days_until) -> str:
        if days_until is not None and days_until < 0:
            return "Verify whether event occurred, whether an order was entered, and whether follow-up relief is needed."
        cat = evt.category.lower()
        if "discovery" in cat:
            return "Prepare deficiency table, service proof, requested relief, and proposed order."
        if "hearing" in cat or "court" in cat:
            return "Prepare exhibit index, financial variance table, custody ledger, and bench summary."
        if "vehicle" in evt.title.lower() or "stabilization" in cat:
            return "Document current impairment, requested remedy, cost estimate, and connection to employment."
        if "animal" in evt.title.lower() or "kennel" in evt.notes.lower():
            return "Update kennel-cost tracker, proof-of-condition request, and injunction compliance analysis."
        return "Review status, preserve source documents, and identify next procedural filing."

    # ── Financial OCR Helpers ─────────────────────────────────────────────────

    def _classify_financial_document(self, text: str) -> str:
        t = text.lower()
        checks = [
            (["w-2", "w2", "wage and tax statement", "box 1", "box 3", "box 5"], "Possible W-2 / Wage and Tax Statement"),
            (["1099-nec", "1099 nec", "nonemployee compensation", "payer", "recipient"], "Possible 1099 / Nonemployee Compensation"),
            (["paystub", "pay stub", "earnings statement", "gross pay", "net pay", "ytd", "year to date"], "Possible Paystub / Earnings Statement"),
            (["statement period", "beginning balance", "ending balance", "deposit", "withdrawal", "account number"], "Possible Bank / Account Statement"),
            (["form 1040", "tax return", "adjusted gross income", "taxable income"], "Possible Tax Return"),
            (["401k", "401(k)", "fidelity", "retirement", "vested balance", "plan balance"], "Possible Retirement / 401(k) Record"),
        ]
        for keywords, label in checks:
            if any(k in t for k in keywords):
                return label
        return "Financial Document - Type Review Needed"

    def _classify_financial_field(self, line: str) -> str:
        t = line.lower()
        patterns = [
            ("Gross Pay / Gross Income", ["gross pay", "gross income", "total gross", "gross earnings", "current gross"]),
            ("Net Pay / Net Income", ["net pay", "net income", "take home", "net amount", "direct deposit"]),
            ("Year-to-Date Income", ["ytd", "year to date", "year-to-date"]),
            ("W-2 Wages", ["box 1", "wages tips", "wages, tips", "medicare wages", "social security wages"]),
            ("1099 Nonemployee Compensation", ["nonemployee compensation", "1099-nec", "1099 nec"]),
            ("Deposit / Credit", ["deposit", "credit", "ach credit", "direct dep", "direct deposit"]),
            ("Withdrawal / Debit", ["withdrawal", "debit", "ach debit", "payment", "purchase"]),
            ("Deduction / Withholding", ["deduction", "withholding", "federal tax", "fica", "medicare", "social security", "pre-tax", "pretax"]),
            ("Employer / Payer", ["employer", "payer", "company", "dreamliner", "garrison", "lyons"]),
            ("Account Balance", ["balance", "ending balance", "beginning balance", "available balance"]),
            ("Retirement / 401(k)", ["401k", "401(k)", "retirement", "fidelity", "vested", "contribution"]),
            ("Tax Return Field", ["adjusted gross income", "agi", "taxable income", "refund", "amount owed"]),
            ("Document Date / Period", ["pay date", "period", "statement date", "for period", "check date"]),
        ]
        for label, keys in patterns:
            if any(k in t for k in keys):
                return label
        if self._extract_money_values(line):
            return "Money Amount - Context Review Needed"
        if self._extract_dates(line):
            return "Date / Period - Context Review Needed"
        return "Unclassified"

    def _extract_money_values(self, line: str) -> list:
        values = []
        patterns = [
            r"\$\s*\(?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?",
            r"\(?\b\d{1,3}(?:,\d{3})+\.\d{2}\b\)?",
            r"\(?\b\d+\.\d{2}\b\)?",
        ]
        for pat in patterns:
            for m in re.findall(pat, line):
                raw = m.replace("$", "").replace(",", "").strip()
                neg = raw.startswith("(") and raw.endswith(")")
                raw = raw.replace("(", "").replace(")", "")
                try:
                    v = float(raw)
                    if neg:
                        v = -v
                    if abs(v) >= 0.01 and v not in values:
                        values.append(v)
                except ValueError:
                    pass
        return values

    def _extract_dates(self, text: str) -> list:
        patterns = [
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        ]
        dates = []
        for pat in patterns:
            dates.extend(re.findall(pat, text, flags=re.IGNORECASE))
        return list(dict.fromkeys(dates))

    def _confidence_score(self, line: str, money_values: list, field_type: str, doc_type: str) -> str:
        score = 0
        if money_values:
            score += 2
        if field_type not in ["Unclassified", "Money Amount - Context Review Needed", "Date / Period - Context Review Needed"]:
            score += 2
        if doc_type != "Financial Document - Type Review Needed":
            score += 1
        if len(line) >= 8:
            score += 1
        if score >= 5:
            return "High"
        if score >= 3:
            return "Medium"
        return "Low"

    def _review_status(self, confidence: str) -> str:
        if confidence == "High":
            return "Detected; verify against source image before court use"
        if confidence == "Medium":
            return "Possible match; manual review recommended"
        return "Manual review needed"

    def _clean_line(self, line: str) -> str:
        line = line.replace("\x0c", " ")
        return re.sub(r"\s+", " ", line).strip()


def _isnan(v) -> bool:
    try:
        return np.isnan(float(v))
    except (TypeError, ValueError):
        return True
