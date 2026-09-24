-- ColettiOS System Coordination Plane v1
create schema if not exists coordination;

create table if not exists coordination.implementations (
 implementation_id text primary key, implementation_key text unique not null, title text not null,
 authorization_state text not null default 'GRANTED' check (authorization_state in ('PROPOSED','GRANTED','REVOKED','EXPIRED')),
 implementation_state text not null default 'PROPOSED' check (implementation_state in ('PROPOSED','IMPLEMENTING','OPERATIONAL','SUSPENDED','RETIRED')),
 intended_state jsonb not null default '{}'::jsonb, current_state jsonb not null default '{}'::jsonb,
 verification_state text not null default 'PENDING' check (verification_state in ('PENDING','IN_PROGRESS','VERIFIED','FAILED','STALE')),
 blocker_state text not null default 'NONE' check (blocker_state in ('NONE','WAITING','BLOCKED','HUMAN_REVIEW')),
 last_known_good jsonb,last_verified_at timestamptz,last_reconciled_at timestamptz,
 metadata jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now()
);
create table if not exists coordination.artifacts (
 artifact_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 system_name text not null check(system_name in ('GITHUB','SUPABASE','RENDER','COLETTIOS','OTHER')),
 artifact_type text not null,artifact_ref text not null,revision text,
 state text not null default 'OBSERVED' check(state in ('EXPECTED','OBSERVED','DEPLOYED','LIVE','MISSING','STALE','UNKNOWN')),
 observed_at timestamptz not null default now(),metadata jsonb not null default '{}'::jsonb
);
create unique index if not exists artifacts_unique_ref on coordination.artifacts(implementation_id,system_name,artifact_type,artifact_ref);
create table if not exists coordination.dependencies (
 dependency_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 depends_on_implementation_id text not null references coordination.implementations on delete cascade,
 dependency_type text not null default 'REQUIRED',state text not null default 'READY' check(state in ('READY','WAITING','BLOCKED','UNKNOWN')),
 metadata jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),
 unique(implementation_id,depends_on_implementation_id,dependency_type),check(implementation_id<>depends_on_implementation_id)
);
create table if not exists coordination.transactions (
 transaction_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 authorization_ref text,phase text not null default 'PREPARE' check(phase in ('PREPARE','VALIDATE','EXECUTE','VERIFY','COMMIT','REPAIR','ROLLBACK','CLOSED','FAILED')),
 planned_state jsonb not null default '{}'::jsonb,preflight_state jsonb not null default '{}'::jsonb,execution_state jsonb not null default '{}'::jsonb,
 verification_state jsonb not null default '{}'::jsonb,result_state jsonb not null default '{}'::jsonb,affected_systems text[] not null default '{}',
 evidence jsonb not null default '[]'::jsonb,rollback_reference text,started_at timestamptz not null default now(),completed_at timestamptz,metadata jsonb not null default '{}'::jsonb
);
create table if not exists coordination.drift_events (
 drift_event_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 drift_type text not null check(drift_type in ('CODE','DATABASE','RUNTIME','CONFIGURATION','GOVERNANCE','DOCUMENTATION','VERIFICATION','DEPENDENCY','UNKNOWN')),
 severity text not null default 'INFO' check(severity in ('INFO','LOW','MEDIUM','HIGH','CRITICAL')),
 confidence text not null default 'UNKNOWN' check(confidence in ('CERTAIN','HIGH','MODERATE','LOW','UNKNOWN')),
 intended_state jsonb not null default '{}'::jsonb,observed_state jsonb not null default '{}'::jsonb,difference jsonb not null default '{}'::jsonb,
 state text not null default 'DETECTED' check(state in ('DETECTED','EXPLAINED','RECONCILING','RESOLVED','UNRESOLVED','FALSE_POSITIVE')),
 detected_at timestamptz not null default now(),resolved_at timestamptz,evidence jsonb not null default '[]'::jsonb,explanation text
);
create table if not exists coordination.reconciliation_queue (
 queue_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 action_type text not null check(action_type in ('OBSERVE','COMPARE','DATABASE_RECONCILIATION','DEPLOYMENT','VERIFICATION','ROLL_FORWARD','ROLLBACK','HUMAN_REVIEW')),
 priority text not null default 'NORMAL' check(priority in ('LOW','NORMAL','HIGH','CRITICAL')),
 state text not null default 'OPEN' check(state in ('OPEN','IN_PROGRESS','WAITING','BLOCKED','RESOLVED','CANCELLED')),
 retry_count integer not null default 0 check(retry_count>=0),retry_limit integer not null default 3 check(retry_limit>=0),
 reason text,confidence text not null default 'UNKNOWN' check(confidence in ('CERTAIN','HIGH','MODERATE','LOW','UNKNOWN')),
 created_at timestamptz not null default now(),started_at timestamptz,resolved_at timestamptz,next_attempt_at timestamptz,evidence jsonb not null default '[]'::jsonb,metadata jsonb not null default '{}'::jsonb
);
create unique index if not exists reconciliation_one_active_action on coordination.reconciliation_queue(implementation_id,action_type) where state in ('OPEN','IN_PROGRESS','WAITING','BLOCKED');
create table if not exists coordination.system_truth_ledger (
 ledger_id uuid primary key default gen_random_uuid(),implementation_id text not null references coordination.implementations on delete cascade,
 event_type text not null,actor_type text not null check(actor_type in ('OWNER','SYSTEM','AGENT','PROVIDER','UNKNOWN')),
 before_state jsonb,after_state jsonb not null default '{}'::jsonb,authority_ref text,evidence jsonb not null default '[]'::jsonb,occurred_at timestamptz not null default now(),metadata jsonb not null default '{}'::jsonb
);

