-- Clients Operating Specification v1
-- Canonical identity remains in registry.clients. Public tables are operational relationship/access projections.

create table public.client_user_links (
  id uuid primary key default gen_random_uuid(),
  client_id text not null references registry.clients(client_id) on delete restrict,
  user_id uuid not null references auth.users(id) on delete cascade,
  relationship_role text not null default 'primary'
    check (relationship_role in ('primary','authorized_contact','billing_contact','contract_contact','read_only')),
  active boolean not null default true,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  revoked_at timestamptz,
  revoke_reason text,
  unique (client_id, user_id)
);

create table public.client_relationship_profiles (
  client_id text primary key references registry.clients(client_id) on delete restrict,
  client_type text not null default 'INDIVIDUAL' check (client_type in ('INDIVIDUAL','ORGANIZATION')),
  legal_name text,
  preferred_name text,
  primary_email text,
  primary_phone text,
  address jsonb not null default '{}'::jsonb,
  preferred_contact_method text check (preferred_contact_method is null or preferred_contact_method in ('PORTAL','EMAIL','PHONE')),
  time_zone text,
  referral_source text,
  relationship_owner uuid references auth.users(id),
  next_action text,
  next_action_date date,
  attention_flags jsonb not null default '[]'::jsonb,
  pricing_classification text not null default 'STANDARD'
    check (pricing_classification in ('STANDARD','REDUCED_FEE','PROMOTIONAL_PILOT','PRO_BONO','CUSTOM')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index client_user_links_user_active_idx on public.client_user_links(user_id, active);
create index client_user_links_client_active_idx on public.client_user_links(client_id, active);
create index client_relationship_profiles_owner_idx on public.client_relationship_profiles(relationship_owner);
create index client_relationship_profiles_next_action_idx on public.client_relationship_profiles(next_action_date) where next_action_date is not null;

create or replace function private.can_access_client(target_client_id text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select private.is_admin()
    or exists (
      select 1 from public.client_user_links l
      where l.client_id = target_client_id
        and l.user_id = (select auth.uid())
        and l.active
    )
    or exists (
      select 1
      from registry.cases c
      join public.case_assignments a on a.case_id = c.case_id
      where c.client_id = target_client_id
        and a.staff_user_id = (select auth.uid())
        and a.active
    );
$$;

alter table public.client_user_links enable row level security;
alter table public.client_relationship_profiles enable row level security;
revoke all on public.client_user_links from anon;
revoke all on public.client_relationship_profiles from anon;
revoke all on public.client_user_links from authenticated;
revoke all on public.client_relationship_profiles from authenticated;
grant select, insert, update on public.client_user_links to authenticated;
grant select, insert, update on public.client_relationship_profiles to authenticated;

create policy client_user_links_select_v1 on public.client_user_links
for select to authenticated using (private.can_access_client(client_id));
create policy client_user_links_admin_insert_v1 on public.client_user_links
for insert to authenticated with check (private.is_admin());
create policy client_user_links_admin_update_v1 on public.client_user_links
for update to authenticated using (private.is_admin()) with check (private.is_admin());

create policy client_relationship_profiles_select_v1 on public.client_relationship_profiles
for select to authenticated using (private.can_access_client(client_id));
create policy client_relationship_profiles_admin_insert_v1 on public.client_relationship_profiles
for insert to authenticated with check (private.is_admin());
create policy client_relationship_profiles_admin_update_v1 on public.client_relationship_profiles
for update to authenticated using (private.is_admin()) with check (private.is_admin());

create trigger trg_client_user_links_updated before update on public.client_user_links
for each row execute function private.set_updated_at();
create trigger trg_client_relationship_profiles_updated before update on public.client_relationship_profiles
for each row execute function private.set_updated_at();
create trigger audit_client_user_links after insert or update or delete on public.client_user_links
for each row execute function private.audit_mutation();
create trigger audit_client_relationship_profiles after insert or update or delete on public.client_relationship_profiles
for each row execute function private.audit_mutation();

create or replace function public.client_directory_v1(p_query text default null,p_status text default null,p_limit integer default 200)
returns table(
  client_id text,display_name text,client_status text,client_type text,primary_email text,primary_phone text,
  referral_source text,relationship_owner uuid,relationship_owner_name text,active_case_count bigint,total_case_count bigint,
  portal_active boolean,next_action text,next_action_date date,pricing_classification text,updated_at timestamptz
)
language sql stable security definer set search_path = ''
as $$
  select c.client_id,coalesce(rp.preferred_name,c.display_name),c.status,coalesce(rp.client_type,'INDIVIDUAL'),rp.primary_email,rp.primary_phone,
    rp.referral_source,rp.relationship_owner,owner_profile.display_name,
    count(distinct cs.case_id) filter (where cs.status not in ('CLOSED','ARCHIVED')),
    count(distinct cs.case_id),
    exists(select 1 from public.client_user_links cul where cul.client_id=c.client_id and cul.active),
    rp.next_action,rp.next_action_date,coalesce(rp.pricing_classification,'STANDARD'),
    greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at),coalesce(max(cs.updated_at),c.updated_at))
  from registry.clients c
  left join public.client_relationship_profiles rp on rp.client_id=c.client_id
  left join public.profiles owner_profile on owner_profile.id=rp.relationship_owner
  left join registry.cases cs on cs.client_id=c.client_id
  where private.can_access_client(c.client_id)
    and (p_status is null or c.status=p_status)
    and (
      nullif(btrim(p_query),'') is null
      or c.client_id ilike '%'||btrim(p_query)||'%'
      or coalesce(rp.preferred_name,c.display_name,'') ilike '%'||btrim(p_query)||'%'
      or coalesce(rp.legal_name,'') ilike '%'||btrim(p_query)||'%'
      or coalesce(rp.primary_email,'') ilike '%'||btrim(p_query)||'%'
      or coalesce(rp.primary_phone,'') ilike '%'||btrim(p_query)||'%'
      or exists(select 1 from registry.cases qcs where qcs.client_id=c.client_id and qcs.case_id ilike '%'||btrim(p_query)||'%')
    )
  group by c.client_id,c.display_name,c.status,c.updated_at,rp.client_type,rp.preferred_name,rp.primary_email,rp.primary_phone,rp.referral_source,
    rp.relationship_owner,owner_profile.display_name,rp.next_action,rp.next_action_date,rp.pricing_classification,rp.updated_at
  order by greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at),coalesce(max(cs.updated_at),c.updated_at)) desc,c.client_id
  limit least(greatest(coalesce(p_limit,200),1),500);
