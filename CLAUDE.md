# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app runs on port 8501 by default. In devcontainer environments it starts automatically with CORS and XSRF protection disabled.

## Architecture

This is a single-case legal operations dashboard ("Coletti OS v2.0") built as a Streamlit multi-page app. All application state lives in `st.session_state` — there is no database. State is lost on server restart unless the user exports it via the Data Export page.

The codebase is four files:

### `coletti_os.py` — Core data framework
All domain dataclasses and the `ColettiOS` master controller. Key relationships:

- **`ColettiOS`** owns `ForensicLedger`, `LitigationDocket`, `EnterpriseManagement`, `IncomeDisparity`, and `CaseValuation` as attributes. It seeds pre-loaded case data in `_seed_environment()` on `__init__`.
- **`LitigationDocket`** holds `List[LegalMotion]` and `List[str]` (active subpoenas). Its `evaluate_docket_leverage()` scores tactical position (max 260).
- **`CaseValuation`** aggregates `Tier1Relief`, `Tier2Damages`, `Tier3Punitive`, `BusinessSabotageDetail`, `IncomeFraud`, and `CaseDates` into computed totals via `@property`.
- All dataclasses implement `to_dict()` / `from_dict()` for JSON round-trip serialization. The full state snapshot is `ColettiOS.to_dict()` / `ColettiOS.load_dict()`.

### `forensic_engine.py` — `ForensicEngine` class
Independent from `ColettiOS`. Manages multi-source income reconstruction, concealment variance analysis, cumulative impact calculation, asset discovery, and court manifest generation. Pre-seeded in `_seed_case_data()` on init. Maintains an internal `audit_trail` list and generates a SHA-256 `audit_hash` over key figures. The manifest (`generate_court_manifest()`) bundles all analysis into a single JSON-serializable dict.

### `document_engine.py` — PDF generation
Uses ReportLab `platypus` flowables. Exposes four builder functions:
- `build_docket_summary(litigation)` — motions, subpoenas, leverage score
- `build_forensic_report(forensics)` — transaction ledger, dissipation analysis
- `build_client_brief(enterprise)` — client portfolio roster
- `build_master_report(sys_instance)` — all three combined with page breaks

All builders return `bytes` (an in-memory PDF). The `_header_footer` canvas callback stamps every page with the firm name, timestamp, page number, and CONFIDENTIAL footer.

### `streamlit_app.py` — UI layer
Instantiates `ColettiOS` and `ForensicEngine` into `st.session_state["os"]` and `st.session_state["fe"]` on first load. All pages read and mutate these objects directly — mutations are in-memory and immediately visible within the session. Pages call `st.rerun()` after mutations to refresh derived metrics.

## State & Serialization

- State is session-scoped only; no persistence across restarts without a JSON export.
- Export format is `ColettiOS.to_dict()` (JSON); import via `ColettiOS.load_dict(data)`. `ForensicEngine` state is not included in the export.
- Default values (case numbers, dollar figures, motions) are baked into `_seed_environment()` and `_seed_case_data()`. Changes to seeded defaults affect all new sessions.

## Dependencies

Only two runtime dependencies: `streamlit` and `reportlab`. No testing framework, no linter configuration, and no type-checking setup is present in the repo.
