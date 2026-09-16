-- Production-closure hardening: lifecycle checkpoints may only be promoted to
-- COMPLETE when the authoritative records prove the checkpoint's work exists.
-- This does not change role authority; it prevents false completion.

create or replace function private.case_lifecycle_completion_evidence_v1(p_case_id text, p_checkpoint_key text)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_client_id text;
  v_case_status text;
  v_case_metadata jsonb;
  v_ok boolean := false;
  v_reason text := 'Required completion evidence is missing.';
begin
  select c.client_id, c.status, c.metadata
    into v_client_id, v_case_status, v_case_metadata
  from registry.cases c
  where c.case_id = p_case_id;

  if v_client_id is null then
    return jsonb_build_object('ok', false, 'reason', 'Canonical Case record does not exist.');
  end if;

  case p_checkpoint_key
    when 'INTAKE' then
      v_ok := exists(
        select 1 from public.intake_submissions i
        where i.case_id = p_case_id
          and (i.submitted_at is not null or i.status in ('SUBMITTED','IN_REVIEW','ACCEPTED','DECLINED','WITHDRAWN'))
      );
      v_reason := 'No submitted intake is linked to the Case.';
    when 'SCREENING' then
      v_ok := exists(
        select 1 from public.intake_submissions i
        where i.case_id = p_case_id and i.status in ('IN_REVIEW','ACCEPTED','DECLINED')
      );
      v_reason := 'No screening/review state is recorded for the linked intake.';
    when 'ACCEPTANCE' then
      v_ok := exists(
        select 1 from public.intake_submissions i where i.case_id = p_case_id and i.status = 'ACCEPTED'
      );
      v_reason := 'No accepted intake is linked to the Case.';
    when 'CLIENT_ONBOARDING' then
      v_ok := exists(
        select 1 from registry.clients c where c.client_id = v_client_id and c.status = 'ACTIVE'
      ) and exists(
        select 1 from public.client_user_links l where l.client_id = v_client_id and l.active
      );
      v_reason := 'Client relationship is not active with at least one active portal/user link.';
    when 'ENGAGEMENT_GATES' then
      v_ok := exists(
        select 1 from public.contract_records cr where cr.case_id = p_case_id and cr.status = 'EXECUTED'
      ) or exists(
        select 1 from registry.contracts rc
        where rc.case_id = p_case_id
          and rc.contract_status in ('EXECUTED','ACTIVE')
          and rc.executed_at is not null
      );
      v_reason := 'No executed engagement contract is linked to the Case.';
    when 'CASE_OPENING' then
      v_ok := true;
      v_reason := 'Canonical Case record does not exist.';
    when 'RECORD_COLLECTION' then
      v_ok := exists(select 1 from registry.sources s where s.case_id = p_case_id);
      v_reason := 'No Case-scoped Records are registered.';
    when 'RECONSTRUCTION' then
      v_ok := exists(select 1 from registry.propositions p where p.case_id = p_case_id)
              and exists(select 1 from registry.findings f where f.case_id = p_case_id);
      v_reason := 'Reconstruction is incomplete: at least one proposition and one finding are required.';
    when 'HUMAN_REVIEW' then
      v_ok := exists(
        select 1 from registry.reviews r where r.case_id = p_case_id and r.human_required
      );
      v_reason := 'No human review record exists for the Case.';
    when 'REPORT_PREPARATION' then
      v_ok := exists(select 1 from registry.reports r where r.case_id = p_case_id);
      v_reason := 'No controlled report record exists for the Case.';
    when 'PUBLICATION_HANDOFF' then
      v_ok := exists(
        select 1 from public.publication_handoffs ph
        where ph.case_id = p_case_id
          and ph.status in ('APPROVED','PUBLISHED')
          and ph.approved_by is not null
          and ph.approved_at is not null
          and ph.first_truth_preflight_status = 'PASSED'
          and ph.first_truth_notice_present
          and ph.professional_boundary_passed
      ) and (
        exists(select 1 from public.published_reports pr where pr.case_id = p_case_id and pr.revoked_at is null)
        or exists(
          select 1 from registry.reports rr
          where rr.case_id = p_case_id and rr.publication_status in ('PUBLISHED','DELIVERED')
        )
      );
      v_reason := 'Publication/handoff lacks approved First Truth preflight, professional-boundary confirmation, or a published deliverable.';
    when 'CLOSEOUT' then
      v_ok := not exists(
        select 1 from public.document_requests dr
        where dr.case_id = p_case_id and dr.status not in ('SATISFIED','WAIVED')
      ) and exists(
        select 1 from public.case_lifecycle_checkpoints cp
        where cp.case_id = p_case_id and cp.checkpoint_key = 'PUBLICATION_HANDOFF' and cp.status = 'COMPLETE'
      );
      v_reason := 'Case cannot close while document requests remain open or publication/handoff is incomplete.';
    when 'ARCHIVE' then
      v_ok := upper(coalesce(v_case_status,'')) = 'CLOSED'
              and exists(
                select 1 from public.case_lifecycle_checkpoints cp
                where cp.case_id = p_case_id and cp.checkpoint_key = 'CLOSEOUT' and cp.status = 'COMPLETE'
              );
      v_reason := 'Case must be closed with closeout complete before archive.';
    else
      v_ok := false;
      v_reason := 'Unknown lifecycle checkpoint.';
  end case;

  return jsonb_build_object('ok', v_ok, 'reason', v_reason);
end;
$$;

revoke all on function private.case_lifecycle_completion_evidence_v1(text,text) from public, anon, authenticated;
grant execute on function private.case_lifecycle_completion_evidence_v1(text,text) to service_role;

