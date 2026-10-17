-- Owner Portal drill-through: read-only, role-gated views.
-- Not a production grant. Deploy only through the existing migration/release gate.
-- No client access, no mutations, and no promotion of archived synthetic fixtures.
create or replace function public.admin_sop_detail_v1(p_artifact_key text)
returns jsonb language plpgsql security definer set search_path = ''
as $fn$
declare result jsonb;
begin
  if auth.uid() is null or coalesce(private.current_user_role(), '') not in ('owner','admin') then
    raise exception 'not authorized' using errcode = '42501';
  end if;
  select jsonb_build_object(
    'sop_id',s.sop_id, 'artifact_key',a.artifact_key, 'title',a.title,
    'owning_domain',s.owning_domain, 'status',s.status,
    'version',a.version, 'approved_by',s.approved_by,'approved_at',s.approved_at,
    'record_key',r.record_key, 'record_status',r.status, 'authority',r.authority,
    'content',r.content, 'source_ref',r.source_ref,
    'authoritative_uri',a.authoritative_uri
  ) into result
  from registry.sops s
  join registry.artifacts a on a.artifact_id = s.artifact_id
  join registry.records r on r.record_id = a.record_id
  where a.artifact_key = p_artifact_key;
  if result is null then raise exception 'procedure not found' using errcode = 'P0002'; end if;
  return result;
end
$fn$;

create or replace function public.admin_case_register_v1()
returns jsonb language plpgsql security definer set search_path = ''
as $fn$
declare result jsonb;
begin
  if auth.uid() is null or coalesce(private.current_user_role(), '') not in ('owner','admin') then
    raise exception 'not authorized' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(jsonb_build_object(
    'case_id', c.case_id, 'case_prefix', c.case_prefix,
    'client_id', c.client_id, 'client_name', cl.display_name,
    'status', c.status, 'opened_on', c.opened_on, 'closed_on', c.closed_on,
    'synthetic', coalesce((c.metadata->>'synthetic')::boolean,false)
  ) order by c.opened_on desc nulls last, c.case_id), '[]'::jsonb)
  into result
  from registry.cases c left join registry.clients cl on cl.client_id=c.client_id;
  return result;
end
$fn$;

create or replace function public.admin_case_detail_v1(p_case_id text)
returns jsonb language plpgsql security definer set search_path = ''
as $fn$
declare result jsonb;
begin
  if auth.uid() is null or coalesce(private.current_user_role(), '') not in ('owner','admin') then
    raise exception 'not authorized' using errcode = '42501';
  end if;
  select jsonb_build_object(
    'case', jsonb_build_object(
      'case_id',c.case_id,'case_prefix',c.case_prefix,
      'client_id',c.client_id,'client_name',cl.display_name,
      'status',c.status,'opened_on',c.opened_on,'closed_on',c.closed_on,
      'synthetic',coalesce((c.metadata->>'synthetic')::boolean,false)
    ),
    'sources',coalesce((
      select jsonb_agg(jsonb_build_object(
        'source_id',s.source_id,'filename',s.original_filename,'source_type',s.source_type,
        'status',s.status,'version',s.version,'authenticity_status',s.authenticity_status,
        'publication_status',s.publication_status,'source_code',s.source_code,
        'linked_at',cs.linked_at
      ) order by cs.linked_at,s.source_id)
      from registry.case_sources cs join registry.sources s on s.source_id=cs.source_id
      where cs.case_id=c.case_id
    ),'[]'::jsonb),
    'uploads',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',u.id,'filename',u.original_filename,'status',u.status,'source_id',u.source_id,
        'storage_bucket',u.storage_bucket,'storage_path',u.storage_path,
        'created_at',u.created_at
      ) order by u.created_at desc)
      from public.upload_records u where u.case_id=c.case_id
    ),'[]'::jsonb),
    'requests',coalesce((select jsonb_agg(to_jsonb(d) order by d.created_at desc)
      from public.document_requests d where d.case_id=c.case_id),'[]'::jsonb),
    'assignments',coalesce((
      select jsonb_agg(jsonb_build_object('staff',p.display_name,'role',a.assignment_role,
        'active',a.active,'assigned_at',a.assigned_at) order by a.assigned_at desc)
      from public.case_assignments a left join public.profiles p on p.id=a.staff_user_id
      where a.case_id=c.case_id
    ),'[]'::jsonb),
    'intakes',coalesce((
      select jsonb_agg(jsonb_build_object('id',i.id,'status',i.status,
        'service_requested',i.service_requested,'submitted_at',i.submitted_at) order by i.created_at desc)
      from public.intake_submissions i where i.case_id=c.case_id
    ),'[]'::jsonb),
    'contracts',coalesce((
      select jsonb_agg(jsonb_build_object('id',ct.id,'title',ct.title,
        'contract_type',ct.contract_type,'status',ct.status,'version',ct.version,
        'updated_at',ct.updated_at) order by ct.updated_at desc)
      from public.contract_records ct where ct.case_id=c.case_id
    ),'[]'::jsonb),
    'events',coalesce((
      select jsonb_agg(jsonb_build_object('title',e.title,'description',e.description,
        'event_code',e.event_code,'status',e.status,'event_at',e.event_at) order by e.event_at)
      from registry.case_events e where e.case_id=c.case_id
    ),'[]'::jsonb),
    'issues',coalesce((
      select jsonb_agg(jsonb_build_object('title',i.title,'issue_code',i.issue_code,
        'status',i.status,'description',i.description) order by i.created_at)
      from registry.case_issues i where i.case_id=c.case_id
    ),'[]'::jsonb),
    'obligations',coalesce((
      select jsonb_agg(jsonb_build_object('title',o.title,'obligation_code',o.obligation_code,
        'performance_status',o.performance_status,'due_at',o.due_at) order by o.created_at)
      from registry.case_obligations o where o.case_id=c.case_id
    ),'[]'::jsonb),
    'notes',coalesce((
      select jsonb_agg(jsonb_build_object('note_type',n.note_type,'body',n.body,
        'created_at',n.created_at) order by n.created_at desc)
      from public.case_notes n where n.case_id=c.case_id
    ),'[]'::jsonb),
    'published_reports',coalesce((
      select jsonb_agg(jsonb_build_object('title',pr.title,'version',pr.version,
        'published_at',pr.published_at,'revoked_at',pr.revoked_at) order by pr.published_at desc)
      from public.published_reports pr where pr.case_id=c.case_id
    ),'[]'::jsonb)
  ) into result
  from registry.cases c left join registry.clients cl on cl.client_id=c.client_id
  where c.case_id=p_case_id;
  if result is null then raise exception 'case not found' using errcode='P0002'; end if;
  return result;
end
$fn$;

revoke all on function public.admin_sop_detail_v1(text) from public, anon;
revoke all on function public.admin_case_register_v1() from public, anon;
revoke all on function public.admin_case_detail_v1(text) from public, anon;
grant execute on function public.admin_sop_detail_v1(text) to authenticated;
grant execute on function public.admin_case_register_v1() to authenticated;
grant execute on function public.admin_case_detail_v1(text) to authenticated;
