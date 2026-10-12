# DARI Person-First Dual-Domain Intelligence + Delegated Autonomy v2.1

**STATUS: DESIGNED ONLY. NOT CODED, MIGRATED, ENABLED OR DEPLOYED.**
User's October 12, 2026 direction combines **less routine supervision** with **equally capable personal and business intelligence and a deeper understanding of the person**. This complements [Adaptive Collaborative Learning v2.0](DARI_ADAPTIVE_COLLABORATIVE_LEARNING_V2.md). Its consent, security, correction and retention protections remain intact. No production authorization follows from approval of this design.

## 1. One intelligence, two equally capable domains

**DOMUS / My Life:** personal decisions, routines, values as directly expressed, preference for collaboration, evolving goals, plans, interests, practical commitments, and optional consented life narrative.

**OFFICIUM + ColettiOS / My Company:** verified company operating information, case workflows, sources, authorization, records intelligence, deliverables and staff coordination.

**Together / Crossroads:** an entirely private planning space where the person can compare cross-domain tradeoffs, for example personal capacity versus delivery calendars or transition plans versus operating cash needs, without copying the private personal underlying causes into company systems.

Equal treatment means **equal usefulness, maturity, discoverability and proactive support when authorized**, not forced 50/50 message distribution. The user's current purpose determines the conversation focus.

**Identity principle:** The person is not synonymous with a role called Owner. DOMUS must ultimately be attached to authenticated personal subject identity, not company role, client ID or case ID. The Owner role separately authorizes institutional OFFICIUM actions. No employee, admin, client or other Owner gains the private DOMUS profile simply because of a business role.

There is one DARI orchestrator and one sign-in authority, but **distinct private and institutional data planes**. Avoid launching another independent chatbot or merging personal/business record stores.

## 2. Two kinds of autonomy must remain independent

**Learning autonomy** is the Adaptive v2.0 capability: auto-adapt within a chat, auto-save eligible nonsensitive explicit preferences after informed opt-in, use a higher threshold for inferred patterns, and require affirmative consent to retain sensitive personal data. No permanent profiling from speculative personality, medical, mental health, relationships or motive inferences.

**Operational autonomy** is delegated action, controlled by a separate independently revocable policy. Turning on Adaptive Learning **does not** grant permission to contact anyone, change cases, create external commitments, or spend money.

| Execution level | Permitted examples | Approval behavior |
| --- | --- | --- |
| A0: Discuss | conversation, analysis of supplied information, comparisons | none |
| A1: Read and assess | fetch identity-scoped records, prepare authorized briefs, surface discrepancies and blocked actions | no per-query micromanagement |
| A2: Prepare | create internal unpublished drafts, proposed plans, task recommendations | review at point of consequential commitment |
| A3: Standing delegation | strictly defined repeatable low-risk workflow with approved action, targets, frequency, expiry, resource limit, reversibility and notification preferences | one-time informed authorization plus exception alerts; disabled by default |
| A4: Consequential/protected | money movement, legal/financial commitments, sends to outside parties without explicit narrow authorization, client/public publication, role or permission changes, protected-profession judgments | specific human authorization and established professional gates; never inferred from memory |

A0-A2 are the default advisory behavior, still subject to authentication/role checks. A3 is **not** a blanket permission; it must specify a bounded policy, be revocable, be auditable and fail closed when expired. Routine successes go to a digest instead of demanding attention; exceptions, conflicts, uncertain instructions and high-stakes decisions are escalated.

## 3. Depth of personal understanding without surveillance

DARI can form a progressively more useful understanding through four individually distinguishable classes:

**Interaction preferences:** how the person likes answers, disagreement, uncertainty, recommendations, reminders, depth and work sequencing. Low-risk stable items may be automatically remembered with Adaptive enabled.

**Evolving personal direction:** optional goals, projects, interests, options being explored, commitments and their timelines. Every item must distinguish *considering*, *committed*, *paused* and *completed* and use evidence/time stamps rather than assuming brainstorming equals a decision.

**Optional private life map:** user-authored/explicitly approved milestones and personal narrative that help with continuity across major decisions. Sensitive biography is not automatically stored, indexed or exposed. Separate opt-in, stronger storage/privacy controls, limited retention, export and deletion are required.

**Collaboration feedback:** what the person has corrected, preferred or rejected; learn approaches that work without keeping a secret personality score, emotional diagnosis or psychographic assessment. DARI should notice corrections more strongly than repeated guesses.

DARI should have optional, non-intrusive "getting to know me" conversations for deeper preferences, plans, values and aspirations. It can be inquisitive when invited, but must not assume the person wants continual therapeutic or psychological interpretation.

