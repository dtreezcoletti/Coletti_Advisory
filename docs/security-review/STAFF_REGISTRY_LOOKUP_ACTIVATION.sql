-- CONTROLLED CANDIDATE — NOT DEPLOYED / NOT YET APPROVED FOR EXECUTION
-- Existing Registry browser port. Do not create a competing client or case registry.
-- Proven current state (2026-10-10): both existing public RPCs deny EXECUTE
-- to anon and authenticated. This file prepares a narrowed authorization
-- replacement, but is stored outside supabase/migrations pending real-user
-- case-isolation tests and migration-history reconciliation.
--
-- Acceptance before any execution:
--   1. Owner/Admin with ACTIVE matching profile and private role sees all;
--   2. assigned ACTIVE analyst/reviewer sees only clients with assigned cases;
--   3. client with multiple cases: staff sees only their assigned case rows
--      and count, never sibling cases;
--   4. unassigned staff, suspended/demoted staff, client, anon are denied;
--   5. no direct Registry table grants or write paths; audit read output.
--
-- REVIEW REQUIRED BEFORE PRODUCTION APPLICATION. No live schema changes have been made by this file.

create or replace function public.staff_registry_lookup(
  p_query text,
  p_limit integer default 10
)
returns table (
  client_id text,
  display_name text,
  client_status text,
  case_count bigint,
  match_reason text,
  match_score double precision
)
language plpgsql
stable
security definer
set search_path = ''
as $function$
begin
  -- is_staff checks a matching active profile and active authoritative role.
  -- has_role alone is insufficient for suspended-profile enforcement.
  if not private.is_staff() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if nullif(btrim(p_query), '') is null then
    raise exception 'query is required' using errcode = '22023';
  end if;

  return query
  select
    r.client_id,
    r.display_name,
    r.status as client_status,
    case
      when private.is_admin() then r.case_count
      else (
        select count(distinct a.case_id)
        from registry.cases c
        join public.case_assignments a on a.case_id = c.case_id
        where c.client_id = r.client_id
          and a.staff_user_id = auth.uid()
          and a.active
      )
    end as case_count,
    r.match_reason,
    r.match_score
  from registry.lookup_clients(
    p_query,
    least(greatest(coalesce(p_limit, 10), 1), 25)
  ) r
  where private.is_admin()
    or exists (
      select 1
      from registry.cases c
      join public.case_assignments a on a.case_id = c.case_id
      where c.client_id = r.client_id
        and a.staff_user_id = auth.uid()
        and a.active
    );
end;
$function$;

create or replace function public.staff_registry_client_cases(
  p_client_id text
)
returns table (
  case_id text,
  case_status text,
  opened_on date,
  closed_on date
)
language plpgsql
stable
security definer
set search_path = ''
as $function$
begin
  if not private.is_staff() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if nullif(btrim(p_client_id), '') is null then
    raise exception 'client_id is required' using errcode = '22023';
  end if;

  return query
  select
    c.case_id,
    c.status,
    c.opened_on,
    c.closed_on
  from registry.cases c
  where c.client_id = btrim(p_client_id)
    and (
      private.is_admin()
      or exists (
        select 1
        from public.case_assignments a
        where a.case_id = c.case_id
          and a.staff_user_id = auth.uid()
          and a.active
      )
    )
  order by c.opened_on desc nulls last, c.case_id;
end;
$function$;

-- Do not create any direct client access to Registry tables.
revoke all on function public.staff_registry_lookup(text, integer) from public, anon;
revoke all on function public.staff_registry_client_cases(text) from public, anon;
grant execute on function public.staff_registry_lookup(text, integer) to authenticated;
grant execute on function public.staff_registry_client_cases(text) to authenticated;

-- DO NOT mark this candidate production-accepted based on source tests alone.
