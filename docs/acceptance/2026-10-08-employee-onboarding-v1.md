# V1 — Controlled Employee Onboarding Acceptance

Date: October 8, 2026
Status: BLOCKED — no legitimate non-Owner employee account exists.
Scope: Existing single-host Supabase Auth -> private.user_roles -> public.profiles -> case_assignments -> employee workspace. No additional service.

## Verified state

- Three Auth accounts: two active Owners and one active Client; none invited; no non-Owner staff profiles.
- Users & Roles can change the role of an existing authenticated account but does not issue invitations or create users.
- Login secure-link sign-in uses shouldCreateUser:false, preventing signup by unknown addresses.
- A newly created Auth user defaults to the client role unless on the separate Owner allowlist; an authorized role change is required later.
- Case staff assignment now requires active matching role, confirmed email and at least one sign-in.
- Owner and Executive operating workspace registry profiles do not create additional Auth roles. Job positions are not credentials.

## Acceptance procedure

1. An Owner identifies one real, authorized non-Owner test mailbox and its responsible recipient. Do not invent or use an unconsenting third-party email.
2. An authorized administrator invites that mailbox using the existing Supabase Auth invitation flow with an allowed return URL https://colettico.com/login/. Do not put privileged Supabase keys in the static site.
3. The recipient accepts the invitation and completes first sign-in. Verify auth.users, profiles and protected user_roles IDs match, the email is confirmed and first sign-in occurred.
4. Owner uses the existing Users & Roles page to assign analyst or reviewer. Verify authoritative private.user_roles and public.profiles agree. Do not grant Owner/Executive status accidentally.
5. Use an approved nonproduction case/consultation fixture and existing gates to test case assignment; do not charge a real payment method or falsely accept an engagement.
6. Employee signs into /employee/, sees only assigned cases, and cannot read unrelated cases or perform unauthorized Owner/Admin operations.
7. Verify suspension immediately blocks case access, auto-assignment excludes unactivated identities, and login/assignment/audit outcomes are captured.
8. Owner reviews results and records PASS/FAIL/BLOCKED. No release promotion without explicit authority.

## Current limits

- Invitation from the Owner portal is not implemented. The existing Supabase Auth administrator interface is a documented interim route, not a portal feature.
- Without an authorized non-Owner mailbox: account acceptance is BLOCKED, not passed.
- A rollback-only Analyst simulation is database evidence, not real browser acceptance.
- V1 is not externally client-ready. The October 9 freeze and Owner-only production boundary remain unchanged.
