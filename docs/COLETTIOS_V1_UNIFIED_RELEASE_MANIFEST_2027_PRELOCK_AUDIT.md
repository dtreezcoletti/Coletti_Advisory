# ColettiOS V1 Unified Release Manifest 2027 — Final Pre-Lock Audit

**Audit snapshot:** 2026-10-12, America/Chicago
**Document state:** PRE-LOCK PROPOSAL / EVIDENCE GAP REGISTER. **NOT THE AUTHORIZED PRODUCTION RELEASE MANIFEST.**
**Target:** 90 days without planned feature development, with an extension to 180 days if production stability and support reserves permit. Security patches, provider compatibility updates, and incident fixes remain allowed.
> **Mandatory scope change — October 12, 2026:** DARI Adversarial Review Pair and Professional Handoff Capsule are no longer deferred. Both are required and blocking in the expanded **ColettiOS Unified V1 2027**. This changes only the release *requirements*, not the live implementation or production authorization. Their [technical and acceptance specification](DARI_ADVERSARIAL_REVIEW_PAIR_AND_PROFESSIONAL_HANDOFF_CAPSULE_V1_ACCEPTANCE.md) governs implementation, tests and sign-off.

**Controlling rule:** Existing Supabase release COLETTI-2026-09-24-008 is OWNER_ONLY_PRODUCTION, not external-client authorization. No registry release row, production flags, DNS, billing credentials, deployments, or protected user privileges are changed by this document.


**Capacity and continuity addendum (2026-10-12):** [Human labor, solo case capacity, case complexity and subscription-independent DARI](COLETTIOS_V1_2027_CASE_CAPACITY_LABOR_AND_CHATGPT_CONTINUITY.md). This now uses the Owner's controlling **45-hour workweek**, **28 founder hours per standard case** and approximately **117 founder case-production hours/month**, with three standard cases/month as the sustainable planning target and four as a fragile mathematical ceiling. Independent human QA is budgeted separately; all capacity and turnaround remain unproven until real-client acceptance. It is part of the pre-lock evidence plan, not permission to promise external delivery dates or activate services.

> **Identity and departmental scope clarification — October 13, 2026:** [Departmental ownership and identity-scoped DARI contract](COLETTIOS_V1_2027_DEPARTMENTAL_OWNERSHIP_IDENTITY_SCOPED_DARI.md). DARI is **not Owner/staff only**: each authenticated Owner, Executive, Admin, employee, assigned contractor, client or specifically authorized outside professional receives only capabilities and data appropriate to their actual roles, case assignments, privacy consent, and purpose. The proposed receptionist is simply **Reception & Communications**; retire the unused ATRIUM name. Departments are accountable business units **served by DARI**, not separate AI apps or subordinate identities. This is **design only**, not a live access change.

## 1. Scope and precedence

One authoritative Supabase data and identity plane; one canonical browser application (Coletti_Advisory/web); private ColettiOS methodology/runtime; DARI as governed personal/business collaborative intelligence; Dispatcher as deterministic scheduler and work enforcement; approved provider connectors; a bounded-agent execution layer; versioned policies, staff roles, case assignments, and owner-controlled release.

The program governs two source repositories plus the institutional Registry/Dispatcher database and deployment manifest. A single canonical deployed application does not require a single Git repository.

The owner wants fewer micro-approvals, deeper person-first DARI, no extra login, and equal personal/business intelligence. These are design goals; the current draft DOMUS V1 is confirmation-only and Owner-role scoped. Adaptive v2/v2.1 remains design-only.

**Preserve explicit supersessions:** Commercial IMP-184 v3 is canonical Coletti & Co.-only scope, superseding IMP-167 mixed 60-SKU/Shopify plan and IMP-036. Consumer Shopify ventures and clothing are **outside the client-production critical path**. Old launch topology IMP-125 and old historical-promotion rows IMP-126–134 require supersession/retirement, not reimplementation. IMP-014 external notification architecture was tabled; this audit reopens it for DESIGN RECONCILIATION ONLY, not unauthorized production sends. IMP-012 has only **two** still-deferred differentiation upgrades after the Owner explicitly required DARI Adversarial Review Pair and Professional Handoff Capsule for Unified V1.

