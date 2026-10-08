-- Enforce staff identity during assignments and deny stale-role case access; live migration 20261008204900.
CREATE OR REPLACE FUNCTION private.can_access_case(target_case_id text)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'private', 'public', 'pg_catalog'
AS $function$
 select private.is_admin()
 or exists (
   select 1 from public.case_memberships m
   where m.case_id=target_case_id and m.user_id=(select auth.uid()) and m.active
 )
 or (
   private.is_staff()
   and exists (
     select 1 from public.case_assignments a
     where a.case_id=target_case_id and a.staff_user_id=(select auth.uid()) and a.active
   )
 )
$function$;

CREATE OR REPLACE FUNCTION private.can_work_case(target_case_id text)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'private', 'public', 'pg_catalog'
AS $function$
 select private.is_admin()
 or (
   private.is_staff()
   and exists (
     select 1 from public.case_assignments a
     where a.case_id=target_case_id and a.staff_user_id=(select auth.uid()) and a.active
   )
 )
$function$;

CREATE OR REPLACE FUNCTION private.validate_active_case_staff_assignment_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
 if new.active and not exists (
   select 1 from public.profiles p
   join private.user_roles r on r.user_id=p.id
   where p.id=new.staff_user_id
     and p.status='ACTIVE'
     and r.active=true
     and p.role=r.role
     and r.role in ('owner','admin','analyst','reviewer')
 ) then
   raise exception 'active staff identity required for case assignment'
     using errcode='22023';
 end if;
 return new;
end;
$function$;

revoke all on function private.validate_active_case_staff_assignment_v1() from public,anon,authenticated;
create trigger validate_active_case_staff_assignment_v1 before insert or update on public.case_assignments for each row execute function private.validate_active_case_staff_assignment_v1();
