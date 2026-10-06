-- Consultation pipeline v1
-- Source-control reconciliation of the Owner-approved Consultation & Qualification SOP.
-- Square remains booking/payment desk; Google Calendar remains master calendar; ColettiOS reconciles state.

create table if not exists public.preconsultation_assignments (
  id uuid primary key default gen_random_uuid(),
  intake_id uuid not null unique references public.intake_submissions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'SUBMITTED' check(status in ('SUBMITTED','REVISION_REQUESTED','LOCKED')),
  engagement_question text not null,
  client_goal text not null,
  client_position text not null,
  proposition_to_test text not null,
  intended_recipient text not null,
  expected_record_count integer not null check(expected_record_count >= 0),
  known_sources jsonb not null default '[]'::jsonb check(jsonb_typeof(known_sources)='array'),
  known_entities jsonb not null default '[]'::jsonb check(jsonb_typeof(known_entities)='array'),
  known_gaps jsonb not null default '[]'::jsonb check(jsonb_typeof(known_gaps)='array'),
  known_conflicts jsonb not null default '[]'::jsonb check(jsonb_typeof(known_conflicts)='array'),
  complexity_factors text not null,
  preliminary_scope text not null,
  submitted_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.preconsultation_assignments enable row level security;
revoke all on public.preconsultation_assignments from public,anon;
grant select on public.preconsultation_assignments to authenticated;
revoke insert,update,delete,truncate,references,trigger on public.preconsultation_assignments from authenticated;
create index if not exists idx_preconsultation_assignments_user on public.preconsultation_assignments(user_id);
drop policy if exists preconsultation_select on public.preconsultation_assignments;
create policy preconsultation_select on public.preconsultation_assignments for select to authenticated
using (user_id=(select auth.uid()) or private.is_staff());

create table if not exists public.consultation_workflows (
  id uuid primary key default gen_random_uuid(),
  intake_id uuid not null unique references public.intake_submissions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  owner_decision text not null default 'PENDING' check(owner_decision in ('PENDING','APPROVED_FOR_CONSULTATION','NEEDS_MORE_INFORMATION','DECLINED_FOR_CONSULTATION')),
  owner_decision_reason text,
  owner_decided_by uuid references auth.users(id),
  owner_decided_at timestamptz,
  square_booking_id text unique,
  square_customer_id text,
  booking_state text not null default 'NOT_BOOKED' check(booking_state in ('NOT_BOOKED','BOOKED','CONFIRMED','UPDATED','RESCHEDULED','CANCELLED','COMPLETED')),
  appointment_start timestamptz,
  appointment_end timestamptz,
  appointment_timezone text not null default 'America/Chicago',
  google_event_id text,
  consultation_fee_cents bigint check(consultation_fee_cents is null or consultation_fee_cents > 0),
  invoice_id uuid unique references public.invoices(id) on delete set null,
  payment_state text not null default 'NOT_ISSUED' check(payment_state in ('NOT_ISSUED','DUE','PENDING','PAID','FAILED','PARTIALLY_REFUNDED','REFUNDED')),
  confirmation_email_state text not null default 'NOT_READY' check(confirmation_email_state in ('NOT_READY','READY','SENDING','SENT','FAILED')),
  confirmation_email_provider_id text,
  confirmation_email_sent_at timestamptz,
  cleared_at timestamptz,
  consultation_completed_at timestamptz,
  qualification_decision text not null default 'PENDING' check(qualification_decision in ('PENDING','QUALIFIED','NEEDS_RECORD_ASSESSMENT','NOT_QUALIFIED')),
  qualification_assessment_id uuid references public.consultation_assessments(id) on delete set null,
  qualified_at timestamptz,
  qualified_by uuid references auth.users(id),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.consultation_workflows enable row level security;
revoke all on public.consultation_workflows from public,anon;
grant select on public.consultation_workflows to authenticated;
revoke insert,update,delete,truncate,references,trigger on public.consultation_workflows from authenticated;
create index if not exists idx_consultation_workflows_user on public.consultation_workflows(user_id);
create index if not exists idx_consultation_workflows_owner_decided_by on public.consultation_workflows(owner_decided_by);
create index if not exists idx_consultation_workflows_qualification_assessment on public.consultation_workflows(qualification_assessment_id);
create index if not exists idx_consultation_workflows_qualified_by on public.consultation_workflows(qualified_by);
drop policy if exists consultation_workflows_select on public.consultation_workflows;
create policy consultation_workflows_select on public.consultation_workflows for select to authenticated
using (user_id=(select auth.uid()) or private.is_staff());

create table if not exists public.consultation_notifications (
  id uuid primary key default gen_random_uuid(),
  consultation_id uuid not null references public.consultation_workflows(id) on delete cascade,
  notification_type text not null default 'APPOINTMENT_CONFIRMATION',
  recipient_email text not null,
  provider text not null default 'resend',
  provider_message_id text,
  status text not null default 'PENDING' check(status in ('PENDING','SENDING','SENT','FAILED')),
  idempotency_key text not null unique,
  failure_reason text,
  sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.consultation_notifications enable row level security;
revoke all on public.consultation_notifications from public,anon,authenticated;
create index if not exists idx_consultation_notifications_consultation on public.consultation_notifications(consultation_id);

CREATE OR REPLACE FUNCTION private.submit_preconsultation_assignment_impl_v1(p_intake_id uuid, p_engagement_question text, p_client_goal text, p_client_position text, p_proposition_to_test text, p_intended_recipient text, p_expected_record_count integer, p_known_sources jsonb DEFAULT '[]'::jsonb, p_known_entities jsonb DEFAULT '[]'::jsonb, p_known_gaps jsonb DEFAULT '[]'::jsonb, p_known_conflicts jsonb DEFAULT '[]'::jsonb, p_complexity_factors text DEFAULT ''::text, p_preliminary_scope text DEFAULT ''::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_intake public.intake_submissions%rowtype;
  v_workflow public.consultation_workflows%rowtype;
  v_id uuid;
begin
  if auth.uid() is null then raise exception 'authentication required' using errcode='42501'; end if;
  select * into v_intake from public.intake_submissions where id=p_intake_id for update;
  if not found or v_intake.user_id<>auth.uid() then raise exception 'intake not found' using errcode='P0002'; end if;
  if v_intake.status in ('ACCEPTED','DECLINED','WITHDRAWN') then raise exception 'intake is closed' using errcode='22023'; end if;

  select * into v_workflow from public.consultation_workflows where intake_id=p_intake_id for update;
  if found and v_workflow.owner_decision not in ('PENDING','NEEDS_MORE_INFORMATION') then
    raise exception 'assignment is locked after owner disposition' using errcode='22023';
  end if;

  if nullif(btrim(p_engagement_question),'') is null
     or nullif(btrim(p_client_goal),'') is null
     or nullif(btrim(p_client_position),'') is null
     or nullif(btrim(p_proposition_to_test),'') is null
     or nullif(btrim(p_intended_recipient),'') is null
     or nullif(btrim(p_complexity_factors),'') is null
     or nullif(btrim(p_preliminary_scope),'') is null then
    raise exception 'all narrative pre-consultation fields are required' using errcode='22023';
  end if;
  if p_expected_record_count is null or p_expected_record_count < 0 then
    raise exception 'expected_record_count must be zero or greater' using errcode='22023';
  end if;
  if jsonb_typeof(coalesce(p_known_sources,'[]'::jsonb))<>'array'
     or jsonb_typeof(coalesce(p_known_entities,'[]'::jsonb))<>'array'
     or jsonb_typeof(coalesce(p_known_gaps,'[]'::jsonb))<>'array'
     or jsonb_typeof(coalesce(p_known_conflicts,'[]'::jsonb))<>'array' then
    raise exception 'known source/entity/gap/conflict values must be arrays' using errcode='22023';
  end if;

  insert into public.preconsultation_assignments(
    intake_id,user_id,status,engagement_question,client_goal,client_position,proposition_to_test,
    intended_recipient,expected_record_count,known_sources,known_entities,known_gaps,known_conflicts,
    complexity_factors,preliminary_scope,submitted_at,updated_at
  ) values (
    p_intake_id,auth.uid(),'SUBMITTED',btrim(p_engagement_question),btrim(p_client_goal),btrim(p_client_position),
    btrim(p_proposition_to_test),btrim(p_intended_recipient),p_expected_record_count,
    coalesce(p_known_sources,'[]'::jsonb),coalesce(p_known_entities,'[]'::jsonb),
    coalesce(p_known_gaps,'[]'::jsonb),coalesce(p_known_conflicts,'[]'::jsonb),
    btrim(p_complexity_factors),btrim(p_preliminary_scope),now(),now()
  )
  on conflict(intake_id) do update set
    status='SUBMITTED',
    engagement_question=excluded.engagement_question,
    client_goal=excluded.client_goal,
    client_position=excluded.client_position,
    proposition_to_test=excluded.proposition_to_test,
    intended_recipient=excluded.intended_recipient,
    expected_record_count=excluded.expected_record_count,
    known_sources=excluded.known_sources,
    known_entities=excluded.known_entities,
    known_gaps=excluded.known_gaps,
    known_conflicts=excluded.known_conflicts,
    complexity_factors=excluded.complexity_factors,
    preliminary_scope=excluded.preliminary_scope,
    submitted_at=now(),updated_at=now()
  returning id into v_id;

  insert into public.consultation_workflows(intake_id,user_id,owner_decision,updated_at)
  values(p_intake_id,auth.uid(),'PENDING',now())
  on conflict(intake_id) do update set
    owner_decision='PENDING',owner_decision_reason=null,owner_decided_by=null,owner_decided_at=null,updated_at=now();

  update public.intake_submissions set status='IN_REVIEW',updated_at=now() where id=p_intake_id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),private.current_user_role(),'PRECONSULTATION_SUBMITTED','preconsultation_assignment',v_id::text,
         jsonb_build_object('intake_id',p_intake_id,'classification','CLIENT_ASSERTION_INPUT'));
  return v_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.submit_preconsultation_assignment_v1(p_intake_id uuid, p_engagement_question text, p_client_goal text, p_client_position text, p_proposition_to_test text, p_intended_recipient text, p_expected_record_count integer, p_known_sources jsonb DEFAULT '[]'::jsonb, p_known_entities jsonb DEFAULT '[]'::jsonb, p_known_gaps jsonb DEFAULT '[]'::jsonb, p_known_conflicts jsonb DEFAULT '[]'::jsonb, p_complexity_factors text DEFAULT ''::text, p_preliminary_scope text DEFAULT ''::text)
 RETURNS uuid
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.submit_preconsultation_assignment_impl_v1(
    p_intake_id,p_engagement_question,p_client_goal,p_client_position,p_proposition_to_test,
    p_intended_recipient,p_expected_record_count,p_known_sources,p_known_entities,p_known_gaps,
    p_known_conflicts,p_complexity_factors,p_preliminary_scope
  );
$function$;

CREATE OR REPLACE FUNCTION private.admin_decide_consultation_impl_v1(p_consultation_id uuid, p_decision text, p_reason text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v public.consultation_workflows%rowtype;
begin
  if auth.uid() is null or private.current_user_role()<>'owner' then raise exception 'owner authorization required' using errcode='42501'; end if;
  if p_decision not in ('APPROVED_FOR_CONSULTATION','NEEDS_MORE_INFORMATION','DECLINED_FOR_CONSULTATION') then
    raise exception 'invalid consultation decision' using errcode='22023';
  end if;
  select * into v from public.consultation_workflows where id=p_consultation_id for update;
  if not found then raise exception 'consultation not found' using errcode='P0002'; end if;
  update public.consultation_workflows set
    owner_decision=p_decision,owner_decision_reason=nullif(btrim(coalesce(p_reason,'')),''),
    owner_decided_by=auth.uid(),owner_decided_at=now(),updated_at=now()
  where id=p_consultation_id;
  update public.preconsultation_assignments set
    status=case when p_decision='NEEDS_MORE_INFORMATION' then 'REVISION_REQUESTED' else 'LOCKED' end,
    updated_at=now()
  where intake_id=v.intake_id;
  if p_decision='DECLINED_FOR_CONSULTATION' then
    update public.intake_submissions set status='DECLINED',updated_at=now() where id=v.intake_id;
  else
    update public.intake_submissions set status='IN_REVIEW',updated_at=now() where id=v.intake_id;
  end if;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),'owner','CONSULTATION_OWNER_DECISION','consultation_workflow',p_consultation_id::text,
         jsonb_build_object('decision',p_decision,'reason',p_reason));
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_decide_consultation_v1(p_consultation_id uuid, p_decision text, p_reason text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.admin_decide_consultation_impl_v1(p_consultation_id,p_decision,p_reason);
$function$;

CREATE OR REPLACE FUNCTION private.admin_link_square_booking_impl_v1(p_consultation_id uuid, p_provider_booking_id text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v public.consultation_workflows%rowtype; b dispatcher.consultation_bookings%rowtype;
begin
  if auth.uid() is null or private.current_user_role()<>'owner' then raise exception 'owner authorization required' using errcode='42501'; end if;
  select * into v from public.consultation_workflows where id=p_consultation_id for update;
  if not found then raise exception 'consultation not found' using errcode='P0002'; end if;
  if v.owner_decision<>'APPROVED_FOR_CONSULTATION' then raise exception 'consultation is not owner-approved' using errcode='22023'; end if;
  select * into b from dispatcher.consultation_bookings
  where provider='square' and provider_booking_id=btrim(p_provider_booking_id);
  if not found then raise exception 'Square booking not found' using errcode='P0002'; end if;
  if b.booking_state='CANCELLED' then raise exception 'cannot link a cancelled booking' using errcode='22023'; end if;
  update public.consultation_workflows set
    square_booking_id=b.provider_booking_id,square_customer_id=b.client_ref,booking_state=b.booking_state,
    appointment_start=b.start_at,appointment_end=b.end_at,appointment_timezone=b.timezone,
    google_event_id=b.google_event_id,confirmation_email_state='NOT_READY',updated_at=now()
  where id=p_consultation_id;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),'owner','SQUARE_BOOKING_LINKED','consultation_workflow',p_consultation_id::text,
         jsonb_build_object('provider_booking_id',b.provider_booking_id,'start_at',b.start_at,'end_at',b.end_at));
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_link_square_booking_v1(p_consultation_id uuid, p_provider_booking_id text)
 RETURNS void
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.admin_link_square_booking_impl_v1(p_consultation_id,p_provider_booking_id);
$function$;

CREATE OR REPLACE FUNCTION private.admin_prepare_consultation_invoice_impl_v1(p_consultation_id uuid, p_fee_cents bigint)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v public.consultation_workflows%rowtype; v_invoice uuid; v_num text;
begin
  if auth.uid() is null or private.current_user_role()<>'owner' then raise exception 'owner authorization required' using errcode='42501'; end if;
  if p_fee_cents is null or p_fee_cents<=0 then raise exception 'consultation fee must be greater than zero' using errcode='22023'; end if;
  select * into v from public.consultation_workflows where id=p_consultation_id for update;
  if not found then raise exception 'consultation not found' using errcode='P0002'; end if;
  if v.owner_decision<>'APPROVED_FOR_CONSULTATION' or v.square_booking_id is null or v.appointment_start is null then
    raise exception 'owner-approved Square appointment is required before billing' using errcode='22023';
  end if;
  if v.invoice_id is not null then return v.invoice_id; end if;
  v_num := 'CONS-'||to_char(now(),'YYYYMMDD')||'-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,6));
  insert into public.invoices(client_user_id,invoice_number,amount_cents,status,due_date,provider)
  values(v.user_id,v_num,p_fee_cents,'DRAFT',current_date,'square')
  returning id into v_invoice;
  update public.consultation_workflows set
    consultation_fee_cents=p_fee_cents,invoice_id=v_invoice,payment_state='DUE',updated_at=now()
  where id=p_consultation_id;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),'owner','CONSULTATION_INVOICE_PREPARED','consultation_workflow',p_consultation_id::text,
         jsonb_build_object('invoice_id',v_invoice,'amount_cents',p_fee_cents));
  return v_invoice;
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_prepare_consultation_invoice_v1(p_consultation_id uuid, p_fee_cents bigint)
 RETURNS uuid
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.admin_prepare_consultation_invoice_impl_v1(p_consultation_id,p_fee_cents);
$function$;

