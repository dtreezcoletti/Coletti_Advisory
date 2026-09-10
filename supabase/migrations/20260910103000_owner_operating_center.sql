create table if not exists public.owner_work_items (
  id uuid primary key default gen_random_uuid(),
  category text not null check (category in ('SINCE_YESTERDAY','DUE_TODAY','DECISION','CARRYOVER','BLOCKER','CAPACITY','SUCCESS_DEFINITION','FIX','GENERAL')),
  title text not null,
  description text,
  status text not null default 'OPEN' check (status in ('OPEN','IN_PROGRESS','WAITING','BLOCKED','READY_FOR_APPROVAL','COMPLETED','CANCELLED')),
  priority text not null default 'NORMAL' check (priority in ('LOW','NORMAL','HIGH','CRITICAL')),
  due_at timestamptz,
  case_id text references registry.cases(case_id),
  assigned_to uuid references auth.users(id),
  owner_required boolean not null default false,
  source_system text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists owner_work_items_status_due_idx on public.owner_work_items(status, due_at);
create index if not exists owner_work_items_case_idx on public.owner_work_items(case_id);
alter table public.owner_work_items enable row level security;
revoke all on public.owner_work_items from anon;
grant select, insert, update, delete on public.owner_work_items to authenticated;
grant all on public.owner_work_items to service_role;
drop policy if exists owner_work_items_admin_select on public.owner_work_items;
create policy owner_work_items_admin_select on public.owner_work_items for select to authenticated using ((select private.is_admin()));
drop policy if exists owner_work_items_admin_insert on public.owner_work_items;
create policy owner_work_items_admin_insert on public.owner_work_items for insert to authenticated with check ((select private.is_admin()));
drop policy if exists owner_work_items_admin_update on public.owner_work_items;
create policy owner_work_items_admin_update on public.owner_work_items for update to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));
drop policy if exists owner_work_items_admin_delete on public.owner_work_items;
create policy owner_work_items_admin_delete on public.owner_work_items for delete to authenticated using ((select private.is_admin()));

create table if not exists public.knowledge_items (
  id uuid primary key default gen_random_uuid(), slug text not null unique, title text not null, category text not null,
  body text not null default '', state text not null default 'DRAFT' check (state in ('WORKING_DRAFT','DRAFT','MASTER','SUPERSEDED','RETIRED')),
  version text not null default '1.0', audiences text[] not null default array['owner']::text[], client_safe boolean not null default false,
  effective_date date, owner_label text, last_review_date date, next_review_date date,
  supersedes_id uuid references public.knowledge_items(id), governed_by text, implements text[] not null default '{}'::text[],
  related_systems text[] not null default '{}'::text[], metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id), updated_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  check (audiences <@ array['owner','admin','employee','client']::text[]), check (not client_safe or 'client' = any(audiences))
);
create index if not exists knowledge_items_state_idx on public.knowledge_items(state);
create index if not exists knowledge_items_audiences_gin on public.knowledge_items using gin(audiences);
alter table public.knowledge_items enable row level security;
revoke all on public.knowledge_items from anon;
grant select, insert, update, delete on public.knowledge_items to authenticated;
grant all on public.knowledge_items to service_role;
drop policy if exists knowledge_items_role_select on public.knowledge_items;
create policy knowledge_items_role_select on public.knowledge_items for select to authenticated using (
  (select private.is_admin())
  or ((select private.has_role(array['analyst','reviewer']::text[])) and ('employee' = any(audiences) or 'admin' = any(audiences)))
  or ((select private.has_role(array['client','read_only']::text[])) and client_safe and 'client' = any(audiences))
);
drop policy if exists knowledge_items_admin_insert on public.knowledge_items;
create policy knowledge_items_admin_insert on public.knowledge_items for insert to authenticated with check ((select private.is_admin()));
drop policy if exists knowledge_items_admin_update on public.knowledge_items;
create policy knowledge_items_admin_update on public.knowledge_items for update to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));
drop policy if exists knowledge_items_admin_delete on public.knowledge_items;
create policy knowledge_items_admin_delete on public.knowledge_items for delete to authenticated using ((select private.is_admin()));

