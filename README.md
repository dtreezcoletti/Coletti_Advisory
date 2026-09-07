# Coletti & Co.

Coletti & Co. is the commercial application layer for the private ColettiOS provenance-first record analysis core.

## Current replacement architecture

`Streamlit UI -> OIDC identity -> RBAC/engagement authorization -> encrypted intake -> ColettiOS adapter -> private ColettiOS service`

The public repository contains no approved real-client or historical-case data. The default application mode is a synthetic demonstration. Real client data must not be entered while `APP_MODE=demo`.

## Authentication

The app uses Streamlit OIDC (`st.login`, `st.user`, `st.logout`) for identity. Password verification remains with the configured identity provider. Coletti & Co. owns authorization through a server-side allowlist/registry and enforces role and engagement access separately.

## Storage

Demo mode uses client-side AES-256-GCM encryption on ephemeral local storage. Production mode fails closed unless Google Cloud Storage is configured; bytes are encrypted before upload and plaintext SHA-256 hashes are registered as source integrity metadata.

## ColettiOS boundary

The commercial repository does not duplicate private ColettiOS engine logic. `HttpColettiOSAdapter` defines the released service contract. Production mode requires an HTTPS ColettiOS service URL and server-side service token.

## Institutional control plane

This repository is authoritative for the **Coletti & Co. commercial application/data plane only**. It is not the complete source of truth for the Coletti institution.

The complete Coletti system state is centralized through the private Colettico Supabase institutional registry and its release-manifest control plane. A unified release manifest pins four separately owned components:

1. ColettiOS Core/IP — `dtreezcoletti/ColettiOS`.
2. Coletti & Co. commercial application — this repository (`dtreezcoletti/Coletti_Advisory`, controlled `main`).
3. Institutional database/state — Colettico Supabase registry.
4. Dispatcher — Supabase Dispatcher State and reconciliation/enforcement controls.

A Git commit, database migration, chat decision, or application change by itself does not represent the complete Coletti system release. Cross-component drift is resolved through the institutional release manifest and Dispatcher reconciliation. Production authorization remains a separate controlled gate.

## Run

```bash
pip install -e .[dev]
streamlit run streamlit_app.py
pytest
```

See `SECURITY_RELEASE_GATE.md`, `PROJECT_BOUNDARY.md`, and `MIGRATION_REGISTER.md`.
