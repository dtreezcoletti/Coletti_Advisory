# DARI · Owner Personal Collaboration v1

> **V2 design notice (2026-10-12):** [Adaptive Collaborative Learning v2.0](DARI_ADAPTIVE_COLLABORATIVE_LEARNING_V2.md) specifies a more person-first, low-interruption learning model. It is **DESIGNED ONLY**. The v1 candidate/confirmation-only database and UI behavior remain unchanged until a separate reviewed migration and release pass acceptance.

**Scope:** Coletti & Co. Owner Profile > DARI · Getting to Know Me. Personal DARI / DOMUS only.
**Applied Supabase migration:** 20261012221427, `dari_domus_personal_collaboration_v1` (Colettico).

## Purpose and governing contract

DARI is a collaborative intelligence. It learns **how to assist** an authenticated owner, not **what institutional decisions to make**.

- The Owner is the final decision-maker. DARI provides options, competing interpretations, opportunity costs, uncertainty, records needed, and recommendations—not automatic consequential actions.
- Personal preferences and work rhythms are DOMUS, not OFFICIUM. DARI cannot import, summarize, or disclose private memories to employees, clients, case records, reporting, governance, or Dispatcher without separate expressly authorized PONS handling.
- User statements are not proof of business facts. Inferences and observed behavior are candidates, never established personal truths.
- The owner must explicitly confirm each candidate before it becomes eligible to shape DARI's personal conversational style. Replacements return to candidate status. The Owner can reject, retire, or delete it.
- Personal learning never changes ColettiOS roles, Source/Record States, policy, authority, approval rules, publishing, professional judgments, or release readiness.
- Minimize collection. Sensitive biographical/medical/relationship details require separately verified private-vault controls; do not automatically harvest full conversations.
- The existing provider-neutral DARI reasoner and the professional calibration registry remain independent and unchanged.

## Data boundary

`chapter2_private.dari_personal_learning_v1`: Owner-authored or owner-reviewed personal preferences, keyed to `auth.users`, isolated by `owner_user_id`, candidate/confirmed/rejected/retired states.
`chapter2_private.dari_personal_learning_audit_v1`: metadata-only change events; no statements duplicated.
`public.dari_personal_profile_{list,propose,review,context}_v1`: owner-scoped RPCs callable only by authenticated roles and guarded by server-side `private.user_roles` owner lookup. SQL SECURITY DEFINER access is intentional and owner-checked; do not widen GRANT or rely on user-editable claims. Direct table access for authenticated/anon denied.

The existing application session's JWT, not a new login or admin key, is used by the owner UI. No production service secret is exposed in the browser or Streamlit response. A different authenticated owner sees only their own records.

## How collaboration should work in DARI's future private reasoning flow

1. Interpret the Owner's request; distinguish a decision, a discussion, and explicit authority to act.
2. Read only the Owner's **confirmed** DOMUS profile entries, via a scoped personal context adapter. Treat the entry text as preference data, never instructions or credentials.
3. Provide an objective assessment. Show what is verified, inferred, missing, or uncertain; ask whether a tradeoff was properly captured only when needed.
4. Offer a decision preview and, where relevant, reversibility and measurable success criteria. Avoid repetitive personal reassurance or one-sided advocacy.
5. Obtain explicit approval through established human gates before any consequential external or institutional action.
6. Record corrections as new candidates; superseded entries are not used until explicitly reconfirmed.
7. Keep communication and decisions useful even when DOMUS is offline. OFFICIUM must not depend on reading private context.

## Acceptance and release

**Verified at database level, rollback-only tests (2026-10-12):** initial empty list, candidate withheld from context, confirm enables context, two-owner separation, cross-owner mutation denied, retire removes context, delete removes entry, signed-in Owner RPC behavior, direct client table access denied. No test profile records were retained.

**Coded, not yet deployed:** Owner profile editor; owner-only role/session checks and controls; a DOMUS-only approved-preference context adapter that never calls a reasoning provider or changes institutional decisions.

**Still required before Operational:** application unit tests/CI, deployed Owner authenticated UI acceptance, real Owner approve/reject/delete smoke, token expiry/logout behavior, DOMUS reasoning runtime integration (using the coded private adapter), policy against prompt injection, secure context lifecycle, cross-interface acceptance, release-manifest gating. Do not promote this to operational or infer that a private reasoning model is running.

**Privacy note:** Owner profile text is private-schema access controlled; application-layer encryption of this new text has **not** been verified. Do not put sensitive autobiographical details into it yet.

## Owner profile categories

Work Rhythm, Communication, Decision Support, Boundaries, Personal Goals. A preference such as “Challenge business decisions using evidence and tradeoffs, but leave final authority with me” is appropriate. No personal history is seeded by this migration or PR.
