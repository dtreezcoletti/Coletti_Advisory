-- STAGING DRAFT ONLY. NOT A PRODUCTION MIGRATION.
-- Verified model: readiness remains NOT_READY with a reason until all prerequisites exist.
-- Sending remains in the existing consultation-confirmation-email Edge Function.

begin;

alter table public.consultation_workflows
  add column if not exists confirmation_email_reason text;

create or replace function private.refresh_consultation_confirmation_readiness_v1(
  p_consultation_id uuid
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  c public.consultation_workflows%rowtype;
  v_payment_url text;
  v_reason text;
begin
  select * into c
  from public.consultation_workflows
  where id=p_consultation_id
  for update;

  if not found then
    return 'NOT_FOUND';
  end if;

  if c.confirmation_email_state='SENT' then
    return 'SENT';
  end if;

  if c.invoice_id is not null then
    select payment_url into v_payment_url
    from public.invoices
    where id=c.invoice_id;
  end if;

  v_reason := case
    when c.owner_decision <> 'APPROVED_FOR_CONSULTATION' then 'OWNER_APPROVAL_REQUIRED'
    when nullif(c.square_booking_id,'') is null then 'SQUARE_BOOKING_REQUIRED'
    when c.appointment_start is null then 'APPOINTMENT_START_REQUIRED'
    when c.invoice_id is null then 'INVOICE_REQUIRED'
    when nullif(v_payment_url,'') is null then 'SQUARE_PAYMENT_LINK_REQUIRED'
    else null
  end;

  if v_reason is null then
    update public.consultation_workflows
       set confirmation_email_state='READY',
           confirmation_email_reason=null,
           updated_at=now()
     where id=p_consultation_id
       and confirmation_email_state <> 'SENT';
    return 'READY';
  end if;

  update public.consultation_workflows
     set confirmation_email_state='NOT_READY',
         confirmation_email_reason=v_reason,
         updated_at=now()
   where id=p_consultation_id
     and confirmation_email_state <> 'SENT';

  return v_reason;
end
$$;

revoke all on function private.refresh_consultation_confirmation_readiness_v1(uuid)
  from public, anon, authenticated;

create or replace function private.consultation_confirmation_workflow_trigger_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform private.refresh_consultation_confirmation_readiness_v1(new.id);
  return new;
end
$$;

revoke all on function private.consultation_confirmation_workflow_trigger_v1()
  from public, anon, authenticated;

create or replace function private.consultation_confirmation_invoice_trigger_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_consultation_id uuid;
begin
  for v_consultation_id in
    select id
    from public.consultation_workflows
    where invoice_id=new.id
  loop
    perform private.refresh_consultation_confirmation_readiness_v1(v_consultation_id);
  end loop;
  return new;
end
$$;

revoke all on function private.consultation_confirmation_invoice_trigger_v1()
  from public, anon, authenticated;

drop trigger if exists consultation_confirmation_readiness_workflow
  on public.consultation_workflows;

create trigger consultation_confirmation_readiness_workflow
after insert or update of owner_decision,square_booking_id,appointment_start,invoice_id
on public.consultation_workflows
for each row
execute function private.consultation_confirmation_workflow_trigger_v1();

drop trigger if exists consultation_confirmation_readiness_invoice
  on public.invoices;

create trigger consultation_confirmation_readiness_invoice
after insert or update of payment_url
on public.invoices
for each row
execute function private.consultation_confirmation_invoice_trigger_v1();

commit;
