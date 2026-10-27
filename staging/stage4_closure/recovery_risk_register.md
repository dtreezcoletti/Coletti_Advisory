# Stage 4 Recovery Risk Register
Status: NONPRODUCTION SOURCE RECORD
Date: 2026-10-27

## RISK-RCV-001 — Missing pre-repository baseline
Evidence:
- First repository migration is 20260910121500_connection_architecture.sql.
- Clean replay failed with SQLSTATE 3F000 because schema private did not exist.
- Replaying the earlier production migration ledger then failed with SQLSTATE 42883 because public.rls_auto_enable() predates that ledger.

Impact:
- Repository migrations alone cannot reconstruct the authoritative database from empty state.
- Disaster-recovery reproducibility is not verified.

Minimum closure:
1. Produce one schema-only authoritative baseline dump.
2. Store the baseline in source control after review/redaction of environment-specific statements.
3. Rebuild a disposable database from baseline plus subsequent migrations.
4. Require two consecutive clean replays before closure.

## RISK-RCV-002 — Duplicate migration version prefix
Evidence:
- supabase/migrations/20261002210000_production_truth_and_function_hardening_v1.sql
- supabase/migrations/20261002210000_square_billing_v1.sql

Impact:
- Migration ordering/history reconciliation is ambiguous.

Minimum closure:
- Preserve production history; repair source history in staging by renaming/rebaselining one migration with a unique version and proving clean replay.

## RISK-RCV-003 — No verified restorable production backup before Stage 4 production writes
Evidence:
- Connected tools did not verify a backup/restore point before the RLS and consultation-readiness production writes.
- Supabase organization currently reports Free plan.
- Current connected tools expose no backup inventory/restore point.

Impact:
- Point-in-time rollback cannot be claimed.

Minimum closure:
- Verify Database > Backups in the Supabase dashboard.
- If no managed backup exists, create and validate a manual logical backup set before further production schema changes.
