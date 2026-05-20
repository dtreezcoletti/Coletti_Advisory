# COLETTI OS v2.6.0 - ELITE FORENSIC LITIGATION SUITE
# ACC (Coletti & Co.) | Case Reference: 24D1003
#
# Modules:
# 1. OCR Evidence Intake: TRANSCRIPT + FINANCIAL
# 2. Evidence Chain-of-Custody Engine
# 3. Court-Safe Translation Layer
# 4. Dynamic Financial Reconstruction Engine
# 5. Procedural Litigation Dashboard
#
# Court-safe design:
# - Uses detected / possible / review needed / subject to proof.
# - Avoids unsupported fraud, motive, or intent conclusions.
# - Treats calculations as working forensic estimates pending source verification.

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, asdict

import cv2
import pytesseract
import pandas as pd
import numpy as np


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
IMAGE_FOLDER = "./evidence_images"
OUTPUT_FOLDER = "./coletti_os_exports"


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
    observed_monthly_net: float = np.nan
    observed_gross: float = np.nan
    ytd_income: float = np.nan
    employer_or_source: str = ""
    notes: str = ""
    confidence: str = "Review Needed"


class ColettiOSCore:
    def __init__(self):
        self.system_id = "ColettiOS_v2.6.0_ELITE_PROD"
        self.case_number = "24D1003"
        self.case_name = "Coletti-Brown v. Brown"
        self.attribution = "ACC (Coletti & Co.)"

        if Path(TESSERACT_PATH).exists():
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

        Path(IMAGE_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

        self.sworn_monthly_net = 4389.80
        self.verified_monthly_net = 9983.18
        self.tracking_months = 22
        self.sequestered_hard_assets = 205642.80
        self.coletti_co_lifetime_net = 23011.04

        self.evidence_ledger = []
        self.litigation_events = []
        self.financial_observations = []

    # -------------------------------------------------------------------------
    # OCR EVIDENCE INTAKE
    # -------------------------------------------------------------------------

    def process_ocr_batch(self, mode="TRANSCRIPT"):
        mode = mode.upper().strip()
        target_dir = Path(IMAGE_FOLDER)

        valid_exts = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"]
        image_files = [f for f in target_dir.iterdir() if f.suffix.lower() in valid_exts]

        if not image_files:
            print(f"[INFO] No images found in {IMAGE_FOLDER}.")
            return pd.DataFrame()

        parsed_records = []

        for img_file in sorted(image_files):
            evidence_record = self.register_evidence_file(img_file, module=f"OCR_{mode}")
            raw_text = self._ocr_image(img_file)

            if not raw_text.strip():
                parsed_records.append({
                    "Case": self.case_number,
                    "Mode": mode,
                    "Evidence_ID": evidence_record.evidence_id,
                    "File": img_file.name,
                    "Line_No": None,
                    "Observed_Text": "",
                    "Review_Status": "OCR did not detect text; manual review needed"
                })
                continue

            if mode == "TRANSCRIPT":
                parsed_records.extend(
                    self._parse_transcript_text(raw_text, img_file.name, evidence_record.evidence_id)
                )
            elif mode == "FINANCIAL":
                parsed_records.extend(
                    self._parse_financial_text(raw_text, img_file.name, evidence_record.evidence_id)
                )
            else:
                raise ValueError("Unsupported mode. Use mode='TRANSCRIPT' or mode='FINANCIAL'.")

        df = pd.DataFrame(parsed_records)

        csv_path = Path(OUTPUT_FOLDER) / f"Court_Ready_{mode}_Export.csv"
        json_path = Path(OUTPUT_FOLDER) / f"Court_Ready_{mode}_Export.json"

        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2)

        print(f"[SUCCESS] Flattened {len(df)} records into:")
        print(f"  - {csv_path}")
        print(f"  - {json_path}")

        if mode == "FINANCIAL":
            self.generate_financial_summary(df)

        self.export_evidence_ledger()

        return df

    def _ocr_image(self, img_file: Path) -> str:
        img = cv2.imread(str(img_file))
        if img is None:
            return ""

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        height, width = gray.shape[:2]
        if width < 1200:
            scale = 1200 / max(width, 1)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.medianBlur(gray, 3)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        return pytesseract.image_to_string(thresh, config=r"--oem 3 --psm 6")

    def _parse_transcript_text(self, text: str, filename: str, evidence_id: str):
        records = []
        time_pattern = r"\b((1[0-2]|0?[1-9]):([0-5][0-9])\s*([AaPp][Mm]))\b"

        for line_no, line in enumerate(text.splitlines(), start=1):
            clean = self._clean_line(line)
            if not clean:
                continue

            time_match = re.search(time_pattern, clean)
            timestamp = time_match.group(0) if time_match else "Unknown"
            msg = clean.replace(timestamp, "").strip()

            if len(msg) > 4 and not any(n in msg for n in ["4G", "LTE", "Wi-Fi", "5G"]):
                records.append({
                    "Case": self.case_number,
                    "Mode": "TRANSCRIPT",
                    "Evidence_ID": evidence_id,
                    "File": filename,
                    "Line_No": line_no,
                    "Timestamp": timestamp,
                    "Data": msg,
                    "Court_Safe_Summary": self.translate_to_court_safe(msg, mode="Timeline"),
                    "Review_Status": "OCR extracted; verify against original image"
                })

        return records

    def _parse_financial_text(self, text: str, filename: str, evidence_id: str):
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
                    "Mode": "FINANCIAL",
                    "Evidence_ID": evidence_id,
                    "File": filename,
                    "Line_No": line_no,
                    "Document_Type_Detected": doc_type,
                    "Field_Type_Detected": field_type,
                    "Observed_Text": clean,
                    "Court_Safe_Summary": self.translate_to_court_safe(clean, mode="Judge"),
                    "Money_Values": "; ".join([f"${v:,.2f}" for v in money_values]),
                    "Primary_Amount": money_values[0] if money_values else np.nan,
                    "Date_Values": "; ".join(date_values),
                    "Document_Periods_Found": "; ".join(detected_periods),
                    "Confidence": confidence,
                    "Review_Status": self._review_status(confidence)
                })

        if not records:
            records.append({
                "Case": self.case_number,
                "Mode": "FINANCIAL",
                "Evidence_ID": evidence_id,
                "File": filename,
                "Line_No": None,
                "Document_Type_Detected": doc_type,
                "Field_Type_Detected": "No structured financial fields detected",
                "Observed_Text": text[:500].replace("\n", " "),
                "Court_Safe_Summary": "The document requires manual review because OCR did not detect reliable structured financial fields.",
                "Money_Values": "",
                "Primary_Amount": np.nan,
                "Date_Values": "; ".join(detected_periods),
                "Document_Periods_Found": "; ".join(detected_periods),
                "Confidence": "Low",
                "Review_Status": "Manual review needed"
            })

        return records

    # -------------------------------------------------------------------------
    # EVIDENTIARY CHAIN-OF-CUSTODY ENGINE
    # -------------------------------------------------------------------------

    def register_evidence_file(self, file_path, module="Manual"):
        file_path = Path(file_path)
        sha = self._sha256_file(file_path)
        imported_at = datetime.utcnow().isoformat() + "Z"
        evidence_id = self._generate_evidence_id(file_path, sha)

        record = EvidenceRecord(
            evidence_id=evidence_id,
            case_number=self.case_number,
            source_file=file_path.name,
            sha256=sha,
            imported_at_utc=imported_at,
            file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            file_extension=file_path.suffix.lower(),
            module=module
        )

        self.evidence_ledger.append(record)
        return record

    def _sha256_file(self, file_path: Path):
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def _generate_evidence_id(self, file_path: Path, sha: str):
        base = file_path.stem[:12].upper().replace(" ", "_")
        return f"EXH-{datetime.utcnow().strftime('%Y%m%d')}-{base}-{sha[:8]}"

    def export_evidence_ledger(self):
        if not self.evidence_ledger:
            return pd.DataFrame()

        df = pd.DataFrame([asdict(r) for r in self.evidence_ledger])
        path = Path(OUTPUT_FOLDER) / "Evidence_Chain_of_Custody_Ledger.csv"
        json_path = Path(OUTPUT_FOLDER) / "Evidence_Chain_of_Custody_Ledger.json"

        df.to_csv(path, index=False)
        df.to_json(json_path, orient="records", indent=2)

        print("[SUCCESS] Evidence custody ledger exported:")
        print(f"  - {path}")
        print(f"  - {json_path}")

        return df

    # -------------------------------------------------------------------------
    # COURT-SAFE TRANSLATION LAYER
    # -------------------------------------------------------------------------

    def translate_to_court_safe(self, raw_statement: str, mode="Judge"):
        if not raw_statement:
            return ""

        text = raw_statement.strip()

        replacements = {
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
            r"\bcareer threat\b": "professional-conduct issue requiring review",
            r"\bpanic\b": "time-sensitive procedural response",
            r"\bcornered\b": "procedurally constrained",
            r"\bdead to rights\b": "subject to evidentiary challenge",
            r"\bslam dunk\b": "strong record-supported argument",
            r"\bnuclear\b": "significant procedural remedy",
        }

        safe = text
        for pattern, replacement in replacements.items():
            safe = re.sub(pattern, replacement, safe, flags=re.IGNORECASE)

        safe = re.sub(r"!+", ".", safe)
        safe = re.sub(r"\s+", " ", safe).strip()

        mode_lower = mode.lower()

        if mode_lower == "judge":
            return (
                "Petitioner respectfully submits that the record reflects the following issue "
                f"requiring review: {safe}"
            )

        if mode_lower == "settlement":
            return (
                "For settlement purposes only, this issue is framed as a documented risk requiring "
                f"resolution: {safe}"
            )

        if mode_lower == "advisory":
            return (
                "Operational risk indicator: "
                f"{safe}. Recommended action: verify source documents and preserve the record."
            )

        if mode_lower == "timeline":
            return f"Record note: {safe}"

        return safe

    def translate_batch_to_court_safe(self, statements, mode="Judge"):
        rows = []
        for idx, statement in enumerate(statements, start=1):
            rows.append({
                "Item": idx,
                "Raw_Statement": statement,
                "Mode": mode,
                "Court_Safe_Output": self.translate_to_court_safe(statement, mode=mode)
            })

        df = pd.DataFrame(rows)
        path = Path(OUTPUT_FOLDER) / f"Court_Safe_Translation_{mode}.csv"
        df.to_csv(path, index=False)

        print(f"[SUCCESS] Court-safe translation exported to {path}")
        return df

    # -------------------------------------------------------------------------
    # DYNAMIC FINANCIAL RECONSTRUCTION ENGINE
    # -------------------------------------------------------------------------

    def add_financial_observation(
        self,
        source,
        observation_date,
        observed_monthly_net=np.nan,
        observed_gross=np.nan,
        ytd_income=np.nan,
        employer_or_source="",
        notes="",
        confidence="Review Needed"
    ):
        obs = FinancialObservation(
            source=source,
            observation_date=observation_date,
            observed_monthly_net=float(observed_monthly_net) if not pd.isna(observed_monthly_net) else np.nan,
            observed_gross=float(observed_gross) if not pd.isna(observed_gross) else np.nan,
            ytd_income=float(ytd_income) if not pd.isna(ytd_income) else np.nan,
            employer_or_source=employer_or_source,
            notes=notes,
            confidence=confidence
        )
        self.financial_observations.append(obs)
        return obs

    def reconstruct_financial_position(self):
        observations_df = pd.DataFrame([asdict(o) for o in self.financial_observations])

        if observations_df.empty:
            observed_avg_net = self.verified_monthly_net
            observed_avg_gross = np.nan
            confidence = "Baseline Constants Only"
        else:
            observed_avg_net = observations_df["observed_monthly_net"].dropna().mean()
            observed_avg_gross = observations_df["observed_gross"].dropna().mean()

            if pd.isna(observed_avg_net):
                observed_avg_net = self.verified_monthly_net

            confidence = self._financial_confidence_from_observations(observations_df)

        monthly_delta = observed_avg_net - self.sworn_monthly_net
        percent_variance = (monthly_delta / self.sworn_monthly_net) * 100 if self.sworn_monthly_net else np.nan
        total_cash_variance = monthly_delta * self.tracking_months
        total_capital_at_issue = total_cash_variance + self.sequestered_hard_assets

        reconstruction = {
            "system_id": self.system_id,
            "case_number": self.case_number,
            "sworn_monthly_net": self.sworn_monthly_net,
            "observed_average_monthly_net": observed_avg_net,
            "observed_average_gross": observed_avg_gross,
            "monthly_net_delta": monthly_delta,
            "percent_variance_from_sworn_net": percent_variance,
            "tracking_months": self.tracking_months,
            "tracking_period_cash_variance": total_cash_variance,
            "sequestered_hard_assets": self.sequestered_hard_assets,
            "total_capital_at_issue_working_estimate": total_capital_at_issue,
            "confidence": confidence,
            "court_safe_summary": (
                "The working reconstruction identifies a variance between the sworn monthly net figure "
                "and observed or verified monthly income indicators. The calculation should be treated as "
                "subject to proof and source-document verification."
            )
        }

        path = Path(OUTPUT_FOLDER) / "Dynamic_Financial_Reconstruction.json"
        path.write_text(json.dumps(reconstruction, indent=2), encoding="utf-8")

        rows_path = Path(OUTPUT_FOLDER) / "Financial_Observations.csv"
        observations_df.to_csv(rows_path, index=False)

        print("[SUCCESS] Dynamic financial reconstruction exported:")
        print(f"  - {path}")
        print(f"  - {rows_path}")

        return reconstruction

    def _financial_confidence_from_observations(self, df):
        count_net = df["observed_monthly_net"].dropna().shape[0]
        count_gross = df["observed_gross"].dropna().shape[0]
        count_ytd = df["ytd_income"].dropna().shape[0]

        score = count_net * 2 + count_gross + count_ytd

        if score >= 6:
            return "High - Multiple Observations"
        if score >= 3:
            return "Medium - Some Observations"
        return "Low - Limited Observations"

    def generate_variance_table(self):
        reconstruction = self.reconstruct_financial_position()

        rows = [
            ["Sworn Monthly Net", reconstruction["sworn_monthly_net"]],
            ["Observed Average Monthly Net", reconstruction["observed_average_monthly_net"]],
            ["Monthly Net Delta", reconstruction["monthly_net_delta"]],
            ["Percent Variance from Sworn Net", reconstruction["percent_variance_from_sworn_net"]],
            [f"{self.tracking_months}-Month Cash Variance", reconstruction["tracking_period_cash_variance"]],
            ["Sequestered / Hard Assets at Issue", reconstruction["sequestered_hard_assets"]],
            ["Total Capital at Issue - Working Estimate", reconstruction["total_capital_at_issue_working_estimate"]],
        ]

        df = pd.DataFrame(rows, columns=["Metric", "Value"])
        path = Path(OUTPUT_FOLDER) / "Financial_Variance_Table.csv"
        df.to_csv(path, index=False)

        print(f"[SUCCESS] Financial variance table exported to {path}")
        return df

    # -------------------------------------------------------------------------
    # PROCEDURAL LITIGATION DASHBOARD
    # -------------------------------------------------------------------------

    def add_litigation_event(
        self,
        title,
        event_date,
        category,
        rule_or_basis="",
        status="Active",
        notes="",
        priority="Medium"
    ):
        event_id = f"EVT-{len(self.litigation_events) + 1:04d}"
        event = LitigationEvent(
            event_id=event_id,
            title=title,
            event_date=event_date,
            category=category,
            rule_or_basis=rule_or_basis,
            status=status,
            notes=notes,
            priority=priority
        )
        self.litigation_events.append(event)
        return event

    def seed_case_24d1003_dashboard(self):
        self.add_litigation_event(
            title="Discovery response due date / production tracking",
            event_date="2026-06-08",
            category="Discovery",
            rule_or_basis="Tenn. R. Civ. P. 26, 33, 34, 37",
            notes="Track whether requested written discovery and production are acknowledged and answered.",
            priority="High"
        )

        self.add_litigation_event(
            title="Status conference",
            event_date="2026-06-18",
            category="Court Date",
            rule_or_basis="Court scheduling / case management",
            notes="Use as procedural checkpoint for discovery status, pending motions, and trial readiness.",
            priority="High"
        )

        self.add_litigation_event(
            title="Evidentiary hearing target window",
            event_date="2026-06-26",
            category="Hearing",
            rule_or_basis="Support / equitable distribution / discovery compliance issues",
            notes="Prepare exhibit list, financial variance table, custody ledger, and court-safe summaries.",
            priority="High"
        )

        self.add_litigation_event(
            title="Vehicle maintenance / stabilization issue",
            event_date="2026-05-20",
            category="Stabilization",
            rule_or_basis="Tenn. Code Ann. Section 36-4-106(d); marital property preservation",
            notes="Track registration, maintenance, insurance, inspection, and repair status.",
            priority="Medium"
        )

        self.add_litigation_event(
            title="Service animal / kennel-related expenditure tracking",
            event_date="2026-05-20",
            category="Injunction / Property / Animal Care",
            rule_or_basis="Tenn. Code Ann. Section 36-4-106(d)",
            notes="Track alleged noncompliance period, kennel-related expenditures, and proof-of-condition requests.",
            priority="Medium"
        )

    def generate_litigation_dashboard(self):
        if not self.litigation_events:
            self.seed_case_24d1003_dashboard()

        today = date.today()
        rows = []

        for event in self.litigation_events:
            try:
                event_dt = datetime.strptime(event.event_date, "%Y-%m-%d").date()
                days_until = (event_dt - today).days
            except Exception:
                days_until = None

            risk_level = self._procedural_risk_level(days_until, event.priority, event.status)
            next_action = self._next_action_for_event(event, days_until)

            rows.append({
                **asdict(event),
                "days_until_or_since": days_until,
                "risk_level": risk_level,
                "recommended_next_action": next_action
            })

        df = pd.DataFrame(rows)
        path = Path(OUTPUT_FOLDER) / "Procedural_Litigation_Dashboard.csv"
        json_path = Path(OUTPUT_FOLDER) / "Procedural_Litigation_Dashboard.json"

        df.to_csv(path, index=False)
        df.to_json(json_path, orient="records", indent=2)

        print("[SUCCESS] Procedural litigation dashboard exported:")
        print(f"  - {path}")
        print(f"  - {json_path}")

        return df

    def _procedural_risk_level(self, days_until, priority, status):
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

    def _next_action_for_event(self, event, days_until):
        category = event.category.lower()

        if days_until is not None and days_until < 0:
            return "Verify whether the event occurred, whether an order was entered, and whether follow-up relief is needed."

        if "discovery" in category:
            return "Prepare deficiency table, service proof, requested relief, and proposed order."

        if "hearing" in category or "court" in category:
            return "Prepare exhibit index, financial variance table, custody ledger, and short bench summary."

        if "vehicle" in event.title.lower() or "stabilization" in category:
            return "Document current impairment, requested remedy, cost estimate, and connection to employment/self-stabilization."

        if "animal" in event.title.lower() or "kennel" in event.notes.lower():
            return "Update kennel-cost tracker, proof-of-condition request, and injunction compliance analysis."

        return "Review status, preserve source documents, and identify next procedural filing or communication."

    # -------------------------------------------------------------------------
    # FINANCIAL OCR HELPERS
    # -------------------------------------------------------------------------

    def _classify_financial_document(self, text: str) -> str:
        t = text.lower()

        if any(k in t for k in ["w-2", "w2", "wage and tax statement", "box 1", "box 3", "box 5"]):
            return "Possible W-2 / Wage and Tax Statement"

        if any(k in t for k in ["1099-nec", "1099 nec", "nonemployee compensation", "payer", "recipient"]):
            return "Possible 1099 / Nonemployee Compensation"

        if any(k in t for k in ["paystub", "pay stub", "earnings statement", "gross pay", "net pay", "ytd", "year to date"]):
            return "Possible Paystub / Earnings Statement"

        if any(k in t for k in ["statement period", "beginning balance", "ending balance", "deposit", "withdrawal", "account number"]):
            return "Possible Bank / Account Statement"

        if any(k in t for k in ["form 1040", "tax return", "adjusted gross income", "taxable income"]):
            return "Possible Tax Return"

        if any(k in t for k in ["401k", "401(k)", "fidelity", "retirement", "vested balance", "plan balance"]):
            return "Possible Retirement / 401(k) Record"

        return "Financial Document - Type Review Needed"

    def _classify_financial_field(self, line: str) -> str:
        t = line.lower()

        field_patterns = [
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
            ("Document Date / Period", ["pay date", "period", "statement date", "for period", "check date"])
        ]

        for label, keys in field_patterns:
            if any(k in t for k in keys):
                return label

        if self._extract_money_values(line):
            return "Money Amount - Context Review Needed"

        if self._extract_dates(line):
            return "Date / Period - Context Review Needed"

        return "Unclassified"

    def _extract_money_values(self, line: str):
        values = []

        patterns = [
            r"\$\s*\(?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?",
            r"\(?\b\d{1,3}(?:,\d{3})+\.\d{2}\b\)?",
            r"\(?\b\d+\.\d{2}\b\)?"
        ]

        for pattern in patterns:
            for match in re.findall(pattern, line):
                raw = match.replace("$", "").replace(",", "").strip()
                negative = raw.startswith("(") and raw.endswith(")")
                raw = raw.replace("(", "").replace(")", "")

                try:
                    val = float(raw)
                    if negative:
                        val = -val
                    if abs(val) >= 0.01:
                        values.append(val)
                except ValueError:
                    pass

        deduped = []
        for value in values:
            if value not in deduped:
                deduped.append(value)

        return deduped

    def _extract_dates(self, text: str):
        patterns = [
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b"
        ]

        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, flags=re.IGNORECASE))

        return list(dict.fromkeys(dates))

    def _confidence_score(self, line: str, money_values: list, field_type: str, doc_type: str):
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

    def _review_status(self, confidence: str):
        if confidence == "High":
            return "Detected; verify against source image before court use"

        if confidence == "Medium":
            return "Possible match; manual review recommended"

        return "Manual review needed"

    def _clean_line(self, line: str):
        line = line.replace("\x0c", " ")
        line = re.sub(r"\s+", " ", line).strip()
        return line

    # -------------------------------------------------------------------------
    # REPORT EXPORTS
    # -------------------------------------------------------------------------

    def generate_financial_summary(self, df: pd.DataFrame):
        if df.empty:
            return pd.DataFrame()

        summary = (
            df.groupby(["File", "Document_Type_Detected", "Field_Type_Detected"], dropna=False)
              .agg(
                  Count=("Observed_Text", "count"),
                  Total_Primary_Amount=("Primary_Amount", "sum"),
                  Max_Primary_Amount=("Primary_Amount", "max")
              )
              .reset_index()
        )

        summary_path = Path(OUTPUT_FOLDER) / "Court_Ready_FINANCIAL_Summary.csv"
        summary.to_csv(summary_path, index=False)

        checklist_path = Path(OUTPUT_FOLDER) / "Court_Ready_FINANCIAL_Review_Checklist.txt"
        lines = [
            "COLETTI OS v2.6.0 - FINANCIAL OCR REVIEW CHECKLIST",
            f"Generated: {datetime.utcnow().isoformat()} UTC",
            f"Case: {self.case_number}",
            "",
            "Use this as an internal review checklist only.",
            "Before filing or relying on any number, verify OCR output against the original document/image.",
            "",
            "Detected field groups:"
        ]

        for _, row in summary.iterrows():
            lines.append(
                f"- {row['File']} | {row['Document_Type_Detected']} | "
                f"{row['Field_Type_Detected']} | Count: {row['Count']} | "
                f"Total observed primary amount: ${row['Total_Primary_Amount']:,.2f}"
            )

        checklist_path.write_text("\n".join(lines), encoding="utf-8")

        print("[SUCCESS] Financial summary exported:")
        print(f"  - {summary_path}")
        print(f"  - {checklist_path}")

        return summary

    def run_financial_calculus(self):
        monthly_delta = self.verified_monthly_net - self.sworn_monthly_net
        total_withheld_cash = monthly_delta * self.tracking_months
        total_shielded_capital = total_withheld_cash + self.sequestered_hard_assets

        annualized_verified_income = self.verified_monthly_net * 12
        economic_asymmetry_factor = (
            annualized_verified_income / self.coletti_co_lifetime_net
            if self.coletti_co_lifetime_net else np.nan
        )

        results = {
            "system_id": self.system_id,
            "case_number": self.case_number,
            "sworn_monthly_net": self.sworn_monthly_net,
            "verified_monthly_net": self.verified_monthly_net,
            "monthly_delta": monthly_delta,
            "tracking_months": self.tracking_months,
            "total_withheld_cash": total_withheld_cash,
            "sequestered_hard_assets": self.sequestered_hard_assets,
            "total_shielded_capital": total_shielded_capital,
            "coletti_co_lifetime_net": self.coletti_co_lifetime_net,
            "annualized_verified_income": annualized_verified_income,
            "economic_asymmetry_factor": economic_asymmetry_factor,
            "review_note": "Working forensic calculation; verify all source numbers before court use."
        }

        out_path = Path(OUTPUT_FOLDER) / "Court_Ready_FINANCIAL_Calculus.json"
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        print("\nCOLETTI OS FINANCIAL CALCULUS")
        print("-" * 60)
        print(f"Sworn Monthly Net:            ${self.sworn_monthly_net:,.2f}")
        print(f"Verified Monthly Net:         ${self.verified_monthly_net:,.2f}")
        print(f"Monthly Delta:                ${monthly_delta:,.2f}")
        print(f"{self.tracking_months}-Month Cash Difference:     ${total_withheld_cash:,.2f}")
        print(f"Sequestered Hard Assets:      ${self.sequestered_hard_assets:,.2f}")
        print(f"Total Shielded Capital:       ${total_shielded_capital:,.2f}")
        print(f"Economic Asymmetry Factor:    {economic_asymmetry_factor:,.2f}x")
        print(f"\n[SUCCESS] Calculus exported to {out_path}")

        return results

    def run_full_system(self):
        print(f"Running {self.system_id}")
        print("=" * 70)

        financial_df = self.process_ocr_batch(mode="FINANCIAL")
        self.run_financial_calculus()
        self.generate_variance_table()
        self.generate_litigation_dashboard()
        self.export_evidence_ledger()

        return financial_df


if __name__ == "__main__":
    os_core = ColettiOSCore()

    os_core.add_financial_observation(
        source="Working verified-income constant",
        observation_date="2026-05-20",
        observed_monthly_net=9983.18,
        employer_or_source="Verified financial records / working calculation",
        notes="Subject to source-document verification.",
        confidence="Working Baseline"
    )

    os_core.translate_batch_to_court_safe(
        [
            "They lied about income and hid money.",
            "The car situation destroyed my ability to stabilize.",
            "Discovery has been ignored and I need the court to intervene."
        ],
        mode="Judge"
    )

    os_core.run_full_system()
