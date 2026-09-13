-- Fix the shared immutable-identifier trigger so non-identifier updates on
-- registry.clients / registry.cases / registry.sources do not reference fields
-- that do not exist on the current trigger table.
create or replace function registry.prevent_stable_identifier_change()
returns trigger
language plpgsql
set search_path to 'registry','pg_temp'
as $$
begin
  if tg_table_name = 'clients'
     and (to_jsonb(old)->>'client_id') is distinct from (to_jsonb(new)->>'client_id') then
    raise exception 'Client ID is immutable';
  elsif tg_table_name = 'cases'
     and (to_jsonb(old)->>'case_id') is distinct from (to_jsonb(new)->>'case_id') then
    raise exception 'Case ID is immutable';
  elsif tg_table_name = 'sources'
     and (to_jsonb(old)->>'source_id') is distinct from (to_jsonb(new)->>'source_id') then
    raise exception 'Source ID is immutable';
  end if;
  return new;
end;
$$;
