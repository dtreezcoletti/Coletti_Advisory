# DARI Adaptive Collaborative Learning v2.0 — DESIGN ONLY

Status: **DESIGNED / NOT IMPLEMENTED**. Owner selected **Adaptive** on 2026-10-12. This document supersedes v1's _mandatory confirmation for every preference_ as the **future intended design**, not as deployed code. Do not change `production_authorized` or the live release manifest because of this document.

## 1. Purpose and identity

DARI is a **person-first collaborative intelligence** that improves how it works with an individual. Being the business Owner is a separate technical role for authorization, *not* the full definition of the person. It assists with analysis, comparison, planning and coordination; never substitutes its preferences or learned inferences for the user's judgment.

The user stays the final authority over personal learning and consequential business actions. A memory about preferred decision support is **not** authorization to execute decisions.

### Laws

1. **Autonomy is narrow:** DARI may adapt its style and, once opt-in is enabled, retain bounded, nonsensitive assistance preferences. It may not autonomously learn sensitive private facts, change operating rules, widen privileges, or initiate protected actions.
2. **DOMUS ≠ OFFICIUM:** Personal collaboration context is stored in private DOMUS; no silent disclosure or copying into cases, employees, clients, Dispatcher, institutional truth, publication or professional analysis. The institutional source/permission system stays authoritative.
3. **Provenance with disclosure:** Learned items carry their basis (explicit user statement, repeated observation, user correction), date, scope, and confidence/consistency metadata. Do not equate inference with fact.
4. **Correction is immediate and higher priority:** Latest explicit instruction or correction defeats past preferences and automatic patterns. Revoked/deleted data must be excluded from prompts, indexes, retrieval, and future inference as soon as reasonably possible.
5. **Data minimization:** Extract the smallest nonsensitive assistance preference needed; do not store the explanatory private narrative, whole conversation, or broad character assessments.
6. **ChatGPT connection is explicit:** A plugin receives only its scoped tool inputs and authorized results. It cannot silently access or synchronize the user's entire ChatGPT conversation history or ChatGPT memories.
7. **No false production promotion:** Code, tests, deployed interfaces and operational status are separate proof gates.

## 2. Consent and default

Adaptive mode is OFF in production until a signed-in user expressly enables it in their private DARI settings. Selecting the proposed design is not data collection consent. Offer a readable notice:

> Allow DARI to save ordinary, nonsensitive collaboration preferences automatically? Sensitive or consequential information still requires explicit approval. You can pause, inspect, correct, export, or delete learning at any time.

Consent setting is owner-scoped, time-stamped, auditable (metadata-only), revocable, and must not be conflated with model training consent or access to institutional tools.

Controls: **Adaptive on/off**, **Pause learning**, **Don't learn from this conversation**, **Review learning**, **Forget this preference**, **Forget all personal learning**, **Export**, and **Last-used/why learned**. Turning Adaptive off stops new auto persistence; it does not silently destroy previously confirmed preferences. Separate control governs whether existing approved preferences are applied while learning is paused.

## 3. Four learning classes

| Class | Examples | Session behavior | Persistent behavior |
| --- | --- | --- | --- |
| **SESSION_ONLY** | Reply length, conversational tone in this exchange | Adapt immediately | No lasting profile write or cross-session access |
| **AUTO_ELIGIBLE** | Answer structure, preference for competing alternatives, familiar vocabulary, ordinary work rhythm, non-sensitive interaction format | Adapt immediately | With Adaptive consent, may save after explicit direct preference or sufficiently repeated pattern; notify unobtrusively |
| **REVIEW_REQUIRED** | Private goals implying financial/life consequences, ambiguous identity statements, inferred values or motives, personal relationship detail, health, trauma, sexuality, religion, legal/financial hardship, or anything sensitive in context | May assist in current conversation with appropriate constraints | No autonomous persistent extraction; user must deliberately opt in to a privacy-checked memory; prefer storing a sanitized collaboration preference rather than sensitive fact |
| **NEVER_LEARN_AS_AUTHORITY** | Account credentials, regulated secrets, policy/role changes, waiver of approvals, case findings, protected-profession effects, permissions, payment instructions | Never treat as standing instruction | Learning cannot enable such actions or overwrite institutional policy |

Sensitive content remains sensitive even if repeated across sessions. If classification is uncertain, choose REVIEW_REQUIRED, not AUTO_ELIGIBLE.

Prohibited profiling: do not infer diagnoses, emotions as enduring identity traits, personality labels, psychological motives, guilt, or intent from conversation patterns. DARI can follow direct user feedback without labeling the person.

## 4. Automatic learning threshold (proposed V2 rule)

