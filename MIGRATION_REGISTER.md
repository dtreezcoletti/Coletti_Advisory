# Legacy Migration Register

Status date: 2026-09-04

## Objective

Remove historical case facts and case-driven assumptions from the commercial code path. Replace them with configuration, generalized interfaces, or synthetic fixtures.

## Completed

- `README.md` now defines the commercial boundary.
- `PROJECT_BOUNDARY.md` establishes allowed/prohibited content.
- `forensic_engine.py` no longer seeds real historical case data; its default demonstration is synthetic and metadata is configurable.

## Open migration items

| File | Known issue | Required action |
|---|---|---|
| `coletti_os.py` | Historical transaction/example constants are embedded in reusable code | Extract reusable logic to ColettiOS core; replace examples with synthetic fixtures |
| `coletti_os_core.py` | Real case number/name and financial constants are hard-coded | Retire as core authority; migrate generalized logic to private ColettiOS repository |
| `forensic_v27.py` | Case-specific production/request text is embedded | Convert to neutral template with injected engagement metadata |
| `pdf_ingestion.py` | Historical case identity appears in reusable module metadata | Remove case identity and keep parser generic |
| `excel_export.py` | Historical case identity is hard-coded into exports | Read engagement metadata from configuration |
| `streamlit_app.py` | Real-case labels, valuation screens, and entity-specific rules appear in public UI code | Replace with synthetic demo workspace and configuration-driven UI |

## Release gate

Coletti & Co. is not commercially production-ready until:

1. a repository scan returns zero prohibited historical identifiers in the active commercial code path;
2. all demonstrations use synthetic fixtures;
3. client facts are supplied by engagement configuration/data rather than source-code defaults;
4. released ColettiOS functionality is consumed through a defined interface instead of duplicated commercial core code;
5. output language distinguishes record-derived observations from professional determinations.

## Important repository-history note

Removing identifiers from the current branch does not erase them from prior public Git history. Historical exposure therefore requires a separate repository-privacy/history-remediation decision in addition to code cleanup.
