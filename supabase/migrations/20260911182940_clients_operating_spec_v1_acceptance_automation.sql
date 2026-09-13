-- Clients v1: acceptance authority + onboarding automation.

create or replace function private.enforce_intake_decision_authority_v1()
returns trigger
language plpgsql
security definer
set search_path=''
as $$
begin
  if new.status is distinct from old.status
     and new.status in ('ACCEPTED','DECLINED')
     and not private.is_admin() then
    raise exception 'Owner/Admin authority is required for a final intake decision' using errcode='42501';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_intake_decision_authority_v1 on public.intake_submissions;
create trigger trg_intake_decision_authority_v1
before update of status on public.intake_submissions
for each row execute function private.enforce_intake_decision_authority_v1();

create or replace function private.enqueue_client_onboarding_v1()
returns trigger
language plpgsql
security definer
set search_path=''
as $$
declare
  target_client text;
  relationship_owner uuid;
  client_name text;
  actor uuid;
begin
  if new.status <> 'ACCEPTED' or old.status is not distinct from new.status then
    return new;
  end if;

  actor := auth.uid();
  select l.client_id into target_client
  from public.client_user_links l
  where l.user_id=new.user_id and l.active and l.relationship_role='primary'
  order by l.created_at desc
  limit 1;

  if target_client is null then
    raise exception 'Accepted intake is missing a canonical Client relationship' using errcode='23514';
  end if;

  select rp.relationship_owner, coalesce(rp.preferred_name,c.display_name,c.client_id)
    into relationship_owner, client_name
  from registry.clients c
  left join public.client_relationship_profiles rp on rp.client_id=c.client_id
  where c.client_id=target_client;

  insert into public.owner_work_items(category,title,description,status,priority,assigned_to,owner_required,source_system,metadata,created_by)
  select 'GENERAL','Confirm pricing path — '||client_name,
         'Confirm the authorized pricing classification before contract generation. Pricing remains authoritative in Pricing; this work item does not change rates.',
         'OPEN','NORMAL',coalesce(relationship_owner,actor),true,'CLIENTS_V1',
         jsonb_build_object('client_id',target_client,'intake_id',new.id,'workflow_step','PRICING_CONFIRMATION','source_status','ACCEPTED'),actor
  where not exists (
    select 1 from public.owner_work_items w
    where w.source_system='CLIENTS_V1' and w.metadata->>'intake_id'=new.id::text
      and w.metadata->>'workflow_step'='PRICING_CONFIRMATION' and w.status <> 'CANCELLED'
  );

  insert into public.owner_work_items(category,title,description,status,priority,assigned_to,owner_required,source_system,metadata,created_by)
  select 'GENERAL','Prepare engagement contract — '||client_name,
         'Prepare the controlled engagement agreement from approved templates. Scope and terms must be executed before a live Case is opened.',
         'OPEN','HIGH',coalesce(relationship_owner,actor),true,'CLIENTS_V1',
         jsonb_build_object('client_id',target_client,'intake_id',new.id,'workflow_step','CONTRACT_PREPARATION','source_status','ACCEPTED'),actor
  where not exists (
    select 1 from public.owner_work_items w
    where w.source_system='CLIENTS_V1' and w.metadata->>'intake_id'=new.id::text
      and w.metadata->>'workflow_step'='CONTRACT_PREPARATION' and w.status <> 'CANCELLED'
  );

  insert into public.owner_work_items(category,title,description,status,priority,assigned_to,owner_required,source_system,metadata,created_by)
  select 'GENERAL','Confirm Client portal access — '||client_name,
         'Verify the primary authenticated Client user and add only authorized additional contacts. Portal access does not create Case access by itself.',
         'OPEN','NORMAL',coalesce(relationship_owner,actor),false,'CLIENTS_V1',
         jsonb_build_object('client_id',target_client,'intake_id',new.id,'workflow_step','PORTAL_ACCESS_CONFIRMATION','source_status','ACCEPTED'),actor
  where not exists (
    select 1 from public.owner_work_items w
    where w.source_system='CLIENTS_V1' and w.metadata->>'intake_id'=new.id::text
      and w.metadata->>'workflow_step'='PORTAL_ACCESS_CONFIRMATION' and w.status <> 'CANCELLED'
  );

  insert into public.owner_work_items(category,title,description,status,priority,assigned_to,owner_required,source_system,metadata,created_by)
  select 'GENERAL','Open Case when engagement gates are satisfied — '||client_name,
         'Queue Case creation only after contract, scope, and pricing authorization are ready. Acceptance of the Client relationship does not itself authorize Case creation.',
         'WAITING','HIGH',coalesce(relationship_owner,actor),true,'CLIENTS_V1',
         jsonb_build_object('client_id',target_client,'intake_id',new.id,'workflow_step','CASE_OPENING_READINESS','source_status','ACCEPTED'),actor
  where not exists (
    select 1 from public.owner_work_items w
    where w.source_system='CLIENTS_V1' and w.metadata->>'intake_id'=new.id::text
      and w.metadata->>'workflow_step'='CASE_OPENING_READINESS' and w.status <> 'CANCELLED'
  );

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(actor,private.current_user_role(),'CLIENT_ONBOARDING_QUEUED','client',target_client,
         jsonb_build_object('intake_id',new.id,'work_items',4,'external_notification_sent',false));

  return new;
end;
$$;

drop trigger if exists trg_client_onboarding_after_accept_v1 on public.intake_submissions;
create trigger trg_client_onboarding_after_accept_v1
after update of status on public.intake_submissions
for each row execute function private.enqueue_client_onboarding_v1();
