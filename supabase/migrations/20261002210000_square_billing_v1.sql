begin;

alter table public.invoices
  add column if not exists provider_order_id text,
  add column if not exists provider_payment_link_id text;

alter table public.payments
  add column if not exists provider_order_id text,
  add column if not exists updated_at timestamptz not null default now();

create unique index if not exists payments_provider_payment_uidx
  on public.payments (provider, provider_payment_id);

create table if not exists public.payment_refunds (
  id uuid primary key default gen_random_uuid(),
  payment_id uuid not null references public.payments(id) on delete cascade,
  amount_cents bigint not null check (amount_cents >= 0),
  status text not null default 'PENDING'
    check (status in ('PENDING','SUCCEEDED','FAILED')),
  provider text not null,
  provider_refund_id text not null,
  refunded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, provider_refund_id)
);

alter table public.payment_refunds enable row level security;

drop policy if exists payment_refunds_select on public.payment_refunds;
create policy payment_refunds_select
  on public.payment_refunds
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.payments p
      join public.invoices i on i.id = p.invoice_id
      where p.id = payment_refunds.payment_id
        and (
          i.client_user_id = (select auth.uid())
          or private.is_admin()
          or (i.case_id is not null and private.can_work_case(i.case_id))
        )
    )
  );

create table if not exists public.payment_provider_events (
  provider text not null,
  event_id text not null,
  event_type text not null,
  object_id text,
  provider_order_id text,
  provider_status text,
  processing_status text not null default 'RECEIVED'
    check (processing_status in ('RECEIVED','PROCESSED','IGNORED','FAILED')),
  event_version text,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  error_message text,
  primary key (provider, event_id)
);

comment on table public.payment_provider_events is
  'Idempotency and processing ledger for external payment-provider webhook events. Stores identifiers/status only; no card data or raw webhook payloads.';

alter table public.payment_provider_events enable row level security;
revoke all on public.payment_provider_events from anon, authenticated;

commit;