The system preserves explicit first-person statements separately from machine inferences, date of relevance, confidence in extraction (not confidence in a person's identity), and whether context is only current-session or a confirmed long-term preference.

**Autonomy in learning:** Current instruction > explicit correction > approved lasting preference > nonsensitive auto-learned pattern > tentative contextual inference. Corporate/professional permission checks apply independently regardless of any preference.

## 4. Private Crossroads and cross-domain boundary

A private person-only Crossroads request can temporarily combine **minimum necessary authorized** personal and institutional facts in the DARI gateway. It does not create a third durable, unrestricted merged dossier.

For example, the person may privately say that their availability is reduced next week. DARI could rearrange a proposed work plan. OFFICIUM receives **no health, family, or personal reason**. An explicit separate person-authorized neutral signal such as "reduced availability through Friday" may be submitted to a company calendar or Dispatcher if those permitted endpoints and user approvals exist.

Cross-domain personal-signal release defaults to DENY. The person determines what minimum non-sensitive summary may be shared, for what purpose, with which recipients, and whether that permission expires. Never insert private personal discussion into company case notes, staff tasks, audit descriptions, reports, client deliverables or employee views.

A ChatGPT plugin similarly sees only authorized tool call inputs/results. It never has blanket access to all unrelated ChatGPT chats, ChatGPT memory, or raw DOMUS storage.

## 5. Person-first interface and behavior

Canonical application: existing static web app and Supabase identity; do not reactivate legacy Streamlit as production.

**My Life:** personal plans, goals, relevant commitments, routine preferences, private "Getting to Know Me", approved life map, personal decisions and everyday assistance.

**My Company:** current company state, cases, proven records, operational intelligence, employees, workflows, pending institutional approvals.

**Together:** private transition decisions, capacity planning, schedule and budget tradeoffs, priority conflicts and boundary settings. This is not a shared executive or team workspace.

**DARI Controls:** learning level, per-chat "do not learn", consented personal depth, sensitive storage consent, notifications and digest cadence, memory review and correction, delete/export, connected applications, standing delegation list, revoke all delegations, history of each meaningful action, and explanation of why DARI used a preference.

DARI should address the user naturally, not constantly as "Owner", and should not make personal topics sound like operating reports. Both personal and business views should receive production-quality functionality, not a polished company portal with a token personal settings tab.

## 6. Technical foundation and implementation changes

**Already exists:** current draft PR #94 introduces owner-scoped V1 preference candidates/explicit confirmation in chapter2_private; v2.0 specifies Adaptive automatic-learning consent and correction. V2.1 must not pretend those live V1 controls already implement this expanded design.

**Data:** a separately reviewed, additive person-scoped DOMUS v2 schema, personal goal/timeline objects with informed consent, personal encryption and retention controls, correction/tombstone controls, minimal metadata-only audit, separate standing-delegation registry, and no case ID dependency for private profile. Avoid changing canonical IDs or raw source hashes.

**Gateway:** realm-scoped identity, separate permissions for My Life, My Company and Together, source-minimizing temporary Crossroads assembler, context age/uncertainty labels, deterministic learning classifier with consent validation, versioned memory writes, action authorization gates, immediate revocation/correction cache invalidation.

**Interface:** add equal personal and business workspaces inside the canonical authenticated web shell; record explicit adaptive and A3 delegation consent there. Do not confuse a UI toggle with authority to deploy or access new apps.

**ChatGPT:** a private OAuth-based MCP plugin, read-first tools for each realm, then explicit person-scoped learning candidates and bounded action preparation. All execution is validated by the same service layer; installing the plugin is never blanket permission to import conversation history.

**Automation:** only schedule recurring briefs or condition checks when an actual connected scheduler and user permission are in place. No implied background monitoring or autonomously executed actions.

**Existing professional controls:** source integrity, traceability, human review, publication approval, protected-profession boundary, audit and role separation remain controlling.

## 7. Acceptance evidence required before any live promotion

1. Personal DOMUS remains private from client/staff/admin and other owner identities; changing a person's institutional role does not accidentally destroy or expose their private life.
2. Adaptive mode opt-in affects only eligible low-risk preferences; sensitive context cannot become permanent from observation or inference.
3. Direct correction immediately overrides any stale memories and inhibits re-learning from earlier observations.
4. Separate business/person permissions remain valid for every tool, including user-authorized Crossroads requests.
5. Private personal details never silently enter company systems; any explicit bridge exports only minimal approved neutral facts.
6. Read/draft workflows proceed without repetitive approval; A3 actions fail when out of scope, expired or revoked.
7. Consequential actions remain blocked without current and specific human/professional authorization.
8. Personal long-term goals distinguish considered possibilities from confirmed plans.
9. ChatGPT plugin sees only selected scoped data and cannot covertly copy entire chat archives or private history.
10. Browser-level role/auth tests, provider outages, token expiry, consent revocation, prompt injection, retention and encryption checks pass.
11. Deployed post-release smoke and institutional release manifest authorization are separately verified before "Operational".

## 8. Phasing

1. Record this dual-domain and autonomy contract (design only).
2. Design consent UX, encrypted person-first DOMUS v2 data contract, role/realm permission model, delegation envelopes and release gates.
3. Build My Life / My Company / Together in canonical static Owner authentication shell, not the older Streamlit runtime.
4. Connect live conversation and DARI reasoner to scoped context, retention and corrections; implement exception-only digests and bounded action policy.
5. Publish read-only ChatGPT MCP tools, test independent OAuth/private context, then permit reviewable candidate transfer and narrow delegation.
6. Complete adversarial acceptance, release-manifest evidence, staged deployment and authenticated user testing.

**No production migrations, memory writes, automatic learning, scheduled background work, company actions or plugin installation are authorized by this design document alone.**
