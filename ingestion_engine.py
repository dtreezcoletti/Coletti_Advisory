"""
=============================================================================
                        COLETTI OS — VERSION 2.5.5
                     DOCUMENT INGESTION & EXHIBIT ENGINE
=============================================================================
Module: Subpoena Return Processing & Exhibit Auto-Population
Objective: Drag-drop PDFs/CSVs → DocumentRecord → ExhibitRecord → Ledger

Note: Uses pymupdf (fitz) — pdfplumber is NOT available in this environment
      due to a cryptography/cffi conflict.
=============================================================================
"""

import re
import fitz                        # pymupdf — replaces pdfplumber
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class DocumentRecord:
    doc_id: str
    source: str                    # e.g. "First Florida Credit Union"
    doc_type: str                  # e.g. "Bank Statement"
    raw_text: str
    date_processed: str = field(default_factory=lambda: datetime.now().isoformat())
    page_count: int = 0
    file_name: str = ""


@dataclass
class ExhibitRecord:
    source_doc: str                # doc_id reference
    transactions: object           # pandas DataFrame
    total_value: float             # sum of all parsed amounts
    deposit_total: float
    withdrawal_total: float
    transaction_count: int
    status: str = "Ready for Audit"
    date_created: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Ingestion Engine ──────────────────────────────────────────────────────────