CREATE OR REPLACE FUNCTION private.admin_mark_consultation_completed_impl_v1(p_consultation_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v public.consultation_workflows%rowtype;
begin
  if auth.uid() is null or private.current_user_role()<>'owner' then raise exception 'owner authorization required' using errcode='42501'; end if;
  select * into v from public.consultation_workflows where id=p_consultation_id for update;
  if not found then raise exception 'consultation not found' using errcode='P0002'; end if;
  if v.payment_state<>'PAID' or v.cleared_at is null then raise exception 'consultation is not financially cleared' using errcode='22023'; end if;
  if v.booking_state='CANCELLED' then raise exception 'cancelled consultation cannot be completed' using errcode='22023'; end if;
  update public.consultation_workflows set consultation_completed_at=now(),booking_state='COMPLETED',updated_at=now()
  where id=p_consultation_id;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),'owner','CONSULTATION_COMPLETED','consultation_workflow',p_consultation_id::text,'{}'::jsonb);
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_mark_consultation_completed_v1(p_consultation_id uuid)
 RETURNS void
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.admin_mark_consultation_completed_impl_v1(p_consultation_id);
$function$;

CREATE OR REPLACE FUNCTION private.admin_record_consultation_impl_v1(p_intake_id uuid, p_engagement_question text, p_client_goal text, p_client_position text, p_proposition_to_test text, p_intended_recipient text, p_expected_record_count integer, p_known_sources jsonb, p_known_entities jsonb, p_known_gaps jsonb, p_known_conflicts jsonb, p_complexity_factors jsonb, p_complexity_level text, p_recommended_products text[], p_preliminary_scope jsonb, p_qualification_decision text, p_decision_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare i public.intake_submissions%rowtype; w public.consultation_workflows%rowtype; v_id uuid;
begin
  if auth.uid() is null or not private.is_staff() then raise exception 'not authorized' using errcode='42501'; end if;
  if p_qualification_decision not in ('QUALIFIED','NOT_QUALIFIED','NEEDS_RECORD_ASSESSMENT') then raise exception 'invalid qualification decision' using errcode='22023'; end if;
  if p_complexity_level is not null and p_complexity_level not in ('LOW','MODERATE','HIGH','VERY_HIGH') then raise exception 'invalid complexity level' using errcode='22023'; end if;
  select * into i from public.intake_submissions where id=p_intake_id for update;
  if not found then raise exception 'intake not found' using errcode='P0002'; end if;
  if i.status in ('DECLINED','WITHDRAWN') then raise exception 'intake closed' using errcode='22023'; end if;
  select * into w from public.consultation_workflows where intake_id=p_intake_id for update;
  if not found or w.consultation_completed_at is null or w.payment_state<>'PAID' or w.cleared_at is null then
    raise exception 'completed financially-cleared consultation required before qualification' using errcode='22023';
  end if;

  update public.consultation_assessments
  set status='NOT_QUALIFIED',qualification_decision='NOT_QUALIFIED',
      decision_reason=coalesce(decision_reason,'Superseded by later consultation assessment'),updated_at=now()
  where intake_id=p_intake_id and status<>'NOT_QUALIFIED';

  insert into public.consultation_assessments(
    intake_id,user_id,status,engagement_question,client_goal,client_position,proposition_to_test,
    intended_recipient,expected_record_count,known_sources,known_entities,known_gaps,known_conflicts,
    complexity_factors,complexity_level,recommended_products,preliminary_scope,
    qualification_decision,decision_reason,assessed_by,assessed_at,metadata
  ) values(
    p_intake_id,i.user_id,p_qualification_decision,p_engagement_question,p_client_goal,p_client_position,
    p_proposition_to_test,p_intended_recipient,p_expected_record_count,coalesce(p_known_sources,'[]'::jsonb),
    coalesce(p_known_entities,'[]'::jsonb),coalesce(p_known_gaps,'[]'::jsonb),coalesce(p_known_conflicts,'[]'::jsonb),
    coalesce(p_complexity_factors,'{}'::jsonb),p_complexity_level,coalesce(p_recommended_products,'{}'::text[]),
    coalesce(p_preliminary_scope,'{}'::jsonb),p_qualification_decision,p_decision_reason,auth.uid(),now(),
    jsonb_build_object('instrument','POST_CONSULTATION_QUALIFICATION','version','1.0','preconsultation_assignment_id',
      (select id from public.preconsultation_assignments where intake_id=p_intake_id))
  ) returning id into v_id;

  update public.intake_submissions
  set status=case when p_qualification_decision='NOT_QUALIFIED' then 'DECLINED' else 'IN_REVIEW' end,updated_at=now()
  where id=p_intake_id;

  update public.consultation_workflows set
    qualification_decision=p_qualification_decision,qualification_assessment_id=v_id,
    qualified_at=now(),qualified_by=auth.uid(),updated_at=now()
  where id=w.id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),private.current_user_role(),'CONSULTATION_ASSESSED','consultation_assessment',v_id::text,
    jsonb_build_object('intake_id',p_intake_id,'qualification_decision',p_qualification_decision,'complexity_level',p_complexity_level));
  return v_id;
