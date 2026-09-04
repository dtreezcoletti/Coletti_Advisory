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

## Run

```bash
pip install -e .[dev]
streamlit run streamlit_app.py
pytest
```

See `SECURITY_RELEASE_GATE.md`, `PROJECT_BOUNDARY.md`, and `MIGRATION_REGISTER.md`.
