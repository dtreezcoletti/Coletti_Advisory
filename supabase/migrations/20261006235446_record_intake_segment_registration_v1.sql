-- Record Intake segment-review and canonical child-Source registration v1.
-- Source-controlled mirror of live migration 20261006235446.

CREATE OR REPLACE FUNCTION private.refresh_record_intake_job_v1(p_upload_id uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  u public.upload_records%rowtype;
  existing_job public.record_intake_jobs%rowtype;
  v_triage jsonb;
  v_key text;
  v_conf numeric;
  v_bundle text;
  v_tax public.source_taxonomy%rowtype;
  v_dup_source text;
  v_dup_upload uuid;
  v_status text;
  v_route text;
  v_exceptions jsonb := '[]'::jsonb;
  v_job uuid;
begin
  select * into u from public.upload_records where id=p_upload_id;
  if not found then raise exception 'upload not found' using errcode='P0002'; end if;

  select * into existing_job from public.record_intake_jobs where upload_id=u.id;

  if u.status='INGESTED'
     and existing_job.id is not null
     and existing_job.status='REGISTERED'
     and existing_job.registered_source_id is null
     and existing_job.proposed_segment_count > 1 then
    return existing_job.id;
  end if;

  if u.source_id is not null then
    insert into public.record_intake_jobs(
      upload_id,case_id,intake_id,status,route,registered_source_id,processed_at,updated_at
    ) values(
      u.id,u.case_id,u.intake_id,'REGISTERED','GREEN',u.source_id,now(),now()
    )
    on conflict(upload_id) do update set
      case_id=excluded.case_id,intake_id=excluded.intake_id,status='REGISTERED',
      route='GREEN',registered_source_id=excluded.registered_source_id,
      processed_at=now(),updated_at=now()
    returning id into v_job;
    return v_job;
  end if;

  if u.status='REJECTED' then
    insert into public.record_intake_jobs(upload_id,case_id,intake_id,status,route,updated_at)
    values(u.id,u.case_id,u.intake_id,'REJECTED','NONE',now())
    on conflict(upload_id) do update set case_id=excluded.case_id,intake_id=excluded.intake_id,status='REJECTED',route='NONE',updated_at=now()
    returning id into v_job;
    return v_job;
  elsif u.status='SUPERSEDED' then
    insert into public.record_intake_jobs(upload_id,case_id,intake_id,status,route,updated_at)
    values(u.id,u.case_id,u.intake_id,'RESOLVED_DUPLICATE','NONE',now())
    on conflict(upload_id) do update set case_id=excluded.case_id,intake_id=excluded.intake_id,status='RESOLVED_DUPLICATE',route='NONE',updated_at=now()
    returning id into v_job;
    return v_job;
  end if;

  v_triage := private.record_intake_filename_triage_v1(u.original_filename,u.mime_type);
  v_key := v_triage->>'taxonomy_key';
  v_conf := nullif(v_triage->>'confidence','')::numeric;
  v_bundle := coalesce(v_triage->>'bundle_state','UNKNOWN');
  select * into v_tax from public.source_taxonomy where taxonomy_key=v_key and active;

  if u.case_id is null then
    v_status := 'WAITING_FOR_CASE'; v_route := 'NONE';
  else
    if u.sha256 is not null then
      select s.source_id into v_dup_source
      from registry.sources s
      where s.case_id=u.case_id and s.sha256=u.sha256 and s.status='ACTIVE'
      order by s.created_at limit 1;
      if v_dup_source is null then
        select x.id into v_dup_upload
        from public.upload_records x
        where x.case_id=u.case_id and x.id<>u.id and x.sha256=u.sha256
          and x.status not in ('REJECTED','SUPERSEDED')
        order by x.created_at limit 1;
      end if;
    end if;

    if v_dup_source is not null or v_dup_upload is not null then
      v_status := 'EXCEPTION'; v_route := 'RED';
      v_exceptions := v_exceptions || jsonb_build_array('EXACT_DUPLICATE');
    elsif v_bundle='PROBABLE_BUNDLE' then
      v_status := 'EXCEPTION'; v_route := 'RED';
      v_exceptions := v_exceptions || jsonb_build_array('PROBABLE_MULTI_DOCUMENT_BUNDLE');
    elsif v_tax.taxonomy_key is null or v_key='other_unclassified' then
      v_status := 'EXCEPTION'; v_route := 'RED';
      v_exceptions := v_exceptions || jsonb_build_array('LOW_CLASSIFICATION_CONFIDENCE');
    elsif v_tax.auto_register_allowed and v_conf >= v_tax.auto_register_threshold then
      v_status := 'AUTO_REGISTER_READY'; v_route := 'GREEN';
    elsif v_conf >= v_tax.quick_confirm_threshold then
      v_status := 'NEEDS_CONFIRMATION'; v_route := 'AMBER';
    else
      v_status := 'EXCEPTION'; v_route := 'RED';
      v_exceptions := v_exceptions || jsonb_build_array('LOW_CLASSIFICATION_CONFIDENCE');
    end if;
  end if;

  insert into public.record_intake_jobs(
    upload_id,case_id,intake_id,status,route,suggested_taxonomy_key,
    suggested_source_type,suggested_source_role,suggested_client_label,
    classification_confidence,exact_duplicate_source_id,duplicate_upload_id,
    bundle_state,extracted_metadata,exception_codes,processor_version,processed_at,updated_at
  ) values(
    u.id,u.case_id,u.intake_id,v_status,v_route,v_key,
    v_tax.source_type,v_tax.default_source_role,v_triage->>'suggested_label',
    v_conf,v_dup_source,v_dup_upload,v_bundle,
    jsonb_build_object('filename',u.original_filename,'mime_type',u.mime_type,'size_bytes',u.size_bytes),
    v_exceptions,'filename_heuristic_v1',now(),now()
  )
  on conflict(upload_id) do update set
    case_id=excluded.case_id,intake_id=excluded.intake_id,
    status=case when public.record_intake_jobs.status='REGISTERED' then 'REGISTERED' else excluded.status end,
    route=case when public.record_intake_jobs.status='REGISTERED' then public.record_intake_jobs.route else excluded.route end,
    suggested_taxonomy_key=excluded.suggested_taxonomy_key,
    suggested_source_type=excluded.suggested_source_type,
    suggested_source_role=excluded.suggested_source_role,
    suggested_client_label=excluded.suggested_client_label,
    classification_confidence=excluded.classification_confidence,
    exact_duplicate_source_id=excluded.exact_duplicate_source_id,
    duplicate_upload_id=excluded.duplicate_upload_id,
    bundle_state=excluded.bundle_state,
    extracted_metadata=public.record_intake_jobs.extracted_metadata || excluded.extracted_metadata,
    exception_codes=excluded.exception_codes,
    processor_version=excluded.processor_version,
    processed_at=now(),updated_at=now()
  returning id into v_job;
  return v_job;
end;
$function$;

CREATE OR REPLACE FUNCTION public.confirm_record_intake_segments_v1(p_job_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  j public.record_intake_jobs%rowtype;
  u public.upload_records%rowtype;
  seg public.record_intake_segments%rowtype;
  t public.source_taxonomy%rowtype;
  v_record uuid;
  v_type_code text;
  v_code text;
  v_source text;
  v_sources jsonb := '[]'::jsonb;
  v_count integer := 0;
  v_seconds integer := 0;
begin
  if auth.uid() is null or not private.is_staff() then
    raise exception 'staff authorization required' using errcode='42501';
  end if;

  select * into j from public.record_intake_jobs where id=p_job_id for update;
  if not found or j.case_id is null or not private.can_work_case(j.case_id) then
    raise exception 'intake job not accessible' using errcode='42501';
  end if;
  if j.status in ('REGISTERED','RESOLVED_DUPLICATE','REJECTED') then
    raise exception 'intake job is already closed' using errcode='22023';
  end if;
  if j.exact_duplicate_source_id is not null or j.duplicate_upload_id is not null then
    raise exception 'duplicate must be resolved before segmentation' using errcode='22023';
  end if;
  if j.page_count is null or j.proposed_segment_count < 2 then
    raise exception 'reviewed multi-document boundaries are required' using errcode='22023';
  end if;

  select * into u from public.upload_records where id=j.upload_id for update;
  if not found then raise exception 'upload not found' using errcode='P0002'; end if;
  if u.sha256 is null or length(u.sha256)<>64 then
    raise exception 'complete SHA-256 required' using errcode='22023';
  end if;

  if exists(
    select 1 from generate_series(1,j.page_count) p(page_no)
    where (
      select count(*) from public.record_intake_segments s
      where s.job_id=p_job_id and s.status='PROPOSED'
        and p.page_no between s.page_start and s.page_end
    ) <> 1
  ) then
    raise exception 'segments must cover each page exactly once' using errcode='22023';
  end if;

  for seg in
    select * from public.record_intake_segments
    where job_id=p_job_id and status='PROPOSED'
    order by segment_index
  loop
    select * into t from public.source_taxonomy
    where taxonomy_key=seg.suggested_taxonomy_key and active;
    if not found then raise exception 'segment taxonomy is no longer active' using errcode='22023'; end if;

    v_type_code := registry.source_type_code(t.source_type);
    v_code := registry.allocate_source_code(j.case_id,v_type_code);
    v_source := j.case_id||'/'||v_code;

    insert into registry.records(
      scope,record_key,record_type,title,content,epistemic_classification,status,
      authority,source_type,source_ref,metadata
    ) values(
      'client',
      'upload-segment-source:'||u.id::text||':'||seg.segment_index::text,
      'SOURCE',
      coalesce(seg.suggested_client_label,u.original_filename||' pages '||seg.page_start||'-'||seg.page_end),
      jsonb_build_object(
        'upload_record_id',u.id,'storage_bucket',u.storage_bucket,'storage_path',u.storage_path,
        'original_filename',u.original_filename,'mime_type',u.mime_type,'size_bytes',u.size_bytes,
        'sha256',u.sha256,'received_at',u.created_at,
        'page_start',seg.page_start,'page_end',seg.page_end,
        'segmented_source',true
      ),
      'FACT','ACTIVE','CLIENT_PROVIDED_RECORD','UPLOAD_SEGMENT',u.id::text,
      jsonb_build_object('registered_via','confirm_record_intake_segments_v1','case_id',j.case_id)
    ) returning record_id into v_record;

    insert into registry.sources(
      source_id,record_id,case_id,source_type,original_filename,ingested_at,sha256,
      version,status,metadata,source_code,client_label,source_role,authenticity_status,
      received_at,version_family_key,access_classification,publication_status
    ) values(
      v_source,v_record,j.case_id,t.source_type,u.original_filename,now(),u.sha256,
      1,'ACTIVE',
      jsonb_build_object(
        'upload_record_id',u.id,'uploaded_by',u.uploaded_by,
        'page_start',seg.page_start,'page_end',seg.page_end,
        'segmented_source',true,'source_file_sha256',u.sha256
      ),
      v_code,coalesce(seg.suggested_client_label,u.original_filename),
      coalesce(seg.suggested_source_role,t.default_source_role),'NOT_TESTED',
      u.created_at,v_source,'ORDINARY','APPROVAL_REQUIRED'
    );

    update public.record_intake_segments
    set status='REGISTERED',registered_source_id=v_source,updated_at=now()
    where id=seg.id;

    insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
    values(
      auth.uid(),private.current_user_role(),'UPLOAD_SEGMENT_REGISTERED_AS_SOURCE',
      'source',v_source,j.case_id,
      jsonb_build_object(
        'upload_id',u.id,'page_start',seg.page_start,'page_end',seg.page_end,
        'source_type',t.source_type,'authenticity_status','NOT_TESTED'
      )
    );

    v_sources := v_sources || jsonb_build_array(v_source);
    v_count := v_count + 1;
  end loop;

  if v_count < 2 then raise exception 'at least two segments must be registered' using errcode='22023'; end if;

  if j.review_started_at is not null then
    v_seconds := greatest(0,extract(epoch from (now()-j.review_started_at))::integer);
  end if;

  update public.record_intake_jobs
  set status='REGISTERED',route='GREEN',registered_source_id=null,
      bundle_state='BUNDLE',reviewed_by=auth.uid(),reviewed_at=now(),
      human_attention_seconds=human_attention_seconds+v_seconds,
      exception_codes='[]'::jsonb,updated_at=now()
  where id=p_job_id;

  update public.upload_records
  set status='INGESTED'
  where id=u.id;

  update public.record_request_matches
  set updated_at=now()
  where upload_id=u.id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(
    auth.uid(),private.current_user_role(),'UPLOAD_SEGMENTATION_ACCEPTED',
    'upload',u.id::text,j.case_id,
    jsonb_build_object('source_count',v_count,'source_ids',v_sources,'page_count',j.page_count)
  );

  perform private.set_lifecycle_signal(
    j.case_id,'RECORD_COLLECTION','IN_PROGRESS',
    'A multi-document upload was segmented into canonical Sources with page-level provenance.',
    'SOURCE_SEGMENTATION'
  );

  return jsonb_build_object('upload_id',u.id,'source_count',v_count,'source_ids',v_sources);
end;
$function$;

CREATE OR REPLACE FUNCTION public.replace_record_intake_segments_v1(p_job_id uuid, p_segments jsonb)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  j public.record_intake_jobs%rowtype;
  seg jsonb;
  t public.source_taxonomy%rowtype;
  n integer := 0;
begin
  if auth.uid() is null or not private.is_staff() then
    raise exception 'staff authorization required' using errcode='42501';
  end if;
  if jsonb_typeof(coalesce(p_segments,'[]'::jsonb)) <> 'array'
     or jsonb_array_length(coalesce(p_segments,'[]'::jsonb)) < 2 then
    raise exception 'at least two proposed segments are required' using errcode='22023';
  end if;

  select * into j from public.record_intake_jobs where id=p_job_id for update;
  if not found or j.case_id is null or not private.can_work_case(j.case_id) then
    raise exception 'intake job not accessible' using errcode='42501';
  end if;
  if j.status in ('REGISTERED','RESOLVED_DUPLICATE','REJECTED') then
    raise exception 'closed intake job cannot be re-segmented' using errcode='22023';
  end if;
  if j.page_count is null then
    raise exception 'page count required before segmentation' using errcode='22023';
  end if;

  delete from public.record_intake_segments where job_id=p_job_id;

  for seg in select value from jsonb_array_elements(p_segments)
  loop
    select * into t from public.source_taxonomy
    where taxonomy_key=seg->>'taxonomy_key' and active;
    if not found then raise exception 'valid taxonomy required for every segment' using errcode='22023'; end if;

    n := n + 1;
    insert into public.record_intake_segments(
      job_id,segment_index,page_start,page_end,status,suggested_taxonomy_key,
      suggested_source_type,suggested_source_role,suggested_client_label,confidence,metadata
    ) values(
      p_job_id,n,(seg->>'page_start')::integer,(seg->>'page_end')::integer,'PROPOSED',
      t.taxonomy_key,t.source_type,
      coalesce(nullif(seg->>'source_role',''),t.default_source_role),
      nullif(seg->>'client_label',''),
      coalesce(nullif(seg->>'confidence','')::numeric,j.classification_confidence),
      jsonb_build_object('manually_reviewed_boundaries',true)
    );
  end loop;

  if exists(
    select 1 from generate_series(1,j.page_count) p(page_no)
    where (
      select count(*) from public.record_intake_segments s
      where s.job_id=p_job_id and p.page_no between s.page_start and s.page_end
    ) <> 1
  ) then
    raise exception 'segments must cover each page exactly once with no gaps or overlaps' using errcode='22023';
  end if;

  update public.record_intake_jobs
  set proposed_segment_count=n,bundle_state='PROBABLE_BUNDLE',
      status='EXCEPTION',route='RED',
      exception_codes=(
        select coalesce(jsonb_agg(distinct x),'[]'::jsonb)
        from jsonb_array_elements(exception_codes || jsonb_build_array('PROPOSED_MULTI_DOCUMENT_BUNDLE')) x
      ),
      reviewed_by=auth.uid(),updated_at=now()
  where id=p_job_id;

  return n;
end;
$function$;

revoke all on function public.replace_record_intake_segments_v1(uuid,jsonb) from public,anon;
grant execute on function public.replace_record_intake_segments_v1(uuid,jsonb) to authenticated;
revoke all on function public.confirm_record_intake_segments_v1(uuid) from public,anon;
grant execute on function public.confirm_record_intake_segments_v1(uuid) to authenticated;
