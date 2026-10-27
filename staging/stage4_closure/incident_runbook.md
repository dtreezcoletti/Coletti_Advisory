# Stage 4.5 Incident Runbook
Status: ONE-PAGE DRAFT — NONPRODUCTION

## Detect
Classify incident:
- AUTH: login/recovery/redirect failure
- CORE: /ready failure, DB connectivity, 429/5xx
- BILLING: Square booking/payment/webhook failure
- COMMUNICATIONS: confirmation/C-FAB/Resend failure
- DATA: RLS, migration, corruption, unexpected cross-client access

## Contain
- Stop the affected production rollout.
- Do not broaden permissions.
- Disable only the failing integration/path where possible.
- Preserve logs, provider IDs, timestamps, and deployment IDs.
- Never delete append-only evidence to make a retry look clean.

## Assess
Record:
- first known bad time
- last known good time
- affected service/commit/config
- real-client impact (if any)
- whether data integrity or confidentiality is affected
- available backup/restore point

## Recover
Use the narrowest rollback:
- code => revert deployment/commit
- DNS => remove new hostname record/binding
- Auth => restore prior URL/template config
- DB policy => revert only approved policy/RLS change
- webhook => unregister/disable provider subscription
- Core DB => restore prior env only if prior target is viable; otherwise keep service closed
- data => restore only from a verified backup/restore point

## Verify
Require real output:
- health/readiness
- login/logout/re-login
- client isolation
- provider signature verification
- idempotency
- zero unexpected residue
- no protected email DNS changes

## Close
Document root cause, evidence, rollback, residual risk, and next preventive control.
Do not mark Operational until acceptance passes.