$$;
revoke all on function public.client_directory_v1(text,text,integer) from public;
revoke all on function public.client_directory_v1(text,text,integer) from anon;
grant execute on function public.client_directory_v1(text,text,integer) to authenticated;

create or replace function public.client_detail_v1(p_client_id text)
returns jsonb language plpgsql stable security definer set search_path = ''
as $$
declare result jsonb;
begin
  if auth.uid() is null or not private.can_access_client(p_client_id) then raise exception 'not authorized' using errcode='42501'; end if;
  select jsonb_build_object(
    'client',jsonb_build_object('client_id',c.client_id,'display_name',coalesce(rp.preferred_name,c.display_name),'legal_name',rp.legal_name,'client_type',coalesce(rp.client_type,'INDIVIDUAL'),'status',c.status,'enrollment_year',c.enrollment_year,'created_at',c.created_at,'updated_at',greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at)),'primary_email',rp.primary_email,'primary_phone',rp.primary_phone,'preferred_contact_method',rp.preferred_contact_method,'time_zone',rp.time_zone,'referral_source',rp.referral_source,'relationship_owner',rp.relationship_owner,'relationship_owner_name',op.display_name,'next_action',rp.next_action,'next_action_date',rp.next_action_date,'attention_flags',coalesce(rp.attention_flags,'[]'::jsonb),'pricing_classification',coalesce(rp.pricing_classification,'STANDARD')),
    'cases',coalesce((select jsonb_agg(jsonb_build_object('case_id',x.case_id,'status',x.status,'opened_on',x.opened_on,'closed_on',x.closed_on) order by x.opened_on desc nulls last,x.case_id) from registry.cases x where x.client_id=c.client_id),'[]'::jsonb),
    'authorized_users',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('user_id',l.user_id,'display_name',p.display_name,'role',l.relationship_role,'active',l.active,'created_at',l.created_at) order by l.created_at) from public.client_user_links l left join public.profiles p on p.id=l.user_id where l.client_id=c.client_id),'[]'::jsonb) else '[]'::jsonb end,
    'contracts',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('contract_id',ct.contract_id,'case_id',ct.case_id,'status',ct.contract_status,'executed_at',ct.executed_at,'effective_from',ct.effective_from,'effective_to',ct.effective_to) order by ct.created_at desc) from registry.contracts ct where ct.client_id=c.client_id),'[]'::jsonb) else '[]'::jsonb end,
    'reports',coalesce((select jsonb_agg(jsonb_build_object('report_id',rr.report_id,'case_id',rr.case_id,'report_type',rr.report_type,'publication_status',rr.publication_status,'published_at',rr.published_at) order by rr.created_at desc) from registry.reports rr where rr.client_id=c.client_id),'[]'::jsonb),
    'invoices',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'case_id',i.case_id,'invoice_number',i.invoice_number,'amount_cents',i.amount_cents,'status',i.status,'due_date',i.due_date) order by i.created_at desc) from public.invoices i join public.client_user_links l on l.user_id=i.client_user_id and l.client_id=c.client_id where l.active),'[]'::jsonb) else '[]'::jsonb end,
    'audit',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('action',a.action,'object_type',a.object_type,'actor_role',a.actor_role,'created_at',a.created_at) order by a.created_at desc) from public.audit_events a where (a.object_type in ('client_user_links','client_relationship_profiles') and (a.metadata->'safe_after'->>'client_id'=c.client_id or a.metadata->'safe_before'->>'client_id'=c.client_id)) or (a.object_type='clients' and a.object_id=c.client_id)),'[]'::jsonb) else '[]'::jsonb end
  ) into result
  from registry.clients c
  left join public.client_relationship_profiles rp on rp.client_id=c.client_id
  left join public.profiles op on op.id=rp.relationship_owner
  where c.client_id=p_client_id;
  if result is null then raise exception 'client not found' using errcode='P0002'; end if;
  return result;
