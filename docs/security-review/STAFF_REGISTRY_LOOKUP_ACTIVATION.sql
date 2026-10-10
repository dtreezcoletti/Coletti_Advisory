-- Normal operating path activation: staff-only browser facade over the authoritative registry.
-- REVIEW REQUIRED BEFORE PRODUCTION APPLICATION: this changes a protected permission surface.
-- It is intentionally additive, read-only, and fail-closed.

create or replace function public.staff_registry_lookup(
  p_query text,
  p_limit integer default 10
)
returns table(
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
as $$
begin
  if auth.uid() is null
     or not private.has_role(array['owner','admin','analyst','reviewer']::text[]) then
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
    r.case_count,
    r.match_reason,
    r.match_score
  from registry.lookup_clients(
    p_query,
    least(greatest(coalesce(p_limit, 10), 1), 25)
  ) r;
end;
$$;

revoke all on function public.staff_registry_lookup(text, integer) from public;
revoke all on function public.staff_registry_lookup(text, integer) from anon;
grant execute on function public.staff_registry_lookup(text, integer) to authenticated;

create or replace function public.staff_registry_client_cases(
  p_client_id text
)
returns table(
  case_id text,
  case_status text,
  opened_on date,
  closed_on date
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null
     or not private.has_role(array['owner','admin','analyst','reviewer']::text[]) then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if nullif(btrim(p_client_id), '') is null then
    raise exception 'client_id is required' using errcode = '22023';
  end if;

  return query
  select c.case_id, c.status as case_status, c.opened_on, c.closed_on
  from registry.cases c
  where c.client_id = btrim(p_client_id)
  order by c.opened_on desc nulls last, c.case_id;
end;
$$;

revoke all on function public.staff_registry_client_cases(text) from public;
revoke all on function public.staff_registry_client_cases(text) from anon;
grant execute on function public.staff_registry_client_cases(text) to authenticated;

-- Acceptance requirements before production activation:
-- 1. anon invocation fails.
-- 2. authenticated client/read_only invocation fails.
-- 3. owner/admin/analyst/reviewer invocation succeeds.
-- 4. results contain only the minimum client/case routing fields above.
-- 5. no mutation path is exposed.
-- 6. registry/dispatcher/chapter2_private schemas remain unavailable directly to anon/authenticated.