end;
$function$;

CREATE OR REPLACE FUNCTION private.admin_complete_consultation_qualification_impl_v1(p_consultation_id uuid, p_qualification_decision text, p_decision_reason text, p_complexity_level text DEFAULT NULL::text, p_complexity_notes text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare w public.consultation_workflows%rowtype; a public.preconsultation_assignments%rowtype;
begin
  if auth.uid() is null or not private.is_staff() then raise exception 'not authorized' using errcode='42501'; end if;
  select * into w from public.consultation_workflows where id=p_consultation_id;
  if not found then raise exception 'consultation not found' using errcode='P0002'; end if;
  select * into a from public.preconsultation_assignments where intake_id=w.intake_id;
  if not found then raise exception 'pre-consultation assignment missing' using errcode='P0002'; end if;
  return private.admin_record_consultation_impl_v1(
    w.intake_id,a.engagement_question,a.client_goal,a.client_position,a.proposition_to_test,
    a.intended_recipient,a.expected_record_count,a.known_sources,a.known_entities,a.known_gaps,a.known_conflicts,
    jsonb_build_object('client_reported',a.complexity_factors,'staff_notes',p_complexity_notes),
    p_complexity_level,'{}'::text[],jsonb_build_object('client_reported',a.preliminary_scope),
    p_qualification_decision,p_decision_reason
  );
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_complete_consultation_qualification_v1(p_consultation_id uuid, p_qualification_decision text, p_decision_reason text, p_complexity_level text DEFAULT NULL::text, p_complexity_notes text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select private.admin_complete_consultation_qualification_impl_v1(
    p_consultation_id,p_qualification_decision,p_decision_reason,p_complexity_level,p_complexity_notes
  );
$function$;

CREATE OR REPLACE FUNCTION public.admin_consultation_queue_v1()
 RETURNS TABLE(consultation_id uuid, intake_id uuid, user_id uuid, client_name text, client_email text, intake_status text, assignment_status text, assignment jsonb, owner_decision text, owner_decision_reason text, booking_state text, square_booking_id text, appointment_start timestamp with time zone, appointment_end timestamp with time zone, appointment_timezone text, google_event_id text, consultation_fee_cents bigint, invoice_id uuid, invoice_number text, invoice_status text, payment_url text, payment_state text, confirmation_email_state text, confirmation_email_sent_at timestamp with time zone, cleared_at timestamp with time zone, consultation_completed_at timestamp with time zone, qualification_decision text, stage text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  if auth.uid() is null or private.current_user_role() not in ('owner','admin') then raise exception 'not authorized' using errcode='42501'; end if;
  return query
  select w.id,w.intake_id,w.user_id,p.display_name,(i.contact->>'email'),i.status,
    a.status,
    case when a.id is null then null else jsonb_build_object(
      'engagement_question',a.engagement_question,'client_goal',a.client_goal,'client_position',a.client_position,
      'proposition_to_test',a.proposition_to_test,'intended_recipient',a.intended_recipient,
      'expected_record_count',a.expected_record_count,'known_sources',a.known_sources,'known_entities',a.known_entities,
      'known_gaps',a.known_gaps,'known_conflicts',a.known_conflicts,'complexity_factors',a.complexity_factors,
      'preliminary_scope',a.preliminary_scope,'submitted_at',a.submitted_at
    ) end,
    w.owner_decision,w.owner_decision_reason,w.booking_state,w.square_booking_id,w.appointment_start,w.appointment_end,
    w.appointment_timezone,w.google_event_id,w.consultation_fee_cents,w.invoice_id,inv.invoice_number,inv.status,inv.payment_url,
    w.payment_state,w.confirmation_email_state,w.confirmation_email_sent_at,w.cleared_at,w.consultation_completed_at,
    w.qualification_decision,
    case
      when a.id is null then 'AWAITING_PRECONSULTATION_ASSIGNMENT'
      when w.owner_decision='PENDING' then 'OWNER_REVIEW'
      when w.owner_decision='NEEDS_MORE_INFORMATION' then 'NEEDS_MORE_INFORMATION'
      when w.owner_decision='DECLINED_FOR_CONSULTATION' then 'DECLINED_FOR_CONSULTATION'
      when w.square_booking_id is null then 'APPROVED_AWAITING_SQUARE_BOOKING'
      when w.invoice_id is null then 'APPOINTMENT_SCHEDULED_AWAITING_PAYMENT_SETUP'
      when inv.payment_url is null then 'SQUARE_PAYMENT_LINK_PENDING'
      when w.confirmation_email_state<>'SENT' then 'CONFIRMATION_EMAIL_PENDING'
      when w.payment_state<>'PAID' then 'AWAITING_PAYMENT'
      when w.consultation_completed_at is null then 'CLEARED_FOR_CONSULTATION'
      when w.qualification_decision='PENDING' then 'POST_CONSULTATION_QUALIFICATION'
      else w.qualification_decision
    end
  from public.consultation_workflows w
  join public.intake_submissions i on i.id=w.intake_id
  left join public.profiles p on p.id=w.user_id
  left join public.preconsultation_assignments a on a.intake_id=w.intake_id
  left join public.invoices inv on inv.id=w.invoice_id
  order by w.updated_at desc;
end;
$function$;

CREATE OR REPLACE FUNCTION public.admin_unlinked_square_consultation_bookings_v1()
 RETURNS TABLE(provider_booking_id text, client_ref text, start_at timestamp with time zone, end_at timestamp with time zone, timezone text, booking_state text, payment_state text, google_event_id text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  if auth.uid() is null or private.current_user_role()<>'owner' then raise exception 'owner authorization required' using errcode='42501'; end if;
  return query
  select b.provider_booking_id,b.client_ref,b.start_at,b.end_at,b.timezone,b.booking_state,b.payment_state,b.google_event_id
  from dispatcher.consultation_bookings b
  where b.provider='square'
    and b.booking_state<>'CANCELLED'
    and not exists(select 1 from public.consultation_workflows w where w.square_booking_id=b.provider_booking_id)
  order by b.start_at desc nulls last;
end;
$function$;

CREATE OR REPLACE FUNCTION private.sync_consultation_from_square_booking_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  update public.consultation_workflows
  set booking_state=new.booking_state,
      appointment_start=new.start_at,appointment_end=new.end_at,appointment_timezone=new.timezone,
      google_event_id=new.google_event_id,
      cleared_at=case when new.booking_state='CANCELLED' then null else cleared_at end,
      updated_at=now()
  where square_booking_id=new.provider_booking_id;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION private.sync_consultation_from_invoice_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  update public.consultation_workflows
  set payment_state=case
        when new.status='PAID' then 'PAID'
        when new.status='PAST_DUE' then 'FAILED'
        when new.status='VOID' then 'FAILED'
        when new.payment_url is not null then 'DUE'
        else payment_state end,
      confirmation_email_state=case
        when new.payment_url is not null and confirmation_email_state='NOT_READY' then 'READY'
        else confirmation_email_state end,
      cleared_at=case when new.status='PAID' then coalesce(cleared_at,now()) when new.status in ('VOID','PAST_DUE') then null else cleared_at end,
      updated_at=now()
  where invoice_id=new.id;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION private.sync_consultation_from_payment_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  update public.consultation_workflows w
  set payment_state=case
        when new.status='SUCCEEDED' then 'PAID'
        when new.status='REFUNDED' then 'REFUNDED'
        when new.status='PARTIALLY_REFUNDED' then 'PARTIALLY_REFUNDED'
        when new.status='FAILED' then 'FAILED'
        else w.payment_state end,
      cleared_at=case when new.status='SUCCEEDED' then coalesce(w.cleared_at,now())
                      when new.status in ('REFUNDED','PARTIALLY_REFUNDED','FAILED') then null else w.cleared_at end,
      updated_at=now()
  where w.invoice_id=new.invoice_id;
  return new;
end;
$function$;

revoke all on function public.submit_preconsultation_assignment_v1(uuid,text,text,text,text,text,integer,jsonb,jsonb,jsonb,jsonb,text,text) from public,anon;
grant execute on function public.submit_preconsultation_assignment_v1(uuid,text,text,text,text,text,integer,jsonb,jsonb,jsonb,jsonb,text,text) to authenticated;
revoke all on function public.admin_decide_consultation_v1(uuid,text,text) from public,anon;
grant execute on function public.admin_decide_consultation_v1(uuid,text,text) to authenticated;
revoke all on function public.admin_link_square_booking_v1(uuid,text) from public,anon;
grant execute on function public.admin_link_square_booking_v1(uuid,text) to authenticated;
revoke all on function public.admin_prepare_consultation_invoice_v1(uuid,bigint) from public,anon;
grant execute on function public.admin_prepare_consultation_invoice_v1(uuid,bigint) to authenticated;
revoke all on function public.admin_mark_consultation_completed_v1(uuid) from public,anon;
grant execute on function public.admin_mark_consultation_completed_v1(uuid) to authenticated;
revoke all on function public.admin_complete_consultation_qualification_v1(uuid,text,text,text,text) from public,anon;
grant execute on function public.admin_complete_consultation_qualification_v1(uuid,text,text,text,text) to authenticated;
revoke all on function public.admin_consultation_queue_v1() from public,anon;
grant execute on function public.admin_consultation_queue_v1() to authenticated;
revoke all on function public.admin_unlinked_square_consultation_bookings_v1() from public,anon;
grant execute on function public.admin_unlinked_square_consultation_bookings_v1() to authenticated;

drop trigger if exists consultation_workflow_square_sync on dispatcher.consultation_bookings;
create trigger consultation_workflow_square_sync
after update of booking_state,start_at,end_at,timezone,google_event_id on dispatcher.consultation_bookings
for each row execute function private.sync_consultation_from_square_booking_v1();

drop trigger if exists consultation_workflow_invoice_sync on public.invoices;
create trigger consultation_workflow_invoice_sync
after update of status,payment_url on public.invoices
for each row execute function private.sync_consultation_from_invoice_v1();

drop trigger if exists consultation_workflow_payment_sync on public.payments;
create trigger consultation_workflow_payment_sync
after insert or update of status on public.payments
for each row execute function private.sync_consultation_from_payment_v1();
