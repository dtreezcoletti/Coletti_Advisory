-- STAGING DRAFT ONLY. NOT A PRODUCTION MIGRATION.
-- Enables RLS while preserving the existing colettios_runtime CRUD path.

begin;

alter table colettios_internal.dari_chatgpt_conversations enable row level security;
alter table colettios_internal.dari_reasoning_runs enable row level security;

revoke all on table colettios_internal.dari_chatgpt_conversations
  from public, anon, authenticated, service_role;
revoke all on table colettios_internal.dari_reasoning_runs
  from public, anon, authenticated, service_role;

drop policy if exists dari_chatgpt_conversations_runtime_access
  on colettios_internal.dari_chatgpt_conversations;
create policy dari_chatgpt_conversations_runtime_access
  on colettios_internal.dari_chatgpt_conversations
  as permissive
  for all
  to colettios_runtime
  using (true)
  with check (true);

drop policy if exists dari_reasoning_runs_runtime_access
  on colettios_internal.dari_reasoning_runs;
create policy dari_reasoning_runs_runtime_access
  on colettios_internal.dari_reasoning_runs
  as permissive
  for all
  to colettios_runtime
  using (true)
  with check (true);

commit;