## 2. Evidence snapshot, not operational inference

Source: live Supabase Colettico project, connected Resend, GitHub canonical repository and issue state, connected platform account inspection on 2026-10-12.

- Supabase extensions installed: pg_cron, pgmq and pgcrypto; **one** active cron job named queue-operational-brief-emails-v1, every ten minutes. 1,008 scheduler runs succeeded over the previous 7 days. **Zero** operational_email_runs records at inspection. Successful cron execution is not email delivery.
- Dispatcher hourly_reconciliation_reports: **31 rows**, latest created October 5, 2026. Dispatcher jobs: **0**. A live universal owner-configured monitoring and alert lifecycle is NOT verified.
- Supabase Registry implementation_matrix: **117 rows**, 36 marked OPERATIONAL, 14 VERIFIED, 41 IMPLEMENTING, 26 APPROVED. These are ledger states, not independent end-to-end production acceptance.
- Supabase 1 Registry case (known synthetic), 0 Evidence Fitness assessments, 0 QA checklists, 0 publication handoffs, 0 published reports, 0 payment-provider events, 0 consultation notifications, 0 operational-email runs. Zero real external-client case acceptance demonstrated.
- Auth/Profile: 3 profiles, 2 active Owner and 1 active Client; 0 active staff.
- Provenance method tables: 9 Evidence Passport records, 9 methodology candidates, 7 propositions, 1 contradiction reconciliation, 0 reviews, 0 source_versions, 0 source_snapshots, 0 methodology_versions. Data existence is not universal live-case runtime proof.
- Client messages: 1 portal_messages row; transactional email integration end-to-end not demonstrated.
- Resend: verified sending domain colettico.com; receiving disabled, zero webhook registrations; **10 published templates**, including **four added October 12, 2026**: consultation confirmation (`coletti-consultation-confirmed`), engagement onboarding (`coletti-engagement-onboarding`), verified payment action (`coletti-payment-action`) and authorized professional handoff (`coletti-professional-handoff`). Earlier six: account/security, portal messages, records-action, report-ready, billing event, operational exception. **Publication is not event wiring or delivery acceptance.** Do not change MX to Resend: IMP-162 requires MOP-EMAIL-001 for separate human mailbox.
- Cloudflare prior account inventory: active zone but no Workers/Pages deployment; Render still hosts static and Python services. No verified Render database-to-Supabase Core cutover or clean backup. Render expired/suspended database requires preservation determination before service retirement.
- GitHub core master issue #52 and commercial IMP-118 acceptance issue #93 remain open; DARI draft PR #94 not merged. Existing website README defines canonical /login/ and /workspace/ routes; Streamlit Owner generations are legacy, not an alternative official portal.

Source records:
- https://github.com/dtreezcoletti/ColettiOS/issues/52
- https://github.com/dtreezcoletti/Coletti_Advisory/issues/93
- https://github.com/dtreezcoletti/Coletti_Advisory/pull/94
- Commercial docs/OPERATIONAL_LIFECYCLE.md
- Commercial docs/CLIENTS_OPERATING_SPEC_v1.md and docs/CLIENT_LIFECYCLE_SOP_v1.md

## 3. Final scope categories

### P0 — Required to authorize any external-client V1

A. **Preservation, deployment and recovery:** version-pin main and migrations; preserve/export or formally disposition any unique Render Postgres data; Cloudflare preview, actual DNS/SSL cutover and rollback; one Python Core execution arrangement; backup and actual restore drill; secret/credential rotation; incident response; failure/queue traces. No legacy fallback secrets left after cutover.

B. **Identity and permissions:** Supabase sole Auth; email and password reset, magic links, inactive/revoked sessions; deliberate second Owner disposition; functional Owner / Executive / Admin / Employee identities and distinct case positions with real authenticated positive and negative tests. Minimum necessary access. Owner override never bypasses First Truth/review/publication.

