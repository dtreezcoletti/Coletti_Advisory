# Stage 4.5 Backup Restore-Test Procedure
Status: PROCEDURE ONLY — NO RESTORE EXECUTED

## Backup creation
Use a secure machine with the production connection string supplied outside chat.

Schema-only baseline:
  supabase db dump --linked -f supabase/baseline_schema.sql

Full logical recovery set:
  supabase db dump --linked -f backup_roles.sql --role-only
  supabase db dump --linked -f backup_schema.sql
  supabase db dump --linked -f backup_data.sql --use-copy --data-only

## Integrity
- Record UTC creation time.
- Hash each file.
- Store outside the production database.
- Never commit data dump, passwords, or secrets to Git.

## Restore test
1. Create/use a disposable nonproduction project.
2. Disable outbound cron/network side effects before loading application objects.
3. Restore roles as applicable.
4. Restore schema.
5. Restore data.
6. Restore migration-history schema/data separately if required.
7. Reapply environment-only secrets/config manually.
8. Run:
   - schema/table count comparison
   - critical function existence
   - RLS/policy comparison
   - synthetic client isolation
   - synthetic Golden Path
   - C-FAB signed webhook test
9. Destroy or sanitize the disposable copy according to retention policy.

## PASS
Restore is PASS only if application acceptance succeeds from the restored copy, not merely if psql exits zero.
