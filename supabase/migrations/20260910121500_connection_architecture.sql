create table if not exists public.system_capabilities (
  capability_key text primary key,
  roles text[] not null,
  active boolean not null default true,
  external_authorization_required boolean not null default false,
  description text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (roles <@ array['owner','admin','analyst','reviewer','client','read_only']::text[])
);

create table if not exists public.canonical_destinations (
  object_type text primary key,
  default_page text not null,
  owner_page text,
  subview text,
  description text not null default '',
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.operational_lifecycle_status (
  capability_key text primary key,
  stage text not null check (stage in (
    'DESIGNED','CODED','DATA_WIRED','PERMISSION_TESTED','DRILL_THROUGH_VERIFIED',
    'CROSS_INTERFACE_VERIFIED','GOLDEN_PATH_PASSED','MESSY_PATH_PASSED','OPERATIONAL'
  )),
  deployment_verified boolean not null default false,
  evidence jsonb not null default '{}'::jsonb,
  owner_note text,
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (stage <> 'OPERATIONAL' or deployment_verified)
);

create table if not exists public.connection_issues (
  id uuid primary key default gen_random_uuid(),
  issue_key text unique,
  title text not null,
  issue_type text not null check (issue_type in (
    'BROKEN','DEGRADED','INCOMPLETE','POLICY_DRIFT','FAILED_TEST','NEEDS_APPROVAL',
    'AUTO_REPAIRABLE','CODE_CHANGE','DATABASE_CHANGE','HUMAN_DECISION','INTEGRATION_FAILURE'
  )),
  severity text not null default 'NORMAL' check (severity in ('LOW','NORMAL','HIGH','CRITICAL')),
  status text not null default 'OPEN' check (status in ('OPEN','IN_PROGRESS','WAITING','BLOCKED','READY_FOR_APPROVAL','RESOLVED','DISMISSED')),
  source_system text,
  source_type text,
  source_id text,
  object_type text,
  destination_page text,
  owner_required boolean not null default false,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table if not exists public.drill_through_events (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references auth.users(id),
  object_type text not null,
  object_id text,
  source_surface text not null,
  destination_page text not null,
  filters jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists connection_issues_status_idx on public.connection_issues(status, severity);
create index if not exists drill_through_events_actor_idx on public.drill_through_events(actor_id, created_at desc);
create index if not exists operational_lifecycle_stage_idx on public.operational_lifecycle_status(stage);

alter table public.system_capabilities enable row level security;
alter table public.canonical_destinations enable row level security;
alter table public.operational_lifecycle_status enable row level security;
alter table public.connection_issues enable row level security;
alter table public.drill_through_events enable row level security;

revoke all on public.system_capabilities from anon;
revoke all on public.canonical_destinations from anon;
revoke all on public.operational_lifecycle_status from anon;
revoke all on public.connection_issues from anon;
revoke all on public.drill_through_events from anon;

grant select on public.system_capabilities, public.canonical_destinations to authenticated;
grant select, insert, update, delete on public.operational_lifecycle_status, public.connection_issues to authenticated;
grant insert on public.drill_through_events to authenticated;
grant select on public.drill_through_events to authenticated;
grant all on public.system_capabilities, public.canonical_destinations, public.operational_lifecycle_status, public.connection_issues, public.drill_through_events to service_role;

drop policy if exists system_capabilities_authenticated_select on public.system_capabilities;
create policy system_capabilities_authenticated_select on public.system_capabilities for select to authenticated using (true);
drop policy if exists system_capabilities_admin_write on public.system_capabilities;
create policy system_capabilities_admin_write on public.system_capabilities for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

drop policy if exists canonical_destinations_authenticated_select on public.canonical_destinations;
create policy canonical_destinations_authenticated_select on public.canonical_destinations for select to authenticated using (true);
drop policy if exists canonical_destinations_admin_write on public.canonical_destinations;
create policy canonical_destinations_admin_write on public.canonical_destinations for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

drop policy if exists operational_lifecycle_admin_all on public.operational_lifecycle_status;
create policy operational_lifecycle_admin_all on public.operational_lifecycle_status for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

drop policy if exists connection_issues_admin_all on public.connection_issues;
create policy connection_issues_admin_all on public.connection_issues for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

drop policy if exists drill_through_insert_own on public.drill_through_events;
create policy drill_through_insert_own on public.drill_through_events for insert to authenticated with check (actor_id = (select auth.uid()));
drop policy if exists drill_through_admin_select on public.drill_through_events;
create policy drill_through_admin_select on public.drill_through_events for select to authenticated using ((select private.is_admin()) or actor_id = (select auth.uid()));

insert into public.system_capabilities (capability_key, roles, active, external_authorization_required, description)
values
  ('records_upload', array['owner','admin','analyst','reviewer','client'], true, false, 'Case-scoped source upload into the universal ingestion gateway'),
  ('google_drive_import', array['owner','admin','analyst','reviewer','client'], true, true, 'Google Drive import through the same case-scoped ingestion gateway'),
  ('zip_archive_import', array['owner','admin','analyst','reviewer','client'], true, false, 'Safe ZIP package extraction with parent/child source lineage'),
  ('team_oversight', array['owner','admin'], true, false, 'Team workload, assignments, case progress, and capacity oversight'),
  ('finance', array['owner','admin'], true, false, 'Owner/admin back-office finance workspace'),
  ('billing', array['owner','admin'], true, false, 'Invoice/payment/receivable workspace'),
  ('contracts', array['owner','admin'], true, false, 'Contract lifecycle workspace'),
  ('docket', array['owner'], true, false, 'Authoritative governance register access'),
  ('implementation_control', array['owner'], true, false, 'Implementation lifecycle and parity control'),
  ('fix_center', array['owner'], true, false, 'Structured system repair queue')
on conflict (capability_key) do update set
  roles = excluded.roles,
  active = excluded.active,
  external_authorization_required = excluded.external_authorization_required,
  description = excluded.description,
  updated_at = now();

insert into public.canonical_destinations (object_type, default_page, owner_page, subview, description)
values
  ('decision','Review Center','Decisions','Needs Decision','Human or owner decision queue'),
  ('approval','Review Center','Decisions','Needs Decision','Protected or ordinary approval'),
  ('blocker','Review Center','Fix Center','Blocked','Blocked work or case issue'),
  ('carryover','Dashboard','Dispatcher','Carryover','Open work carried from a prior day'),
  ('due_today','Dashboard','Dispatcher','Due Today','Work due today'),
  ('source','Evidence','Records','Source','Registered source record'),
  ('record','Evidence','Records','Record','Record/source workspace'),
  ('case','Engagements','Cases','Case','Canonical case workspace'),
  ('report','Reports','Reports','Report','Report/review publication object'),
  ('invoice','Billing','Billing','Invoices','Invoice record'),
  ('receivable','Billing','Billing','Receivables','Outstanding receivable'),
  ('payment','Billing','Billing','Payments','Payment record'),
  ('contract','Contracts','Contracts','Contract','Contract/agreement record'),
  ('capacity','Administration','Capacity','Workload','Capacity/workload state'),
  ('employee','Administration','Team','Person','Team member work state'),
  ('knowledge','Help & Support','Knowledge','Guides & Resources','Authorized knowledge item'),
  ('policy','Administration','Docket','Policy','Controlling governance artifact'),
  ('implementation','Administration','Implementation','Implementation','Implementation Matrix item'),
  ('notification','Dashboard','Notifications','Notifications','Operational notification'),
  ('integration','Administration','Integrations','Integrations','Integration state'),
  ('deployment','Administration','Deployments','Deployments','Deployment state or failure'),
  ('fix','Administration','Fix Center','Fix','Structured repair item'),
  ('referral','Administration','Referrals','Referrals','Referral opportunity or partner'),
  ('communication','Messages','Notifications','Message','Communication thread or message')
on conflict (object_type) do update set
  default_page = excluded.default_page,
  owner_page = excluded.owner_page,
  subview = excluded.subview,
  description = excluded.description,
  updated_at = now();

comment on table public.canonical_destinations is 'Single routing registry used by dashboard, notifications, DARI, KPIs, and alerts to resolve authoritative operating destinations.';
comment on table public.operational_lifecycle_status is 'Strict ecosystem lifecycle: Designed -> Coded -> Data Wired -> Permission Tested -> Drill-Through Verified -> Cross-Interface Verified -> Golden Path Passed -> Messy Path Passed -> Operational.';
comment on table public.connection_issues is 'Fix Center source-of-truth queue for broken, degraded, incomplete, drift, test, integration, database, code, and human-decision issues.';
comment on table public.drill_through_events is 'Minimal routing telemetry proving that a visible system-state surface resolved to a canonical destination. No client document contents belong here.';
