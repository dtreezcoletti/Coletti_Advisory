-- Exact applied migration; keep in sync with Supabase.

-- Explicit default-deny mirrors chapter2_private's existing policy pattern.
-- Direct client table access remains forbidden; owner access uses guarded RPC only.
create policy dari_personal_learning_v1_deny_client_access
 on chapter2_private.dari_personal_learning_v1 for all to anon,authenticated
 using (false) with check (false);
create policy dari_personal_learning_audit_v1_deny_client_access
 on chapter2_private.dari_personal_learning_audit_v1 for all to anon,authenticated
 using (false) with check (false);