create table if not exists public.contract_records (
  id uuid primary key default gen_random_uuid(), case_id text references registry.cases(case_id), contract_type text not null, title text not null,
  counterparty text, status text not null default 'DRAFT' check (status in ('DRAFT','IN_REVIEW','AWAITING_SIGNATURE','EXECUTED','EXPIRED','TERMINATED','SUPERSEDED')),
  version text not null default '1.0', draft_body text, storage_path text, effective_date date, expiration_date date,
  created_by uuid references auth.users(id), approved_by uuid references auth.users(id), approved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists contract_records_status_idx on public.contract_records(status);
create index if not exists contract_records_case_idx on public.contract_records(case_id);
alter table public.contract_records enable row level security;
revoke all on public.contract_records from anon;
grant select, insert, update, delete on public.contract_records to authenticated;
grant all on public.contract_records to service_role;
drop policy if exists contract_records_admin_all on public.contract_records;
create policy contract_records_admin_all on public.contract_records for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

create table if not exists public.operating_expenses (
  id uuid primary key default gen_random_uuid(), case_id text references registry.cases(case_id), vendor_name text not null, category text,
  amount_cents bigint not null check (amount_cents >= 0), incurred_on date not null default current_date,
  status text not null default 'RECORDED' check (status in ('PLANNED','RECORDED','PAID','REIMBURSED','VOID')),
  notes text, created_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists operating_expenses_date_idx on public.operating_expenses(incurred_on desc);
alter table public.operating_expenses enable row level security;
revoke all on public.operating_expenses from anon;
grant select, insert, update, delete on public.operating_expenses to authenticated;
grant all on public.operating_expenses to service_role;
drop policy if exists operating_expenses_admin_all on public.operating_expenses;
create policy operating_expenses_admin_all on public.operating_expenses for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

create table if not exists public.vendors (
  id uuid primary key default gen_random_uuid(), name text not null unique, category text,
  status text not null default 'ACTIVE' check (status in ('PROSPECT','ACTIVE','PAUSED','ENDED')),
  contact_name text, contact_email text, notes text, created_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
alter table public.vendors enable row level security;
revoke all on public.vendors from anon;
grant select, insert, update, delete on public.vendors to authenticated;
grant all on public.vendors to service_role;
drop policy if exists vendors_admin_all on public.vendors;
create policy vendors_admin_all on public.vendors for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(), vendor_id uuid references public.vendors(id), service_name text not null,
  amount_cents bigint check (amount_cents >= 0), cadence text, next_charge_date date,
  status text not null default 'ACTIVE' check (status in ('TRIAL','ACTIVE','PAUSED','CANCELLED','ENDED')),
  notes text, created_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists subscriptions_next_charge_idx on public.subscriptions(next_charge_date) where status in ('TRIAL','ACTIVE');
alter table public.subscriptions enable row level security;
revoke all on public.subscriptions from anon;
grant select, insert, update, delete on public.subscriptions to authenticated;
grant all on public.subscriptions to service_role;
drop policy if exists subscriptions_admin_all on public.subscriptions;
create policy subscriptions_admin_all on public.subscriptions for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

comment on table public.owner_work_items is 'Owner/admin operating queue powering Start My Day, decisions, blockers, capacity, success-definition, and Fix Center surfaces.';
comment on table public.knowledge_items is 'Role-filtered institutional knowledge layer. The authoritative Docket remains the governing register; this table is the usable knowledge surface.';
comment on table public.contract_records is 'Back-office contract and agreement register. Execution/approval remains human-controlled.';
comment on table public.operating_expenses is 'Operational expense ledger for owner/admin back-office visibility; not an accounting system of record.';
comment on table public.vendors is 'Owner/admin vendor register.';
comment on table public.subscriptions is 'Owner/admin recurring service/subscription register.';
