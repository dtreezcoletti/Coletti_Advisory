-- Applied Supabase migration, version 20261012221427.
-- DOMUS-only owner-controlled learning; no institutional authority.

-- DARI Personal Collaboration v1: DOMUS-only, Owner-controlled learning.
-- No legacy registry/knowledge calibration, policy, case or role objects are altered.
create table if not exists chapter2_private.dari_personal_learning_v1 (
  learning_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  profile_key text not null check (length(profile_key) between 3 and 100),
  statement text not null check (length(statement) between 1 and 1800),
  category text not null check (category in ('WORK_RHYTHM','COMMUNICATION','DECISION_SUPPORT','BOUNDARIES','PERSONAL_GOALS')),
  basis text not null default 'USER_DIRECT' check (basis in ('USER_DIRECT','OBSERVED','INFERRED')),
  status text not null default 'CANDIDATE' check (status in ('CANDIDATE','CONFIRMED','REJECTED','RETIRED')),
  provenance_ref text check (provenance_ref is null or length(provenance_ref) <= 300),
  revision integer not null default 1 check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id,profile_key)
);
create index if not exists dari_personal_learning_v1_owner_status_idx
 on chapter2_private.dari_personal_learning_v1 (owner_user_id,status,updated_at desc);
alter table chapter2_private.dari_personal_learning_v1 enable row level security;
-- Private schema, no direct anonymous or authenticated table access; all operations
-- must pass owner-checked RPCs. Neither personal learning nor content crosses PONS.
revoke all on table chapter2_private.dari_personal_learning_v1 from PUBLIC, anon, authenticated;
grant select, insert, update, delete on table chapter2_private.dari_personal_learning_v1 to service_role;

create table if not exists chapter2_private.dari_personal_learning_audit_v1 (
  audit_id uuid primary key default gen_random_uuid(),
  learning_id uuid not null,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('PROPOSE','REPLACE_CANDIDATE','CONFIRM','REJECT','RETI RE','DELETE')),
  revision integer not null check (revision > 0),
  occurred_at timestamptz not null default now()
);
-- Typographical string in initial action declaration above is normalized below before use.
alter table chapter2_private.dari_personal_learning_audit_v1
 drop constraint if exists dari_personal_learning_audit_v1_action_check;
alter table chapter2_private.dari_personal_learning_audit_v1
 add constraint dari_personal_learning_audit_v1_action_check
 check (action in ('PROPOSE','REPLACE_CANDIDATE','CONFIRM','REJECT','RETIRE','DELETE'));
alter table chapter2_private.dari_personal_learning_audit_v1 enable row level security;
revoke all on table chapter2_private.dari_personal_learning_audit_v1 from PUBLIC, anon, authenticated;
grant select, insert on table chapter2_private.dari_personal_learning_audit_v1 to service_role;

create or replace function public.dari_personal_profile_list_v1()
returns table (
  learning_id uuid, profile_key text, statement text, category text,
  basis text, status text, provenance_ref text, revision integer,
  created_at timestamptz, updated_at timestamptz
)
language plpgsql security definer set search_path=pg_catalog as $fn$
declare v_owner uuid := auth.uid();
begin
  if v_owner is null or not exists (
    select 1 from private.user_roles r
    where r.user_id=v_owner and lower(r.role)='owner' and r.active
  ) then
    raise exception 'Owner authentication required' using errcode='42501';
  end if;
  return query
  select p.learning_id,p.profile_key,p.statement,p.category,p.basis,p.status,
         p.provenance_ref,p.revision,p.created_at,p.updated_at
  from chapter2_private.dari_personal_learning_v1 p
  where p.owner_user_id=v_owner order by p.updated_at desc;
end $fn$;

create or replace function public.dari_personal_profile_propose_v1(
  p_key text, p_statement text, p_category text,
  p_basis text default 'USER_DIRECT', p_provenance_ref text default null
) returns uuid
language plpgsql security definer set search_path=pg_catalog as $fn$
declare
  v_owner uuid := auth.uid();
  v_id uuid;
  v_rev integer;
  v_prior boolean;
