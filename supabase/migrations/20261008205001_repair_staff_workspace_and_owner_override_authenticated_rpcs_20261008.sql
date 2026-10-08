-- Existing private implementations independently enforce staff/case/Owner authorization.
-- Live migration: 20261008205001. Do not create new public access or identity roles.
CREATE OR REPLACE FUNCTION public.staff_case_workspace_v1(p_case_id text)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select private.staff_case_workspace_impl_v1(p_case_id);
$function$;

revoke all on function public.staff_case_workspace_v1(text) from public,anon;
grant execute on function public.staff_case_workspace_v1(text) to authenticated;
CREATE OR REPLACE FUNCTION public.owner_override_assignment_v1(p_case_id text, p_staff_user_id uuid, p_assignment_role text, p_reason text, p_deactivate_existing_role_matches boolean DEFAULT true)
 RETURNS uuid
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select private.owner_override_assignment_impl_v1(
  p_case_id,p_staff_user_id,p_assignment_role,p_reason,p_deactivate_existing_role_matches
 );
$function$;

revoke all on function public.owner_override_assignment_v1(text,uuid,text,text,boolean) from public,anon;
grant execute on function public.owner_override_assignment_v1(text,uuid,text,text,boolean) to authenticated;