C. **Golden Path:** lead/referral -> consultation -> qualification -> accepted Client identity -> proposal/controlled contract -> payment condition -> case open exactly once -> eligible staff assignment -> file upload and source registration -> case reconstruction -> QA/Fresh Eyes -> human approval -> 8 approved deliverables, or contracted subset -> permissioned delivery -> retention/retainer and closeout. Messy-path tests: duplicate booking, disputed source, cross-case request, revoked person, missing source, partial outage, duplicate webhook, ineligible employee, expired link.

D. **Client communications minimum:** working two-way private portal message threading and real human mailbox; Resend transactional sending, signed event webhooks, delivery/bounce/failure readback; accurate notification-vs-acknowledgement semantics; calendar confirmations; preference and quiet-hour controls; retries and dead-letter behavior; client/private-case separation.

E. **Evidence methodology:** all 15 IMP-118 dimensions and First Truth proof tested on real authorized source workflow, original bytes in commercial encrypted storage, hash/version/case-scoped fingerprint continuity, untrusted source quarantine, record-state integrity, controlled inference, reproducible report snapshot and signed delivery. Production cannot rely on synthetic fixtures alone.

F. **Operations:** functioning Dispatcher scheduler, staff assignment/deadline thresholds, escalation and queue recovery; one authoritative status table and drill-through controls; scheduled email briefs with delivery proof, exception routing and human fallback.

