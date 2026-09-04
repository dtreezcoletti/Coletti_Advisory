# Production Infrastructure Gate v1.0

Status date: 2026-09-04
Owner: Coletti & Co. commercial deployment
Gate status: CLOSED — SYNTHETIC/DEMO ONLY

## Purpose

This gate defines the minimum infrastructure conditions required before `coletti2.streamlit.app` may accept real client records. Passing unit tests or having production-capable code is not sufficient by itself. Every mandatory production dependency must be live, configured, validated, and evidenced.

## Release rule

Real client data is prohibited until every item marked REQUIRED is PASS and the production end-to-end acceptance test is PASS.

## Infrastructure register

| ID | Control | Requirement | Current status | Acceptance evidence |
|---|---|---|---|---|
| PI-001 | Commercial release | Tested Coletti & Co. commit pinned by deployment shim | PASS | `coletti-os` deployment shim pins tested `Coletti_Advisory` release |
| PI-002 | Production startup preflight | App validates required production configuration before external backends are constructed | PASS | `validate_production_configuration()` plus automated tests |
| PI-003 | Identity provider | Real OIDC provider configured in Streamlit secrets | REQUIRED / NOT VALIDATED | Successful login with production identity and valid iat/exp claims |
| PI-004 | Authorization registry | Server-side authorization registry contains only approved users/engagements | REQUIRED / NOT VALIDATED | Approved production `AUTHZ_REGISTRY_JSON` and revocation test |
| PI-005 | Session control | Production session TTL configured and expiration/re-authentication tested | REQUIRED / CODE READY | Expiration and re-login acceptance test |
| PI-006 | Object storage | Private production Google Cloud Storage bucket created and credentials configured | REQUIRED / NOT DEPLOYED | Successful encrypted upload to intended private bucket |
| PI-007 | Client-side encryption | 32-byte production storage key provisioned outside Git | REQUIRED / NOT PROVISIONED | Preflight pass plus encrypted-object verification |
| PI-008 | Source integrity | SHA-256 plaintext hash generated and retained as source integrity metadata | PASS / CODE | Intake and storage implementation/tests |
| PI-009 | Private ColettiOS service | ColettiOS service deployed behind HTTPS with bearer authentication | REQUIRED / NOT DEPLOYED | `/health` reachable; protected `/v1/*` rejects missing/invalid token and accepts valid token |
| PI-010 | ColettiOS persistence | Core evidence state stored on encrypted durable persistence, not ephemeral container filesystem | REQUIRED / NOT DEPLOYED | Restart/redeploy persistence test passes |
| PI-011 | Commercial-to-core credential | Strong server-to-server token provisioned in both environments through secret management | REQUIRED / NOT PROVISIONED | Successful authenticated service call; invalid-token rejection test |
| PI-012 | Engagement isolation | User cannot access an engagement outside authorization scope | REQUIRED / CODE READY | Two-engagement negative authorization test passes in production path |
| PI-013 | Backup/recovery | Production data backup and restore procedure implemented and tested | REQUIRED / NOT IMPLEMENTED | Restore test reconstructs encrypted object and core manifest state |
| PI-014 | Operational logging | Production failures and security-relevant events observable without logging secret values or client record contents | REQUIRED / NOT IMPLEMENTED | Logging review and controlled failure test |
| PI-015 | Deployment rollback | Last known-good commercial release can be restored through deployment-shim pin | PASS / DESIGN | Pin-based release mechanism documented and functioning |
| PI-016 | Git/history disposition | Historical/public repository exposure decision documented | REQUIRED / OPEN | Migration register LM-006 closed or formally accepted with remediation decision |
| PI-017 | Production E2E | Full synthetic production-path engagement succeeds end to end | REQUIRED / NOT RUN | Signed acceptance record for production E2E suite |
| PI-018 | Real-client authorization | Explicit real-client acceptance gate approved only after all infrastructure/report/workflow gates pass | REQUIRED / NOT AUTHORIZED | `REAL_CLIENT_ACCEPTANCE_GATE_v1.0` = PASS |

## Required production configuration

The commercial application currently expects these deployment values outside source control:

- `APP_MODE=production`
- `STORAGE_BACKEND=gcs`
- `COLETTIOS_BACKEND=http`
- `GCS_BUCKET`
- `GCP_SERVICE_ACCOUNT_JSON`
- `STORAGE_MASTER_KEY`
- `COLETTIOS_API_URL` using HTTPS
- `COLETTIOS_API_TOKEN`
- `AUTHZ_REGISTRY_JSON`
- `SESSION_TTL_MINUTES`
- Streamlit `[auth]` configuration and provider client credentials

No real secret values belong in Git.

## Production-path acceptance sequence

The infrastructure gate is not PASS until the following sequence succeeds using synthetic records on the real production backends:

1. authenticate through the configured OIDC provider;
2. resolve the authenticated account through the production authorization registry;
3. select only an authorized engagement;
4. upload a synthetic source record;
5. generate the plaintext SHA-256 content hash;
6. encrypt the source before object-storage upload;
7. confirm the object exists only in the intended engagement path;
8. register the source through the HTTPS ColettiOS service;
9. confirm the authenticated audit actor and engagement context are preserved;
10. retrieve the engagement manifest after application/service restart;
11. reject cross-engagement access;
12. reject revoked/expired identity or authorization;
13. restore from backup/recovery procedure;
14. complete report/publishing-path acceptance when the report engine is ready.

## Current blockers to opening this gate

The remaining blockers are deployment/operations work rather than missing architectural concepts:

- production OIDC credentials/configuration;
- private GCS bucket and service account;
- production AES storage key;
- deployed HTTPS ColettiOS service;
- durable encrypted persistence for the core service;
- server-to-server service secret;
- backup/recovery implementation and restore test;
- operational logging/monitoring validation;
- Git-history disposition decision;
- full production-path synthetic E2E test;
- real-client acceptance authorization.

## Release decision

Until this document records PASS for every REQUIRED control, `coletti2.streamlit.app` remains synthetic/demo only and must not receive real client, legal, medical, financial, or identifying records.
