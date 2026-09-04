from pathlib import Path
import ast
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

ACTIVE_SOURCE_DIRS = ("coletti_advisory", "services")
PROHIBITED_DIRECT_CORE_IMPORTS = {
    "colettios_core",
    "coletti_os",
    "coletti_os_core",
}
CASE_NUMBER_LITERAL = re.compile(r"\b\d{2}D-?\d{4}\b", re.IGNORECASE)


def _active_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    files: list[Path] = []
    for directory in ACTIVE_SOURCE_DIRS:
        source_root = root / directory
        if source_root.exists():
            files.extend(source_root.rglob("*.py"))
    return files


def test_retired_case_driven_modules_are_not_present():
    root = Path(__file__).resolve().parents[1]
    present = {path.name for path in root.iterdir() if path.is_file()}
    assert not (RETIRED_ROOT_MODULES & present)


def test_active_commercial_source_contains_no_case_number_literals():
    for path in _active_python_files():
        assert not CASE_NUMBER_LITERAL.search(path.read_text(encoding="utf-8")), path


def test_commercial_source_does_not_import_core_implementation_directly():
    """Coletti & Co. may call ColettiOS through adapters, not import its internals."""
    for path in _active_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0]}
            else:
                continue
            assert not (imported & PROHIBITED_DIRECT_CORE_IMPORTS), path


def test_demo_defaults_are_synthetic_and_nonproduction():
    """A clean launch must default to the synthetic demo path, never client data."""
    root = Path(__file__).resolve().parents[1]
    main_source = (root / "coletti_advisory" / "main.py").read_text(encoding="utf-8")
    assert '_secret("APP_MODE", "demo")' in main_source
    assert '_secret("STORAGE_BACKEND", "local_demo")' in main_source
    assert '_secret("COLETTIOS_BACKEND", "synthetic")' in main_source