G. **Release and security:** production RLS/SECURITY DEFINER actor tests, original Git history/privacy disposition (IMP-090 and open issue #15), accepted risk register including leaked-password protection deferred pending Pro (IMP-161), confidentiality/retention/legal-hold and client/consumer policies, data deletion/export, observability and runbooks, CI and independent user/browser acceptance, release manifest signed to exact SHAs/migrations/versions/provider scopes.

### P1 — Required only if Owner chooses **fully unified DARI V1** rather than external-client V1

- Canonical **identity-scoped DARI** in the role-filtered web workspace (not Streamlit): Owner, Executive, Admin, Employee, assigned contractor and Client each have their *separately permissioned* DARI experience; verified outside professionals have handoff-only permitted assistance. The Owner's private DOMUS remains person-scoped, not role-shared. Other personal-profile access requires separate opt-in/privacy design. Live OpenAI backend, provider budgets, Adaptive consent, corrections, encrypted private profiles and strict OFFICIUM boundary remain required.
- Scoped, authenticated ChatGPT OAuth/MCP plugin with minimum read-only tools, explicit opt-in selected-chat handoff and separation of personal/business grants. No passive full ChatGPT synchronization.
- Six internal DARI specialist capabilities: Personal, Intake, Records, Quality, Report and Operations intelligence; one Dispatcher instead of separate competing agent schedulers. Do not add six user-facing apps.
- **MANDATORY V1 scope override, October 12, 2026:** DARI Adversarial Review Pair (independent Primary/Challenge source-bounded reasoning and human-reviewed disagreement matrix) and Professional Handoff Capsule (recipient-verified, client-authorized, exact-version source/evidence/review/limitations package, expiring access and audit) are REQUIRED for the expanded unified V1. See [dedicated V1 acceptance contract](DARI_ADVERSARIAL_REVIEW_PAIR_AND_PROFESSIONAL_HANDOFF_CAPSULE_V1_ACCEPTANCE.md). Both block full Unified V1 promotion until accepted.
- A0 discuss, A1 read/assess, A2 internal draft by default; A3 per-action bounded standing delegation only after explicit approval; protected decisions/publishing never inferred from memories. Run tracing, tool ACL, retries, idempotence, exception escalation, cost ceilings, prompt-injection tests.
- Client and staff experience must not be held hostage to optional personal AI if Owner narrows external-client release scope. If all-inclusive freeze is mandatory, these become explicit P0 dependencies with corresponding schedule/financial consequences.

### P2 — Explicitly evaluated but default deferred unless vital for a P0/P1 workflow

- **Only TWO IMP-012 upgrades remain deferred:** Claim-Level Model Consensus Ledger and Temporal Intelligence / "What We Knew Then". DARI Adversarial Review Pair and Professional Handoff Capsule have been **explicitly added as mandatory V1 requirements** on October 12, 2026. Evidence Passport and Case Time Machine remain selected V1 requirements, with normal-path and timezone/version replay acceptance still required.
- Advanced animated Case Map; speculative automated document discovery; industry-specific verticals; multiple independent LLM frameworks; consumer Shopify apparel and unrelated ventures; new separate portal or authentication; voice telephony/recording, two-way SMS/WhatsApp; native apps; speculative AI autonomy. Make interfaces extensible without a promise of features not accepted.
- IMP-088 Dispatcher QoL Control Pack: currently APPROVED without observed operational detail; inventory against required UI features and explicitly INCLUDE or DEFER, never silently claim included.
- IMP-123 18-area institutional closure: reconcile exact source records and 18-to-implementation mapping. Prior retrieved work tree of 16 stages is not automatically an exact substitution for the 18-area program.

## 4. Monitoring and scheduling — Monitor Center V1

**Current status:** pg_cron available, one active operational-email queue scheduler, Dispatcher job/approval tables, no evidenced general Owner-created Monitor Center.

**Architecture:** one authoritative monitor_rules table plus monitor_runs, monitor_observations, monitor_alerts, monitor_subscriptions and monitor_deliveries (names provisional, version via additive migration). Dispatcher reconciles and owns timers; Supabase pg_cron invokes a small recurring dispatcher; pgmq/queue-backed workers handle checks; incoming signed event webhooks take precedence over polling. Do not create one pg_cron job for every logical monitor. Do not introduce a second independent authority for work-state.

Rule fields: unique monitor ID; domain DOMUS/OFFICIUM; Owner/user or case scope; verified connected source; predicate/evaluation version; evidence pointer; cron/timezone or event trigger; urgency, frequency, allowed fetch budget, cost, dedup window, alert routing, quiet hours, last check/status/change, expiry, disabled state; audit/version and explicit domain data boundary.

Operational lifecycle: DEFINE -> AUTHORIZED -> ENABLED -> DUE -> CLAIMED/LEASED -> FETCHED -> NORMALIZED -> EVALUATED -> UNCHANGED or CHANGED/ERROR -> ACTION QUEUED -> SENT/DELIVERED/ACKNOWLEDGED -> RESOLVED; timeout, backoff, dead-letter, pause, safety stop and idempotent retry. Delivery and acknowledgement must be separate.

Suggested capacity commitments:
- **V1 target: 250 configured active monitor rules**, not a verified limit or a provider guarantee.
- **V1 capacity test: 1,000 configured rules**, with actual sustainable rate determined by sources, network/API quotas, cost and processor/DB performance.
- With 250 rules evaluated every 15 min, 24,000 evaluations/day: load-test, do not promise. Most provider events should be webhook-based, internal checks run deterministically and AI only activates for changed/complex exceptions.
- Urgent source with supported event webhooks: process as events (latency SLO set per provider). Operational exceptions: 5–15 min evaluation; ordinary cases: hourly; trend/quality: daily or weekly. Low-value unchanged checks should produce no owner alert.
- Alert fatigue: dedupe, severity thresholds, owner quiet hours, rate caps, digest, suppression, escalation, auto-close/reopen, evidence/source drill-through, notification failures and coverage gaps.
- Categories: case deadlines / incomplete records / source-version conflict / staff assignment and SLA / finance and receivables / booking and payments / inbound/outbound communication / website and authentication / service health, queues, storage and backup / policy drift, CI and integration token expiry / owner-consented personal reminders.
- Never promise ongoing monitoring of Gmail/Calendar/third-party systems until the specific account's authorization, quota and actual ingestion or webhook path are proven.
- Budget limits: daily provider request ceilings, AI token/cost budgets, queue-depth thresholds and kill switch.

Reference official docs: https://supabase.com/docs/guides/cron ; https://developers.cloudflare.com/workers/configuration/cron-triggers/ . ChatGPT Plus task cap is separate and does not constrain ColettiOS rule counts.

**Acceptance:** owner creates 20 diverse real rules in UI; event and scheduled checks; no more than one alert for duplicate signal; unauthorized cross-client and DOMUS access denied; expired/revoked token fails closed; webhook signature/replay rejection; outage/retry/recovery; simulated 250/1,000-load benchmark; system restarts without losing queued work; alert delivery and acknowledgement separately recorded; owner digest excludes unchanged records.

### V1 template activation and provider status — October 12, 2026

All four new Resend templates were **created and published**. They have **not been bound to authenticated application triggers or tested through actual provider deliveries**. Publication itself sent zero emails.

| Resend alias | Exactly when it may send | Approval / safety gate |
| --- | --- | --- |
| `coletti-consultation-confirmed` | Square-origin appointment actually confirmed and reconciled with Calendar | Signed/replay-safe booking event, correct date/time/timezone; no optimistic confirmation |
| `coletti-engagement-onboarding` | Human-accepted Client with onboarding portal and controlled requirements ready | Do not claim contract signed, payment complete or Case active until separately verified |
| `coletti-payment-action` | Authoritative account ledger identifies an actually outstanding or failed payment needing action | Reconcile in-flight/recent payment; deduplicate; do not incorrectly demand a second payment |
| `coletti-professional-handoff` | Client-directed recipient permission, fixed approved report/capsule and secure access already established | Explicit disclosure authorization and recipient verification; do not attach confidential case materials to transactional email |

**Shared preconditions:** sanitize and allowlist `PORTAL_URL` to an approved authenticated domain; escape and validate all user-derived template variables; use idempotency per business event, case/recipient scoping, provider message ID and delivery/bounce/failure webhook reconciliation. Address incorrect/expired/deactivated recipients and consent/quiet hours. Sending domain is verified but Resend receiving and webhooks are unconfigured. No actual client communication is operationally proven by these template publishes. Full acceptance requires actual test events with negative role tests, no duplicate sends and audit readback.

## 5. Communications Fabric — channel and identity contract

**Additional October 2026 scope:** [Issue #96 — recipient-specific viewed/acknowledged receipts, full populated template previews, optional DARI personal notes, and three-way business phone/SMS/voicemail provider comparison](https://github.com/dtreezcoletti/Coletti_Advisory/issues/96). These are acceptance requirements or provider decisions only; no live message tracking, phone number or DARI send authorization is implied.



**Canonical communications model:** conversation/thread -> message/event -> actor/channel/domain/case relation -> outbound submission or inbound verified receipt -> delivery/status event -> read/acknowledge (when genuine) -> correspondence retention and authorized legal hold -> case/client timeline, activity index, reply or follow-up Dispatcher job.

**HUMAN MAIL:** IMP-162 specifically proposes Lark mailbox cutover MOP-EMAIL-001 for the business identity. Test identity, login, mailbox access, existing mail preservation, SPF/DKIM/DMARC, MX cutover, sender and reply-to, incoming replies, forwarding and disaster fallback. Do not change MX blindly or confuse Resend receiving (currently disabled) with a human mailbox.

**TRANSACTIONAL EMAIL:** Resend sending verified, six published templates; no webhooks yet. Configure delivery, bounce, complained, failed, delivered and retry events. Store provider event ID, status, timestamps, idempotency key, recipient, email classification and linked client/case/work item with minimal subject/PII. Signed event verification; no duplicate sends or optimistic delivery assertions.

**PORTAL:** private thread-per-case for client<->assigned staff, secure attachment references, role-scoped unread counts, archive, notifications with links back to canonical thread, send/edit/delete status and audit; cross-client isolation. No client content copied into personal DOMUS; messages from outside are untrusted agent inputs.

**CONSULTATIONS:** Square booking/payment, Calendar authoritative availability/invite, email confirmation and reminders, conflict/cancellation/timezone/reschedule, duplicate callbacks and payment reconciliation. Full initiation through completion, not merely a scheduled event.

**STAFF/OWNER:** role-specific in-app inbox, exception queue, operational briefs, assignments, approvals, follow-up tasks, fallback when Resend fails. Distinguish Owner/Audit vs institutional alerts and personal reminders. Quiet hours, acknowledgement timers, escalation paths.

**REFERRALS / CUSTOMER SUPPORT:** referral intake and professional handoff recipient verification, consent to share report, outbound no-send-until-approved; website contact and support ticket -> Owner/Admin queue -> status and SLA; email-to-task integration only after hardened sender trust, verified signature, tool-scoped processing and prompt-injection isolation. Do not let untrusted email issue agent commands.

**CHANNELS:** Required V1 = human email + transactional email + secure portal messaging + authenticated calendar + in-app alerts. Provider-neutral interfaces may reserve SMS, push, telephone, WhatsApp, social DMs as future adapters. Activating those requires separate provider, verified opt-in/opt-out/quiet-hours/legal review and acceptance; no phantom integrations.

**Acceptance:** real sent and received tests; reply and threading; signature/delivery/retry/dead-letter; staff/client same message views within scope; untrusted email cannot trigger protected action; expired token / malicious attachment / unavailable provider tests; no false 'sent' claim; backup and replay.

## 6. Core methodology pre-freeze verification

Preserve Core as **generalized provenance-first reconstruction**, not an AI-generated conclusion engine. Record States are the ten canonical states: Documented Fact, Reconciliation Result, Inconsistency, Missing Documentation, Process Deviation, Unresolved Question, Client Assertion, Third-Party Conclusion, Referral Required, Identified Pattern. Source State lifecycle is separate.

Canonical source-bound ladder: Source -> Proposition -> Contradiction -> Reconciliation -> Reviewer Conclusion -> Escalation -> Audit. Independent publication approval follows; deterministic No-AI, LUNA, TERRA, SOL are reasoning classes not vendor-dependent models. First Truth blocks protected-profession determinations by the AI.

**Methodology acceptance matrix:**
1. Original source bytes, content hashes, source/case identity and immutable snapshots remain traceable, versioned and reversible at report time.
2. Distinguish document assertion, third-party assertion, direct observation, verified fact, inference and unidentified gaps. Quotes/communication timestamps need attribution and time zone handling.
3. Temporal reconstruction distinguishes event time, record-creation time, ingestion time, effective/operative date and known-at-the-time visibility. Case Time Machine must prevent hindsight contamination and enable exact replay.
4. Contradiction model preserves both claims and source citations until authorized reasoned reconciliation. Negative evidence/absence must not become fact without scope/coverage showing why expected record was absent.
5. Coverage and record sufficiency: completeness, search boundary, what is known/unknown, missing documentation register, coverage percentage only if denominator defensible, confidence labels with disclosed basis and uncertainty.
6. Canonical entity/name/alias and transaction relationship resolution; unresolved identity remains flagged; do not silently conflate people, clients, cases, duplicate records or transfers.
7. Versioned parsing, extraction, OCR and normalization (including corrupted or partial material) with source-page anchors, quality flags, human correction and reproducible reruns.
8. Source relation lineage through split/merge/transformation, de-duplication, versions, redaction and provider export; no evidence overwrites.
9. IMP-118 all 15 controls: sufficiency; description vs inference; semantic collisions; decomposed approvals; attribution; multi-dimensional reconciliation; purpose; isolation/quarantine; temporal provenance; dependency; duplicates; suppression; partial failures; provider/process tracing; revocation/reprocessing.
10. Adversarial test harness for fabricated sources, prompt-injection in external mail/files, model hallucinations, cross-tenant access, conflicting snapshots, stale evidence, wrong case ID and repeat reingestion.
11. Independent Fresh Eyes and QA separation where policy requires; no role self-sign-off, complete reviewer attribution, published fixed snapshot, change-after-approval requires fresh gate.
12. Versioned methodology and calibration governance; generalized improvements from synthetic/historical validation must pass isolated synthetic twin and reflection/approval gate, no unapproved historical writeback.
13. Eight contracted deliverable types, appropriate standalone variants, case scope, linked citations, limitations, professional handoff boundaries and rejection/reissue/revoke lifecycle.
14. Data stewardship: retention, consent, legal hold, export/erasure rules (client originals vs audit), cryptographic backup/restore and key rotation.
15. Cross-industry independence: commercial/legal-specific templates sit in authorized adapters, never inside neutral Core invariants.

**Known proof gaps:** Evidence Passport rows exist but no demonstrated real production publication; source snapshots/versions and methodology_versions currently zero; review and published findings zero; only synthetic case currently registered. Treat functional presence separately from coverage. Do not add duplicative methodology primitives when one exists but is unwired.

## 7. Previously tabled or incompletely reconciled proposals

**Must explicitly disposition before lock:**
- IMP-123 (18-area institutional operating-closure directive) and IMP-124 execution sequence: map all areas to owned implementation IDs, acceptance and status; no invented mapping.
- IMP-088 Dispatcher QoL Control Pack: determine exact functions from source documents and explicitly keep/retire/defer; no blanket 'included'.
- IMP-059 DARI Watch / Start-Resume / Preview-Undo / Correction and Secure Workbench isolated executor: verify the ordinary run path, not only merged primitives.
- IMP-156 WBA/WBS work-state semantics and work-period reconstruction: live deterministic activity capture and source linkage, no phantom ChatGPT transcription.
- IMP-158 EFFÍCIO ETOP: explicit and authorized conversation capture handoff only; ChatGPT runtime does not grant passive transcript access.
- IMP-154 Adaptive Memory architecture plus Oct 12 v2/v2.1: consent, person-first DOMUS, encryption, correction, delegation and private cross-domain context; current draft PR #94 only v1 foundation.
- IMP-145 and IMP-153 v2 Communications Fabric; IMP-162 mailbox MOP-EMAIL-001; IMP-014 tabled Dispatcher notification architecture — reconcile into ONE authoritative communication service.
- IMP-169 Square/Google master consultation acceptance; IMP-183 production closure; IMP-187 SOP; IMP-191 controlled engagement contract; IMP-184 commercial v3 propagation.
- IMP-097 traceability policy-to-code/database drift, IMP-101 temporal/generalization audit, IMP-069 First Truth, IMP-118 fitness, IMP-108 canonical IDs, IMP-129 proof/disproof matrix, IMP-110 controlled docket/document subsystem (not default general Core).
- IMP-012 six differentiated upgrades: **FOUR are now required for Unified V1**: Evidence Passport, Case Time Machine, DARI Adversarial Review Pair and Professional Handoff Capsule. The latter two are a user-directed scope override dated October 12, 2026, governed by [their acceptance contract](DARI_ADVERSARIAL_REVIEW_PAIR_AND_PROFESSIONAL_HANDOFF_CAPSULE_V1_ACCEPTANCE.md). **Only Claim-Level Model Consensus Ledger and Temporal Intelligence / "What We Knew Then" remain deferred**, absent another explicit override.
- IMP-163 Social/Audience/Growth and founder pilot: decide minimal V1 referral/pilot conversion measurement without tying site launch to unrelated consumer catalog.
- IMP-090 public Git-history remediation and issue #15: secrets/privacy archive remediation and risk disposition.
- Owner DOMUS, PONS/PORTA, Estates General permission bridge; private founder case must not be promoted to production business records absent explicit human-controlled transfer.
- Visual Case Map and document-controlled policies/procedures/contracts: decide scope by evidence of essential workflow need, not by attractiveness.
- Existing naming/brand authority: commercial-facing Coletti & Co. must not automatically expose ColettiOS private engine/IP or protected-profession claims.

## 8. 90–180 day operating durability and cost envelope

**Must be in V1, even if unglamorous:**
- Monitoring/alert coverage and on-call fallback; service level objectives (SLO), RTO/RPO goals with proved restores.
- Provider-specific quotas and budget: OpenAI tokens/spend limits, Cloudflare requests, Supabase DB, storage growth/egress, signed links, Resend delivery quota, Square fees and refunds; billing-change alerts.
- Connection lifecycle: OAuth consent expiry, secret rotation/revoke, webhook re-registration, certificate/DNS expiry, provider outage and fallback, IdP recovery; preventive health checks.
- Work queues: idempotency keys, row locks/leases, backpressure, dead-letter, retry with bounded exponential backoff, poison-message quarantine, cancellation, replay.
- Owner absence: named staff role fallback, delegated low-risk process, approval queues with protected action hold; do not falsely use service agents as protected human reviewer.
- Privacy: data retention schedule for case/DOMUS/comms, access requests, export/deletion, email suppression/bounce, provenance of consent, breach process, logging minimization and prompt/tool-injection.
- Migration discipline: backward-compatible DB changes, migrations verified against running code, rollback tested, one source-of-truth registry, recovery proof.
- Business operational measurements: time to first response, booked consult -> accepted engagements, case turnaround, bottleneck ageing, report rework, collection/receivables, actual cost per case, staff capacity, source processing cost, referral conversion; dashboard drill-through to real objects.
- Documentation: current runbooks and SOPs for staff invitation, support, client disputes, missing records, security incident, refund/cancellation, provider outage, client offboarding, correction/reissue, data recovery.
- Consistent timezone UTC storage and local display; DST and working-hour window acceptance. Accessibility and Android/mobile/PWA realistic tests.
- Progressive rollout and feature flags. Stable freeze means no planned architectural development, not suppressing bug/security patches.

**Operational phases:** 90-day freeze begins only after all in-scope gates pass and a versioned production manifest is signed. At day 30 check error trends and finances; at day 60 check reliability/methodology drift; day 90 decide extend same version to 180 days (security/compatibility maintenance allowed) or deliberately start V1.1. No automatic extension if client safety, finances, or recovery readiness deteriorate.

## 9. Final release evidence required

For each item: ID, owner/domain, REQUIRED/OPTIONAL/DEFERRED/SUPERSEDED, current state DESIGNED/CODED/DATA_WIRED/PERMISSION_TESTED/DRILL_THROUGH_VERIFIED/CROSS_INTERFACE_VERIFIED/GOLDEN_PATH/MESSY_PATH/OPERATIONAL, current git SHA, migration version, provider/auth scope, real/fixture test IDs, pass/fail, failure policy, rollback, cost, runbook, decision record, production promotion ID.

**Hard STOP:**
1. Render unique-data preservation unknown, or unverified Cloudflare/Core runtime cutover;
2. a real human role required for verification cannot sign in or perform permitted work;
3. no real authorized case and independent reviewer/QA/publication/delivery evidence;
4. unverified emails, mailbox routing or payment webhook acceptance while sold as operational;
5. source/case cross-tenant isolation or First Truth breach;
6. missing restore/rollback proof or serious credentials/historical leakage not disposed;
7. false 'operational' promotion from a repository merge, deployed function, cron success, or table count;
8. published actions without protected human authority;
9. incomplete or untested independent DARI Adversarial Review Pair or Professional Handoff Capsule, including third-party consent, exact approved snapshot, access expiry and independent human QA.

## 10. Explicit pre-lock decisions

Proposed choices, not yet executed:

- **Monitors:** single Dispatcher Monitor Center, initial 250 rules/1,000 load-test benchmark, event-first, weekly and daily exception views.
- **Comms:** Lark human mailbox if MOP-EMAIL-001 accepted; Resend for transactional sends; Portal for case messages; Calendar master for bookings; no mandatory SMS/phone automation absent tested provider.
- **Agents:** six internal capabilities under DARI and Dispatcher, no separate applications; protected decisions remain gated.
- **DARI scope:** Owner-directed choice whether person-first cross-interface ChatGPT/MCP must block client production or be a separately versioned, private release, both recorded with no false claim.
- **Differentiation:** Evidence Passport, Case Time Machine, DARI Adversarial Review Pair and Professional Handoff Capsule are mandatory V1, subject to the exact acceptance contract. **Only two** remaining upgrades are deferred: Claim-Level Model Consensus Ledger and Temporal Intelligence / "What We Knew Then".
- **Commercial:** Coletti & Co. service/engagement workflow under IMP-184 v3; other consumer commerce separate.
- **Freeze:** 90-day observation target; conditional extension to 180 days.
- **Current document:** design/audit only, no authority to roll back, migrate, activate clients, alter DNS, configure billing/keys, send external notifications or issue new production manifest.

**This is a pre-lock disposition register and specification for the eventual ColettiOS V1 Unified Release Manifest 2027, not evidence of full implementation.**