create index if not exists implementations_state_idx on coordination.implementations(authorization_state,implementation_state,verification_state,blocker_state);
create index if not exists artifacts_impl_idx on coordination.artifacts(implementation_id,observed_at desc);
create index if not exists dependencies_impl_idx on coordination.dependencies(implementation_id,state);
create index if not exists transactions_impl_idx on coordination.transactions(implementation_id,started_at desc);
create index if not exists drift_impl_idx on coordination.drift_events(implementation_id,state,detected_at desc);
create index if not exists queue_state_idx on coordination.reconciliation_queue(state,priority,created_at);
create index if not exists ledger_impl_idx on coordination.system_truth_ledger(implementation_id,occurred_at desc);

alter table coordination.implementations enable row level security;
alter table coordination.artifacts enable row level security;
alter table coordination.dependencies enable row level security;
alter table coordination.transactions enable row level security;
alter table coordination.drift_events enable row level security;
alter table coordination.reconciliation_queue enable row level security;
alter table coordination.system_truth_ledger enable row level security;

create policy coordination_owner_impl on coordination.implementations for all to authenticated using((select auth.uid()) is not null) with check((select auth.uid()) is not null);
create policy coordination_owner_artifacts on coordination.artifacts for all to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=artifacts.implementation_id)) with check(exists(select 1 from coordination.implementations i where i.implementation_id=artifacts.implementation_id));
create policy coordination_owner_dependencies on coordination.dependencies for all to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=dependencies.implementation_id)) with check(exists(select 1 from coordination.implementations i where i.implementation_id=dependencies.implementation_id));
create policy coordination_owner_transactions on coordination.transactions for all to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=transactions.implementation_id)) with check(exists(select 1 from coordination.implementations i where i.implementation_id=transactions.implementation_id));
create policy coordination_owner_drift on coordination.drift_events for all to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=drift_events.implementation_id)) with check(exists(select 1 from coordination.implementations i where i.implementation_id=drift_events.implementation_id));
create policy coordination_owner_queue on coordination.reconciliation_queue for all to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=reconciliation_queue.implementation_id)) with check(exists(select 1 from coordination.implementations i where i.implementation_id=reconciliation_queue.implementation_id));
create policy coordination_owner_ledger on coordination.system_truth_ledger for select to authenticated using(exists(select 1 from coordination.implementations i where i.implementation_id=system_truth_ledger.implementation_id));

revoke all on schema coordination from anon;
grant usage on schema coordination to authenticated;
grant select,insert,update,delete on all tables in schema coordination to authenticated;

insert into coordination.implementations(implementation_id,implementation_key,title,authorization_state,implementation_state,intended_state,current_state,verification_state,blocker_state,metadata)
values('IMP-SYSCOORD-001','SYSTEM-COORDINATION-PLANE-001','ColettiOS System Coordination Plane','GRANTED','OPERATIONAL',
'{"coherence_model":"INTENDED_VS_ACTUAL","reconciliation":"CLOSED_LOOP","last_known_good":true,"implementation_transactions":true,"drift_detection":true,"dependency_graph":true,"temporal_state":true}',
'{"database":"CONFIRMED","coordination_schema":"DEPLOYED","provider_integrations":"PENDING","runtime_integration":"PENDING"}','PENDING','NONE',
'{"governed_by":"GRANTED_ORDER_LAW","operational_scope":"FOUNDATIONAL_COORDINATION_PLANE","verification_scope":"DATABASE_STRUCTURE_ONLY"}')
on conflict(implementation_id) do update set authorization_state=excluded.authorization_state,implementation_state=excluded.implementation_state,intended_state=excluded.intended_state,current_state=excluded.current_state,metadata=excluded.metadata,updated_at=now();

insert into coordination.system_truth_ledger(implementation_id,event_type,actor_type,after_state,authority_ref,evidence,metadata)
values('IMP-SYSCOORD-001','FOUNDATIONAL_PLANE_DEPLOYED','SYSTEM',
'{"implementation":"OPERATIONAL","database":"CONFIRMED","provider_integrations":"PENDING","runtime_integration":"PENDING"}','GRANTED_ORDER_LAW',
'[{"type":"migration","name":"system_coordination_plane_v1"}]','{"verification":"database_structure_only"}');

create or replace function coordination.refresh_reconciliation_for_implementation(p_implementation_id text)
returns void language plpgsql security invoker set search_path=coordination,public as $$
declare v record;
begin
 select * into v from coordination.implementations where implementation_id=p_implementation_id;
 if not found then return; end if;
 if v.authorization_state='GRANTED' and v.implementation_state='OPERATIONAL' and v.verification_state<>'VERIFIED' then
  insert into coordination.reconciliation_queue(implementation_id,action_type,priority,state,reason,confidence)
  values(p_implementation_id,case when v.current_state->>'database'<>'CONFIRMED' then 'DATABASE_RECONCILIATION' else 'VERIFICATION' end,
  case when v.blocker_state='BLOCKED' then 'HIGH' else 'NORMAL' end,'OPEN','Operational implementation requires reconciliation or verification.','CERTAIN')
  on conflict do nothing;
 end if;
end;$$;
revoke all on function coordination.refresh_reconciliation_for_implementation(text) from public,anon,authenticated;

create or replace function coordination.set_last_known_good(p_implementation_id text,p_state jsonb,p_evidence jsonb)
returns void language plpgsql security invoker set search_path=coordination,public as $$
begin
 update coordination.implementations set last_known_good=jsonb_build_object('state',p_state,'evidence',p_evidence,'recorded_at',now()),last_verified_at=now(),verification_state='VERIFIED',updated_at=now()
 where implementation_id=p_implementation_id;
end;$$;
revoke all on function coordination.set_last_known_good(text,jsonb,jsonb) from public,anon,authenticated;
