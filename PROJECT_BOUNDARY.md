# Coletti & Co. Project Boundary

Status: CONTROLLED
Effective date: 2026-09-06
Security profile: `docs/SPLIT_PLANE_SECURITY_IMPLEMENTATION_v2.0.md`

## Role

Coletti & Co. is the commercial application and encrypted client-data plane for ColettiOS. It packages services, manages engagements, authenticates and authorizes users, handles secure intake/storage, controls client-facing publication and presents outputs generated through released ColettiOS interfaces.

## Service/core separation rule

Coletti & Co. owns:

- service definitions and scope controls;
- engagement workflows and milestones;
- OIDC identity/session handling;
- RBAC and engagement authorization;
- authenticated intake;
- encryption and durable storage of original source bytes;
- retention/hold/deletion workflows;
- report/publication state and client presentation;
- contracts, operating procedures, payments and administrative processes;
- client/employee/owner user experiences.

ColettiOS owns:

- reusable evidence/provenance methodology;
- source identity/hash invariants;
- evidence-state logic and state history;
- proposition creation rules;
- contradiction preservation;
- reconciliation logic;
- reviewer-conclusion separation;
- escalation and audit mechanics;
- generalized adapter rules;
- engagement manifests and private Core persistence.

The commercial repository may call released ColettiOS functionality only through a defined adapter/service contract. It may not duplicate, fork or silently re-implement reusable ColettiOS Core logic.

## Canonical security boundary

The September 3 embedded-v4-vault deployment topology is superseded by ColettiOS Split-Plane Security Architecture v2.0.

- Original client source-file bytes remain in the Coletti & Co. encrypted data plane.
- ColettiOS Core stores source hashes, approved metadata, provenance objects, evidence states and audit/manifests — not original source bytes.
- Coletti & Co. must not assume Core encrypted or scanned a source.
- ColettiOS must not assume the commercial layer successfully stored, retained, scanned or recovered a source merely because its hash was registered.
- Cross-plane handoffs are explicit, attributable and production-tested.

Historical v4 controls remain security provenance and mapped production requirements; they are not a second live architecture.

## Allowed here

- service definitions and scope controls;
- engagement intake schemas;
- client workspace and identity/authorization logic;
- encrypted source-byte storage implementation;
- data-plane security/recovery controls;
- reporting templates and presentation adapters;
- report publication state;
- contracts, operating procedures and billing workflows;
- synthetic demonstrations;
- adapters that call released ColettiOS functionality.

## Not allowed here

- reusable ColettiOS Core logic that belongs in the Core repository;
- real historical case facts used as source-code constants;
- real party names, case numbers, settlement terms or evidentiary narratives;
- private source documents in Git;
- public demonstration data copied from a real engagement;
- plaintext production secrets or encryption keys;
- a system-generated legal, accounting, tax, investigative or professional conclusion presented as if Coletti & Co. itself made the licensed determination.

## Real-client/default prohibition

Client-specific or historical facts may enter only through an engagement-specific configuration or data layer. They may never become reusable source-code defaults, example constants, built-in demo content, test fixtures derived from a real engagement or fallback values used when engagement data is absent.

Synthetic fixtures are the only approved built-in/default engagement data.

## Historical-material rule

Historical case material is migration debt and methodology provenance only. It is not approved commercial architecture. Any workflow, rule, model or interface derived from historical work must be generalized, stripped of case facts and proven on unrelated synthetic data before it can be treated as reusable product architecture.

## Engagement principle

Client-specific facts enter through an engagement configuration/data layer. They do not become reusable source-code defaults.

## Output principle

Coletti & Co. organizes and reconstructs records, identifies conflicts and gaps and presents traceable findings about what the records establish. Where a conclusion requires a licensed or professional determination, the output marks that boundary explicitly.