end;
$$;
revoke all on function public.client_detail_v1(text) from public;
revoke all on function public.client_detail_v1(text) from anon;
grant execute on function public.client_detail_v1(text) to authenticated;

create or replace function public.admin_client_duplicate_candidates_v1(p_name text default null,p_email text default null,p_phone text default null)
returns table(client_id text,display_name text,primary_email text,primary_phone text,reason text)
language plpgsql stable security definer set search_path=''
as $$
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  return query
  select c.client_id,coalesce(rp.preferred_name,c.display_name),rp.primary_email,rp.primary_phone,
    concat_ws(', ',case when nullif(btrim(p_email),'') is not null and lower(rp.primary_email)=lower(btrim(p_email)) then 'email match' end,
      case when nullif(regexp_replace(coalesce(p_phone,''),'\D','','g'),'') is not null and regexp_replace(coalesce(rp.primary_phone,''),'\D','','g')=regexp_replace(coalesce(p_phone,''),'\D','','g') then 'phone match' end,
      case when nullif(btrim(p_name),'') is not null and lower(coalesce(rp.legal_name,rp.preferred_name,c.display_name,''))=lower(btrim(p_name)) then 'name match' end)
  from registry.clients c left join public.client_relationship_profiles rp on rp.client_id=c.client_id
  where (nullif(btrim(p_email),'') is not null and lower(coalesce(rp.primary_email,''))=lower(btrim(p_email)))
     or (nullif(regexp_replace(coalesce(p_phone,''),'\D','','g'),'') is not null and regexp_replace(coalesce(rp.primary_phone,''),'\D','','g')=regexp_replace(coalesce(p_phone,''),'\D','','g'))
     or (nullif(btrim(p_name),'') is not null and lower(coalesce(rp.legal_name,rp.preferred_name,c.display_name,''))=lower(btrim(p_name)))
  order by c.updated_at desc limit 25;
