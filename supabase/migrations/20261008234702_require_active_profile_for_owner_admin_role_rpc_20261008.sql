-- Enforce ACTIVE Owner/Admin profile gate in the existing role RPC.
-- Live migration 20261008234702. The current_user_role check alone did not
-- block role changes by SUSPENDED Owners. No role or authority expansion.
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_user_id uuid, target_role text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  caller_role text;
  previous_role text;
  owner_count integer;
begin
  if auth.uid() is null then
    raise exception 'not authorized' using errcode='42501';
  end if;

  caller_role := private.current_user_role();
  if caller_role not in ('owner','admin') or caller_role is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if target_role is null or target_role not in
     ('owner','admin','analyst','reviewer','client','read_only') then
    raise exception 'invalid role' using errcode='22023';
  end if;

  if target_user_id is null or not exists
    (select 1 from public.profiles where id=target_user_id) then
    raise exception 'target account not found' using errcode='P0002';
  end if;

  select role into previous_role
    from private.user_roles
   where user_id=target_user_id for update;

  if caller_role <> 'owner' and
     (target_role='owner' or previous_role='owner') then
    raise exception 'Owner authority required for Owner role changes'
      using errcode='42501';
  end if;

  if previous_role='owner' and target_role<>'owner' then
    select count(*) into owner_count from private.user_roles
      where role='owner' and active=true;
    if owner_count<=1 then
      raise exception 'cannot demote the last active owner'
        using errcode='23514';
    end if;
  end if;

  insert into private.user_roles(user_id,role,active)
  values(target_user_id,target_role,true)
  on conflict(user_id)
  do update set role=excluded.role,active=true,updated_at=now();
  -- Existing sync and audit triggers update public.profiles and audit events.
end;
$function$;
