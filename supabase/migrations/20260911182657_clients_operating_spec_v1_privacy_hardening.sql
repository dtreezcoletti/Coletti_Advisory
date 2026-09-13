-- Clients v1 privacy hardening: RPC-only reads and minimum-necessary fields.

revoke all on public.client_user_links from authenticated;
revoke all on public.client_relationship_profiles from authenticated;
revoke all on public.client_user_links from anon;
revoke all on public.client_relationship_profiles from anon;
revoke all on public.client_user_links from public;
revoke all on public.client_relationship_profiles from public;

revoke all on function public.staff_registry_lookup(text,integer) from public;
revoke all on function public.staff_registry_lookup(text,integer) from anon;
grant execute on function public.staff_registry_lookup(text,integer) to authenticated;
revoke all on function public.staff_registry_client_cases(text) from public;
revoke all on function public.staff_registry_client_cases(text) from anon;
grant execute on function public.staff_registry_client_cases(text) to authenticated;

create or replace function public.client_directory_v1(p_query text default null,p_status text default null,p_limit integer default 200)
returns table(
  client_id text,display_name text,client_status text,client_type text,primary_email text,primary_phone text,
  referral_source text,relationship_owner uuid,relationship_owner_name text,active_case_count bigint,total_case_count bigint,
  portal_active boolean,next_action text,next_action_date date,pricing_classification text,updated_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select c.client_id,
    coalesce(rp.preferred_name,c.display_name),
    c.status,
    coalesce(rp.client_type,'INDIVIDUAL'),
    case when private.is_admin() or exists(select 1 from public.client_user_links own_link where own_link.client_id=c.client_id and own_link.user_id=auth.uid() and own_link.active) then rp.primary_email else null end,
    case when private.is_admin() or exists(select 1 from public.client_user_links own_link where own_link.client_id=c.client_id and own_link.user_id=auth.uid() and own_link.active) then rp.primary_phone else null end,
    case when private.is_admin() then rp.referral_source else null end,
    rp.relationship_owner,
    owner_profile.display_name,
    count(distinct cs.case_id) filter (where (private.is_admin() or private.can_access_case(cs.case_id)) and cs.status not in ('CLOSED','ARCHIVED')),
    count(distinct cs.case_id) filter (where private.is_admin() or private.can_access_case(cs.case_id)),
    case when private.is_admin() then exists(select 1 from public.client_user_links cul where cul.client_id=c.client_id and cul.active)
         else exists(select 1 from public.client_user_links cul where cul.client_id=c.client_id and cul.user_id=auth.uid() and cul.active) end,
    case when private.is_staff() then rp.next_action else null end,
    case when private.is_staff() then rp.next_action_date else null end,
    case when private.is_admin() then coalesce(rp.pricing_classification,'STANDARD') else null end,
    greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at),coalesce(max(cs.updated_at) filter (where private.is_admin() or private.can_access_case(cs.case_id)),c.updated_at))
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
      or (private.is_admin() and coalesce(rp.primary_email,'') ilike '%'||btrim(p_query)||'%')
      or (private.is_admin() and coalesce(rp.primary_phone,'') ilike '%'||btrim(p_query)||'%')
      or exists(select 1 from registry.cases qcs where qcs.client_id=c.client_id and (private.is_admin() or private.can_access_case(qcs.case_id)) and qcs.case_id ilike '%'||btrim(p_query)||'%')
    )
  group by c.client_id,c.display_name,c.status,c.updated_at,rp.client_type,rp.preferred_name,rp.primary_email,rp.primary_phone,rp.referral_source,
    rp.relationship_owner,owner_profile.display_name,rp.next_action,rp.next_action_date,rp.pricing_classification,rp.updated_at
  order by greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at),coalesce(max(cs.updated_at) filter (where private.is_admin() or private.can_access_case(cs.case_id)),c.updated_at)) desc,c.client_id
  limit least(greatest(coalesce(p_limit,200),1),500);
$$;

create or replace function public.client_detail_v1(p_client_id text)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare result jsonb; self_link boolean;
begin
  if auth.uid() is null or not private.can_access_client(p_client_id) then raise exception 'not authorized' using errcode='42501'; end if;
  select exists(select 1 from public.client_user_links l where l.client_id=p_client_id and l.user_id=auth.uid() and l.active) into self_link;
  select jsonb_build_object(
    'client',jsonb_build_object(
      'client_id',c.client_id,'display_name',coalesce(rp.preferred_name,c.display_name),
      'legal_name',case when private.is_admin() or self_link then rp.legal_name else null end,
      'client_type',coalesce(rp.client_type,'INDIVIDUAL'),'status',c.status,'enrollment_year',c.enrollment_year,'created_at',c.created_at,
      'updated_at',greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at)),
      'primary_email',case when private.is_admin() or self_link then rp.primary_email else null end,
      'primary_phone',case when private.is_admin() or self_link then rp.primary_phone else null end,
      'preferred_contact_method',case when private.is_admin() or self_link then rp.preferred_contact_method else null end,
      'time_zone',case when private.is_admin() or self_link then rp.time_zone else null end,
      'referral_source',case when private.is_admin() then rp.referral_source else null end,
      'relationship_owner',rp.relationship_owner,'relationship_owner_name',op.display_name,
      'next_action',case when private.is_staff() then rp.next_action else null end,
      'next_action_date',case when private.is_staff() then rp.next_action_date else null end,
      'attention_flags',case when private.is_admin() then coalesce(rp.attention_flags,'[]'::jsonb) else '[]'::jsonb end,
      'pricing_classification',case when private.is_admin() then coalesce(rp.pricing_classification,'STANDARD') else null end),
    'cases',coalesce((select jsonb_agg(jsonb_build_object('case_id',x.case_id,'status',x.status,'opened_on',x.opened_on,'closed_on',x.closed_on) order by x.opened_on desc nulls last,x.case_id) from registry.cases x where x.client_id=c.client_id and (private.is_admin() or private.can_access_case(x.case_id))),'[]'::jsonb),
    'authorized_users',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('user_id',l.user_id,'email',u.email,'display_name',p.display_name,'role',l.relationship_role,'active',l.active,'created_at',l.created_at,'revoked_at',l.revoked_at,'revoke_reason',l.revoke_reason) order by l.created_at) from public.client_user_links l join auth.users u on u.id=l.user_id left join public.profiles p on p.id=l.user_id where l.client_id=c.client_id),'[]'::jsonb) else '[]'::jsonb end,
    'contracts',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('contract_id',ct.contract_id,'case_id',ct.case_id,'status',ct.contract_status,'executed_at',ct.executed_at,'effective_from',ct.effective_from,'effective_to',ct.effective_to) order by ct.created_at desc) from registry.contracts ct where ct.client_id=c.client_id),'[]'::jsonb) else '[]'::jsonb end,
    'reports',coalesce((select jsonb_agg(jsonb_build_object('report_id',rr.report_id,'case_id',rr.case_id,'report_type',rr.report_type,'publication_status',rr.publication_status,'published_at',rr.published_at) order by rr.created_at desc) from registry.reports rr where rr.client_id=c.client_id and (private.is_admin() or (rr.case_id is not null and private.can_access_case(rr.case_id)))),'[]'::jsonb),
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
