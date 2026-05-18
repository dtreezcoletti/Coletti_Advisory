"""
Coletti OS v2.5.5 — Bank Statement PDF Ingestion Module
Case No. 24D-1003 | Coletti v. Brown

Provides BankStatementParser for extracting and normalising transaction data
from bank-statement PDFs using PyMuPDF (fitz).
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Known institution fingerprints (first-page keyword → canonical name)
# ---------------------------------------------------------------------------
_INSTITUTION_PATTERNS: List[Tuple[str, str]] = [
    (r"first\s+florida\s+credit\s+union", "First Florida Credit Union"),
    (r"wells\s+fargo", "Wells Fargo"),
    (r"bank\s+of\s+america", "Bank of America"),
    (r"chase\b", "Chase"),
    (r"dreamliner", "Dreamliner"),
    (r"r\.?e\.?\s*garrison", "R.E. Garrison Trucking"),
    (r"citibank", "Citibank"),
    (r"us\s+bank\b", "U.S. Bank"),
    (r"suntrust", "SunTrust"),
    (r"truist", "Truist"),
    (r"regions\s+bank", "Regions Bank"),
    (r"td\s+bank", "TD Bank"),
    (r"navy\s+federal", "Navy Federal Credit Union"),
    (r"pnc\s+bank", "PNC Bank"),
    (r"capital\s+one", "Capital One"),
    (r"ally\s+bank", "Ally Bank"),
    (r"american\s+express", "American Express"),
    (r"discover\s+bank", "Discover Bank"),
]

# ---------------------------------------------------------------------------
# Date patterns (ordered most-specific to least)
# ---------------------------------------------------------------------------
_DATE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # YYYY-MM-DD
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "YYYY-MM-DD"),
    # MM/DD/YYYY  or  MM-DD-YYYY
    (re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b"), "MM/DD/YYYY"),
    # MM/DD/YY
    (re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b"), "MM/DD/YY"),
]

# ---------------------------------------------------------------------------
# Amount pattern  — captures digits / commas / decimal / sign / DR/CR/parens
# ---------------------------------------------------------------------------
_AMOUNT_RE = re.compile(
    r"""
    (?:
        \(\s*\$?\s*(?P<paren>[\d,]+(?:\.\d{1,2})?)\s*\)   # (1,234.56)
        |
        (?P<signed>-?\s*\$?\s*[\d,]+(?:\.\d{1,2})?)       # -$1,234.56 or $1,234.56
        \s*(?P<suffix>DR|CR|D|C)?                          # optional DR/CR
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Full transaction-line pattern  (date … amount … description)
# We try this first; if it fails we fall back to looser matching.
# ---------------------------------------------------------------------------
_TX_LINE_RE = re.compile(
    r"""
    ^(?P<raw_date>
        \d{4}-\d{2}-\d{2}               # YYYY-MM-DD
        |\d{1,2}[/\-]\d{1,2}[/\-]\d{4} # MM/DD/YYYY
        |\d{1,2}[/\-]\d{1,2}[/\-]\d{2} # MM/DD/YY
    )\s+
    (?P<desc>.+?)\s+
    (?P<raw_amount>
        \(\s*\$?[\d,]+(?:\.\d{1,2})?\s*\) # (1,234.56)
        |-?\s*\$?[\d,]+(?:\.\d{1,2})?(?:\s*(?:DR|CR))? # -$1,234.56 or 1,234.56 DR
    )\s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Looser fallback: at least a date and an amount somewhere on the line
_TX_LOOSE_RE = re.compile(
    r"""
    (?P<raw_date>
        \d{4}-\d{2}-\d{2}
        |\d{1,2}[/\-]\d{1,2}[/\-]\d{4}
        |\d{1,2}[/\-]\d{1,2}[/\-]\d{2}
    )
    (?P<rest>.*)
    """,
    re.VERBOSE | re.IGNORECASE,
)


class BankStatementParser:
    """
    Extracts and normalises transactions from bank-statement PDFs.

    Usage::

        parser = BankStatementParser()
        rows = parser.parse(pdf_bytes)
        summary = parser.summary(rows)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, pdf_bytes: bytes) -> List[dict]:
        """
        Main entry point. Accepts raw PDF bytes and returns a list of
        transaction dicts with keys:
            effective_date, amount, description, raw_line, page, confidence
        """
        rows: List[dict] = []
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return rows

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            return rows

        for page_num, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text")
            except Exception:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                result = self._parse_line(line, page_num)
                if result is not None:
                    rows.append(result)

        doc.close()
        return rows

    def extract_tables(self, pdf_bytes: bytes) -> List[dict]:
        """
        Attempt structured table extraction using fitz.Page.find_tables().
        Returns a list of table dicts: {page, rows: [[cell, ...], ...]}
        Falls back gracefully when tables are not found.
        """
        tables_out: List[dict] = []
        try:
            import fitz
        except ImportError:
            return tables_out

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            return tables_out

        for page_num, page in enumerate(doc, start=1):
            try:
                # find_tables() available in PyMuPDF >= 1.23
                tab_result = page.find_tables()
                for table in tab_result.tables:
                    data = table.extract()
                    if data:
                        tables_out.append({"page": page_num, "rows": data})
            except AttributeError:
                # Older PyMuPDF — fall back to blocks
                try:
                    blocks = page.get_text("blocks")
                    rows = [b[4].strip() for b in blocks if b[4].strip()]
                    if rows:
                        tables_out.append({"page": page_num, "rows": [[r] for r in rows]})
                except Exception:
                    pass
            except Exception:
                pass

        doc.close()
        return tables_out

    def parse_amount(self, text: str) -> float:
        """
        Parse a dollar-amount string into a positive float.

        Handles:
            $1,234.56   →  1234.56
            (1,234.56)  →  1234.56
            -1,234.56   →  1234.56
            1234.56     →  1234.56
            1,234.56 DR →  1234.56
            1,234.56 CR →  1234.56
        """
        if not text:
            raise ValueError("Empty amount string")
        text = text.strip()

        # Parenthetical negative: (1,234.56)
        m = re.match(r"^\(\s*\$?\s*([\d,]+(?:\.\d{1,2})?)\s*\)$", text)
        if m:
            return float(m.group(1).replace(",", ""))

        # Strip leading minus / dollar sign, trailing DR/CR, whitespace
        cleaned = re.sub(r"(?i)\s*(DR|CR|D|C)\s*$", "", text)
        cleaned = re.sub(r"^\s*-?\s*\$?\s*", "", cleaned)
        cleaned = cleaned.replace(",", "").strip()

        if not cleaned:
            raise ValueError(f"Cannot parse amount: {text!r}")

        return abs(float(cleaned))

    def detect_institution(self, pdf_bytes: bytes) -> str:
        """
        Scan the first page of the PDF for known institution keywords.
        Returns the canonical institution name or "Unknown".
        """
        try:
            import fitz
        except ImportError:
            return "Unknown"

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            first_page_text = doc[0].get_text("text").lower() if len(doc) > 0 else ""
            doc.close()
        except Exception:
            return "Unknown"

        for pattern, name in _INSTITUTION_PATTERNS:
            if re.search(pattern, first_page_text, re.IGNORECASE):
                return name

        return "Unknown"

    def summary(self, parsed_rows: List[dict]) -> dict:
        """
        Return high-level summary stats for a list of parsed transaction dicts.
        """
        if not parsed_rows:
            return {
                "total_rows": 0,
                "total_amount": 0.0,
                "date_min": None,
                "date_max": None,
            }

        total = sum(r["amount"] for r in parsed_rows)
        dates = [r["effective_date"] for r in parsed_rows if r.get("effective_date")]

        return {
            "total_rows": len(parsed_rows),
            "total_amount": round(total, 2),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_line(self, line: str, page: int) -> Optional[dict]:
        """
        Try to extract a transaction from a single text line.
        Returns None if the line does not look like a transaction.
        Errors never propagate — malformed lines are silently skipped.
        """
        try:
            return self._try_structured(line, page) or self._try_loose(line, page)
        except Exception:
            return None

    def _try_structured(self, line: str, page: int) -> Optional[dict]:
        """Strict pattern: date  description  amount at end of line."""
        m = _TX_LINE_RE.match(line)
        if not m:
            return None
        raw_date = m.group("raw_date")
        raw_amount = m.group("raw_amount")
        desc = m.group("desc").strip()

        iso_date = self._normalise_date(raw_date)
        if iso_date is None:
            return None

        try:
            amount = self.parse_amount(raw_amount)
        except (ValueError, TypeError):
            return None

        return {
            "effective_date": iso_date,
            "amount": amount,
            "description": desc,
            "raw_line": line,
            "page": page,
            "confidence": 0.95,
        }

    def _try_loose(self, line: str, page: int) -> Optional[dict]:
        """
        Fallback: find a date anywhere, then find the largest amount on the line.
        Confidence is lower (0.55) to reflect the ambiguity.
        """
        m = _TX_LOOSE_RE.search(line)
        if not m:
            return None

        raw_date = m.group("raw_date")
        iso_date = self._normalise_date(raw_date)
        if iso_date is None:
            return None

        # Find all amounts on the rest of the line
        rest = m.group("rest") if m.group("rest") else line
        amounts = self._find_amounts(rest)
        if not amounts:
            # Try full line
            amounts = self._find_amounts(line)
        if not amounts:
            return None

        # Take the last numeric hit (typically the transaction amount column)
        amount = amounts[-1]

        # Description = rest of line with date and amount tokens stripped
        desc = self._strip_amount_tokens(rest).strip()
        if not desc:
            desc = line

        return {
            "effective_date": iso_date,
            "amount": amount,
            "description": desc[:200],
            "raw_line": line,
            "page": page,
            "confidence": 0.55,
        }

    # ------------------------------------------------------------------
    # Date normalisation
    # ------------------------------------------------------------------

    def _normalise_date(self, raw: str) -> Optional[str]:
        """Convert any supported date format to ISO 8601 (YYYY-MM-DD)."""
        raw = raw.strip()

        # YYYY-MM-DD  — already ISO
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
        if m:
            try:
                datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return raw
            except ValueError:
                return None

        # MM/DD/YYYY or MM-DD-YYYY
        m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", raw)
        if m:
            mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                datetime(yr, mo, da)
                return f"{yr:04d}-{mo:02d}-{da:02d}"
            except ValueError:
                return None

        # MM/DD/YY
        m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})$", raw)
        if m:
            mo, da, yr2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            yr = 2000 + yr2 if yr2 < 70 else 1900 + yr2
            try:
                datetime(yr, mo, da)
                return f"{yr:04d}-{mo:02d}-{da:02d}"
            except ValueError:
                return None

        return None

    # ------------------------------------------------------------------
    # Amount utilities
    # ------------------------------------------------------------------

    def _find_amounts(self, text: str) -> List[float]:
        """Return a list of floats for every amount-like token found in text."""
        results: List[float] = []
        for m in _AMOUNT_RE.finditer(text):
            try:
                if m.group("paren"):
                    results.append(float(m.group("paren").replace(",", "")))
                elif m.group("signed"):
                    raw = re.sub(r"[\$\s]", "", m.group("signed"))
                    results.append(abs(float(raw.replace(",", ""))))
            except (ValueError, TypeError):
                pass
        return results

    def _strip_amount_tokens(self, text: str) -> str:
        """Remove amount tokens from a string, leaving the description."""
        cleaned = _AMOUNT_RE.sub(" ", text)
        # Also strip lone dollar signs and extra spaces
        cleaned = re.sub(r"\$\s*", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip()
