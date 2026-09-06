# Coletti & Co. Split-Plane Security Implementation v2.0

Status: CONTROLLED IMPLEMENTATION PROFILE
Effective date: 2026-09-06
Canonical architecture authority: private ColettiOS `docs/CANONICAL_SECURITY_ARCHITECTURE_v2.0.md`
Production verification: CLOSED / SYNTHETIC-DEMO ONLY until all required gates pass

## Purpose

This document is **not a second security architecture**. It defines how the Coletti & Co. commercial application implements its side of the canonical ColettiOS Split-Plane Security Architecture v2.0.

The September 3 embedded-v4-vault deployment topology is superseded. Historical v4 controls remain security provenance and are mapped into the v2 control model; they are not an alternate production path.

## Canonical split

### Coletti & Co. — encrypted client-data plane

Coletti & Co. owns:

- OIDC identity and session lifecycle;
- server-side RBAC and engagement authorization;
- intake and client uploads;
- plaintext SHA-256 generation before encryption;
- intake scanning/quarantine policy;
- encryption of original source bytes before durable storage;
- Google Cloud Storage security controls, versioning, retention/hold behavior and recovery;
- report/publication state;
- client/employee/owner presentation and role-specific visibility;
- data-plane operational logging that excludes client content and secret values.

### ColettiOS — private provenance/control plane

ColettiOS owns:

- immutable source identity and source hash registration;
- evidence states and state history;
- source-linked propositions;
- contradiction preservation;
- reconciliation without silent promotion;
- reviewer conclusions;
- escalations;
- authenticated audit events;
- engagement manifests;
- domain-neutral invariants and adapter rules;
- transactional engagement persistence.

Original source-file bytes never enter Core persistence.

## Source encryption profile

The commercial data plane implements the following v2 profile:

1. `STORAGE_MASTER_KEY` is a 256-bit root secret stored outside Git.
2. The root secret is **not used directly as the AES data key for source objects**.
3. A 256-bit object key is derived with HKDF-SHA256 from:
   - security architecture version;
   - key derivation scheme;
   - purpose (`source-object`);
   - organization ID;
   - engagement ID;
   - source ID;
   - the code-controlled cryptographic profile/key version (initial release: `v1`).
4. AES-256-GCM encrypts the source with a fresh random 96-bit nonce.
5. Authenticated associated data binds the ciphertext to:
   - architecture version;
   - key version;
   - organization;
   - engagement;
   - source identity;
   - filename;
   - plaintext SHA-256 digest.
6. The GCS object records non-secret verification metadata including security architecture, derivation scheme and key version.
7. Original uploads are create-only (`if_generation_match=0`) and bucket versioning is mandatory.

This gives source-level cryptographic domain separation while retaining one externally managed root secret for the initial deployment. The initial release hard-pins cryptographic profile `v1` in code. A future key/profile version is a code-and-test migration; an operator cannot rotate cryptographic profiles merely by changing a secret or environment setting. A future KMS/HSM-backed root-key provider may replace secret-manager root material without changing the Core evidence model.

## Security metadata rule

Security metadata may identify technical organization/engagement/source IDs needed for recovery and integrity verification. It must not contain:

- passwords;
- bearer tokens;
- OAuth credentials;
- raw encryption keys;
- recovery secrets;
- unnecessary client narrative/content;
- private analyst notes;
- professional conclusions.

## v4 control migration

The commercial layer carries the following v4 obligations forward:

| Historical v4 control | Commercial v2 implementation |
|---|---|
| Per-case vault | Per-engagement encrypted object namespace + engagement authorization |
| Content encryption | HKDF-scoped AES-256-GCM source encryption before storage |
| Content integrity | Plaintext SHA-256 bridge into Core source identity |
| Version history | GCS versioning + create-only original upload |
| Quarantine | Intake/security workflow plus Core `QUARANTINED` state; production proof required |
| Malware screening | Mandatory production intake control for untrusted uploads; production proof required |
| PII/sensitive-data handling | Config/policy-owned intake classification; must not mutate evidence truth |
| Legal hold / deletion controls | Storage-policy and operating-workflow responsibility; production proof required where engagement policy requires |
| Backup / recovery | Restore must reconstruct encrypted source objects plus corresponding Core manifests |
| Key rotation | Code-controlled profile `v1` plus versioned derivation; future rotation requires a code+test migration and an operational rotation/recovery test before certification |

A documented mapping is not a PASS. Controls identified as production requirements remain closed until exercised against the real production stack.

## Cross-plane transaction law

A successful source intake is not complete merely because GCS accepted ciphertext or Core accepted a hash.

The normal workflow must preserve a recoverable relationship among:

- encrypted stored object;
- exact plaintext SHA-256;
- organization ID;
- engagement ID;
- source ID;
- Core registration/audit event;
- actor/session attribution.

If the second half of a cross-plane operation fails, the workflow must surface an exception and route it to reconciliation/cleanup rather than silently claiming complete intake.

## Production certification requirements

Real-client authorization remains closed until production evidence proves at minimum:

- real OIDC login, expiry and revocation;
- cross-engagement authorization rejection;
- scoped-key encrypted GCS write/read/decrypt/hash verification;
- source hash continuity into Core;
- private Core authentication;
- concurrent Core writes without lost state;
- quarantine/malware handling for untrusted uploads;
- retention/hold behavior required by policy;
- backup and isolated restore of both planes;
- security-safe operational logging;
- report publication gates;
- one unrelated synthetic engagement through the entire live production path.

## Canonical rule

**Coletti & Co. protects client bytes and access. ColettiOS protects provenance, analytical state and auditability. Neither layer may claim the other layer's control without verification.**
