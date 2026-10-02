-- Queue Dispatcher morning/evening briefs for audited Resend delivery.
-- Delivery itself is intentionally separate: this migration creates exactly-once
-- QUEUED records and a DST-safe scheduler, but does not embed provider credentials.

create extension if not exists pg_cron with schema pg_catalog;
grant usage on schema cron to postgres;
grant all privileges on all tables in schema cron to postgres;

create or replace function private.queue_operational_brief_emails_v1(
  p_now timestamptz default now()
)
returns jsonb
language plpgsql
security definer
set search_path = 'pg_catalog', 'private', 'registry', 'dispatcher'
as $function$
declare
  local_now timestamp;
  local_day date;
  queued_count integer := 0;
begin
  local_now := p_now at time zone 'America/Chicago';
  local_day := local_now::date;

  with eligible as (
    select
      b.brief_id,
      b.local_date,
      b.brief_type,
      b.scheduled_local_time,
      b.content_ref,
      b.state_snapshot,
      case
        when b.brief_type='MORNING' then 'DAILY_0900'
        when b.brief_type='EVENING' then 'DAILY_1900'
      end as email_type
    from dispatcher.brief_runs b
    where b.local_date = local_day
      and b.valid_workday = true
      and b.status = 'ISSUED'
      and b.brief_type in ('MORNING','EVENING')
      and b.scheduled_local_time <= local_now::time
  ),
  ins as (
    insert into registry.operational_email_runs(
      email_type,
      local_date,
      intended_local_time,
      recipient_ref,
      provider,
      idempotency_key,
      status,
      content_hash,
      metadata
    )
    select
      e.email_type,
      e.local_date,
      e.scheduled_local_time,
      'OWNER_PRIMARY',
      'resend',
      'operational-brief:' || e.local_date::text || ':' || lower(e.brief_type),
      'QUEUED',
      encode(extensions.digest(
        coalesce(e.content_ref,'') || '|' || coalesce(e.state_snapshot::text,''),
        'sha256'
      ), 'hex'),
      jsonb_build_object(
        'brief_id', e.brief_id,
        'brief_type', e.brief_type,
        'content_ref', e.content_ref,
        'state_snapshot', e.state_snapshot,
        'queued_by', 'private.queue_operational_brief_emails_v1',
        'timezone', 'America/Chicago'
      )
    from eligible e
    where e.email_type is not null
    on conflict (idempotency_key) do nothing
    returning 1
  )
  select count(*) into queued_count from ins;

  return jsonb_build_object(
    'local_date', local_day,
    'local_time', local_now::time,
    'queued_count', queued_count
  );
end;
$function$;

revoke all on function private.queue_operational_brief_emails_v1(timestamptz) from public, anon, authenticated;
grant execute on function private.queue_operational_brief_emails_v1(timestamptz) to postgres;

do $$
declare
  existing_job bigint;
begin
  select jobid into existing_job
  from cron.job
  where jobname='queue-operational-brief-emails-v1'
  limit 1;

  if existing_job is not null then
    perform cron.unschedule(existing_job);
  end if;

  perform cron.schedule(
    'queue-operational-brief-emails-v1',
    '*/10 * * * *',
    'select private.queue_operational_brief_emails_v1();'
  );
end
$$;
