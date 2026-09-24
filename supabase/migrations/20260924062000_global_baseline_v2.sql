-- Global Baseline v2.0
-- Canonical source migration for GBL-2026-09-24-001.
-- Applied operationally to Supabase before this source artifact was committed.
-- Historical baseline versions are immutable by policy; future versions supersede them.

create schema if not exists global_state;

create table if not exists global_state.baselines (
  baseline_id text primary key,
  baseline_version integer not null,
  effective_at timestamptz not null default now(),
  authority_state text not null check (authority_state in ('AUTHORIZED','SUPERSEDED','REVOKED')),
  intended_state jsonb not null default '{}'::jsonb,
  actual_state jsonb not null default '{}'::jsonb,
  verification_state jsonb not null default '{}'::jsonb,
  exception_state jsonb not null default '{}'::jsonb,
  dependency_state jsonb not null default '{}'::jsonb,
  continuity_state jsonb not null default '{}'::jsonb,
  confidence_state jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  supersedes_baseline text references global_state.baselines(baseline_id),
  reconciled_at timestamptz,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  unique (baseline_version)
);

create table if not exists global_state.baseline_domains (
  baseline_id text not null references global_state.baselines(baseline_id) on delete cascade,
  domain_key text not null,
  authority_state text not null check (authority_state in ('AUTHORIZED','PENDING','EXCEPTION','NOT_APPLICABLE')),
  intended_state jsonb not null default '{}'::jsonb,
  actual_state jsonb not null default '{}'::jsonb,
  verification_state jsonb not null default '{}'::jsonb,
  exception_state jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  last_observed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  primary key (baseline_id, domain_key)
);

create table if not exists global_state.baseline_changes (
  change_id uuid primary key default gen_random_uuid(),
  baseline_id text not null references global_state.baselines(baseline_id) on delete cascade,
  change_type text not null check (change_type in ('AUTHORIZATION','INTENT','CODE','DATABASE','RUNTIME','SECURITY','GOVERNANCE','DEPENDENCY','VERIFICATION','EXCEPTION','CONTINUITY','OTHER')),
  source_ref text,
  prior_state jsonb,
  resulting_state jsonb not null default '{}'::jsonb,
  confidence text not null default 'UNKNOWN' check (confidence in ('CONFIRMED','SUPPORTED','OBSERVED','INFERRED','PENDING','UNKNOWN')),
  evidence_refs jsonb not null default '[]'::jsonb,
  occurred_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists global_state.baseline_exceptions (
  exception_id uuid primary key default gen_random_uuid(),
  baseline_id text not null references global_state.baselines(baseline_id) on delete cascade,
  exception_key text not null,
  exception_type text not null check (exception_type in ('DRIFT','BLOCKER','PENDING_VERIFICATION','DEPENDENCY','HUMAN_DECISION','UNKNOWN_STATE','OTHER')),
  severity text not null default 'LOW' check (severity in ('INFO','LOW','MEDIUM','HIGH','CRITICAL')),
  state text not null default 'OPEN' check (state in ('OPEN','MONITORED','RESOLVED','SUPERSEDED')),
  description text,
  required_action text,
  authority_ref text,
  evidence_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  unique (baseline_id, exception_key)
);

create index if not exists baseline_domains_domain_idx on global_state.baseline_domains(domain_key, baseline_id);
create index if not exists baseline_changes_idx on global_state.baseline_changes(baseline_id, occurred_at desc);
create index if not exists baseline_exceptions_idx on global_state.baseline_exceptions(baseline_id, state, severity);

alter table global_state.baselines enable row level security;
alter table global_state.baseline_domains enable row level security;
alter table global_state.baseline_changes enable row level security;
alter table global_state.baseline_exceptions enable row level security;

create policy global_baseline_owner on global_state.baselines
for all to authenticated using ((select auth.uid()) is not null)
with check ((select auth.uid()) is not null);

create policy global_baseline_domains_owner on global_state.baseline_domains
for all to authenticated
using (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_domains.baseline_id))
with check (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_domains.baseline_id));

create policy global_baseline_changes_owner on global_state.baseline_changes
for all to authenticated
using (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_changes.baseline_id))
with check (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_changes.baseline_id));

create policy global_baseline_exceptions_owner on global_state.baseline_exceptions
for all to authenticated
using (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_exceptions.baseline_id))
with check (exists (select 1 from global_state.baselines b where b.baseline_id=baseline_exceptions.baseline_id));

revoke all on schema global_state from anon;
grant usage on schema global_state to authenticated;
grant select, insert, update, delete on all tables in schema global_state to authenticated;
