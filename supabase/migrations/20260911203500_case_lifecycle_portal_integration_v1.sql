-- Canonical cross-portal Case lifecycle checkpoint model.
-- One authoritative state is rendered differently for Client, Employee, Admin, and Owner.

create table public.case_lifecycle_checkpoint_catalog (
  checkpoint_key text primary key,
  sequence_no integer not null unique,
  label text not null,
  client_label text not null,
  responsible_domain text not null,
  description text not null,
  client_description text not null,
  client_visible boolean not null default true,
  required boolean not null default true,
  protected_gate boolean not null default false
);

insert into public.case_lifecycle_checkpoint_catalog
(checkpoint_key,sequence_no,label,client_label,responsible_domain,description,client_description,client_visible,required,protected_gate)
values
('INTAKE',10,'Intake','Intake','Clients','Prospect/intake information is submitted and preserved.','Your intake information has been received and is being handled through the controlled intake process.',true,true,true),
('SCREENING',20,'Screening & Review','Review','Clients','Scope, completeness, boundary, referral, and duplicate checks are reviewed.','Coletti & Co. is reviewing scope, completeness, and fit before engagement work begins.',true,true,true),
('ACCEPTANCE',30,'Acceptance Decision','Engagement Decision','Clients','Owner/Admin records the final acceptance decision.','The engagement decision has been recorded through the controlled acceptance process.',true,true,true),
('CLIENT_ONBOARDING',40,'Client Onboarding','Onboarding','Clients','Permanent Client relationship, portal access, and onboarding controls are established.','Your secure relationship and access are being prepared.',true,true,true),
('ENGAGEMENT_GATES',50,'Pricing + Contract + Scope','Engagement Setup','Back Office','Pricing, controlled contract, and engagement scope are confirmed before substantive Case work.','Pricing, engagement terms, and scope are confirmed before substantive work begins.',true,true,true),
('CASE_OPENING',60,'Case Opening','Case Opened','Cases','Canonical Case identity, access, and assignments are established.','Your Case workspace has been opened with controlled access.',true,true,true),
('RECORD_COLLECTION',70,'Record Collection','Record Collection','Records','Case-scoped source universe is collected, registered, and provenance preserved.','Records are being securely collected and organized for your Case.',true,true,false),
('RECONSTRUCTION',80,'Reconstruction / Analysis','Reconstruction','ColettiOS','Records are reconstructed, reconciled, and analyzed under First Truth controls.','Coletti & Co. is reconstructing and reconciling the record.',true,true,false),
('HUMAN_REVIEW',90,'Human Review','Human Review','Review','Required human review resolves or dispositions findings, contradictions, and publication gates.','The reconstructed record is undergoing required human review.',true,true,false),
('REPORT_PREPARATION',100,'Report Preparation','Report Preparation','Reports','Controlled deliverables are prepared from reviewed record state.','Your controlled deliverable is being prepared from reviewed records.',true,true,false),
('PUBLICATION_HANDOFF',110,'Publication / Professional Handoff','Delivery','Reports','Approved deliverables are published and any professional handoff is explicitly authorized.','Approved deliverables are made available and any professional handoff is prepared when applicable.',true,true,true),
('CLOSEOUT',120,'Case Closeout','Closeout','Cases','Open requests, deliverables, access, billing/handoff obligations, and retention state are dispositioned.','Your Case is being formally closed out after the required work and delivery steps.',true,true,true),
('ARCHIVE',130,'Archive','Archived','Cases','Historical Case state is retained without deleting institutional history.','The completed Case is retained as a historical record under controlled access.',true,true,true);

create table public.case_lifecycle_checkpoints (
  case_id text not null references registry.cases(case_id) on delete cascade,
  checkpoint_key text not null references public.case_lifecycle_checkpoint_catalog(checkpoint_key) on delete restrict,
  status text not null default 'NOT_STARTED'
    check (status in ('NOT_STARTED','READY','IN_PROGRESS','WAITING','BLOCKED','AWAITING_HUMAN','COMPLETE','NOT_APPLICABLE')),
  public_note text,
  internal_note text,
  blocking_reason text,
  completed_by uuid references auth.users(id),
  completed_at timestamptz,
  last_transition_by uuid references auth.users(id),
  last_transition_at timestamptz,
  source_system text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(case_id, checkpoint_key)
);

