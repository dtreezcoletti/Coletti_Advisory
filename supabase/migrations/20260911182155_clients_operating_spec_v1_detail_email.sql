-- Owner/Admin client detail needs the linked portal user's email for access administration.
create or replace function public.client_detail_v1(p_client_id text)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare result jsonb;
begin
  if auth.uid() is null or not private.can_access_client(p_client_id) then raise exception 'not authorized' using errcode='42501'; end if;
  select jsonb_build_object(
    'client',jsonb_build_object(
      'client_id',c.client_id,'display_name',coalesce(rp.preferred_name,c.display_name),'legal_name',rp.legal_name,
      'client_type',coalesce(rp.client_type,'INDIVIDUAL'),'status',c.status,'enrollment_year',c.enrollment_year,'created_at',c.created_at,
      'updated_at',greatest(c.updated_at,coalesce(rp.updated_at,c.updated_at)),'primary_email',rp.primary_email,'primary_phone',rp.primary_phone,
      'preferred_contact_method',rp.preferred_contact_method,'time_zone',rp.time_zone,'referral_source',rp.referral_source,
      'relationship_owner',rp.relationship_owner,'relationship_owner_name',op.display_name,'next_action',rp.next_action,'next_action_date',rp.next_action_date,
      'attention_flags',coalesce(rp.attention_flags,'[]'::jsonb),'pricing_classification',coalesce(rp.pricing_classification,'STANDARD')),
    'cases',coalesce((select jsonb_agg(jsonb_build_object('case_id',x.case_id,'status',x.status,'opened_on',x.opened_on,'closed_on',x.closed_on) order by x.opened_on desc nulls last,x.case_id) from registry.cases x where x.client_id=c.client_id),'[]'::jsonb),
    'authorized_users',case when private.is_admin() then coalesce((select jsonb_agg(jsonb_build_object('user_id',l.user_id,'email',u.email,'display_name',p.display_name,'role',l.relationship_role,'active',l.active,'created_at',l.created_at,'revoked_at',l.revoked_at,'revoke_reason',l.revoke_reason) order by l.created_at) from public.client_user_links l join auth.users u on u.id=l.user_id left join public.profiles p on p.id=l.user_id where l.client_id=c.client_id),'[]'::jsonb) else '[]'::jsonb end,
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