end;
$$;
revoke all on function public.admin_client_duplicate_candidates_v1(text,text,text) from public;
revoke all on function public.admin_client_duplicate_candidates_v1(text,text,text) from anon;
grant execute on function public.admin_client_duplicate_candidates_v1(text,text,text) to authenticated;

create or replace function public.admin_accept_intake_v1(p_intake_id uuid,p_client_type text default 'INDIVIDUAL')
returns text language plpgsql security definer set search_path=''
as $$
declare i public.intake_submissions%rowtype; existing_client text; new_record uuid; new_client text; person_name text; person_email text; person_phone text;
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  if p_client_type not in ('INDIVIDUAL','ORGANIZATION') then raise exception 'invalid client type' using errcode='22023'; end if;
  select * into i from public.intake_submissions where id=p_intake_id for update;
  if not found then raise exception 'intake not found' using errcode='P0002'; end if;
  if i.status in ('DECLINED','WITHDRAWN') then raise exception 'declined or withdrawn intake cannot be accepted' using errcode='22023'; end if;
  select l.client_id into existing_client from public.client_user_links l where l.user_id=i.user_id and l.active and l.relationship_role='primary' order by l.created_at limit 1;
  person_name:=coalesce(nullif(i.contact->>'display_name',''),(select p.display_name from public.profiles p where p.id=i.user_id),(select u.email from auth.users u where u.id=i.user_id),'Client');
  person_email:=coalesce(nullif(i.contact->>'email',''),(select u.email from auth.users u where u.id=i.user_id));
  person_phone:=nullif(i.contact->>'phone','');
  if existing_client is not null then
    update public.intake_submissions set status='ACCEPTED' where id=i.id;
    insert into public.client_relationship_profiles(client_id,client_type,legal_name,preferred_name,primary_email,primary_phone,referral_source,relationship_owner)
    values(existing_client,p_client_type,person_name,person_name,person_email,person_phone,i.referral_source,auth.uid())
    on conflict(client_id) do update set primary_email=coalesce(public.client_relationship_profiles.primary_email,excluded.primary_email),primary_phone=coalesce(public.client_relationship_profiles.primary_phone,excluded.primary_phone),referral_source=coalesce(public.client_relationship_profiles.referral_source,excluded.referral_source),updated_at=now();
    insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
    values(auth.uid(),private.current_user_role(),'INTAKE_ACCEPTED_EXISTING_CLIENT','client',existing_client,jsonb_build_object('intake_id',i.id));
    return existing_client;
  end if;
  if person_email is not null and exists(select 1 from public.client_relationship_profiles rp where lower(rp.primary_email)=lower(person_email)) then raise exception 'possible duplicate client: email already exists; review duplicate candidates before acceptance' using errcode='23505'; end if;
  if person_phone is not null and regexp_replace(person_phone,'\D','','g')<>'' and exists(select 1 from public.client_relationship_profiles rp where regexp_replace(coalesce(rp.primary_phone,''),'\D','','g')=regexp_replace(person_phone,'\D','','g')) then raise exception 'possible duplicate client: phone already exists; review duplicate candidates before acceptance' using errcode='23505'; end if;
  insert into registry.records(scope,record_key,record_type,title,content,epistemic_classification,status,authority,source_type,source_ref,metadata)
  values('client','client-intake:'||i.id::text,'client_identity',person_name,jsonb_build_object('intake_id',i.id,'auth_user_id',i.user_id),'FACT','ACTIVE','INSTITUTIONAL_REGISTRY','INTAKE',i.id::text,jsonb_build_object('created_via','admin_accept_intake_v1')) returning record_id into new_record;
  insert into registry.clients(client_id,record_id,enrollment_year,display_name,status,metadata)
  values(null,new_record,extract(year from current_date)::int,person_name,'ONBOARDING',jsonb_build_object('origin_intake_id',i.id)) returning client_id into new_client;
  insert into public.client_user_links(client_id,user_id,relationship_role,active,created_by) values(new_client,i.user_id,'primary',true,auth.uid());
  insert into public.client_relationship_profiles(client_id,client_type,legal_name,preferred_name,primary_email,primary_phone,referral_source,relationship_owner)
  values(new_client,p_client_type,person_name,person_name,person_email,person_phone,i.referral_source,auth.uid());
  update public.intake_submissions set status='ACCEPTED' where id=i.id;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),private.current_user_role(),'CLIENT_ACCEPTED','client',new_client,jsonb_build_object('intake_id',i.id,'client_type',p_client_type));
  return new_client;