create or replace function public.transition_case_checkpoint_v1(
  p_case_id text,
  p_checkpoint_key text,
  p_target_status text,
  p_reason text default null::text,
  p_public_note text default null::text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  role_name text;
  cat public.case_lifecycle_checkpoint_catalog%rowtype;
  cp public.case_lifecycle_checkpoints%rowtype;
  prior_missing text;
  actor uuid;
  evidence jsonb;
  case_is_synthetic boolean := false;
begin
  actor:=auth.uid();
  role_name:=coalesce(private.current_user_role(),'');
  if actor is null or not private.can_access_case(p_case_id) then raise exception 'not authorized' using errcode='42501'; end if;
  if p_target_status not in ('NOT_STARTED','READY','IN_PROGRESS','WAITING','BLOCKED','AWAITING_HUMAN','COMPLETE','NOT_APPLICABLE') then raise exception 'invalid lifecycle status' using errcode='22023'; end if;
  perform private.seed_case_lifecycle(p_case_id);
  select * into cat from public.case_lifecycle_checkpoint_catalog where checkpoint_key=p_checkpoint_key;
  if not found then raise exception 'unknown checkpoint' using errcode='22023'; end if;

  if role_name in ('owner','admin') then null;
  elsif role_name in ('analyst','reviewer') and private.can_work_case(p_case_id)
        and p_checkpoint_key in ('RECORD_COLLECTION','RECONSTRUCTION','HUMAN_REVIEW','REPORT_PREPARATION')
        and p_target_status in ('IN_PROGRESS','WAITING','BLOCKED','AWAITING_HUMAN','COMPLETE') then null;
  else raise exception 'role not authorized for lifecycle transition' using errcode='42501';
  end if;

  if cat.protected_gate and role_name not in ('owner','admin') then raise exception 'protected lifecycle gate requires Owner/Admin' using errcode='42501'; end if;
  if p_target_status in ('BLOCKED','COMPLETE','NOT_APPLICABLE') and nullif(btrim(coalesce(p_reason,'')),'') is null then
    raise exception 'reason required for this lifecycle transition' using errcode='22023';
  end if;

  if p_target_status='NOT_APPLICABLE' and cat.required then
    select coalesce((c.metadata->>'synthetic')::boolean,false)
      into case_is_synthetic from registry.cases c where c.case_id=p_case_id;
    if not coalesce(case_is_synthetic,false) then
      raise exception 'required lifecycle checkpoint cannot be marked not applicable for a real Case' using errcode='23514';
    end if;
  end if;

  if p_target_status='COMPLETE' then
    select prior_cat.label into prior_missing
    from public.case_lifecycle_checkpoint_catalog prior_cat
    join public.case_lifecycle_checkpoints prior_cp
      on prior_cp.checkpoint_key=prior_cat.checkpoint_key and prior_cp.case_id=p_case_id
    where prior_cat.sequence_no<cat.sequence_no and prior_cat.required
      and prior_cp.status not in ('COMPLETE','NOT_APPLICABLE')
    order by prior_cat.sequence_no limit 1;
    if prior_missing is not null then
      raise exception 'prior lifecycle checkpoint incomplete: %',prior_missing using errcode='23514';
    end if;

    evidence:=private.case_lifecycle_completion_evidence_v1(p_case_id,p_checkpoint_key);
    if not coalesce((evidence->>'ok')::boolean,false) then
      raise exception 'completion evidence missing: %',coalesce(evidence->>'reason','required evidence not found') using errcode='23514';
    end if;
  end if;

  select * into cp from public.case_lifecycle_checkpoints
  where case_id=p_case_id and checkpoint_key=p_checkpoint_key for update;

  update public.case_lifecycle_checkpoints
  set status=p_target_status,
      public_note=coalesce(p_public_note,public_note),
      internal_note=case when nullif(btrim(coalesce(p_reason,'')),'') is not null then p_reason else internal_note end,
      blocking_reason=case when p_target_status='BLOCKED' then p_reason when status='BLOCKED' and p_target_status<>'BLOCKED' then null else blocking_reason end,
      completed_by=case when p_target_status in ('COMPLETE','NOT_APPLICABLE') then actor else null end,
      completed_at=case when p_target_status in ('COMPLETE','NOT_APPLICABLE') then now() else null end,
      last_transition_by=actor,
      last_transition_at=now(),
      source_system='PORTAL_LIFECYCLE'
  where case_id=p_case_id and checkpoint_key=p_checkpoint_key;

  insert into public.case_lifecycle_events(case_id,checkpoint_key,prior_status,new_status,actor_user_id,actor_role,reason,public_note)
  values(p_case_id,p_checkpoint_key,cp.status,p_target_status,actor,role_name,p_reason,p_public_note);
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(actor,role_name,'CASE_LIFECYCLE_TRANSITION','case_lifecycle_checkpoint',p_checkpoint_key,p_case_id,
    jsonb_build_object('from',cp.status,'to',p_target_status,'reason',p_reason));

  if p_checkpoint_key='CLOSEOUT' and p_target_status='COMPLETE' then
    update registry.cases set status='CLOSED',closed_on=coalesce(closed_on,current_date),updated_at=now() where case_id=p_case_id;
  elsif p_checkpoint_key='ARCHIVE' and p_target_status='COMPLETE' then
    update registry.cases set status='ARCHIVED',closed_on=coalesce(closed_on,current_date),updated_at=now() where case_id=p_case_id;
  end if;

  return public.case_lifecycle_snapshot_v1(p_case_id);
end;
$$;
