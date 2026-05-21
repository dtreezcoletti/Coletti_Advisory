"""
Coletti OS — Statement Ingestion Engine
Extracts structured transaction tables from PDF bank statements and scanned images.
Uses pdfplumber for digital PDFs, pytesseract for images (graceful fallback if not installed).
"""

import io
import re
from datetime import datetime

import pandas as pd

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ── Parsing helpers ───────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
    r'\b(\d{4}-\d{2}-\d{2})\b',
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
]
_AMOUNT_PATTERN = r'-?\$?[\d,]+\.\d{2}'


def _parse_amount(text: str) -> float | None:
    m = re.search(_AMOUNT_PATTERN, text)
    if not m:
        return None
    raw = m.group(0).replace('$', '').replace(',', '')
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_date(text: str) -> str | None:
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(0)
            for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y'):
                try:
                    return datetime.strptime(raw.replace(',', ''), fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
    return None


def _rows_to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Date', 'Amount']).reset_index(drop=True)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    return df[['Date', 'Description', 'Amount']]


# ── PDF extraction ────────────────────────────────────────────────────────────

def extract_from_pdf(file_bytes: bytes) -> tuple[pd.DataFrame, list[str]]:
    """
    Extract transactions from a digital PDF using pdfplumber.
    Returns (DataFrame, list_of_warnings).
    """
    warnings = []
    if not PDFPLUMBER_AVAILABLE:
        return pd.DataFrame(), ["pdfplumber not installed. Run: pip install pdfplumber"]

    rows = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Try structured table extraction first
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    text = ' '.join(str(c or '') for c in row)
                    date = _parse_date(text)
                    amount = _parse_amount(text)
                    if date and amount is not None:
                        # Description: everything between date and amount
                        desc = re.sub(_AMOUNT_PATTERN, '', text)
                        desc = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', desc).strip()
                        rows.append({'Date': date, 'Description': desc, 'Amount': amount})

            # Fallback: line-by-line text parse
            if not tables:
                text = page.extract_text() or ''
                for line in text.splitlines():
                    line = line.strip()
                    date = _parse_date(line)
                    amount = _parse_amount(line)
                    if date and amount is not None:
                        desc = re.sub(_AMOUNT_PATTERN, '', line)
                        desc = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', desc).strip()
                        rows.append({'Date': date, 'Description': desc, 'Amount': amount})

    if not rows:
        warnings.append("No transactions detected. The PDF may be scanned (image-based). Try the image OCR path.")

    return _rows_to_df(rows), warnings


# ── Image OCR extraction ──────────────────────────────────────────────────────

def extract_from_image(file_bytes: bytes) -> tuple[pd.DataFrame, list[str]]:
    """
    Extract transactions from a scanned image using pytesseract.
    Returns (DataFrame, list_of_warnings).
    """
    warnings = []
    if not TESSERACT_AVAILABLE:
        return pd.DataFrame(), [
            "pytesseract / Pillow not installed. Run: pip install pytesseract Pillow  "
            "and install Tesseract binary: sudo apt-get install tesseract-ocr"
        ]

    img = Image.open(io.BytesIO(file_bytes))
    # Pre-process: greyscale + threshold improves OCR accuracy on bank statements
    img = img.convert('L')
    raw_text = pytesseract.image_to_string(img, config='--psm 6')

    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        date = _parse_date(line)
        amount = _parse_amount(line)
        if date and amount is not None:
            desc = re.sub(_AMOUNT_PATTERN, '', line)
            desc = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', desc).strip()
            rows.append({'Date': date, 'Description': desc, 'Amount': amount})

    if not rows:
        warnings.append("No transactions found in image. Check image quality and orientation.")

    return _rows_to_df(rows), warnings


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_statement(file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Route to PDF or image extractor based on file extension.
    Returns (DataFrame with Date/Description/Amount, warnings).
    """
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return extract_from_pdf(file_bytes)
    elif ext in ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'):
        return extract_from_image(file_bytes)
    else:
        return pd.DataFrame(), [f"Unsupported file type: .{ext}. Upload a PDF or image."]
