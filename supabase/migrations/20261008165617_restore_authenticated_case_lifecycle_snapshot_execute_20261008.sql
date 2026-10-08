-- WBA-2026-10-08-01 / RB-01
-- Reconcile the migration applied to the authoritative Supabase project
-- as 20261008165617_restore_authenticated_case_lifecycle_snapshot_execute_20261008.
--
-- Case lifecycle snapshots render in authorized owner/admin/staff/client
-- workspaces. The existing RPC (SECURITY DEFINER) checks auth.uid() and
-- private.can_access_case(p_case_id) before any state is returned.
-- This migration restores the intended authenticated EXECUTE permission,
-- without granting public/anonymous access or weakening case isolation.
--
-- Acceptance evidence, October 8, 2026:
--  1. authenticated EXECUTE = true; anon EXECUTE = false.
--  2. Assigned owner role can read the lifecycle snapshot in a rollback-only
--     database-role test.
--  3. Authenticated role with a UUID without any case authorization receives
--     SQLSTATE 42501, "not authorized", in a rollback-only test.
--  4. Real user/browser positive and negative acceptance remains required.
REVOKE ALL ON FUNCTION public.case_lifecycle_snapshot_v1(text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.case_lifecycle_snapshot_v1(text) TO authenticated;
