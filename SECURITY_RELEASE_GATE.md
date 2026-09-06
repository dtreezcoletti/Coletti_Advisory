# Authentication & Security Release Gate

Canonical model: ColettiOS Split-Plane Security Architecture v2.0
Commercial implementation: `docs/SPLIT_PLANE_SECURITY_IMPLEMENTATION_v2.0.md`
Production infrastructure/security gate: `PRODUCTION_INFRASTRUCTURE_SECURITY_GATE_v2.0.md`

## Architectural declaration

The September 3 embedded-v4-vault deployment topology is superseded. Coletti & Co. is now the encrypted client-data plane and ColettiOS is the private provenance/audit control plane. Historical v4 controls remain mapped production requirements; they are not a second production architecture.

## Implemented controls

- ✅ secrets excluded from Git
- ✅ real login through Streamlit OIDC
- ✅ password verification delegated to the configured identity provider
- ✅ signed OIDC identity processing delegated to Streamlit/Authlib
- ✅ explicit `iat` / `exp` identity-token lifetime enforcement
- ✅ application session expiration and re-authentication lifecycle
- ✅ logout and server-side application authorization revocation
- ✅ RBAC enforcement
- ✅ engagement-level authorization
- ✅ authenticated upload pipeline
- ✅ plaintext SHA-256 source hashing before encryption
- ✅ AES-256-GCM encrypted source storage implementation
- ✅ HKDF-SHA256 source-object key derivation scoped by organization, engagement, source and code-controlled cryptographic profile
- ✅ cryptographic profile/key version `v1` hard-pinned for the initial release
- ✅ GCS uniform-access / public-access-prevention / versioning gate in code
- ✅ authenticated audit actor propagation into ColettiOS
- ✅ source mutation protection in ColettiOS
- ✅ encrypted publication-state storage with a separate cryptographic purpose scope
- ✅ production configuration preflight

## Production-verification controls still required

The following may have code/design support but are **not PASS** until exercised on the live production stack:

- production OIDC provider and account registry;
- private GCS bucket and scoped-key encryption roundtrip;
- private HTTPS ColettiOS service;
- durable PostgreSQL persistence;
- multi-worker same-engagement transactional write proof;
- cross-engagement rejection;
- malware screening and quarantine path for untrusted uploads;
- applicable sensitive-data/PII handling policy;
- applicable retention/legal-hold/deletion controls;
- backup coverage for both the encrypted data plane and Core control plane;
- isolated restore;
- future key-profile rotation procedure;
- operational logging review;
- complete unrelated synthetic production E2E.

## Portal correction

OLD:

```text
Client Authentication
[ dropdown containing client names ]
```

NEW (after a real OIDC login):

```text
Authenticated as:
Demetriés Coletti
Role: Owner

Authorized workspace:
[ Coletti & Co. Synthetic Demo ▼ ]
```

The workspace selector is authorization, not identity. Users may only see engagements granted to their authenticated account.

## Production gate

Production mode fails closed unless all required configuration and runtime controls are present. Real-client data remains prohibited until the full production infrastructure/security gate is PASS.

Synthetic mode remains intentionally available without OIDC so the public demonstration can be viewed without exposing approved client data. Demo uploads are synthetic-only and use encrypted ephemeral storage.
