-- Apply content-aware intake analysis without allowing the processor to
-- establish authenticity, publication approval, or request satisfaction.

create or replace function public.apply_record_intake_analysis_v1(
  p_upload_id uuid,
  p_taxonomy_key text,
  p_confidence numeric,
  p_client_label text,
  p_page_count integer,
  p_bundle_state text,
  p_segments jsonb default '[]'::jsonb,
  p_metadata jsonb default '{}'::jsonb,
  p_version_family_key text default null,
  p_exception_codes jsonb default '[]'::jsonb,
  p_request_matches jsonb default '[]'::jsonb
) returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  j public.record_intake_jobs%rowtype;
  t public.source_taxonomy%rowtype;
  v_route text;
  v_status text;
  v_bundle text;
  v_exceptions jsonb := '[]'::jsonb;
  v_seg jsonb;
  v_match jsonb;
  v_segments integer := 0;
  v_match_count integer := 0;
  v_request uuid;
begin
  if p_confidence is null or p_confidence < 0 or p_confidence > 1 then
    raise exception 'classification confidence must be between 0 and 1' using errcode='22023';
  end if;
  if p_page_count is not null and p_page_count <= 0 then
    raise exception 'page count must be positive' using errcode='22023';
  end if;
  if jsonb_typeof(coalesce(p_segments,'[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_exception_codes,'[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_request_matches,'[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_metadata,'{}'::jsonb)) <> 'object' then
    raise exception 'analysis payload has invalid JSON shape' using errcode='22023';
  end if;

  select * into j
  from public.record_intake_jobs
  where upload_id=p_upload_id
  for update;

  if not found then raise exception 'record intake job not found' using errcode='P0002'; end if;

  if j.status in ('REGISTERED','RESOLVED_DUPLICATE','REJECTED') then
    return jsonb_build_object('job_id',j.id,'status',j.status,'route',j.route,'ignored',true);
  end if;

  select * into t from public.source_taxonomy
  where taxonomy_key=p_taxonomy_key and active;
  if not found then raise exception 'active source taxonomy selection required' using errcode='22023'; end if;

  v_bundle := case
    when p_bundle_state in ('UNKNOWN','SINGLE','PROBABLE_BUNDLE','BUNDLE') then p_bundle_state
    else 'UNKNOWN'
  end;

  if j.exact_duplicate_source_id is not null or j.duplicate_upload_id is not null then
    v_exceptions := v_exceptions || jsonb_build_array('EXACT_DUPLICATE');
  end if;

  for v_seg in select value from jsonb_array_elements(coalesce(p_segments,'[]'::jsonb))
  loop
    if coalesce((v_seg->>'page_start')::integer,0) <= 0
       or coalesce((v_seg->>'page_end')::integer,0) < coalesce((v_seg->>'page_start')::integer,0) then
      raise exception 'invalid proposed page segment' using errcode='22023';
    end if;
    v_segments := v_segments + 1;
  end loop;

  if v_segments > 1 then
    v_bundle := 'PROBABLE_BUNDLE';
    v_exceptions := v_exceptions || jsonb_build_array('PROPOSED_MULTI_DOCUMENT_BUNDLE');
  elsif v_bundle in ('PROBABLE_BUNDLE','BUNDLE') then
    v_exceptions := v_exceptions || jsonb_build_array('PROBABLE_MULTI_DOCUMENT_BUNDLE');
  end if;

  if nullif(btrim(coalesce(p_version_family_key,'')),'') is not null then
    v_exceptions := v_exceptions || jsonb_build_array('PROBABLE_VERSION_FAMILY');
  end if;

  v_exceptions := v_exceptions || coalesce(p_exception_codes,'[]'::jsonb);

  if v_exceptions ? 'EXACT_DUPLICATE'
     or v_exceptions ? 'PROBABLE_MULTI_DOCUMENT_BUNDLE'
     or v_exceptions ? 'PROPOSED_MULTI_DOCUMENT_BUNDLE'
     or v_exceptions ? 'PROBABLE_VERSION_FAMILY'
     or v_exceptions ? 'TEXT_EXTRACTION_SPARSE_OR_SCAN'
     or v_exceptions ? 'FILE_TOO_LARGE_FOR_CONTENT_PROCESSOR'
     or v_exceptions ? 'PDF_PAGE_LIMIT_EXCEEDED'
     or p_taxonomy_key='other_unclassified' then
    v_route := 'RED'; v_status := 'EXCEPTION';
  elsif t.auto_register_allowed and p_confidence >= t.auto_register_threshold then
    v_route := 'GREEN'; v_status := 'AUTO_REGISTER_READY';
  elsif p_confidence >= t.quick_confirm_threshold then
    v_route := 'AMBER'; v_status := 'NEEDS_CONFIRMATION';
  else
    v_route := 'RED'; v_status := 'EXCEPTION';
    v_exceptions := v_exceptions || jsonb_build_array('LOW_CLASSIFICATION_CONFIDENCE');
  end if;

  delete from public.record_intake_segments where job_id=j.id;
  for v_seg in select value from jsonb_array_elements(coalesce(p_segments,'[]'::jsonb))
  loop
    insert into public.record_intake_segments(
      job_id,segment_index,page_start,page_end,status,
      suggested_taxonomy_key,suggested_source_type,suggested_source_role,
      suggested_client_label,confidence,metadata
    ) values (
      j.id,
      coalesce((v_seg->>'segment_index')::integer,
               (select coalesce(max(segment_index),0)+1 from public.record_intake_segments where job_id=j.id)),
      (v_seg->>'page_start')::integer,
      (v_seg->>'page_end')::integer,
      'PROPOSED',
      nullif(v_seg->>'taxonomy_key',''),
      nullif(v_seg->>'source_type',''),
      nullif(v_seg->>'source_role',''),
      nullif(v_seg->>'client_label',''),
      nullif(v_seg->>'confidence','')::numeric,
      coalesce(v_seg->'metadata','{}'::jsonb)
    );
  end loop;

  delete from public.record_request_matches
  where upload_id=p_upload_id and status='SUGGESTED';

  for v_match in select value from jsonb_array_elements(coalesce(p_request_matches,'[]'::jsonb))
  loop
    begin v_request := (v_match->>'request_id')::uuid;
    exception when others then v_request := null; end;

    if v_request is not null and exists(
      select 1 from public.document_requests r
      where r.id=v_request and r.case_id=j.case_id
    ) then
      insert into public.record_request_matches(
        request_id,upload_id,source_id,match_confidence,match_reason,status,metadata
      ) values (
        v_request,p_upload_id,null,
        least(1,greatest(0,coalesce((v_match->>'confidence')::numeric,0))),
        nullif(v_match->>'reason',''),'SUGGESTED',
        coalesce(v_match->'metadata','{}'::jsonb)
      )
      on conflict(request_id,upload_id) do update set
        match_confidence=excluded.match_confidence,
        match_reason=excluded.match_reason,
        metadata=excluded.metadata,
        updated_at=now()
      where public.record_request_matches.status='SUGGESTED';
      v_match_count := v_match_count + 1;
    end if;
  end loop;

  update public.record_intake_jobs
  set status=v_status,route=v_route,
      suggested_taxonomy_key=t.taxonomy_key,
      suggested_source_type=t.source_type,
      suggested_source_role=coalesce(suggested_source_role,t.default_source_role),
      suggested_client_label=coalesce(nullif(btrim(coalesce(p_client_label,'')),''),suggested_client_label),
      classification_confidence=p_confidence,
      probable_version_family_key=nullif(btrim(coalesce(p_version_family_key,'')),''),
      bundle_state=v_bundle,page_count=p_page_count,proposed_segment_count=v_segments,
      extracted_metadata=coalesce(extracted_metadata,'{}'::jsonb) || coalesce(p_metadata,'{}'::jsonb),
      exception_codes=(
        select coalesce(jsonb_agg(distinct x),'[]'::jsonb)
        from jsonb_array_elements(v_exceptions) x
      ),
      processor_version=coalesce(nullif(p_metadata->>'processor_version',''),'record_content_processor_v1'),
      processed_at=now(),failure_reason=null,updated_at=now()
  where id=j.id;

  return jsonb_build_object(
    'job_id',j.id,'route',v_route,'status',v_status,
    'segments',v_segments,'request_matches',v_match_count,
    'taxonomy_key',t.taxonomy_key,'confidence',p_confidence
  );
end;
$function$;

revoke all on function public.apply_record_intake_analysis_v1(uuid,text,numeric,text,integer,text,jsonb,jsonb,text,jsonb,jsonb)
from public,anon,authenticated;
grant execute on function public.apply_record_intake_analysis_v1(uuid,text,numeric,text,integer,text,jsonb,jsonb,text,jsonb,jsonb)
to service_role;

create or replace function public.record_intake_metrics_v1(p_case_id text)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_total integer; v_registered integer; v_green integer; v_amber integer; v_red integer;
  v_waiting integer; v_duplicates integer; v_bundles integer; v_failed integer;
  v_attention bigint; v_score integer; v_band text;
begin
  if auth.uid() is null or not private.is_staff() or not private.can_work_case(p_case_id) then
    raise exception 'case work authorization required' using errcode='42501';
  end if;

  select count(*)::integer,
    count(*) filter(where status='REGISTERED')::integer,
    count(*) filter(where route='GREEN' and status<>'REGISTERED')::integer,
    count(*) filter(where route='AMBER')::integer,
    count(*) filter(where route='RED')::integer,
    count(*) filter(where status='WAITING_FOR_CASE')::integer,
    count(*) filter(where exception_codes ? 'EXACT_DUPLICATE')::integer,
    count(*) filter(where exception_codes ? 'PROBABLE_MULTI_DOCUMENT_BUNDLE'
                         or exception_codes ? 'PROPOSED_MULTI_DOCUMENT_BUNDLE')::integer,
    count(*) filter(where status='FAILED')::integer,
    coalesce(sum(human_attention_seconds),0)::bigint
  into v_total,v_registered,v_green,v_amber,v_red,v_waiting,
       v_duplicates,v_bundles,v_failed,v_attention
  from public.record_intake_jobs where case_id=p_case_id;

  if coalesce(v_total,0)=0 then v_score := 0;
  else
    v_score := least(100,round(
      100.0 * (
        (coalesce(v_red,0)*5.0)+(coalesce(v_amber,0)*1.5)+
        (coalesce(v_bundles,0)*3.0)+(coalesce(v_failed,0)*5.0)
      ) / greatest(v_total*5.0,1)
    )::integer);
  end if;

  v_band := case when v_score<=20 then 'LOW' when v_score<=45 then 'MODERATE'
                 when v_score<=70 then 'HIGH' else 'EXTREME' end;

  return jsonb_build_object(
    'total',coalesce(v_total,0),'registered',coalesce(v_registered,0),
    'green',coalesce(v_green,0),'amber',coalesce(v_amber,0),'red',coalesce(v_red,0),
    'waiting_for_case',coalesce(v_waiting,0),'duplicates',coalesce(v_duplicates,0),
    'probable_bundles',coalesce(v_bundles,0),'failed',coalesce(v_failed,0),
    'human_attention_seconds',coalesce(v_attention,0),
    'human_attention_minutes',round(coalesce(v_attention,0)::numeric/60.0,1),
    'intake_complexity_index',v_score,'intake_complexity_band',v_band,
    'complexity_calibration_state','UNCALIBRATED_V1'
  );
end;
$function$;

revoke all on function public.record_intake_metrics_v1(text) from public,anon;
grant execute on function public.record_intake_metrics_v1(text) to authenticated;
