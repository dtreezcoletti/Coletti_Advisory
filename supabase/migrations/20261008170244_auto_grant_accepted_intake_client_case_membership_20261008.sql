-- October 8, 2026: Golden Path client membership handoff (controlled repair).
-- Live Supabase migration 20261008170244: auto_grant_accepted_intake_client_case_membership_20261008.
-- Grant only the primary intake user's 'client' membership on the newly
-- opened case; preserve the existing accepted-intake, agreement and staff gates.
-- The case + membership + assignment are one transactional function call.
-- Non-owner browser acceptance is still pending. No general production promotion.
CREATE OR REPLACE FUNCTION private.admin_open_case_from_intake_impl_v1(p_intake_id uuid, p_case_prefix text DEFAULT 'BRI'::text, p_assignment_role text DEFAULT 'case_manager'::text)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  i public.intake_submissions%rowtype;
  v_client text;
  v_record uuid;
  v_case text;
  v_staff uuid;
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if p_assignment_role not in (
    'case_manager','analyst','reviewer','fresh_eyes_reviewer',
    'qa_reviewer','publication_preparer','delivery_coordinator'
  ) then
    raise exception 'invalid assignment role' using errcode='22023';
  end if;

  select * into i
  from public.intake_submissions
  where id=p_intake_id
  for update;

  if not found then raise exception 'intake not found' using errcode='P0002'; end if;
  if i.status <> 'ACCEPTED' then raise exception 'accepted intake required' using errcode='22023'; end if;
  if i.case_id is not null then return i.case_id; end if;

  select l.client_id into v_client
  from public.client_user_links l
  where l.user_id=i.user_id
    and l.active
    and l.relationship_role='primary'
  order by l.created_at
  limit 1;

  if v_client is null then
    raise exception 'accepted client relationship required' using errcode='22023';
  end if;

  if not private.has_controlled_engagement_acceptance_v1(p_intake_id,null) then
    raise exception 'controlled engagement agreement acceptance required before case opening' using errcode='22023';
  end if;

  select p.id into v_staff
  from public.profiles p
  left join public.case_assignments ca
    on ca.staff_user_id=p.id and ca.active
  where p.status='ACTIVE'
    and p.role in ('owner','admin','analyst','reviewer')
  group by p.id,p.role
  order by
    count(ca.id),
    case p.role
      when 'analyst' then 1
      when 'admin' then 2
      when 'owner' then 3
      when 'reviewer' then 4
      else 5
    end,
    p.id
  limit 1;

  if v_staff is null then
    raise exception 'no eligible staff available for assignment' using errcode='22023';
  end if;

  insert into registry.records(
    scope,record_key,record_type,title,content,epistemic_classification,status,
    authority,source_type,source_ref,metadata
  )
  values(
    'client','case-from-intake:'||p_intake_id::text,'CASE',
    coalesce(i.matter_summary,'Coletti & Co. Reconstruction Engagement'),
    jsonb_build_object('intake_id',p_intake_id,'client_id',v_client,'service_requested',i.service_requested),
    'PLAN','ACTIVE','INSTITUTIONAL_REGISTRY','INTAKE',p_intake_id::text,
    jsonb_build_object('created_via','admin_open_case_from_intake_v1')
  )
  returning record_id into v_record;

  insert into registry.cases(
    case_id,record_id,client_id,case_prefix,opened_on,status,metadata
  )
  values(
    null,v_record,v_client,upper(p_case_prefix),current_date,'OPEN',
    jsonb_build_object('origin_intake_id',p_intake_id,'auto_assignment',true)
  )
  returning case_id into v_case;

  update public.intake_submissions
  set case_id=v_case,updated_at=now()
  where id=p_intake_id;

  -- Grant client access only to the authenticated identity linked to the
  -- accepted intake. The earlier active-primary client link and controlled
  -- engagement checks must have passed for execution to reach this point.
  insert into public.case_memberships(case_id,user_id,access_level,active)
  values(v_case,i.user_id,'client',true)
  on conflict (case_id,user_id) do nothing;

  update public.engagement_acceptances
  set case_id=v_case
  where intake_id=p_intake_id
    and accepted=true
    and case_id is null;

  insert into public.case_assignments(
    case_id,staff_user_id,assignment_role,active,assigned_by
  )
  values(v_case,v_staff,p_assignment_role,true,auth.uid());

  insert into public.audit_events(
    actor_user_id,actor_role,action,object_type,object_id,case_id,metadata
  )
  values(
    auth.uid(),private.current_user_role(),'CASE_OPENED_AND_ASSIGNED','case',v_case,v_case,
    jsonb_build_object(
      'intake_id',p_intake_id,'client_id',v_client,
      'assigned_staff_user_id',v_staff,'assignment_role',p_assignment_role
    )
  );

  return v_case;
end;
$function$
;
