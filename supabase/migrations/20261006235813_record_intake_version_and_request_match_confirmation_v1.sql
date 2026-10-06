-- Version-family and document-request match confirmation controls.
-- Source-controlled mirror of live migration 20261006235813.

CREATE OR REPLACE FUNCTION private.confirm_record_intake_job_impl_v1(p_job_id uuid, p_taxonomy_key text DEFAULT NULL::text, p_source_role text DEFAULT NULL::text, p_client_label text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  j public.record_intake_jobs%rowtype;
  t public.source_taxonomy%rowtype;
  v_key text;
  v_role text;
  v_label text;
  v_source_id text;
  v_seconds integer := 0;
  v_candidate_job uuid;
  v_candidate_source text;
  v_next_version integer;
begin
  if auth.uid() is null or not private.is_staff() then
    raise exception 'staff authorization required' using errcode='42501';
  end if;

  select * into j from public.record_intake_jobs where id=p_job_id for update;
  if not found then raise exception 'intake job not found' using errcode='P0002'; end if;
  if j.case_id is null or not private.can_work_case(j.case_id) then
    raise exception 'case work authorization required' using errcode='42501';
  end if;
  if j.status in ('REGISTERED','RESOLVED_DUPLICATE','REJECTED') then
    if j.registered_source_id is not null then return j.registered_source_id; end if;
    raise exception 'intake job is already closed' using errcode='22023';
  end if;

  v_key := coalesce(nullif(btrim(p_taxonomy_key),''),j.suggested_taxonomy_key);
  select * into t from public.source_taxonomy where taxonomy_key=v_key and active;
  if not found then raise exception 'valid source taxonomy selection required' using errcode='22023'; end if;

  v_role := coalesce(nullif(btrim(p_source_role),''),j.suggested_source_role,t.default_source_role);
  v_label := coalesce(nullif(btrim(p_client_label),''),j.suggested_client_label);

  v_source_id := private.register_upload_as_source_impl_v1(
    j.upload_id,t.source_type,v_role,v_label
  );

  update public.record_request_matches
  set source_id=v_source_id,updated_at=now()
  where upload_id=j.upload_id and source_id is null;

  if nullif(btrim(coalesce(j.probable_version_family_key,'')),'') is not null then
    begin
      v_candidate_job := nullif(j.extracted_metadata->>'probable_version_job_id','')::uuid;
    exception when others then
      v_candidate_job := null;
    end;

    if v_candidate_job is not null then
      select coalesce(c.registered_source_id,u.source_id)
      into v_candidate_source
      from public.record_intake_jobs c
      left join public.upload_records u on u.id=c.upload_id
      where c.id=v_candidate_job and c.case_id=j.case_id
      limit 1;
    end if;

    if v_candidate_source is not null and v_candidate_source<>v_source_id then
      update registry.sources
      set version_family_key=j.probable_version_family_key,updated_at=now()
      where source_id=v_candidate_source;

      select coalesce(max(version),0)+1 into v_next_version
      from registry.sources
      where case_id=j.case_id
        and version_family_key=j.probable_version_family_key
        and source_id<>v_source_id;

      update registry.sources
      set version_family_key=j.probable_version_family_key,
          version=greatest(coalesce(v_next_version,2),2),
          updated_at=now()
      where source_id=v_source_id;

      insert into registry.source_relationships(
        case_id,source_id,related_source_id,relationship_type,confidence,created_by,metadata
      ) values(
        j.case_id,v_source_id,v_candidate_source,'VERSION_OF',
        j.classification_confidence,auth.uid(),
        jsonb_build_object('confirmed_from_intake_job',j.id,'family_key',j.probable_version_family_key)
      )
      on conflict(source_id,related_source_id,relationship_type) do nothing;

      insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
      values(
        auth.uid(),private.current_user_role(),'SOURCE_VERSION_FAMILY_CONFIRMED',
        'source',v_source_id,j.case_id,
        jsonb_build_object('related_source_id',v_candidate_source,'version_family_key',j.probable_version_family_key)
      );
    else
      update registry.sources
      set version_family_key=j.probable_version_family_key,updated_at=now()
      where source_id=v_source_id;
    end if;
  end if;

  if j.review_started_at is not null then
    v_seconds := greatest(0,extract(epoch from (now()-j.review_started_at))::integer);
  end if;

  update public.record_intake_jobs
  set status='REGISTERED',route='GREEN',registered_source_id=v_source_id,
      suggested_taxonomy_key=t.taxonomy_key,suggested_source_type=t.source_type,
      suggested_source_role=v_role,suggested_client_label=v_label,
      reviewed_by=auth.uid(),reviewed_at=now(),
      human_attention_seconds=human_attention_seconds+v_seconds,
      exception_codes='[]'::jsonb,failure_reason=null,updated_at=now()
  where id=p_job_id;

  return v_source_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.confirm_record_request_match_v1(p_match_id uuid, p_request_status text DEFAULT 'UNDER_REVIEW'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  m public.record_request_matches%rowtype;
  r public.document_requests%rowtype;
begin
  if p_request_status not in ('UPLOADED','UNDER_REVIEW') then
    raise exception 'match confirmation may only move a request to UPLOADED or UNDER_REVIEW' using errcode='22023';
  end if;
  if auth.uid() is null or not private.is_staff() then
    raise exception 'staff authorization required' using errcode='42501';
  end if;

  select * into m from public.record_request_matches where id=p_match_id for update;
  if not found then raise exception 'request match not found' using errcode='P0002'; end if;
  select * into r from public.document_requests where id=m.request_id for update;
  if not found or not private.can_work_case(r.case_id) then
    raise exception 'record request not accessible' using errcode='42501';
  end if;

  update public.record_request_matches
  set status='CONFIRMED',reviewed_by=auth.uid(),reviewed_at=now(),updated_at=now()
  where id=p_match_id;

  if r.status in ('OPEN','UPLOADED','UNDER_REVIEW') then
    update public.document_requests set status=p_request_status,updated_at=now() where id=r.id;
  end if;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(
    auth.uid(),private.current_user_role(),'DOCUMENT_REQUEST_MATCH_CONFIRMED',
    'document_request_match',p_match_id::text,r.case_id,
    jsonb_build_object('request_id',r.id,'upload_id',m.upload_id,'source_id',m.source_id,'request_status',p_request_status)
  );
end;
$function$;

CREATE OR REPLACE FUNCTION public.reject_record_request_match_v1(p_match_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  m public.record_request_matches%rowtype;
  r public.document_requests%rowtype;
begin
  if auth.uid() is null or not private.is_staff() then
    raise exception 'staff authorization required' using errcode='42501';
  end if;

  select * into m from public.record_request_matches where id=p_match_id for update;
  if not found then raise exception 'request match not found' using errcode='P0002'; end if;
  select * into r from public.document_requests where id=m.request_id;
  if not found or not private.can_work_case(r.case_id) then
    raise exception 'record request not accessible' using errcode='42501';
  end if;

  update public.record_request_matches
  set status='REJECTED',reviewed_by=auth.uid(),reviewed_at=now(),updated_at=now()
  where id=p_match_id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(
    auth.uid(),private.current_user_role(),'DOCUMENT_REQUEST_MATCH_REJECTED',
    'document_request_match',p_match_id::text,r.case_id,
    jsonb_build_object('request_id',r.id,'upload_id',m.upload_id,'source_id',m.source_id)
  );
end;
$function$;

revoke all on function public.confirm_record_request_match_v1(uuid,text) from public,anon;
grant execute on function public.confirm_record_request_match_v1(uuid,text) to authenticated;
revoke all on function public.reject_record_request_match_v1(uuid) from public,anon;
grant execute on function public.reject_record_request_match_v1(uuid) to authenticated;
