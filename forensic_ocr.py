"""
=============================================================================
                          COLETTI OS - VERSION 2.1
                  FORENSIC OCR & STATEMENT EXTRACTION ENGINE
=============================================================================
Module: Automated Evidence Processing
Objective: Ingest PDF/Image bank statements and output trial-ready JSON ledgers.

Note: pdfplumber replaced with pymupdf (fitz) — identical extraction output,
      no cryptography/cffi dependency conflict in this environment.
=============================================================================
"""

import re
import json
import fitz                          # pymupdf — drop-in for pdfplumber
import pytesseract
from PIL import Image
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from datetime import datetime


@dataclass
class ExtractedTransaction:
    date: str
    description: str
    amount: float
    transaction_type: str
    raw_line: str = ""
    page: int = 0
    confidence: float = 1.0


class ForensicOCREngine:
    def __init__(self):
        # Matches MM/DD, MM/DD/YY, MM/DD/YYYY, YYYY-MM-DD, MM-DD-YYYY
        self.date_pattern = (
            r'(\d{4}-\d{2}-\d{2}'
            r'|\d{2}/\d{2}/\d{2,4}'
            r'|\d{2}-\d{2}-\d{2,4}'
            r'|\d{2}/\d{2})'
        )
        # Matches $1,234.56 | (1,234.56) | -1,234.56 | 1,234.56 DR/CR
        self.amount_pattern = (
            r'(\([\d,]+\.\d{2}\)'          # (1,234.56) — negative
            r'|-?\$?[\d,]+\.\d{2}\s*(?:DR|CR)?)'
        )

    # ── PDF Extraction ────────────────────────────────────────────────────────

    def process_pdf(self, file_path: str) -> List[ExtractedTransaction]:
        """Extracts text directly from digital PDF bank statements."""
        print(f"[!] Initiating PDF Extraction Protocol on: {file_path}")
        transactions = []
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                transactions.extend(
                    self._parse_raw_text(text, page_num=page_num)
                )
            doc.close()
        except Exception as e:
            print(f"[ERROR] Failed to read PDF: {e}")
        print(f"[-] Successfully extracted {len(transactions)} viable transactions.")
        return transactions

    def process_pdf_bytes(self, pdf_bytes: bytes) -> List[ExtractedTransaction]:
        """Same as process_pdf but accepts raw bytes (for Streamlit file uploader)."""
        print("[!] Initiating PDF Extraction Protocol on uploaded bytes...")
        transactions = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                transactions.extend(
                    self._parse_raw_text(text, page_num=page_num)
                )
                # Also try table extraction for tabular statements
                transactions.extend(
                    self._extract_from_tables(page, page_num)
                )
            doc.close()
        except Exception as e:
            print(f"[ERROR] Failed to read PDF bytes: {e}")
        # Deduplicate near-identical rows
        transactions = self._deduplicate(transactions)
        print(f"[-] Successfully extracted {len(transactions)} viable transactions.")
        return transactions

    def _extract_from_tables(self, page, page_num: int) -> List[ExtractedTransaction]:
        """Tries structured table extraction for bank statements with clean tables."""
        transactions = []
        try:
            tabs = page.find_tables()
            for tab in tabs:
                for row in tab.extract():
                    if not row:
                        continue
                    row_text = " ".join(str(c) for c in row if c)
                    parsed = self._parse_raw_text(row_text, page_num=page_num)
                    for t in parsed:
                        t.confidence = min(t.confidence + 0.15, 1.0)  # table rows = higher confidence
                        transactions.append(t)
        except Exception:
            pass
        return transactions

    # ── Image / OCR Extraction ────────────────────────────────────────────────

    def process_image(self, file_path: str) -> List[ExtractedTransaction]:
        """Uses Tesseract OCR to read scanned paper receipts or screenshots."""
        print(f"[!] Initiating Optical Character Recognition on: {file_path}")
        try:
            image = Image.open(file_path)
            raw_text = pytesseract.image_to_string(image)
            transactions = self._parse_raw_text(raw_text)
            print(f"[-] Successfully extracted {len(transactions)} viable transactions.")
            return transactions
        except Exception as e:
            print(f"[ERROR] Failed to process image: {e}")
            return []

    def process_image_bytes(self, image_bytes: bytes) -> List[ExtractedTransaction]:
        """Accepts raw image bytes from Streamlit file uploader."""
        print("[!] Initiating OCR on uploaded image bytes...")
        try:
            import io
            image = Image.open(io.BytesIO(image_bytes))
            raw_text = pytesseract.image_to_string(image)
            transactions = self._parse_raw_text(raw_text)
            print(f"[-] Successfully extracted {len(transactions)} viable transactions.")
            return transactions
        except Exception as e:
            print(f"[ERROR] Failed to process image bytes: {e}")
            return []

    # ── Core Parser ───────────────────────────────────────────────────────────

    def _parse_raw_text(self, text: str, page_num: int = 0) -> List[ExtractedTransaction]:
        """Hunts for transaction patterns in the raw text dump."""
        transactions = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if len(line) < 6:
                continue

            date_match = re.search(self.date_pattern, line)
            if not date_match:
                continue

            amount_matches = re.findall(self.amount_pattern, line)
            if not amount_matches:
                continue

            date_str = self._normalise_date(date_match.group(1))
            if not date_str:
                continue

            # First recognised amount = transaction value; last = running balance (skip)
            raw_amount = amount_matches[0]
            amount = self.parse_amount(raw_amount)
            if amount is None:
                continue

            # Strip date and amount tokens to get description
            description = line
            description = description.replace(date_match.group(0), '', 1)
            for am in amount_matches:
                description = description.replace(am, '', 1)
            description = re.sub(r'\s{2,}', ' ', description).strip(' |-_')

            confidence = 1.0
            if not re.search(r'\d{4}', line):   # no 4-digit year → slightly less certain
                confidence -= 0.2
            if len(description) < 3:
                confidence -= 0.3

            t_type = "deposit" if amount > 0 else "withdrawal"

            transactions.append(ExtractedTransaction(
                date=date_str,
                description=description[:60].strip(),
                amount=abs(amount),
                transaction_type=t_type,
                raw_line=line[:120],
                page=page_num,
                confidence=round(max(confidence, 0.1), 2),
            ))

        return transactions

    # ── Helpers ───────────────────────────────────────────────────────────────

    def parse_amount(self, text: str) -> Optional[float]:
        """
        Handles: $1,234.56 | (1,234.56) | -1,234.56 | 1,234.56 DR | 1,234.56 CR
        Returns signed float, or None on failure.
        """
        text = text.strip()
        negative = False

        if text.startswith('(') and text.endswith(')'):
            negative = True
            text = text[1:-1]

        upper = text.upper()
        if upper.endswith(' DR'):
            negative = True
            text = text[:-3]
        elif upper.endswith('DR'):
            negative = True
            text = text[:-2]
        elif upper.endswith(' CR'):
            text = text[:-3]      # CR = credit = positive, no sign change
        elif upper.endswith('CR'):
            text = text[:-2]

        text = text.replace('$', '').replace(',', '').strip()

        try:
            value = float(text)
            return -value if negative else value
        except ValueError:
            return None

    def _normalise_date(self, raw: str) -> Optional[str]:
        """Convert any matched date format to ISO YYYY-MM-DD."""
        formats = [
            "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d",
            "%m-%d-%Y", "%m-%d-%y", "%m/%d",
        ]
        for fmt in formats:
            try:
                d = datetime.strptime(raw, fmt)
                if d.year == 1900:           # strptime defaults year-less dates to 1900
                    d = d.replace(year=datetime.now().year)
                return d.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def detect_institution(self, pdf_bytes: bytes) -> str:
        """Scans first page for known institution names."""
        known = [
            "First Florida Credit Union",
            "Wells Fargo", "Bank of America", "Chase", "JPMorgan",
            "Citibank", "US Bank", "Truist", "SunTrust", "BB&T",
            "Regions Bank", "Fifth Third", "PNC", "TD Bank",
            "Dreamliner", "R.E. Garrison",
        ]
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            first_page_text = doc[0].get_text("text") if len(doc) > 0 else ""
            doc.close()
            for name in known:
                if name.lower() in first_page_text.lower():
                    return name
        except Exception:
            pass
        return "Unknown Institution"

    def summary(self, transactions: List[ExtractedTransaction]) -> dict:
        """Returns summary stats for a parsed transaction list."""
        if not transactions:
            return {"count": 0, "total": 0.0, "date_range": "N/A"}
        dates = sorted(t.date for t in transactions if t.date)
        return {
            "count": len(transactions),
            "total": round(sum(t.amount for t in transactions), 2),
            "deposits": round(sum(t.amount for t in transactions if t.transaction_type == "deposit"), 2),
            "withdrawals": round(sum(t.amount for t in transactions if t.transaction_type == "withdrawal"), 2),
            "date_range": f"{dates[0]} → {dates[-1]}" if dates else "N/A",
            "avg_confidence": round(sum(t.confidence for t in transactions) / len(transactions), 2),
        }

    def _deduplicate(self, transactions: List[ExtractedTransaction]) -> List[ExtractedTransaction]:
        """Remove near-duplicate rows produced by both text and table passes."""
        seen = set()
        unique = []
        for t in transactions:
            key = (t.date, round(t.amount, 2), t.description[:20])
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    # ── Export ────────────────────────────────────────────────────────────────

    def export_to_coletti_os(
        self,
        transactions: List[ExtractedTransaction],
        output_filename: str,
    ):
        """Dumps extracted data into a JSON file ready for Coletti OS ingestion."""
        data = [asdict(t) for t in transactions]
        with open(output_filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[+] Extraction complete. Exhibit data saved to: {output_filename}")

    def to_coletti_transactions(self, transactions: List[ExtractedTransaction]) -> list:
        """
        Converts ExtractedTransactions to the Transaction dicts expected by
        coletti_os.ForensicLedger — ready for direct import.
        """
        from coletti_os import Transaction
        result = []
        for t in transactions:
            result.append(Transaction(
                effective_date=t.date,
                amount=t.amount,
                description=t.description,
                category="Uncategorised",
                is_marital_dissipation=False,
            ))
        return result


# ==========================================
# EXECUTION TERMINAL
# ==========================================
if __name__ == "__main__":
    engine = ForensicOCREngine()

    print("=" * 60)
    print(" COLETTI OS: FORENSIC EXTRACTION TERMINAL ")
    print("=" * 60)

    # ---------------------------------------------------------
    # INSTRUCTIONS: Change the filename below to your scan.
    # If it is a picture: engine.process_image('scan.jpg')
    # If it is a PDF:     engine.process_pdf('statement.pdf')
    # ---------------------------------------------------------

    target_file = "scanned_statement.pdf"   # Replace with your actual file

    # Comment/Uncomment the correct one for your file type:
    # extracted_data = engine.process_pdf(target_file)
    # extracted_data = engine.process_image('receipt_scan.jpg')

    # engine.export_to_coletti_os(extracted_data, "exhibit_C_raw_data.json")
    print("\n[SYSTEM IDLE] - Awaiting target file input.")
