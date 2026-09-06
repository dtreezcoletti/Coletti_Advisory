# Production Infrastructure & Security Gate v2.0

Status date: 2026-09-06
Owner: Coletti & Co. commercial deployment
Gate status: **CLOSED — SYNTHETIC/DEMO ONLY**
Canonical security authority: ColettiOS `docs/CANONICAL_SECURITY_ARCHITECTURE_v2.0.md`
Commercial implementation profile: `docs/SPLIT_PLANE_SECURITY_IMPLEMENTATION_v2.0.md`

## Purpose

This gate is the only path from code-ready software to authorization for real client records. Passing unit tests, having production-capable classes, or preserving historical v4 controls in documentation is not enough. Every mandatory production control must be live, configured, exercised and evidenced on the actual production stack.

## Operational completeness rule

- **PASS / VERIFIED OPERATIONAL** — successfully exercised in the environment where the control must operate, with acceptance evidence retained.
- **IMPLEMENTED / NOT VERIFIED** — code/configuration exists, but the real production path has not been proven.
- **MISSING / FAILING** — absent, incomplete, unsafe, or demonstrably failing.

No aggregate score can override one failed mandatory control.

## Architectural declaration

The September 3 embedded-v4-vault deployment topology is superseded by Split-Plane Security Architecture v2.0.

- **Coletti & Co.** is the encrypted client-data plane: identity, authorization, intake, source-byte encryption, object storage, publication state and client presentation.
- **ColettiOS** is the private provenance/control plane: hashes, source identity, evidence states, propositions, contradictions, reconciliations, conclusions, escalations, audit events and engagement manifests.
- Original source-file bytes do not enter Core persistence.
- Historical v4 controls are mapped requirements, not a second live architecture.

## Infrastructure and security register

| ID | Control | Current status | Production acceptance evidence |
|---|---|---|---|
| PI-001 | Tested commercial release pinned by deployment shim | PASS / DESIGN | Verified release pin |
| PI-002 | Production startup preflight | PASS / CODE | Automated configuration tests |
| PI-003 | Real OIDC identity provider | REQUIRED / NOT VALIDATED | Production login with valid iat/exp |
| PI-004 | Server-side authorization registry | REQUIRED / NOT VALIDATED | Approved registry + revocation test |
| PI-005 | Session TTL / reauthentication | REQUIRED / CODE READY | Expiry and re-login test |
| PI-006 | Private GCS bucket | REQUIRED / NOT DEPLOYED | Live bucket probe PASS |
| PI-007 | Root storage secret outside Git | REQUIRED / NOT PROVISIONED | Secret-manager evidence; value never displayed |
| PI-008 | Versioned HKDF-SHA256 scoped data keys | IMPLEMENTED / NOT VERIFIED | Live probe proves derived key != root and successful decrypt/hash roundtrip |
| PI-009 | AES-256-GCM source encryption before durable storage | IMPLEMENTED / NOT VERIFIED | Live encrypted write/read/decrypt test |
| PI-010 | Source SHA-256 continuity | PASS / CODE; LIVE PROOF REQUIRED | GCS metadata + Core registered digest match exact synthetic plaintext |
| PI-011 | GCS uniform access / public-access prevention / versioning | IMPLEMENTED GATE / NOT VERIFIED | Live bucket inspection PASS |
| PI-012 | Create-only original-source upload | PASS / CODE; LIVE PROOF REQUIRED | Duplicate generation write rejected |
| PI-013 | Private HTTPS ColettiOS service | REQUIRED / NOT DEPLOYED | Health ready; missing/invalid token rejected; valid token accepted |
| PI-014 | Durable PostgreSQL Core persistence | REQUIRED / NOT DEPLOYED | Restart/redeploy persistence roundtrip |
| PI-015 | Same-engagement transactional Core writes | IMPLEMENTED / NOT VERIFIED | Multi-worker concurrent mutation test preserves all state/audit events |
| PI-016 | Different-engagement concurrency | IMPLEMENTED / NOT VERIFIED | Parallel synthetic engagements complete without global lock/cross-state |
| PI-017 | Engagement isolation | REQUIRED / CODE READY | Two-engagement negative authorization test on production path |
| PI-018 | Authenticated actor/session propagation | PASS / CODE; LIVE PROOF REQUIRED | Core audit event contains expected production identity context |
| PI-019 | Intake malware screening | REQUIRED / NOT YET VERIFIED | Known-safe and test-malicious synthetic artifacts route correctly; unsafe content cannot enter active review silently |
| PI-020 | Quarantine workflow | REQUIRED / NOT YET VERIFIED | Quarantined upload remains isolated and Core state reflects controlled quarantine path |
| PI-021 | Sensitive-data/PII handling policy | REQUIRED / POLICY/OPS OPEN | Synthetic sensitive-data test proves routing/handling without changing evidence truth |
| PI-022 | Retention / legal-hold controls | REQUIRED WHEN POLICY APPLIES / NOT VERIFIED | Hold prevents prohibited deletion; release/deletion is explicit and audited |
| PI-023 | Publication-state encryption | IMPLEMENTED / NOT VERIFIED | Encrypted state survives restart and cannot be read with wrong scope/key |
| PI-024 | Report review / approval / publish separation | PASS / CODE; LIVE PROOF REQUIRED | Changed approved draft cannot publish; client sees only published snapshot |
| PI-025 | Backup coverage for both planes | REQUIRED / NOT IMPLEMENTED | Encrypted GCS objects + Core PostgreSQL included in independent recoverable backup |
| PI-026 | Isolated restore | REQUIRED / NOT RUN | Restore reconstructs exact source ciphertext/integrity bridge + Core manifest without overwriting production |
| PI-027 | Key-version / rotation procedure | REQUIRED / NOT RUN | Controlled synthetic rotation/recovery demonstrates correct key-version selection |
| PI-028 | Operational logging without secrets/client content | REQUIRED / NOT IMPLEMENTED | Controlled failure review verifies safe telemetry |
| PI-029 | Deployment rollback | PASS / DESIGN | Last known-good commercial release pin can be restored |
| PI-030 | Git/history exposure disposition | REQUIRED / OPEN-HIGH | LM-006 formally closed or accepted with documented remediation decision |
| PI-031 | Complete live production E2E | REQUIRED / NOT RUN | Unrelated synthetic engagement intake → analysis → review → publication → recovery succeeds without developer intervention |
| PI-032 | Explicit real-client authorization | REQUIRED / NOT AUTHORIZED | Real-client acceptance gate signed only after every applicable REQUIRED row is PASS |

