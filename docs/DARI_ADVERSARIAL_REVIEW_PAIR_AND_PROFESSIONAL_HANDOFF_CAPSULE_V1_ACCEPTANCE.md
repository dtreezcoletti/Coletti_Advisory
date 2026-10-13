# ColettiOS Unified V1 — Mandatory Adversarial Review Pair and Professional Handoff Capsule

**Status: OWNER-REQUIRED V1 SCOPE, October 12, 2026. DESIGN/ACCEPTANCE SPEC ONLY.**
This requirement overrides the previous *deferral* for these TWO differentiators in IMP-012. It does not automatically operationalize the capabilities, expand AI professional authority, authorize external recipients, or change the Owner-only production release. The other deferred differentiation upgrades remain deferred: Claim-Level Model Consensus Ledger and Temporal Intelligence / "What We Knew Then". Evidence Passport and Case Time Machine remain independently selected V1 requirements.

## 1. DARI Adversarial Review Pair — V1 mandatory

### Purpose
Independently challenge a proposed reconstruction so unsupported interpretations, contradictions, omissions, alternative explanations and premature Record State promotions are found **before** a human reviewer considers publication. This is an analytical challenge control, **not two models voting to establish a fact**.

### Roles and execution
1. **Primary Reasoner** receives an authorized, fixed case/source snapshot and produces the strongest *source-supported* draft reconstruction: proposition identifiers; precise case-scoped source/exhibit references; timestamp and time-scope; Record State candidates; supporting evidence; known gaps; explicit uncertainty; tool/model/process version and run ID.
2. **Independent Challenge Reasoner** receives the **same sealed source snapshot**, target reconstruction output for challenge if needed *after* recording its own independent source review. Its initial source-only pass must not be contaminated by the primary's conclusions. It checks contrary records, missing evidence, logical overreach, suspicious attribution, version conflict, selection bias, alternative explanations, what was knowable at each relevant time, and protected-profession overreach.
3. **Comparison/Reconciliation assembler** produces a structured **agreement / disputed / unresolved / evidence-request** matrix with source reference pointers and conflicting proposition IDs. Agreement between two models is **not** evidence of truth, and disagreement is not arbitrarily resolved by confidence scores.
4. **Human Fresh Eyes / QA reviewer** inspects the paired analyses and raw source citations; adjudicates only what the records justify, leaving unresolved propositions unresolved. Staff independence and conflicts-of-interest rules remain controlling. DARI cannot serve as the independent required human.
5. **Publication preparation** references the versioned review result and explicit human approval gate. No direct AI promotion to Documented Fact, protected professional opinion, accepted claim, publication or external action.

### System contract
- Input: canonical client_id / case_id / source IDs with immutable source-snapshot hash, purpose and authenticated actor; no cross-case or unsourced AI reasoning.
- Output: immutable linked run records, model/adapter provenance, token/cost/failure metadata, cited challenges, disposition and human reviewer outcome.
- Provider independence: NO_AI fallback and LUNA/TERRA/SOL are governance classes, not guaranteed API model names. If provider is unavailable, mark adversarial work INCOMPLETE/HOLD and do not treat a single primary pass as dual review.
- Attack checklist: source authenticity/scope; counterevidence; missing/negative evidence; temporal/operative-version confusion; calculation/identity reconciliation; incomplete source coverage; language overreach; contradiction preservation; suppressed/revoked sources; professional-boundary violations; prompt injection embedded in records.
- Fresh Eyes independence: seal snapshot and perform independent reconstruction **before** exposure to original conclusions where policy requires it; actual human review remains separate from model-model challenge. Honor any existing cooling-off and reviewer separation policy.
- UI: Case > Review > Adversarial Pair, including run state, supported sources, primary reasoning, challenges, conflicts, unanswered questions, cited evidence and a mandatory human decision record.
- Never route private DOMUS memory into this institutional case workflow. DARI personal collaboration preference is not an evidentiary fact.

### Minimum release tests
1. Authenticated permitted analyst can initiate only for assigned case; other-case, Client, inactive and unassigned identities are denied.
2. Identical version-pinned source snapshot serves both agents; independent source-only challenge stage executes before comparisons and can identify planted contrary evidence.
3. Unsupported inference is challenged, remains unpromoted, and appears in report limitations/missing evidence.
4. An obviously conflicting record remains a conflict after both models agree to ignore it (agreement ≠ factual evidence).
5. Source revocation, revised material, stale evidence, new source version or snapshot mismatch forces HOLD/re-run.
6. Provider outage, token quota and timeout fail closed without inventing dual-review completion.
7. Human Fresh Eyes/QA and publication approvals cannot be self-signed by AI or skipped through Owner override.
8. Cost and time budgets are enforced; full traceability plus correction/replay is verified with actual source IDs and cited exhibits.
9. One synthetic adversarial suite and one real authorized normal client case demonstrate end-to-end review/persistence before V1 production authorization.

## 2. Professional Handoff Capsule — V1 mandatory

### Purpose
Produce a **controlled professional-ready package** so a verified external attorney, CPA, financial advisor, investigator, insurer, HR reviewer, CFO or consultant receives exactly the authorized materials required to understand the reconstructed record, its limitations and outstanding professional questions—without mistaking ColettiOS work for professional legal, accounting or other regulated determinations.