end;
$$;
revoke all on function public.admin_accept_intake_v1(uuid,text) from public;
revoke all on function public.admin_accept_intake_v1(uuid,text) from anon;
grant execute on function public.admin_accept_intake_v1(uuid,text) to authenticated;

create or replace function public.admin_set_client_status_v1(p_client_id text,p_status text,p_reason text default null)
returns void language plpgsql security definer set search_path=''
as $$
declare old_status text;
begin
  if auth.uid() is null or not private.is_admin() then raise exception 'not authorized' using errcode='42501'; end if;
  if p_status not in ('ONBOARDING','ACTIVE','INACTIVE','ARCHIVED') then raise exception 'invalid client status' using errcode='22023'; end if;
  select status into old_status from registry.clients where client_id=p_client_id for update;
  if not found then raise exception 'client not found' using errcode='P0002'; end if;
  update registry.clients set status=p_status,updated_at=now() where client_id=p_client_id;
  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,metadata)
  values(auth.uid(),private.current_user_role(),'CLIENT_STATUS_CHANGE','client',p_client_id,jsonb_build_object('old_status',old_status,'new_status',p_status,'reason',p_reason));
end;
$$;
revoke all on function public.admin_set_client_status_v1(text,text,text) from public;
revoke all on function public.admin_set_client_status_v1(text,text,text) from anon;
grant execute on function public.admin_set_client_status_v1(text,text,text) to authenticated;

create or replace function public.staff_registry_lookup(p_query text,p_limit integer default 10)
returns table(client_id text,display_name text,client_status text,case_count bigint,match_reason text,match_score double precision)
language plpgsql stable security definer set search_path=''
as $$
begin
  if auth.uid() is null or not private.has_role(array['owner','admin','analyst','reviewer']::text[]) then raise exception 'not authorized' using errcode='42501'; end if;
  if nullif(btrim(p_query),'') is null then raise exception 'query is required' using errcode='22023'; end if;
  return query
  select r.client_id,r.display_name,r.status,r.case_count,r.match_reason,r.match_score
  from registry.lookup_clients(p_query,least(greatest(coalesce(p_limit,10),1),25)) r
  where private.is_admin() or exists(select 1 from registry.cases c join public.case_assignments a on a.case_id=c.case_id where c.client_id=r.client_id and a.staff_user_id=auth.uid() and a.active);
end;
$$;

create or replace function public.staff_registry_client_cases(p_client_id text)
returns table(case_id text,case_status text,opened_on date,closed_on date)
language plpgsql stable security definer set search_path=''
as $$
begin
  if auth.uid() is null or not private.has_role(array['owner','admin','analyst','reviewer']::text[]) then raise exception 'not authorized' using errcode='42501'; end if;
  if nullif(btrim(p_client_id),'') is null then raise exception 'client_id is required' using errcode='22023'; end if;
  if not private.is_admin() and not private.can_access_client(btrim(p_client_id)) then raise exception 'not authorized' using errcode='42501'; end if;
  return query select c.case_id,c.status,c.opened_on,c.closed_on from registry.cases c where c.client_id=btrim(p_client_id) order by c.opened_on desc nulls last,c.case_id;
end;
$$;