## Required production configuration

The commercial application expects these values outside source control:

- `APP_MODE=production`
- `STORAGE_BACKEND=gcs`
- `COLETTIOS_BACKEND=http`
- `GCS_BUCKET`
- `GCP_SERVICE_ACCOUNT_JSON`
- `STORAGE_MASTER_KEY`
- `STORAGE_KEY_VERSION` (initial release: `v1`)
- `COLETTIOS_API_URL` using HTTPS
- `COLETTIOS_API_TOKEN`
- `AUTHZ_REGISTRY_JSON`
- `SESSION_TTL_MINUTES`
- Streamlit `[auth]` provider configuration and credentials

No real secret values belong in Git, documentation, screenshots, ordinary logs, Core manifests or client-visible metadata.

## Production-path acceptance sequence

The gate cannot open until this exact synthetic sequence succeeds on the real production backends:

1. authenticate through production OIDC;
2. resolve the identity through the production authorization registry;
3. prove an unauthorized engagement cannot be selected/read/written;
4. inspect the real GCS security controls;
5. ingest a synthetic source through the normal authenticated intake path;
6. compute plaintext SHA-256;
7. run required scan/classification and quarantine logic;
8. derive the scoped `v1` source data key from the external root secret;
9. AES-256-GCM encrypt the source with identity/hash-bound AAD;
10. write ciphertext create-only to the authorized engagement namespace;
11. read it back, authenticate/decrypt it and reproduce the exact SHA-256;
12. register the source hash/context through private HTTPS ColettiOS;
13. prove Core audit attribution and engagement identity;
14. concurrently submit multiple same-engagement Core mutations through more than one deployed worker and prove no lost updates;
15. concurrently operate a separate engagement and prove no cross-state/global lock;
16. restart/redeploy commercial and Core services and verify persistence;
17. create/review/approve/publish a synthetic report and prove unpublished/internal state is inaccessible to the client surface;
18. exercise required retention/hold controls;
19. restore both planes into an isolated recovery target;
20. reconcile restored source digest with restored Core source identity;
21. complete one unrelated synthetic engagement end to end without developer intervention;
22. retain the signed acceptance evidence.

## Release decision

Until all applicable REQUIRED controls are PASS, the application remains synthetic/demo only and must not receive real client, legal, medical, financial, employment, insurance, tax, identity or other confidential records.