begin
  if v_owner is null or not exists (
    select 1 from private.user_roles r where r.user_id=v_owner
    and lower(r.role)='owner' and r.active
  ) then
    raise exception 'Owner authentication required' using errcode='42501';
  end if;
  if p_key is null or length(p_key) not between 3 and 100
      or p_key !~ '^[a-z][a-z0-9_.-]+$'
      or p_statement is null or length(btrim(p_statement)) not between 1 and 1800
      or p_category is null or p_category not in ('WORK_RHYTHM','COMMUNICATION','DECISION_SUPPORT','BOUNDARIES','PERSONAL_GOALS')
      or p_basis is null or p_basis not in ('USER_DIRECT','OBSERVED','INFERRED')
      or (p_provenance_ref is not null and length(p_provenance_ref)>300) then
    raise exception 'Invalid personal learning entry' using errcode='22023';
  end if;
  select exists (
    select 1 from chapter2_private.dari_personal_learning_v1
    where owner_user_id=v_owner and profile_key=p_key
  ) into v_prior;
  insert into chapter2_private.dari_personal_learning_v1
    (owner_user_id,profile_key,statement,category,basis,provenance_ref,status)
  values (v_owner,p_key,btrim(p_statement),p_category,p_basis,p_provenance_ref,'CANDIDATE')
  on conflict(owner_user_id,profile_key) do update set
    statement=excluded.statement, category=excluded.category,
    basis=excluded.basis, provenance_ref=excluded.provenance_ref,
    status='CANDIDATE', revision=chapter2_private.dari_personal_learning_v1.revision+1,
    updated_at=now()
  returning chapter2_private.dari_personal_learning_v1.learning_id,
            chapter2_private.dari_personal_learning_v1.revision into v_id,v_rev;
  insert into chapter2_private.dari_personal_learning_audit_v1
    (learning_id,owner_user_id,action,revision)
  values (v_id,v_owner,case when v_prior then 'REPLACE_CANDIDATE' else 'PROPOSE' end,v_rev);
  return v_id;
end $fn$;

create or replace function public.dari_personal_profile_review_v1(p_learning_id uuid,p_action text)
returns boolean
language plpgsql security definer set search_path=pg_catalog as $fn$
declare v_owner uuid := auth.uid(); v_rev integer; v_status text;
begin
  if v_owner is null or not exists (
    select 1 from private.user_roles r where r.user_id=v_owner
    and lower(r.role)='owner' and r.active
  ) then
    raise exception 'Owner authentication required' using errcode='42501';
  end if;
  if p_action not in ('CONFIRM','REJECT','RETIRE','DELETE') or p_action is null then
    raise exception 'Invalid review action' using errcode='22023';
  end if;
  select p.status,p.revision into v_status,v_rev
  from chapter2_private.dari_personal_learning_v1 p
  where p.learning_id=p_learning_id and p.owner_user_id=v_owner for update;
  if not found then
    raise exception 'Personal learning entry not found' using errcode='P0002';
  end if;
  if (p_action='CONFIRM' and v_status<>'CANDIDATE')
   or (p_action='REJECT' and v_status<>'CANDIDATE')
   or (p_action='RETIRE' and v_status<>'CONFIRMED') then
    raise exception 'Invalid learning state transition' using errcode='22023';
  end if;
  if p_action='DELETE' then
    delete from chapter2_private.dari_personal_learning_v1
    where learning_id=p_learning_id and owner_user_id=v_owner;
  else
    update chapter2_private.dari_personal_learning_v1
    set status=case p_action when 'CONFIRM' then 'CONFIRMED'
                            when 'REJECT' then 'REJECTED'
                            else 'RETIRED' end,
        revision=revision+1, updated_at=now()
    where learning_id=p_learning_id and owner_user_id=v_owner;
  end if;
  insert into chapter2_private.dari_personal_learning_audit_v1
    (learning_id,owner_user_id,action,revision)
  values (p_learning_id,v_owner,p_action,v_rev+1);
  return true;
end $fn$;

create or replace function public.dari_personal_profile_context_v1()
returns table(profile_key text, statement text, category text)
language plpgsql security definer set search_path=pg_catalog as $fn$
declare v_owner uuid := auth.uid();
begin
  if v_owner is null or not exists (
    select 1 from private.user_roles r where r.user_id=v_owner
    and lower(r.role)='owner' and r.active
  ) then
    raise exception 'Owner authentication required' using errcode='42501';
  end if;
  return query
  select p.profile_key,p.statement,p.category
  from chapter2_private.dari_personal_learning_v1 p
  where p.owner_user_id=v_owner and p.status='CONFIRMED'
  order by p.profile_key;
end $fn$;

revoke all on function public.dari_personal_profile_list_v1() from PUBLIC, anon;
revoke all on function public.dari_personal_profile_propose_v1(text,text,text,text,text) from PUBLIC, anon;
revoke all on function public.dari_personal_profile_review_v1(uuid,text) from PUBLIC, anon;
revoke all on function public.dari_personal_profile_context_v1() from PUBLIC, anon;
grant execute on function public.dari_personal_profile_list_v1() to authenticated;
grant execute on function public.dari_personal_profile_propose_v1(text,text,text,text,text) to authenticated;
grant execute on function public.dari_personal_profile_review_v1(uuid,text) to authenticated;
grant execute on function public.dari_personal_profile_context_v1() to authenticated;
comment on table chapter2_private.dari_personal_learning_v1 is
 'DOMUS Owner-only learning; candidates never affect DARI until explicitly confirmed; never institutional authority.';