- Clear **first-person, nonsensitive, stable preference** directly expressed by user ("For business comparisons, show options and tradeoffs"): may become AUTO_ACTIVE immediately if Adaptive is enabled and not contradicted.
- **Inferred preference**: no persistence from a single impression. Require repeated consistent evidence from at least three interactions across at least two separate sessions, no material contradiction, and high classifier confidence (proposed threshold >= 0.85; calibrate using testing). Observations should be bounded metadata, not a permanent cache of private utterances.
- Vague or provisional wording ("today I'd rather...") remains SESSION_ONLY.
- Direct phrase "remember this" about nonsensitive preference can go directly to USER_CONFIRMED after explicit wording, respecting the person's privacy controls; specific high-sensitivity storage still requires clear separately informed consent.
- No learning from client-supplied documents, retrieved websites, attachments, tool output, impersonated user messages, or agent-generated analysis. Only the authenticated user's own direct interaction may be a learning source.

The classifier must produce a *preference*, not a supposed truth about the user's personality. Examples:
- Good: "Show comparative options and evidence before an entrepreneurial recommendation."
- Not acceptable: "Owner distrusts relationships because of trauma."

## 5. State machine and conflict resolution

Proposed active lifecycle:

`OBSERVED_EPHEMERAL -> AUTO_ACTIVE | REVIEW_REQUIRED -> USER_CONFIRMED | REJECTED | RETIRED -> DELETED`.

Actual transitions:
- SESSION_ONLY never enters permanent memory.
- Low-risk eligible item may be AUTO_ACTIVE if consent and eligibility pass; same subject replaces or supersedes earlier item atomically.
- High-risk/ambiguous item remains outside persistent memory by default; where optional candidate storage is enabled, it must be protected, limited, and explicitly confirmed before use.
- AUTO_ACTIVE or USER_CONFIRMED may be CORRECTED, RETIRED, or DELETED at any time.
- Corrected/rejected/deleted item is excluded immediately from future DARI prompts; caches invalidated; active response may need rerun.
- Explicit correction supersedes all older auto observations about that key. Prevent automatic re-learning of expressly rejected ideas without new affirmative user instruction.
- New observations cannot silently reverse a direct user correction.

Priority: **Current direct instruction > latest explicit correction > user-confirmed standing preference > auto-learned preference > session observation > inferred pattern**. Institutional authorization/policies supersede all of these for operational action.

A versioned event stream (metadata-only) permits explaining and auditing transitions; avoid storing an unneeded copy of corrected sensitive text in the audit trail.

## 6. Time limits and quality

Suggested configurable defaults rather than unchangeable constants:
- SESSION_ONLY: current conversation, with any server cache minimized and short-lived.
- Inferred AUTO_ACTIVE: review/expire after **90 days** without reconfirming use or user endorsement.
- Explicit nonsensitive stable AUTO_ACTIVE: prompt lightweight review after **180 days** or upon contradiction.
- Candidate observation aggregate: expire after **30 days** if the threshold is not reached.
- Auto-learning weekly digest or on-demand review; *no interruptive approval pop-up per low-risk memory*.
- Notification: unobtrusive "DARI learned: [specific preference]" with Undo and Why? link.
- No automatic indefinite retention; define user-configurable retention, deletion propagation, and backup expiry policies before live activation.

Confidence is an extraction-quality signal, not a probability that a person "is" a certain way.

## 7. Private memory data contract

Keep Supabase as authority and use a private DOMUS namespace, keyed to authenticated subject identity. Do **not** expose private tables directly to browser clients or use service-role keys in frontend code.

V2 requires a **new additive reviewed database migration**; do not overload the existing `CANDIDATE/CONFIRMED/REJECTED/RETIRED` CHECK as if it supported AUTO_ACTIVE. Fields proposed:

- `learning_id`, `subject_user_id`, stable `profile_key`, short `statement`, `category`
- `classification` (SESSION_ONLY never stored / AUTO_ELIGIBLE / REVIEW_REQUIRED)
- `status` (AUTO_ACTIVE / USER_CONFIRMED / REJECTED / RETIRED / DELETED)
- `basis` (USER_DIRECT / REPEATED_OBSERVATION / USER_CORRECTION)
- `consent_version`, `source_surface` (Owner Portal / explicit ChatGPT plugin invocation), `provenance_ref` (minimum)
- `evidence_count`, `independent_session_count`, `quality_score`, `last_observed_at`, `review_due_at`, `expires_at`
- `supersedes_id`, `revision`, `created_at`, `updated_at`, `deleted_at`
- Minimal metadata-only audit; enforce owner-scoped read/write and API permissions server-side

The existing `chapter2_private.dari_personal_learning_v1` and its owner-checked RPCs are the current storage baseline. Upgrade via additive migration and careful API versioning. Keep the prior `context_v1` semantics unchanged until v2's access checks, review flow and migration pass. The future `context_v2` may return active AUTO_ACTIVE or USER_CONFIRMED items *only* to the authenticated subject's DOMUS reasoner. No institution-facing API or broad personal-context fetch.

