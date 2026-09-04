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
| LM-001 | Case-driven Streamlit dashboard | Remove from active commercial entrypoint | CLOSED | Retired from active entrypoint on `release/coletti2-migration-2026-09-04` |
| LM-002 | Historical/default case constants | Remove from active source and replace with configuration/synthetic data | CLOSED-PENDING-REGRESSION | Release cleanup recorded. Default-branch searches on 2026-09-04 returned no matches for `24D-1003`, `divorce`, or `Dreamliner`. Add automated prohibited-default regression test. |
| LM-003 | Duplicated ColettiOS core modules in commercial repo | Retire duplicates; consume ColettiOS through a defined adapter/interface | CLOSED-PENDING-INTERFACE-TEST | Duplicated core modules recorded as retired on migration branch. Verify commercial tests fail if direct internal-core imports are introduced. |
| LM-004 | Real-client facts as source-code defaults | Prohibit by repository policy and regression test | CONTROL-ACTIVE | `PROJECT_BOUNDARY.md` prohibits real party names, case numbers, settlement terms, evidentiary narratives, private source documents, and real-engagement demo data. Automated scan still required. |
| LM-005 | Synthetic default engagement | Keep synthetic fixture as the only built-in/default engagement | CONTROL-ACTIVE | Migration branch records synthetic fixture as only default. Add runtime acceptance test proving clean install/demo loads only synthetic data. |
| LM-006 | Historical material remaining in public Git history | Administrative remediation: assess history, visibility, exposure, and whether rewrite/archive/replacement is required | OPEN-HIGH | Current-branch cleanup does not erase prior commits. Complete Git-history exposure review before real-client production use. |
| LM-007 | Commercial/core repository boundary | Keep services, engagement workflow, client UI/auth, reporting presentation, contracts/ops in commercial repo; reusable engine logic in ColettiOS | CONTROL-ACTIVE | `PROJECT_BOUNDARY.md` documents allowed and prohibited responsibilities. Add import/dependency boundary test. |
| LM-008 | Production identity/storage/service boundary | Fail closed unless authenticated identity, authorization registry, durable encrypted storage, and private ColettiOS service are configured | BLOCKED-DEPLOYMENT | OIDC, RBAC, session controls, encrypted intake, hashing, GCS backend, and private-adapter requirements recorded. Production cutover remains prohibited until deployment credentials/configuration are validated. |
| LM-009 | Superseded/parallel repositories (`coletti-os`, `COLETTI-AVDVIORY-FIRM`) | Determine authoritative status; archive, label, or migrate anything still required | OPEN | Repositories still exist in the connected GitHub account. Triage whether either contains unique approved code or historical-only material. |
| LM-010 | Historical case material as architectural precedent | Preserve methodology only; do not approve case facts/workflows as product architecture without generalization and synthetic proof | CONTROL-ACTIVE | Governing rule established here and in project boundary. Core acceptance must demonstrate unrelated synthetic engagement with zero historical-case dependency. |

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

## Required acceptance tests

Before this migration register can be considered fully CLOSED:

- prohibited historical/client-default scan passes;
- synthetic clean-install/default-engagement test passes;
- commercial-to-core dependency/import boundary test passes;
- unrelated synthetic engagement passes end-to-end with zero historical-case dependency;
- legacy parallel repositories are classified and dispositioned;
- Git-history exposure/remediation decision is documented;
- production deployment gate is validated before any real client data is accepted.

## Production hold

The live `coletti2.streamlit.app` must not accept real client data until OIDC secrets, authorization registry, durable storage credentials, the private ColettiOS service endpoint, and all production-gate acceptance checks are configured and validated.