class DataIngestionEngine:
    """
    Accepts a file path or raw bytes (from Streamlit uploader).
    Produces DocumentRecord + ExhibitRecord ready for Coletti OS import.
    """

    # Regex: MM/DD/YYYY  MM/DD/YY  YYYY-MM-DD  MM-DD-YYYY
    _DATE_RE = re.compile(
        r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{2,4}|\d{2}-\d{2}-\d{2,4}|\d{2}/\d{2})'
    )
    # Regex: $1,234.56 | (1,234.56) | -1,234.56 | 1,234.56 DR/CR
    _AMOUNT_RE = re.compile(
        r'(\([\d,]+\.\d{2}\)|-?\$?[\d,]+\.\d{2}\s*(?:DR|CR)?)'
    )

    def __init__(self, file_path: Optional[str] = None, source_name: str = "Unknown"):
        self.file_path = file_path
        self.source_name = source_name
        self.raw_text = ""

    # ── PDF extraction ────────────────────────────────────────────────────────

    def extract_text_from_pdf(self) -> tuple[str, int]:
        """Extract full text from a PDF file path. Returns (text, page_count)."""
        print(f"[!] Ingesting: {self.file_path}")
        text_parts = []
        try:
            doc = fitz.open(self.file_path)
            page_count = len(doc)
            for page in doc:
                text_parts.append(page.get_text("text"))
                # Also try table extraction for tabular statements
                for tab in page.find_tables():
                    for row in tab.extract():
                        if row:
                            text_parts.append(" ".join(str(c) for c in row if c))
            doc.close()
        except Exception as e:
            print(f"[ERROR] PDF extraction failed: {e}")
            return "", 0
        self.raw_text = "\n".join(text_parts)
        return self.raw_text, page_count

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> tuple[str, int]:
        """Same as above but from raw bytes (Streamlit st.file_uploader)."""
        print("[!] Ingesting PDF from uploaded bytes...")
        text_parts = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            for page in doc:
                text_parts.append(page.get_text("text"))
                for tab in page.find_tables():
                    for row in tab.extract():
                        if row:
                            text_parts.append(" ".join(str(c) for c in row if c))
            doc.close()
        except Exception as e:
            print(f"[ERROR] PDF bytes extraction failed: {e}")
            return "", 0
        self.raw_text = "\n".join(text_parts)
        return self.raw_text, page_count

    # ── CSV extraction ────────────────────────────────────────────────────────

    def extract_from_csv(self, csv_bytes: bytes) -> pd.DataFrame:
        """
        Reads a CSV export (common from online banking portals).
        Tries to auto-detect Date, Description, Amount columns.
        """
        import io
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes))
        except Exception as e:
            print(f"[ERROR] CSV read failed: {e}")
            return pd.DataFrame()

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # Map common column name variants
        col_map = {}
        for col in df.columns:
            if any(k in col for k in ("date", "posted", "trans date")):
                col_map["Date"] = col
            elif any(k in col for k in ("desc", "memo", "narr", "payee")):
                col_map["Description"] = col
            elif any(k in col for k in ("amount", "debit", "credit", "value")):
                if "Amount" not in col_map:
                    col_map["Amount"] = col

        if not col_map:
            return df  # return as-is if we can't guess

        df_out = pd.DataFrame()
        for friendly, raw_col in col_map.items():
            df_out[friendly] = df[raw_col]

        if "Amount" in df_out.columns:
            df_out["Amount"] = (
                df_out["Amount"]
                .astype(str)
                .str.replace(r'[\$,()]', '', regex=True)
                .str.strip()
            )
            df_out["Amount"] = pd.to_numeric(df_out["Amount"], errors="coerce").fillna(0)

        return df_out

    # ── Financial Parser ──────────────────────────────────────────────────────

    def parse_financial_data(self) -> tuple[pd.DataFrame, float]:
        """
        Scans self.raw_text for transaction lines (date + description + amount).
        Returns (DataFrame, total_value).
        """
        transactions = []

        for line in self.raw_text.splitlines():
            line = line.strip()
            if len(line) < 8:
                continue

            date_m = self._DATE_RE.search(line)
            if not date_m:
                continue

            amount_ms = self._AMOUNT_RE.findall(line)
            if not amount_ms:
                continue

            amount = self._parse_amount(amount_ms[0])
            if amount is None:
                continue

            # Description = line minus date and amount tokens
            desc = line
            desc = desc.replace(date_m.group(0), "", 1)
            for am in amount_ms:
                desc = desc.replace(am, "", 1)
            desc = re.sub(r'\s{2,}', ' ', desc).strip(" |-_")

            transactions.append({
                "Date": date_m.group(1),
                "Description": desc[:80],
                "Amount": round(abs(amount), 2),
                "Type": "Deposit" if amount > 0 else "Withdrawal",
                "Raw": line[:120],
            })

        df = pd.DataFrame(transactions) if transactions else pd.DataFrame(
            columns=["Date", "Description", "Amount", "Type", "Raw"]
        )
        total = df["Amount"].sum() if not df.empty else 0.0
        return df, float(total)

    # ── High-level wizard ─────────────────────────────────────────────────────

    def run_ingestion_wizard(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str = "pdf",
    ) -> tuple[DocumentRecord, ExhibitRecord]:
        """
        One-call ingestion for Streamlit: bytes in → (DocumentRecord, ExhibitRecord) out.
        file_type: "pdf" or "csv"
        """
        page_count = 0

        if file_type == "csv":
            df = self.extract_from_csv(file_bytes)
            total = float(df["Amount"].sum()) if "Amount" in df.columns else 0.0
            deposits = float(df.loc[df["Amount"] > 0, "Amount"].sum()) if "Amount" in df.columns else 0.0
            withdrawals = float(df.loc[df["Amount"] < 0, "Amount"].abs().sum()) if "Amount" in df.columns else 0.0
            raw_text = df.to_string()
        else:
            raw_text, page_count = self.extract_text_from_pdf_bytes(file_bytes)
            self.raw_text = raw_text
            df, total = self.parse_financial_data()
            deposits = float(df.loc[df["Type"] == "Deposit", "Amount"].sum()) if not df.empty else 0.0
            withdrawals = float(df.loc[df["Type"] == "Withdrawal", "Amount"].sum()) if not df.empty else 0.0

        doc_id = f"DOC_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        doc = DocumentRecord(
            doc_id=doc_id,
            source=self.source_name,
            doc_type="Financial Ledger",
            raw_text=raw_text,
            page_count=page_count,
            file_name=file_name,
        )

        exhibit = ExhibitRecord(
            source_doc=doc_id,
            transactions=df,
            total_value=round(total, 2),
            deposit_total=round(deposits, 2),
            withdrawal_total=round(withdrawals, 2),
            transaction_count=len(df),
            status="Ready for Audit",
        )

        print("-" * 50)
        print("COLETTI OS: INGESTION COMPLETE")
        print(f"  Document ID   : {doc.doc_id}")
        print(f"  Source        : {doc.source}")
        print(f"  File          : {file_name} ({page_count} pages)")
        print(f"  Transactions  : {exhibit.transaction_count}")
        print(f"  Total Parsed  : ${exhibit.total_value:,.2f}")
        print("-" * 50)

        return doc, exhibit

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_amount(self, text: str):
        text = text.strip()
        negative = False
        if text.startswith('(') and text.endswith(')'):
            negative = True
            text = text[1:-1]
        upper = text.upper()
        if upper.endswith(' DR') or upper.endswith('DR'):
            negative = True
            text = text.rstrip('DR').rstrip(' DR')
        elif upper.endswith(' CR') or upper.endswith('CR'):
            text = text.rstrip('CR').rstrip(' CR')
        text = text.replace('$', '').replace(',', '').strip()
        try:
            v = float(text)
            return -v if negative else v
        except ValueError:
            return None