At rest: enforce validated encryption/key management for personal preference text, minimize logging and provider retention. The previously deployed private-schema v1 tables are access controlled but encryption-of-new-profile-text is **not yet independently verified**. Do not ingest highly sensitive narratives until that is addressed.

## 8. UI — person-first learning panel

Place inside canonical `web/workspace/` DARI > **Getting to Know Me**, not the legacy Streamlit production path. Main sections:

- **How we collaborate** — active preference summaries in plain language
- **Recently learned** — low-risk autosaves with Undo / Correct / Why this?
- **Needs my permission** — only user-initiated sensitive memory requests, clearly explained
- **My boundaries** — learning toggle; chat exclusions; cross-surface permissions
- **Memory controls** — pause, correction, retirement, deletion, export, evidence/provenance, retention
- **My roles** — business permissions shown in a separate panel, not used to define personal identity

Do not display a sensitivity alarm every time a sensitive topic is mentioned. Do not show an empty corporate "Owner persona" template as if it fully defines the person.

## 9. Model and tool execution flow

`authenticated input -> realm + source validation -> sensitive gate -> current-session adaptation -> candidate extraction -> consent/eligibility check -> auto save OR review/no-save -> metadata log -> minimal active context retrieval -> DARI response`.

The model can *propose* a structured memory item but cannot write memory directly. A deterministic policy layer validates category, consent, origin, scope, conflict, rate limit, and revocation state before any persisted mutation. Treat preference text as data, never as an instruction superseding higher-trust rules.

No "learned" instruction can grant permission to send messages, spend money, alter data, approve publication, share case records, remove human reviews, or access other people's private data. Tool actions are enforced by authenticated service and existing ColettiOS gates.

## 10. ChatGPT connector behavior

The ChatGPT side can obtain active preferences only through authorized `dari_get_personal_preferences`-style tool requests, subject to OAuth, user approval and data-minimization. DARI only sees chat content explicitly passed into the plugin operation, not ChatGPT's entire live conversation or system memory. The private Owner Portal may independently auto-learn from its authenticated interactions after Adaptive opt-in; ChatGPT cannot silently auto-learn from an unrelated conversation.

Recommended plugin tools:
- `dari_get_collaboration_profile` (read, minimal active preference payload)
- `dari_propose_preference` (write candidate only, scope-checked)
- `dari_review_preference` (user-authenticated confirm/reject/correct/delete)
- `dari_get_explanation` (specific preference provenance/scope, avoiding private transcript disclosure)

For ChatGPT-originated learning, require explicit call or user's request to transmit selected information, plus the same server-side eligibility and consent checks. Do not promise passive cross-app memory sync.

## 11. Verification / acceptance contract (must pass before operational)

1. Without Adaptive opt-in, no AUTO_ACTIVE item can be persisted or used across sessions.
2. Once enabled, a direct ordinary preference saves without a modal, is visible in "Recently learned", and can be undone.
3. A one-off request stays session-only; a repeated nonsensitive pattern only saves after independent corroboration.
4. Sensitive mention does not become a durable fact, nor leak in logs, backups, embeddings, summaries or employees' views.
5. A direct correction is reflected in the next DARI turn and prevents outdated cache/observation resurrection.
6. Reject, retire, deletion and consent revocation work; private-context fetch never includes retired/deleted items.
7. Owner identity A cannot read or modify Owner identity B's DOMUS records; other staff/client/anonymous users receive a deny.
8. Untrusted client case records and prompt-injection text cannot create personal memory or expand tool authority.
9. ChatGPT plugin cannot silently access whole conversation; only selected tool arguments reach ColettiOS, with explicit scope.
10. DARI can keep working in ordinary chat with DOMUS unavailable; OFFICIUM business operations are unaffected.
11. No learning profile can authorize financial, personnel, case, legal, protected-profession or publication actions.
12. Tests run in canonical web app and real deployed environment, across login/logout/refresh, multiple sessions, and access denial.
13. New DB change undergoes RLS/SECURITY DEFINER audit, privacy review, release manifest approval and post-deployment smoke before "Operational".

## 12. Implementation stages

**Phase A (design approval):** This document only. No live collection.

**Phase B (V2 contracts & DB):** Encryption/retention/security decision; private schema migration; v2 owner-checked RPCs and no-candidate leakage tests.

**Phase C (canonical web UI):** Adaptive settings, active/recent memory, Undo, correction, deletion, why-learned; use `web/` as the canonical deployment target.

**Phase D (DARI runtime):** Policy engine, session classifier, context resolver, live Owner chat adapter and revocation cache invalidation.

**Phase E (ChatGPT):** Private OAuth MCP plugin with minimal tools. Read-first and explicit learning handoff, no passive full-chat sync.

**Phase F (production promotion):** Acceptance evidence, cross-interface privacy verification, deployment, owner smoke, release manifest and monitoring.

A passing unit test or a committed schema alone is **not** production activation.
