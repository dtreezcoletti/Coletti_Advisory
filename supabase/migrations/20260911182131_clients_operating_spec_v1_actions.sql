-- Clients Operating Specification v1: controlled Owner/Admin actions.

create or replace function public.admin_update_client_relationship_v1(
  p_client_id text,
  p_legal_name text default null,
  p_preferred_name text default null,
  p_primary_email text default null,
  p_primary_phone text default null,
  p_preferred_contact_method text default null,
  p_time_zone text default null,
  p_referral_source text default null,
  p_next_action text default null,
  p_next_action_date date default null,
  p_pricing_classification text default 'STANDARD'
)
returns void
language plpgsql
security definer
set search_path=''
as $$
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  if not exists(select 1 from registry.clients where client_id=p_client_id) then raise exception 'client not found' using errcode='P0002'; end if;
  if p_preferred_contact_method is not null and p_preferred_contact_method not in ('PORTAL','EMAIL','PHONE') then raise exception 'invalid contact method' using errcode='22023'; end if;
  if p_pricing_classification not in ('STANDARD','REDUCED_FEE','PROMOTIONAL_PILOT','PRO_BONO','CUSTOM') then raise exception 'invalid pricing classification' using errcode='22023'; end if;

  insert into public.client_relationship_profiles(
    client_id,legal_name,preferred_name,primary_email,primary_phone,preferred_contact_method,time_zone,
    referral_source,relationship_owner,next_action,next_action_date,pricing_classification
  ) values(
    p_client_id,nullif(btrim(p_legal_name),''),nullif(btrim(p_preferred_name),''),nullif(btrim(p_primary_email),''),
    nullif(btrim(p_primary_phone),''),p_preferred_contact_method,nullif(btrim(p_time_zone),''),nullif(btrim(p_referral_source),''),
    auth.uid(),nullif(btrim(p_next_action),''),p_next_action_date,p_pricing_classification
  )
  on conflict(client_id) do update set
    legal_name=excluded.legal_name,
    preferred_name=excluded.preferred_name,
    primary_email=excluded.primary_email,
    primary_phone=excluded.primary_phone,
    preferred_contact_method=excluded.preferred_contact_method,
    time_zone=excluded.time_zone,
    referral_source=excluded.referral_source,
    next_action=excluded.next_action,
    next_action_date=excluded.next_action_date,
    pricing_classification=excluded.pricing_classification,
    updated_at=now();

  if nullif(btrim(p_preferred_name),'') is not null then
    update registry.clients set display_name=btrim(p_preferred_name),updated_at=now() where client_id=p_client_id;
  end if;
end;
$$;

revoke all on function public.admin_update_client_relationship_v1(text,text,text,text,text,text,text,text,text,date,text) from public;
revoke all on function public.admin_update_client_relationship_v1(text,text,text,text,text,text,text,text,text,date,text) from anon;
grant execute on function public.admin_update_client_relationship_v1(text,text,text,text,text,text,text,text,text,date,text) to authenticated;

create or replace function public.admin_set_client_portal_user_v1(
  p_client_id text,
  p_email text,
  p_relationship_role text default 'authorized_contact',
  p_active boolean default true,
  p_reason text default null
)
returns uuid
language plpgsql
security definer
set search_path=''
as $$
declare target_user uuid; link_id uuid;
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  if p_relationship_role not in ('primary','authorized_contact','billing_contact','contract_contact','read_only') then raise exception 'invalid relationship role' using errcode='22023'; end if;
  if not exists(select 1 from registry.clients where client_id=p_client_id) then raise exception 'client not found' using errcode='P0002'; end if;
  select id into target_user from auth.users where lower(email)=lower(btrim(p_email)) limit 1;
  if target_user is null then raise exception 'no authenticated user exists for that email' using errcode='P0002'; end if;

  insert into public.client_user_links(client_id,user_id,relationship_role,active,created_by,revoked_at,revoke_reason)
  values(p_client_id,target_user,p_relationship_role,p_active,auth.uid(),case when p_active then null else now() end,case when p_active then null else nullif(btrim(p_reason),'') end)
  on conflict(client_id,user_id) do update set
    relationship_role=excluded.relationship_role,
    active=excluded.active,
    revoked_at=case when excluded.active then null else now() end,
    revoke_reason=case when excluded.active then null else nullif(btrim(p_reason),'') end,
    updated_at=now()
  returning id into link_id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),private.current_user_role(),case when p_active then 'CLIENT_PORTAL_ACCESS_GRANTED' else 'CLIENT_PORTAL_ACCESS_REVOKED' end,
    'client',p_client_id,jsonb_build_object('linked_user_id',target_user,'relationship_role',p_relationship_role,'reason',p_reason));
  return link_id;
end;
$$;

revoke all on function public.admin_set_client_portal_user_v1(text,text,text,boolean,text) from public;
revoke all on function public.admin_set_client_portal_user_v1(text,text,text,boolean,text) from anon;
grant execute on function public.admin_set_client_portal_user_v1(text,text,text,boolean,text) to authenticated;

create or replace function public.admin_client_intake_queue_v1(p_limit integer default 100)
returns table(
  intake_id uuid,status text,service_requested text,display_name text,email text,phone text,matter_summary text,
  referral_source text,created_at timestamptz,submitted_at timestamptz
)
language plpgsql
stable
security definer
set search_path=''
as $$
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  return query
  select i.id,i.status,i.service_requested,
    coalesce(nullif(i.contact->>'display_name',''),p.display_name,u.email),
    coalesce(nullif(i.contact->>'email',''),u.email),
    nullif(i.contact->>'phone',''),i.matter_summary,i.referral_source,i.created_at,i.submitted_at
  from public.intake_submissions i
  join auth.users u on u.id=i.user_id
  left join public.profiles p on p.id=i.user_id
  where i.status in ('SUBMITTED','IN_REVIEW')
  order by coalesce(i.submitted_at,i.created_at) asc
  limit least(greatest(coalesce(p_limit,100),1),500);
end;
$$;

revoke all on function public.admin_client_intake_queue_v1(integer) from public;
revoke all on function public.admin_client_intake_queue_v1(integer) from anon;
grant execute on function public.admin_client_intake_queue_v1(integer) to authenticated;
