# Legacy Migration Register

Status date: 2026-09-04
Control status: ACTIVE
Owner: Coletti & Co. commercial repository

## Purpose

This register treats historical-case code, facts, duplicated core logic, and superseded repository structures as migration debt. None of those materials are approved commercial architecture merely because they existed in an earlier build.

The target commercial architecture is a synthetic, configuration-driven Coletti & Co. application that consumes released ColettiOS functionality only through defined interfaces.

## Governing rules

1. Real-client or historical-case facts may enter only through engagement data/configuration paths; they may not be source-code defaults.
2. Reusable evidence/provenance logic belongs in ColettiOS, not the Coletti & Co. commercial repository.
3. Synthetic fixtures are the only approved built-in/default engagement data.
4. Historical code or facts found in active commercial paths are migration debt and must be removed, isolated, or replaced.
5. A migration item is not CLOSED until its acceptance evidence is recorded.
6. Public Git history is treated separately from current-branch cleanup because deleting active files does not remove prior commits.

## Migration debt register

| ID | Migration debt / control | Required disposition | Status | Acceptance evidence / next proof |
|---|---|---|---|---|
| LM-001 | Case-driven Streamlit dashboard | Remove from active commercial entrypoint | CLOSED | Retired from active entrypoint on `release/coletti2-migration-2026-09-04`. |
| LM-002 | Historical/default case constants | Remove from active source and replace with configuration/synthetic data | CLOSED | Default-branch searches returned no matches for obvious historical identifiers; automated repository-boundary regression now enforces prohibited case-number patterns. CI run 33911492798 passed on 2026-09-04. |
| LM-003 | Duplicated ColettiOS core modules in commercial repo | Retire duplicates; consume ColettiOS through a defined adapter/interface | CLOSED | Retired modules are prohibited by `tests/test_repository_boundary.py`; direct `colettios_core` imports are prohibited in active commercial paths. CI run 33911492798 passed. |
| LM-004 | Real-client facts as source-code defaults | Prohibit by repository policy and regression test | CONTROL-VERIFIED | `PROJECT_BOUNDARY.md` now expressly prohibits real-client/historical facts as defaults, fixtures, example constants, demo data, or fallback values. Boundary regression is active and passing. |
| LM-005 | Synthetic default engagement | Keep synthetic fixture as the only built-in/default engagement | CONTROL-VERIFIED | Runtime/default test verifies demo/synthetic defaults; production configuration remains fail-closed. CI run 33911492798 passed. |
| LM-006 | Historical material remaining in public Git history | Administrative remediation: assess history, visibility, exposure, and whether rewrite/archive/replacement is required | OPEN-HIGH | Current-branch cleanup does not erase prior commits. Complete Git-history exposure review before real-client production use. |
| LM-007 | Commercial/core repository boundary | Keep services, engagement workflow, client UI/auth, reporting presentation, contracts/ops in commercial repo; reusable engine logic in ColettiOS | CONTROL-VERIFIED | `PROJECT_BOUNDARY.md` contains an explicit service/core separation rule; dependency/import boundary regression is active and passing. |
| LM-008 | Production identity/storage/service boundary | Fail closed unless authenticated identity, authorization registry, durable encrypted storage, and private ColettiOS service are configured | BLOCKED-DEPLOYMENT | OIDC, RBAC, session controls, encrypted intake, hashing, GCS backend, and private-adapter requirements recorded. Production cutover remains prohibited until deployment credentials/configuration are validated. |
| LM-009 | Parallel repositories (`coletti-os`, `COLETTI-AVDVIORY-FIRM`) | Classify and prevent architectural ambiguity | CLOSED | `coletti-os` is classified as Streamlit deployment compatibility shim only and pins a verified `Coletti_Advisory` release. `COLETTI-AVDVIORY-FIRM` is classified RETIRED/NON-AUTHORITATIVE and contains no approved production role. |
| LM-010 | Historical case material as architectural precedent | Preserve methodology only; do not approve case facts/workflows as product architecture without generalization and synthetic proof | CONTROL-VERIFIED | `PROJECT_BOUNDARY.md` explicitly declares historical case material migration debt/methodology provenance only; generalized architecture requires unrelated synthetic proof. |

## Five repository-boundary acceptance requirements

As of 2026-09-04, the following controls are COMPLETE as repository-governance requirements:

- [x] Commercial repository boundary documented.
- [x] Service scope separated from ColettiOS core.
- [x] Legacy migration register active.
- [x] Real-client facts prohibited as source-code defaults.
- [x] Historical case material treated as migration debt, not approved commercial architecture.

These five completed controls do not remove the separate production hold or the open Git-history exposure review.

## Completed on `release/coletti2-migration-2026-09-04`

- legacy case UI removed from the active entrypoint;
- historical/default case constants removed with retired legacy modules;
- duplicated core modules retired from the commercial branch;
- synthetic fixture is the only default engagement;
- Streamlit OIDC authentication path added;
- RBAC and engagement authorization added;
- application session expiration and logout added;
- authenticated actor context propagated through the ColettiOS adapter contract;
- AES-256-GCM encrypted intake storage added;
- SHA-256 source hashing added;
- durable Google Cloud Storage backend implemented for production configuration;
- synthetic adapter retained only for public demonstration mode;
- production mode fails closed without authenticated identity, GCS, and private ColettiOS HTTP adapter;
- CORS/XSRF protections restored in Streamlit configuration.

## Remaining migration-program acceptance work

The five repository-boundary requirements above are complete. The broader migration program remains open until:

- unrelated synthetic engagement passes end-to-end with zero historical-case dependency;
- Git-history exposure/remediation decision is documented;
- production deployment gate is validated before any real client data is accepted.

## Production hold

The live `coletti2.streamlit.app` must not accept real client data until OIDC secrets, authorization registry, durable storage credentials, the private ColettiOS service endpoint, and all production-gate acceptance checks are configured and validated.
