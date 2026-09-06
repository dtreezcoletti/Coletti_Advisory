# Coletti & Co. Domain-Assumption Audit v1.0

Status: controlled architecture audit

## Standard

ColettiOS is considered domain-neutral when:

- Core vocabulary remains limited to Source, Proposition, Contradiction, Reconciliation, Conclusion, Escalation, Audit, and the generic evidence-state machine;
- domain adapters translate industry-specific records into the Core schema;
- configuration owns terminology, risk definitions, review policy, verification routing, workflow labels, and report naming;
- Coletti & Co. owns commercial acceptance, approval, publication, and client-delivery decisions;
- an unrelated domain can run without editing Core engine/model code.

## Audit result

No litigation-specific object model was found in the current ColettiOS Core. The reusable Core already uses generalized source/proposition/contradiction/reconciliation/conclusion/escalation/audit primitives. The remaining hidden domain assumptions were concentrated in Coletti & Co. presentation and policy code, especially intake classification and verification routing.

| Term / concept | Prior location | Classification | Disposition |
| --- | --- | --- | --- |
| `Operational Audit` | intake UI, synthetic fixture, analysis routing | Config layer | New intake label changed to `Operational Record`; legacy label retained only as a config alias for old metadata |
| `Business Record` | intake UI and verification routing | Config layer | Source-classification option and routing moved to `CommercialDomainConfig` |
| `Financial Record` | intake UI and verification routing | Config layer | Source-classification option and routing moved to `CommercialDomainConfig` |
| `Correspondence` | intake UI and verification routing | Config layer | Source-classification option and routing moved to `CommercialDomainConfig` |
| record-class → professional verifier mapping | `analysis.py` | Config layer | Moved to `verification_targets_by_record_class` |
| review-trigger evidence states | `analysis.py` | Config layer | Moved to `review_trigger_states` |
| free-text reconciliation outcome heuristics | `analysis.py` | Config layer | Moved to ordered `resolution_rules` |
| resolution states acceptable for publication readiness | `reporting.py` | Config layer | Moved to `publication_ready_resolution_states` |
| report names | `reporting.py` | Config layer | Moved to `report_labels` |
| report purposes | `reporting.py` | Config layer | Moved to `report_purposes` |
| report boundary language | `reporting.py` | Config / commercial boundary | Moved to `report_boundaries` |
| severity vocabulary (`CRITICAL/HIGH/MODERATE/LOW/CLEAR`) | previously absent as a formal boundary | Config layer | Added as `risk_taxonomy`; intentionally separate from evidence state |
| escalation reviewer roles | previously implicit | Config layer | Added as `escalation_review_roles` |
| PDF/CSV/JSON/plain-text extraction | `document_processing.py` | Adapter / format translation | Correct. Extracts candidate text only and does not promote it to evidence automatically |
| source `classification` metadata | intake → Core metadata | Adapter/config payload | Correct when treated as opaque metadata; Core does not interpret the domain label |
| human review before proposition promotion | `app_shell.py` | Coletti & Co. commercial workflow | Correct |
| report review / approve / publish / revoke | `publication.py` | Coletti & Co. commercial workflow | Correct; publication state does not alter Core evidence |
| `CLIENT` role and client-visible frozen snapshots | commercial auth/publication layer | Coletti & Co. | Correct |
| legal/accounting/medical/investigative/regulatory boundary disclaimers | service/report presentation | Coletti & Co. | Correct. These are scope limitations, not Core domain semantics |
| Records Reconstruction / Operations Reconstruction / Findings Report | commercial report layer | Config + Coletti & Co. | Correct once report names/purposes are configuration-owned |

## Core terms that required extraction

None were found in the current `colettios_core` evidence/provenance model. The audit therefore does not rename or mutate validated Core primitives.

The key fix is instead to prevent the commercial application from silently turning one firm's current terminology into a Core requirement.

## Configuration boundary

`CommercialDomainConfig` now owns:

- source classification vocabulary;
- report labels, purposes, and boundary language;
- verification routing by record class;
- verification guidance by issue type;
- risk taxonomy;
- escalation review roles;
- review-trigger states;
- reconciliation interpretation rules;
- publication-ready resolution states.

A future engagement/domain profile can replace those values without changing the Core engine.

## Adapter boundary

Domain adapters answer questions such as:

- What fields from a lab result become source metadata and candidate propositions?
- How does an invoice or purchase order map into a source record?
- How are grant-award records or donor restrictions normalized?
- Which source-specific locators should be preserved?

Adapters do not decide evidentiary truth, silently resolve contradictions, authorize publication, or redefine Core evidence states.

## Commercial boundary

Coletti & Co. remains responsible for:

- who may review an escalation;
- what a client-facing report is called;
- whether a draft is ready for approval;
- whether a finding is sufficiently supported for release;
- whether the client is authorized to receive a published snapshot;
- professional-verification/referral language and service-scope limitations.

## Acceptance requirement

The regression suite must include at least one unrelated-domain configuration whose source classes, verification targets, and report labels are not Coletti & Co.'s defaults. That test must pass through analysis and report generation without editing Core code or the analysis/report builders.

Any future change that introduces industry vocabulary directly into Core models, Core evidence states, or Core reconciliation behavior fails this architecture gate.
