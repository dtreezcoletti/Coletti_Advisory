-- REVIEW REQUIRED BEFORE PRODUCTION APPLICATION.
-- Existing public.admin_case_assignment_catalog_v1 RPC hardening candidate.
-- NOT A DEPLOYED MIGRATION. Do not expose directly or autoapply.
--
-- Verified live function currently gates only private.current_user_role(),
-- which checks active private role rows, not public.profiles.status='ACTIVE'.
-- private.is_admin() also verifies the matched ACTIVE public profile and
-- authoritative active Owner/Admin role; this closes suspended-profile access.
-- The SELECT shape, registry ownership and returned fields remain unchanged.
--
-- Real authenticated Owner/Admin, suspended/demoted Owner/Admin, staff,
-- client and anon negative tests are required before activating.
--
create or replace function public.admin_case_assignment_catalog_v1()
returns table(
  case_id text,
  client_id text,
  client_name text,
  case_status text,
  opened_on date,
  active_assignment_count bigint
)
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  return query
  select
    c.case_id,
    c.client_id,
    cl.display_name,
    c.status,
    c.opened_on,
    count(ca.id) filter (where ca.active)
  from registry.cases c
  left join registry.clients cl on cl.client_id = c.client_id
  left join public.case_assignments ca on ca.case_id = c.case_id
  where upper(c.status) not in ('ARCHIVED','CLOSED')
  group by c.case_id,c.client_id,cl.display_name,c.status,c.opened_on
  order by c.opened_on desc nulls last,c.case_id;
end;
$function$;

revoke all on function public.admin_case_assignment_catalog_v1() from public, anon;
grant execute on function public.admin_case_assignment_catalog_v1() to authenticated;

-- No table grants, new data exposure or mutation paths authorized.