### Capsule content (scope by engagement and permission)
- Matter/case overview and engagement scope, recipient and client-directed purpose.
- Definitive released report/snapshot ID, version, approval provenance and checksum.
- Controlled source manifest and **Evidence Passport** references with case-scoped human-readable exhibit labels; original source SHA-256 remains protected internally. Short fingerprint/reference tokens are not full verification.
- Reconstructed chronology with dates and time-zone conventions.
- Findings and Proof/Disproof Matrix, contradiction register, missing-documentation register and unresolved questions.
- Record State labeling and limitations/coverage statement; explicit third-party assertion / client assertion distinction.
- Reviewer history (authorized professional-safe summary, not confidential internal staff discussions), Fresh Eyes/QA release status and specific First Truth boundary notice.
- Referral questions / requested professional determination kept separate from Coletti & Co.'s own record findings.
- Minimal appropriate source package: only specifically permissioned files, redacted/sanitized where required, never all-case material by default.
- Recipient identity, authorized communication channel, one-time/expiring least-privilege access, download/revocation/reissue log.

### Delivery contract
- **Client-first default**: a finished approved deliverable may go to the authorized Client without external professional involvement.
- Sending to a third-party professional requires **explicit case-specific Client instruction/authorization**, verified recipient identity/contact, approval of the exact released version and the allowed file subset. A referral is optional and never a prerequisite for client delivery.
- DARI may **assemble a draft capsule**, detect missing metadata, flag scope/consent defects and prepare a transmission checklist; it may not choose an outside recipient, authorize a disclosure, send unapproved files, render a regulated professional conclusion or silently bypass a hold.
- Hand-off actions must write exact actor, time, linked client/case, report snapshot ID, recipient, consent record, channel, attachment/source subset, provider transmission status, access expiry, revoke/reissue and audit event.
- Delivery attempt, provider-delivered, recipient-accessed and recipient-acknowledged are **different events**; do not claim recipient acceptance from an email service status.
- Supporting secure transfer must enforce expiring signed links, no anonymous listing, single-purpose access credentials where appropriate, malware/quarantine and unauthorized access rejection.

### Minimum release tests
1. Client's own approved report delivery succeeds **without** outside professional consent.
2. Unauthorized third-party referral/download/transmission is blocked even when a recipient email is provided.
3. Wrong recipient, wrong client/case, wrong document version, changed approval state or unsupported source are denied.
4. Signed link expires as designed; access revocation and reissue work; downloads and denial events are auditable.
5. A properly authorized professional receives a version-fixed, appropriately redacted capsule and sees correct First Truth disclaimers and unresolved questions.
6. Capsule checksum, controlled manifest, evidence references and audit events reconcile to the immutable approved report snapshot.
7. No AI/human bypass of qualified-professional determinations; professional opinions are external recipient decisions, not Core conclusions.
8. Portal/Resend events, correspondence retention and provider failures are reconciled; no false 'sent', 'delivered', 'read' or 'accepted' claim.
9. Human-reviewed, actual permitted case and recipient acceptance is required before external-client production promotion.

## 3. Dependencies and ownership

- **DARI runtime:** two authorized independent reasoning passes; source snapshot/immutability; run and comparison records; model budget; reliable failure/retry; UI for review; full independent human QA chain.
- **ColettiOS Core:** First Truth; 10 Record States; Evidence Fitness IMP-118; source provenance/fingerprints; temporal case reconstruction; Record State and contradiction rules; case-scoped source citations.
- **Delivery:** Professional Independence/Handoff policy IMP-011; Client-First Delivery IMP-013; eight approved client deliverable components, with contract-specific variation; Communications Fabric IMP-145/153; private bucket signed URLs; external recipient consent and identity; audit trail.
- **Identity:** case membership, assigned reviewer, authorized Client, optional separately verified professional recipient; no employee scope expansion.
- **Dispatcher:** review-required HOLD and task routing, SLA timers and notification, owner exception only when decision authority genuinely required.

**Meaning of mandatory:** These two are explicit V1 release dependencies under the user's *expanded unified* scope; if not accepted, that release is **BLOCKED** rather than described as fully complete. A narrower separate client-only launch would need a new explicit scope-and-authority decision; it is not assumed.

## 4. Release evidence to attach

- Exact Core/commercial Git commits and migrations; tested provider integrations and permissions.
- Synthetic attack fixtures and genuine authorized case review traces.
- Independent human sign-off, case/source/approved snapshot IDs and protected-state results.
- Successful client-only and authorized third-party handoff, plus intentional unauthorized/expired/revoked attempts.
- Immutable output manifest and hash/reissue/retention traces.
- No false promotion: stage from Designed → Coded → Data Wired → Permission Tested → Drill-Through Verified → Cross-Interface Verified → Golden Path Passed → Messy Path Passed → Operational.

**Approval:** User explicitly stated October 12, 2026: "This have to be added to the v1 — DARI Adversarial Review Pair; Professional Handoff Capsule." This is a V1 **scope override** only; not production activation.
