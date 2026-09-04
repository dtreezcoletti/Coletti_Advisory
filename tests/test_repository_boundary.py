from pathlib import Path
import re


RETIRED_ROOT_MODULES = {
    "coletti_os.py",
    "coletti_os_core.py",
    "document_engine.py",
    "excel_export.py",
    "forensic_engine.py",
    "forensic_ocr.py",
    "forensic_v27.py",
    "ingestion_engine.py",
    "pdf_ingestion.py",
}


def test_retired_case_driven_modules_are_not_present():
    root = Path(__file__).resolve().parents[1]
    present = {path.name for path in root.iterdir() if path.is_file()}
    assert not (RETIRED_ROOT_MODULES & present)


def test_active_commercial_package_contains_no_case_number_literals():
    root = Path(__file__).resolve().parents[1] / "coletti_advisory"
    case_number = re.compile(r"\b\d{2}D-?\d{4}\b", re.IGNORECASE)
    for path in root.rglob("*.py"):
        assert not case_number.search(path.read_text(encoding="utf-8")), path
