# Coletti & Co.

Coletti & Co. is the commercial application layer for the private ColettiOS provenance-first record analysis core.

## Canonical production architecture

Production has one application surface and one authentication authority:

```text
https://colettico.com
        |
        v
Render static web application (web/)
        |
        v
Supabase
  - Auth
  - Postgres / RLS
  - Storage
  - Edge Functions
        |
        +--> external rails such as Square
```

The browser application owns the public site, secure sign-in, password recovery UI, client workspace, employee workspace, and owner/admin workspace. Role-aware routing changes the permitted workspace after authentication; it does not create a separate application.

### Canonical routes

- Public site: `https://colettico.com/`
- Secure authentication and recovery: `https://colettico.com/login/`
- Authenticated application shell: `https://colettico.com/workspace/`
- Legacy `/owner/` and `/portal/` paths are compatibility redirects into `/workspace/`.
- Legacy `/recovery/` and `/reset-password/` paths are compatibility redirects into `/login/` while preserving the recovery parameters.

## Authentication

Supabase Auth is the sole production identity and password authority. The browser uses the Supabase publishable key only. Password-reset and magic-link redirects are pinned to the canonical HTTPS origin instead of being derived from proxy request metadata.

After authentication:
- owner/admin -> `/workspace/#/admin/home`
- analyst/reviewer -> `/workspace/#/workspace/home`
- client -> `/workspace/#/portal/home`

Authorization remains enforced by authoritative roles, RLS, case membership, and assignment controls.

## Deployment

`render.yaml` defines exactly one production-facing Render service: the static `web/` application.

The prior Streamlit/Python application generation is not a production runtime and must not be attached to `colettico.com`, used for password recovery, or treated as an alternate owner/client portal. Historical Python code may remain for tests or migration reference until separately retired, but it is outside the production request path.

## Institutional control plane

This repository is authoritative for the **Coletti & Co. commercial application/data plane only**. The complete Coletti system state remains controlled through the institutional Supabase registry/release manifest across:

1. ColettiOS Core/IP — `dtreezcoletti/ColettiOS`.
2. Coletti & Co. commercial application — this repository.
3. Institutional database/state — Colettico Supabase.
4. Dispatcher — Supabase Dispatcher State and reconciliation/enforcement controls.

A code commit alone does not authorize production. `production_authorized` remains a separate evidence-based gate.

## Local checks

```bash
pytest
```

See `SECURITY_RELEASE_GATE.md`, `PROJECT_BOUNDARY.md`, `MIGRATION_REGISTER.md`, and `web/README.md`.