create index case_lifecycle_checkpoints_status_idx on public.case_lifecycle_checkpoints(status, updated_at desc);
create index case_lifecycle_checkpoints_transition_by_idx on public.case_lifecycle_checkpoints(last_transition_by) where last_transition_by is not null;
create index case_lifecycle_checkpoints_completed_by_idx on public.case_lifecycle_checkpoints(completed_by) where completed_by is not null;

create table public.case_lifecycle_events (
  id uuid primary key default gen_random_uuid(),
  case_id text not null references registry.cases(case_id) on delete cascade,
  checkpoint_key text not null references public.case_lifecycle_checkpoint_catalog(checkpoint_key) on delete restrict,
  prior_status text,
  new_status text not null,
  actor_user_id uuid references auth.users(id),
  actor_role text,
  reason text,
  public_note text,
  source_system text not null default 'PORTAL_LIFECYCLE',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index case_lifecycle_events_case_time_idx on public.case_lifecycle_events(case_id, created_at desc);
create index case_lifecycle_events_actor_idx on public.case_lifecycle_events(actor_user_id) where actor_user_id is not null;

alter table public.case_lifecycle_checkpoint_catalog enable row level security;
alter table public.case_lifecycle_checkpoints enable row level security;
alter table public.case_lifecycle_events enable row level security;

revoke all on public.case_lifecycle_checkpoint_catalog from anon, authenticated;
revoke all on public.case_lifecycle_checkpoints from anon, authenticated;
revoke all on public.case_lifecycle_events from anon, authenticated;

create trigger trg_case_lifecycle_checkpoint_updated
before update on public.case_lifecycle_checkpoints
for each row execute function private.set_updated_at();

create or replace function private.seed_case_lifecycle(target_case_id text)
returns void
language sql
security definer
set search_path=''
as $$
  insert into public.case_lifecycle_checkpoints(case_id,checkpoint_key,status,source_system)
  select target_case_id,c.checkpoint_key,
    case when c.checkpoint_key='CASE_OPENING' then 'COMPLETE' else 'NOT_STARTED' end,
    'CASE_LIFECYCLE_SEED'
  from public.case_lifecycle_checkpoint_catalog c
  where exists(select 1 from registry.cases rc where rc.case_id=target_case_id)
  on conflict(case_id,checkpoint_key) do nothing;
$$;
revoke all on function private.seed_case_lifecycle(text) from public, anon, authenticated;

create or replace function private.seed_case_lifecycle_trigger()
returns trigger
language plpgsql
security definer
set search_path=''
as $$
begin
  perform private.seed_case_lifecycle(new.case_id);
  return new;
end;
$$;

create trigger trg_seed_case_lifecycle
after insert on registry.cases
for each row execute function private.seed_case_lifecycle_trigger();

select private.seed_case_lifecycle(c.case_id) from registry.cases c;

create or replace function private.set_lifecycle_signal(
  p_case_id text,
  p_checkpoint_key text,
  p_status text,
  p_note text,
  p_source text
)
returns void
language plpgsql
security definer
set search_path=''
as $$
declare old_status text;
begin
  select status into old_status
  from public.case_lifecycle_checkpoints
  where case_id=p_case_id and checkpoint_key=p_checkpoint_key
  for update;

  if old_status is null then return; end if;
  if p_status='IN_PROGRESS' and old_status not in ('NOT_STARTED','READY','WAITING') then return; end if;
  if p_status='COMPLETE' and old_status in ('COMPLETE','NOT_APPLICABLE') then return; end if;
  if p_status='COMPLETE' and p_checkpoint_key not in ('INTAKE','ACCEPTANCE','CASE_OPENING','PUBLICATION_HANDOFF','CLOSEOUT','ARCHIVE') then return; end if;

  update public.case_lifecycle_checkpoints
  set status=p_status,
      public_note=coalesce(public_note,p_note),
      source_system=p_source,
      last_transition_at=now(),
      completed_at=case when p_status='COMPLETE' then coalesce(completed_at,now()) else completed_at end
  where case_id=p_case_id and checkpoint_key=p_checkpoint_key;

  if old_status is distinct from p_status then
    insert into public.case_lifecycle_events(case_id,checkpoint_key,prior_status,new_status,reason,public_note,source_system,metadata)
    values(p_case_id,p_checkpoint_key,old_status,p_status,'Deterministic authoritative-state signal',p_note,p_source,jsonb_build_object('automatic',true));
  end if;
end;
$$;
revoke all on function private.set_lifecycle_signal(text,text,text,text,text) from public, anon, authenticated;

create or replace function public.refresh_case_lifecycle_v1(p_case_id text)
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare c registry.cases%rowtype; client_status text; accepted_intake boolean; in_review_intake boolean; executed_contract boolean;
begin
  if auth.uid() is null or not private.can_access_case(p_case_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  select * into c from registry.cases where case_id=p_case_id;
  if not found then raise exception 'case not found' using errcode='P0002'; end if;
  perform private.seed_case_lifecycle(p_case_id);

  select rc.status into client_status from registry.clients rc where rc.client_id=c.client_id;
  select exists(select 1 from public.intake_submissions i where i.case_id=p_case_id and i.status='ACCEPTED') into accepted_intake;
  select exists(select 1 from public.intake_submissions i where i.case_id=p_case_id and i.status in ('IN_REVIEW','ACCEPTED')) into in_review_intake;
  select exists(select 1 from public.contract_records cr where cr.case_id=p_case_id and cr.status='EXECUTED')
      or exists(select 1 from registry.contracts rc where rc.case_id=p_case_id and rc.contract_status in ('EXECUTED','ACTIVE') and rc.executed_at is not null)
    into executed_contract;

  if in_review_intake then perform private.set_lifecycle_signal(p_case_id,'SCREENING','IN_PROGRESS','Intake review activity is recorded.','INTAKE'); end if;
  if accepted_intake then
    perform private.set_lifecycle_signal(p_case_id,'INTAKE','COMPLETE','Accepted intake is linked to this Case.','INTAKE');
    perform private.set_lifecycle_signal(p_case_id,'ACCEPTANCE','COMPLETE','Acceptance is recorded for the linked intake.','INTAKE');
  end if;
  if client_status='ACTIVE' then perform private.set_lifecycle_signal(p_case_id,'CLIENT_ONBOARDING','IN_PROGRESS','The Client relationship is active; onboarding completion remains a controlled checkpoint.','CLIENTS');
  elsif client_status='ONBOARDING' then perform private.set_lifecycle_signal(p_case_id,'CLIENT_ONBOARDING','IN_PROGRESS','Client onboarding is in progress.','CLIENTS'); end if;
  if executed_contract then perform private.set_lifecycle_signal(p_case_id,'ENGAGEMENT_GATES','IN_PROGRESS','An executed contract is recorded; final pricing/scope gate confirmation remains controlled.','CONTRACTS'); end if;

  perform private.set_lifecycle_signal(p_case_id,'CASE_OPENING','COMPLETE','Canonical Case identity exists.','REGISTRY');

  if exists(select 1 from registry.sources s where s.case_id=p_case_id) then
    perform private.set_lifecycle_signal(p_case_id,'RECORD_COLLECTION','IN_PROGRESS','Case-scoped Records have been registered.','REGISTRY');
  end if;
  if exists(select 1 from registry.propositions p where p.case_id=p_case_id)
     or exists(select 1 from registry.findings f where f.case_id=p_case_id) then
    perform private.set_lifecycle_signal(p_case_id,'RECONSTRUCTION','IN_PROGRESS','Source-linked reconstruction activity is recorded.','REGISTRY');
  end if;
  if exists(select 1 from registry.reviews r where r.case_id=p_case_id) then
    perform private.set_lifecycle_signal(p_case_id,'HUMAN_REVIEW','IN_PROGRESS','Human review activity is recorded.','REGISTRY');
  end if;
  if exists(select 1 from registry.reports r where r.case_id=p_case_id) then
    perform private.set_lifecycle_signal(p_case_id,'REPORT_PREPARATION','IN_PROGRESS','A controlled report record exists.','REGISTRY');
  end if;
  if exists(select 1 from public.published_reports pr where pr.case_id=p_case_id and pr.revoked_at is null)
     or exists(select 1 from registry.reports rr where rr.case_id=p_case_id and rr.publication_status in ('PUBLISHED','DELIVERED')) then
    perform private.set_lifecycle_signal(p_case_id,'PUBLICATION_HANDOFF','COMPLETE','An approved publication/delivery record exists.','PUBLICATION');
  end if;
  if c.closed_on is not null or upper(c.status) in ('CLOSED','ARCHIVED') then
    perform private.set_lifecycle_signal(p_case_id,'CLOSEOUT','COMPLETE','The authoritative Case record is closed.','REGISTRY');
  end if;
  if upper(c.status)='ARCHIVED' then
    perform private.set_lifecycle_signal(p_case_id,'ARCHIVE','COMPLETE','The authoritative Case record is archived.','REGISTRY');
  end if;

  return jsonb_build_object('case_id',p_case_id,'refreshed',true);
end;
$$;
revoke all on function public.refresh_case_lifecycle_v1(text) from public, anon;
grant execute on function public.refresh_case_lifecycle_v1(text) to authenticated;

create or replace function public.case_lifecycle_snapshot_v1(p_case_id text)
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare result jsonb; role_name text; is_internal boolean;
begin
  if auth.uid() is null or not private.can_access_case(p_case_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  perform public.refresh_case_lifecycle_v1(p_case_id);
  role_name:=coalesce(private.current_user_role(),'client');
  is_internal:=role_name in ('owner','admin','analyst','reviewer');

  select jsonb_build_object(
    'case',jsonb_build_object(
      'case_id',c.case_id,'client_id',c.client_id,'status',c.status,'opened_on',c.opened_on,'closed_on',c.closed_on,
      'current_checkpoint',(
        select cp.checkpoint_key from public.case_lifecycle_checkpoints cp
        join public.case_lifecycle_checkpoint_catalog cat using(checkpoint_key)
        where cp.case_id=c.case_id and cp.status not in ('COMPLETE','NOT_APPLICABLE')
          and (is_internal or cat.client_visible)
        order by cat.sequence_no limit 1
      )
    ),
    'checkpoints',coalesce((
      select jsonb_agg(jsonb_build_object(
        'key',cat.checkpoint_key,
        'sequence',cat.sequence_no,
        'label',case when is_internal then cat.label else cat.client_label end,
        'domain',case when is_internal then cat.responsible_domain else null end,
        'description',case when is_internal then cat.description else cat.client_description end,
        'status',cp.status,
        'protected_gate',case when is_internal then cat.protected_gate else null end,
        'required',cat.required,
        'public_note',cp.public_note,
        'internal_note',case when is_internal then cp.internal_note else null end,
        'blocking_reason',case when is_internal then cp.blocking_reason else null end,
        'completed_at',cp.completed_at,
        'updated_at',cp.updated_at
      ) order by cat.sequence_no)
      from public.case_lifecycle_checkpoints cp
      join public.case_lifecycle_checkpoint_catalog cat using(checkpoint_key)
      where cp.case_id=c.case_id and (is_internal or cat.client_visible)
    ),'[]'::jsonb),
    'open_requests',(select count(*) from public.document_requests dr where dr.case_id=c.case_id and dr.status not in ('SATISFIED','WAIVED') and (is_internal or dr.client_visible)),
    'published_reports',(select count(*) from public.published_reports pr where pr.case_id=c.case_id and pr.revoked_at is null and (is_internal or pr.client_visible)),
    'message_count',(select count(*) from public.portal_messages pm where pm.case_id=c.case_id and (is_internal or pm.thread_type='CLIENT')),
    'viewer_role',role_name
  ) into result
  from registry.cases c where c.case_id=p_case_id;

  if result is null then raise exception 'case not found' using errcode='P0002'; end if;
  return result;
end;
$$;
revoke all on function public.case_lifecycle_snapshot_v1(text) from public, anon;
grant execute on function public.case_lifecycle_snapshot_v1(text) to authenticated;

create or replace function public.transition_case_checkpoint_v1(
  p_case_id text,
  p_checkpoint_key text,
  p_target_status text,
  p_reason text default null,
  p_public_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare role_name text; cat public.case_lifecycle_checkpoint_catalog%rowtype; cp public.case_lifecycle_checkpoints%rowtype; prior_missing text; actor uuid;
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

  if p_target_status='COMPLETE' then
    select prior_cat.label into prior_missing
    from public.case_lifecycle_checkpoint_catalog prior_cat
    join public.case_lifecycle_checkpoints prior_cp on prior_cp.checkpoint_key=prior_cat.checkpoint_key and prior_cp.case_id=p_case_id
    where prior_cat.sequence_no<cat.sequence_no and prior_cat.required
      and prior_cp.status not in ('COMPLETE','NOT_APPLICABLE')
    order by prior_cat.sequence_no limit 1;
    if prior_missing is not null then
      raise exception 'prior lifecycle checkpoint incomplete: %',prior_missing using errcode='23514';
    end if;
  end if;

  select * into cp from public.case_lifecycle_checkpoints where case_id=p_case_id and checkpoint_key=p_checkpoint_key for update;

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
revoke all on function public.transition_case_checkpoint_v1(text,text,text,text,text) from public, anon;
grant execute on function public.transition_case_checkpoint_v1(text,text,text,text,text) to authenticated;
