-- Project-to-Supabase reconciliation live controls
-- 2026-10-05
--
-- Scope:
--   1) Fail-close legacy registry.memories.
--   2) Add owner/admin-gated PONS/PORTA runtime RPCs.
--   3) Add Square consultation booking -> Dispatcher calendar-protection bridge.
--   4) Add a narrow consultation-only calendar policy approval.
--
-- This migration does NOT authorize external client production and does NOT
-- create a Square credential, webhook subscription, or Google credential.

-- ---------------------------------------------------------------------------
-- registry.memories: explicit fail-closed posture
-- ---------------------------------------------------------------------------
revoke all on table registry.memories from public;
revoke all on table registry.memories from anon;
revoke all on table registry.memories from authenticated;
revoke all on table registry.memories from service_role;

alter table registry.memories enable row level security;

drop policy if exists memories_fail_closed on registry.memories;
create policy memories_fail_closed
on registry.memories
as restrictive
for all
to public
using (false)
with check (false);

comment on table registry.memories is
'Private legacy memory table. Fail-closed by design as of 2026-10-05: RLS enabled, explicit restrictive deny-all policy, no common API-role grants. Any future access requires an explicit governed policy/grant change.';

-- ---------------------------------------------------------------------------
-- PONS / PORTA runtime
-- ---------------------------------------------------------------------------
create or replace function private.pons_request_transfer_impl_v1(
  p_from_domain_key text,
  p_to_domain_key text,
  p_purpose text,
  p_minimum_necessary jsonb default '{}'::jsonb,
  p_requested_records jsonb default '[]'::jsonb,
  p_privacy_classifications jsonb default '[]'::jsonb,
  p_edict_refs jsonb default '[]'::jsonb
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_from uuid;
  v_to uuid;
  v_request uuid;
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if nullif(btrim(p_purpose),'') is null then
    raise exception 'purpose is required' using errcode='22023';
  end if;

  if upper(coalesce(p_from_domain_key,'')) = upper(coalesce(p_to_domain_key,'')) then
    raise exception 'source and destination domains must differ' using errcode='22023';
  end if;

  select domain_id into v_from
  from registry.domains
  where domain_key=upper(btrim(p_from_domain_key)) and status='ACTIVE';

  select domain_id into v_to
  from registry.domains
  where domain_key=upper(btrim(p_to_domain_key)) and status='ACTIVE';

  if v_from is null or v_to is null then
    raise exception 'active source and destination domains are required' using errcode='22023';
  end if;

  if jsonb_typeof(coalesce(p_requested_records,'[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_privacy_classifications,'[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_edict_refs,'[]'::jsonb)) <> 'array' then
    raise exception 'requested_records, privacy_classifications and edict_refs must be arrays' using errcode='22023';
  end if;

  insert into registry.pons_transfer_requests(
    from_domain_id,to_domain_id,purpose,minimum_necessary,requested_records,
    privacy_classifications,edict_refs,requested_by,status
  ) values (
    v_from,v_to,btrim(p_purpose),coalesce(p_minimum_necessary,'{}'::jsonb),
    coalesce(p_requested_records,'[]'::jsonb),
    coalesce(p_privacy_classifications,'[]'::jsonb),
    coalesce(p_edict_refs,'[]'::jsonb),
    auth.uid(),'PENDING'
  )
  returning transfer_request_id into v_request;

  return v_request;
end;
$$;

create or replace function public.pons_request_transfer_v1(
  p_from_domain_key text,
  p_to_domain_key text,
  p_purpose text,
  p_minimum_necessary jsonb default '{}'::jsonb,
  p_requested_records jsonb default '[]'::jsonb,
  p_privacy_classifications jsonb default '[]'::jsonb,
  p_edict_refs jsonb default '[]'::jsonb
)
returns uuid
language sql
set search_path = ''
as $$
  select private.pons_request_transfer_impl_v1(
    p_from_domain_key,p_to_domain_key,p_purpose,p_minimum_necessary,
    p_requested_records,p_privacy_classifications,p_edict_refs
  );
$$;

create or replace function private.pons_decide_transfer_impl_v1(
  p_transfer_request_id uuid,
  p_decision text,
  p_source_porta_approved boolean default false,
  p_destination_porta_approved boolean default false,
  p_expires_minutes integer default 60
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_req registry.pons_transfer_requests%rowtype;
  v_pathway uuid;
  v_decision text := upper(btrim(coalesce(p_decision,'')));
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if v_decision not in ('APPROVED','DENIED') then
    raise exception 'decision must be APPROVED or DENIED' using errcode='22023';
  end if;

  select * into v_req
  from registry.pons_transfer_requests
  where transfer_request_id=p_transfer_request_id
  for update;

  if not found then
    raise exception 'transfer request not found' using errcode='P0002';
  end if;

  if v_req.status <> 'PENDING' then
    raise exception 'transfer request is not pending' using errcode='22023';
  end if;

  if v_decision='DENIED' then
    update registry.pons_transfer_requests
    set status='DENIED',decided_at=now()
    where transfer_request_id=p_transfer_request_id;
    return null;
  end if;

  if not coalesce(p_source_porta_approved,false)
     or not coalesce(p_destination_porta_approved,false) then
    raise exception 'both source and destination PORTA approvals are required' using errcode='42501';
  end if;

  if p_expires_minutes is null or p_expires_minutes < 5 or p_expires_minutes > 1440 then
    raise exception 'expires_minutes must be between 5 and 1440' using errcode='22023';
  end if;

  insert into registry.domain_pathways(
    from_domain_id,to_domain_id,purpose,scope,matter_ref,permitted_data,
    applicable_policy_refs,authorized_by,authorized_at,expires_at,status,opened_at
  ) values (
    v_req.from_domain_id,
    v_req.to_domain_id,
    v_req.purpose,
    jsonb_build_object(
      'transfer_request_id',v_req.transfer_request_id,
      'source_porta_approved',true,
      'destination_porta_approved',true,
      'minimum_necessary',v_req.minimum_necessary,
      'estates_general_gate','APPROVED'
    ),
    'PONS:'||v_req.transfer_request_id::text,
    v_req.requested_records,
    v_req.edict_refs,
    auth.uid(),
    now(),
    now() + make_interval(mins => p_expires_minutes),
    'OPEN',
    now()
  )
  returning pathway_id into v_pathway;

  update registry.pons_transfer_requests
  set status='APPROVED',decided_at=now()
  where transfer_request_id=p_transfer_request_id;

  return v_pathway;
end;
$$;

create or replace function public.pons_decide_transfer_v1(
  p_transfer_request_id uuid,
  p_decision text,
  p_source_porta_approved boolean default false,
  p_destination_porta_approved boolean default false,
  p_expires_minutes integer default 60
)
returns uuid
language sql
set search_path = ''
as $$
  select private.pons_decide_transfer_impl_v1(
    p_transfer_request_id,p_decision,p_source_porta_approved,
    p_destination_porta_approved,p_expires_minutes
  );
$$;

create or replace function private.pons_record_transfer_impl_v1(
  p_transfer_request_id uuid,
  p_source_ref text,
  p_transferred_representation jsonb,
  p_lineage_refs jsonb default '[]'::jsonb,
  p_classification text default null,
  p_retention_until timestamptz default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_req registry.pons_transfer_requests%rowtype;
  v_pathway registry.domain_pathways%rowtype;
  v_record uuid;
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if nullif(btrim(p_source_ref),'') is null then
    raise exception 'source_ref is required' using errcode='22023';
  end if;

  if jsonb_typeof(coalesce(p_lineage_refs,'[]'::jsonb)) <> 'array' then
    raise exception 'lineage_refs must be an array' using errcode='22023';
  end if;

  select * into v_req
  from registry.pons_transfer_requests
  where transfer_request_id=p_transfer_request_id
  for update;

  if not found then
    raise exception 'transfer request not found' using errcode='P0002';
  end if;

  if v_req.status <> 'APPROVED' then
    raise exception 'transfer request is not approved' using errcode='42501';
  end if;

  select * into v_pathway
  from registry.domain_pathways
  where from_domain_id=v_req.from_domain_id
    and to_domain_id=v_req.to_domain_id
    and matter_ref='PONS:'||v_req.transfer_request_id::text
    and status='OPEN'
    and authorized_at is not null
    and expires_at > now()
    and coalesce((scope->>'source_porta_approved')::boolean,false)=true
    and coalesce((scope->>'destination_porta_approved')::boolean,false)=true
  order by opened_at desc
  limit 1
  for update;

  if not found then
    raise exception 'no active dual-PORTA authorized pathway exists' using errcode='42501';
  end if;

  insert into registry.pons_transfer_records(
    transfer_request_id,source_ref,transferred_representation,lineage_refs,
    classification,retention_until
  ) values (
    p_transfer_request_id,
    btrim(p_source_ref),
    coalesce(p_transferred_representation,'{}'::jsonb),
    coalesce(p_lineage_refs,'[]'::jsonb) || jsonb_build_array(
      jsonb_build_object('pathway_id',v_pathway.pathway_id),
      jsonb_build_object('transfer_request_id',p_transfer_request_id),
      jsonb_build_object('estates_general_gate','APPROVED')
    ),
    p_classification,
    p_retention_until
  )
  returning transfer_record_id into v_record;

  return v_record;
end;
$$;

create or replace function public.pons_record_transfer_v1(
  p_transfer_request_id uuid,
  p_source_ref text,
  p_transferred_representation jsonb,
  p_lineage_refs jsonb default '[]'::jsonb,
  p_classification text default null,
  p_retention_until timestamptz default null
)
returns uuid
language sql
set search_path = ''
as $$
  select private.pons_record_transfer_impl_v1(
    p_transfer_request_id,p_source_ref,p_transferred_representation,
    p_lineage_refs,p_classification,p_retention_until
  );
$$;

create or replace function private.pons_close_pathway_impl_v1(
  p_pathway_id uuid,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null or not private.is_admin() then
    raise exception 'not authorized' using errcode='42501';
  end if;

  if length(btrim(coalesce(p_reason,''))) < 10 then
    raise exception 'closure reason must be at least 10 characters' using errcode='22023';
  end if;

  update registry.domain_pathways
  set status='CLOSED',
      closed_at=now(),
      closure_reason=btrim(p_reason),
      updated_at=now()
  where pathway_id=p_pathway_id and status='OPEN';

  if not found then
    raise exception 'open pathway not found' using errcode='P0002';
  end if;
end;
$$;

create or replace function public.pons_close_pathway_v1(
  p_pathway_id uuid,
  p_reason text
)
returns void
language sql
set search_path = ''
as $$
  select private.pons_close_pathway_impl_v1(p_pathway_id,p_reason);
$$;

revoke all on function public.pons_request_transfer_v1(text,text,text,jsonb,jsonb,jsonb,jsonb) from public,anon;
revoke all on function public.pons_decide_transfer_v1(uuid,text,boolean,boolean,integer) from public,anon;
revoke all on function public.pons_record_transfer_v1(uuid,text,jsonb,jsonb,text,timestamptz) from public,anon;
revoke all on function public.pons_close_pathway_v1(uuid,text) from public,anon;

grant execute on function public.pons_request_transfer_v1(text,text,text,jsonb,jsonb,jsonb,jsonb) to authenticated;
grant execute on function public.pons_decide_transfer_v1(uuid,text,boolean,boolean,integer) to authenticated;
grant execute on function public.pons_record_transfer_v1(uuid,text,jsonb,jsonb,text,timestamptz) to authenticated;
grant execute on function public.pons_close_pathway_v1(uuid,text) to authenticated;

-- ---------------------------------------------------------------------------
-- Square consultation -> Dispatcher calendar protection bridge
-- ---------------------------------------------------------------------------
create table if not exists dispatcher.consultation_bookings (
  booking_id uuid primary key default gen_random_uuid(),
  provider text not null default 'square',
  provider_booking_id text not null,
  service_key text,
  client_ref text,
  start_at timestamptz,
  end_at timestamptz,
  timezone text not null default 'America/Chicago',
  booking_state text not null default 'BOOKED'
    check (booking_state in ('BOOKED','CONFIRMED','UPDATED','RESCHEDULED','CANCELLED','COMPLETED')),
  payment_state text,
  google_event_id text,
  protection_calendar_command_id uuid references dispatcher.calendar_commands(command_id),
  protection_event_id text,
  last_event_type text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider,provider_booking_id)
);

revoke all on table dispatcher.consultation_bookings from public,anon,authenticated;
revoke all on table dispatcher.consultation_bookings from service_role;

create or replace function dispatcher.policy_approve_consultation_calendar_command(
  p_command_id uuid
)
returns dispatcher.calendar_commands
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_cmd dispatcher.calendar_commands%rowtype;
  v_req dispatcher.execution_requests%rowtype;
begin
  select * into v_cmd
  from dispatcher.calendar_commands
  where command_id=p_command_id
  for update;

  if not found then
    raise exception 'calendar command not found' using errcode='P0002';
  end if;

  if v_cmd.requested_by <> 'square_consultation_bridge'
     or v_cmd.title <> 'Consultation Morning — Protected'
     or v_cmd.operation not in ('CREATE','DELETE','RECONCILE')
     or coalesce(v_cmd.params->>'source','') <> 'square_consultation_bridge' then
    raise exception 'command is outside consultation calendar policy scope' using errcode='42501';
  end if;

  update dispatcher.execution_requests
  set approval_state='POLICY_APPROVED',
      updated_at=now()
  where request_id=v_cmd.execution_request_id
  returning * into v_req;

  insert into dispatcher.execution_events(request_id,event_type,actor,details)
  values (
    v_req.request_id,
    'POLICY_APPROVED',
    'consultation-calendar-rule',
    jsonb_build_object(
      'rule','dispatcher.consultation.booking_calendar_control.v1',
      'calendar_command_id',v_cmd.command_id,
      'scope','Consultation Morning — Protected only'
    )
  );

  v_req := dispatcher.route_execution_request(v_req.request_id);

  update dispatcher.calendar_commands
  set state=v_req.state,
      approval_state=v_req.approval_state,
      updated_at=now()
  where command_id=v_cmd.command_id
  returning * into v_cmd;

  return v_cmd;
end;
$$;

revoke all on function dispatcher.policy_approve_consultation_calendar_command(uuid)
from public,anon,authenticated,service_role;

create or replace function private.square_consultation_event_impl_v1(
  p_provider_booking_id text,
  p_event_type text,
  p_start_at timestamptz default null,
  p_end_at timestamptz default null,
  p_timezone text default 'America/Chicago',
  p_google_event_id text default null,
  p_payment_state text default null,
  p_service_key text default null,
  p_client_ref text default null,
  p_payload jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_role text := coalesce((current_setting('request.jwt.claims',true)::jsonb)->>'role','');
  v_event text := upper(btrim(coalesce(p_event_type,'')));
  v_tz text := coalesce(nullif(btrim(p_timezone),''),'America/Chicago');
  v_existing dispatcher.consultation_bookings%rowtype;
  v_old_event_id text;
  v_old_date date;
  v_new_date date;
  v_protect_start timestamptz;
  v_protect_end timestamptz;
  v_cmd dispatcher.calendar_commands;
  v_cleanup_cmd dispatcher.calendar_commands;
  v_booking dispatcher.consultation_bookings%rowtype;
begin
  if v_role <> 'service_role' then
    raise exception 'service role required' using errcode='42501';
  end if;

  if nullif(btrim(p_provider_booking_id),'') is null then
    raise exception 'provider_booking_id is required' using errcode='22023';
  end if;

  if v_event not in ('BOOKED','CONFIRMED','UPDATED','RESCHEDULED','CANCELLED','COMPLETED') then
    raise exception 'unsupported consultation event type' using errcode='22023';
  end if;

  select * into v_existing
  from dispatcher.consultation_bookings
  where provider='square' and provider_booking_id=btrim(p_provider_booking_id)
  for update;

  if found then
    v_old_date := case when v_existing.start_at is null then null
                       else (v_existing.start_at at time zone v_existing.timezone)::date end;
    v_old_event_id := coalesce(
      v_existing.protection_event_id,
      (
        select result->>'event_id'
        from dispatcher.calendar_commands
        where command_id=v_existing.protection_calendar_command_id
          and result ? 'event_id'
      )
    );
  end if;

  if v_event in ('BOOKED','CONFIRMED','UPDATED','RESCHEDULED') then
    if p_start_at is null or p_end_at is null or p_end_at <= p_start_at then
      raise exception 'valid start_at and end_at are required for active bookings' using errcode='22023';
    end if;

    v_new_date := (p_start_at at time zone v_tz)::date;
    v_protect_start := (v_new_date + time '08:00') at time zone v_tz;
    v_protect_end := (v_new_date + time '12:00') at time zone v_tz;

    if v_old_date is not null and v_old_date <> v_new_date and v_old_event_id is not null then
      v_cleanup_cmd := dispatcher.stage_calendar_command(
        'DELETE','square_consultation_bridge',
        'Remove the prior consultation-morning protection after a Square reschedule.',
        'Consultation Morning — Protected',null,null,v_existing.timezone,'primary',
        v_old_event_id,
        jsonb_build_object(
          'source','square_consultation_bridge',
          'provider_booking_id',p_provider_booking_id,
          'reason','RESCHEDULED'
        ),
        'consultation-protection:delete:'||p_provider_booking_id||':'||v_old_date::text
      );
      v_cleanup_cmd := dispatcher.policy_approve_consultation_calendar_command(v_cleanup_cmd.command_id);
    end if;

    v_cmd := dispatcher.stage_calendar_command(
      'CREATE','square_consultation_bridge',
      'Protect the consultation morning on the master Google Calendar. Do not create a duplicate consultation appointment.',
      'Consultation Morning — Protected',
      v_protect_start,v_protect_end,v_tz,'primary',null,
      jsonb_build_object(
        'source','square_consultation_bridge',
        'provider','square',
        'provider_booking_id',p_provider_booking_id,
        'square_google_event_id',p_google_event_id,
        'consultation_start_at',p_start_at,
        'consultation_end_at',p_end_at,
        'busy',true,
        'duplicate_consultation_event_prohibited',true
      ),
      'consultation-protection:create:'||p_provider_booking_id||':'||v_new_date::text
    );
    v_cmd := dispatcher.policy_approve_consultation_calendar_command(v_cmd.command_id);

    insert into dispatcher.consultation_bookings(
      provider,provider_booking_id,service_key,client_ref,start_at,end_at,timezone,
      booking_state,payment_state,google_event_id,protection_calendar_command_id,
      last_event_type,payload,updated_at
    ) values (
      'square',btrim(p_provider_booking_id),p_service_key,p_client_ref,p_start_at,p_end_at,v_tz,
      v_event,p_payment_state,p_google_event_id,v_cmd.command_id,
      v_event,coalesce(p_payload,'{}'::jsonb),now()
    )
    on conflict(provider,provider_booking_id) do update set
      service_key=coalesce(excluded.service_key,dispatcher.consultation_bookings.service_key),
      client_ref=coalesce(excluded.client_ref,dispatcher.consultation_bookings.client_ref),
      start_at=excluded.start_at,
      end_at=excluded.end_at,
      timezone=excluded.timezone,
      booking_state=excluded.booking_state,
      payment_state=coalesce(excluded.payment_state,dispatcher.consultation_bookings.payment_state),
      google_event_id=coalesce(excluded.google_event_id,dispatcher.consultation_bookings.google_event_id),
      protection_calendar_command_id=excluded.protection_calendar_command_id,
      last_event_type=excluded.last_event_type,
      payload=excluded.payload,
      updated_at=now()
    returning * into v_booking;

  else
    if not found then
      raise exception 'consultation booking not found' using errcode='P0002';
    end if;

    if v_event='CANCELLED' and v_old_event_id is not null then
      v_cleanup_cmd := dispatcher.stage_calendar_command(
        'DELETE','square_consultation_bridge',
        'Remove consultation-morning protection after Square cancellation.',
        'Consultation Morning — Protected',null,null,v_existing.timezone,'primary',
        v_old_event_id,
        jsonb_build_object(
          'source','square_consultation_bridge',
          'provider_booking_id',p_provider_booking_id,
          'reason','CANCELLED'
        ),
        'consultation-protection:cancel:'||p_provider_booking_id
      );
      v_cleanup_cmd := dispatcher.policy_approve_consultation_calendar_command(v_cleanup_cmd.command_id);
    elsif v_event='CANCELLED' and v_old_event_id is null then
      v_cleanup_cmd := dispatcher.stage_calendar_command(
        'RECONCILE','square_consultation_bridge',
        'Reconcile and remove any consultation-morning protection associated with the cancelled Square booking. Do not alter unrelated events.',
        'Consultation Morning — Protected',null,null,v_existing.timezone,'primary',null,
        jsonb_build_object(
          'source','square_consultation_bridge',
          'provider_booking_id',p_provider_booking_id,
          'reason','CANCELLED_WITHOUT_BOUND_EVENT_ID',
          'prior_protection_command_id',v_existing.protection_calendar_command_id
        ),
        'consultation-protection:reconcile-cancel:'||p_provider_booking_id
      );
      v_cleanup_cmd := dispatcher.policy_approve_consultation_calendar_command(v_cleanup_cmd.command_id);
    end if;

    update dispatcher.consultation_bookings
    set booking_state=v_event,
        payment_state=coalesce(p_payment_state,payment_state),
        google_event_id=coalesce(p_google_event_id,google_event_id),
        last_event_type=v_event,
        payload=coalesce(p_payload,'{}'::jsonb),
        updated_at=now()
    where booking_id=v_existing.booking_id
    returning * into v_booking;
  end if;

  return jsonb_build_object(
    'booking_id',v_booking.booking_id,
    'provider_booking_id',v_booking.provider_booking_id,
    'booking_state',v_booking.booking_state,
    'protection_calendar_command_id',v_booking.protection_calendar_command_id,
    'protection_command_state',case when v_cmd.command_id is null then null else v_cmd.state end,
    'protection_approval_state',case when v_cmd.command_id is null then null else v_cmd.approval_state end,
    'cleanup_calendar_command_id',case when v_cleanup_cmd.command_id is null then null else v_cleanup_cmd.command_id end,
    'cleanup_command_state',case when v_cleanup_cmd.command_id is null then null else v_cleanup_cmd.state end,
    'google_event_id',v_booking.google_event_id,
    'protection_title','Consultation Morning — Protected',
    'master_calendar','primary',
    'duplicate_consultation_event_created',false
  );
end;
$$;

create or replace function public.square_consultation_event_v1(
  p_provider_booking_id text,
  p_event_type text,
  p_start_at timestamptz default null,
  p_end_at timestamptz default null,
  p_timezone text default 'America/Chicago',
  p_google_event_id text default null,
  p_payment_state text default null,
  p_service_key text default null,
  p_client_ref text default null,
  p_payload jsonb default '{}'::jsonb
)
returns jsonb
language sql
security definer
set search_path = ''
as $$
  select private.square_consultation_event_impl_v1(
    p_provider_booking_id,p_event_type,p_start_at,p_end_at,p_timezone,
    p_google_event_id,p_payment_state,p_service_key,p_client_ref,p_payload
  );
$$;

revoke all on function private.square_consultation_event_impl_v1(text,text,timestamptz,timestamptz,text,text,text,text,text,jsonb)
from public,anon,authenticated;
revoke all on function public.square_consultation_event_v1(text,text,timestamptz,timestamptz,text,text,text,text,text,jsonb)
from public,anon,authenticated;
grant execute on function public.square_consultation_event_v1(text,text,timestamptz,timestamptz,text,text,text,text,text,jsonb)
to service_role;
