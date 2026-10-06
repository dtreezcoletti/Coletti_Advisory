-- Automated Records Intake & Exception Routing v1
-- Owner-approved solo-first intake architecture.
-- Administrative triage does not establish authenticity or publication eligibility.

create table if not exists public.source_taxonomy (
  taxonomy_key text primary key,
  category text not null,
  source_type text not null,
  label text not null,
  default_source_role text not null default 'NATIVE_SOURCE'
    check(default_source_role in ('NATIVE_SOURCE','DERIVATIVE','WORKING_ANALYSIS','EXHIBIT','PRODUCTION_COPY','SUPPLEMENTAL_COPY','CORRECTED_RECORD','OTHER')),
  quick_confirm_threshold numeric(4,3) not null default 0.750
    check(quick_confirm_threshold >= 0 and quick_confirm_threshold <= 1),
  auto_register_threshold numeric(4,3) not null default 0.950
    check(auto_register_threshold >= 0 and auto_register_threshold <= 1),
  auto_register_allowed boolean not null default false,
  active boolean not null default true,
  sort_order integer not null default 100,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.source_taxonomy enable row level security;
revoke all on public.source_taxonomy from public,anon;
grant select on public.source_taxonomy to authenticated;
drop policy if exists source_taxonomy_staff_select on public.source_taxonomy;
create policy source_taxonomy_staff_select on public.source_taxonomy
for select to authenticated using (private.is_staff());

insert into public.source_taxonomy(
  taxonomy_key,category,source_type,label,default_source_role,
  quick_confirm_threshold,auto_register_threshold,auto_register_allowed,sort_order
) values
('financial_bank_statement','FINANCIAL','Financial Record','Bank / account statement','NATIVE_SOURCE',0.750,0.950,false,10),
('financial_credit_card_statement','FINANCIAL','Financial Record','Credit card statement','NATIVE_SOURCE',0.750,0.950,false,20),
('financial_tax_record','FINANCIAL','Financial Record','Tax record','NATIVE_SOURCE',0.800,0.970,false,30),
('business_invoice','BUSINESS','Business Record','Invoice','NATIVE_SOURCE',0.800,0.950,true,40),
('business_receipt','BUSINESS','Business Record','Receipt','NATIVE_SOURCE',0.800,0.950,true,50),
('correspondence_email','CORRESPONDENCE','Correspondence','Email / message','NATIVE_SOURCE',0.800,0.960,false,60),
('correspondence_letter','CORRESPONDENCE','Correspondence','Letter / correspondence','NATIVE_SOURCE',0.800,0.960,false,70),
('agreement_contract','AGREEMENT','Agreement','Agreement / contract','NATIVE_SOURCE',0.850,0.990,false,80),
('court_filing','LEGAL_RECORD','Court Filing','Court filing / order','NATIVE_SOURCE',0.850,0.990,false,90),
('government_record','GOVERNMENT','Government Record','Government / agency record','NATIVE_SOURCE',0.850,0.990,false,100),
('spreadsheet_data_export','DATA','Data Export','Spreadsheet / data export','NATIVE_SOURCE',0.750,0.950,true,110),
('photograph_image','MEDIA','Image','Photograph / image','NATIVE_SOURCE',0.750,0.950,true,120),
('audio_video','MEDIA','Media','Audio / video','NATIVE_SOURCE',0.750,0.950,true,130),
('identity_organizational','IDENTITY','Identity / Organizational Record','Identity / organizational record','NATIVE_SOURCE',0.850,0.990,false,140),
('other_unclassified','OTHER','Other','Other / unclassified','OTHER',0.990,1.000,false,999)
on conflict(taxonomy_key) do update set
  category=excluded.category,source_type=excluded.source_type,label=excluded.label,
  default_source_role=excluded.default_source_role,
  quick_confirm_threshold=excluded.quick_confirm_threshold,
  auto_register_threshold=excluded.auto_register_threshold,
  auto_register_allowed=excluded.auto_register_allowed,
  sort_order=excluded.sort_order,updated_at=now();

create table if not exists public.record_intake_jobs (
  id uuid primary key default gen_random_uuid(),
  upload_id uuid not null unique references public.upload_records(id) on delete cascade,
  case_id text references registry.cases(case_id) on delete cascade,
  intake_id uuid references public.intake_submissions(id) on delete cascade,
  status text not null default 'RECEIVED'
    check(status in ('RECEIVED','WAITING_FOR_CASE','PROCESSING','AUTO_REGISTER_READY','NEEDS_CONFIRMATION','EXCEPTION','REGISTERED','RESOLVED_DUPLICATE','REJECTED','FAILED')),
  route text not null default 'NONE' check(route in ('NONE','GREEN','AMBER','RED')),
  suggested_taxonomy_key text references public.source_taxonomy(taxonomy_key),
  suggested_source_type text,
  suggested_source_role text
    check(suggested_source_role is null or suggested_source_role in ('NATIVE_SOURCE','DERIVATIVE','WORKING_ANALYSIS','EXHIBIT','PRODUCTION_COPY','SUPPLEMENTAL_COPY','CORRECTED_RECORD','OTHER')),
  suggested_client_label text,
  classification_confidence numeric(4,3)
    check(classification_confidence is null or (classification_confidence >= 0 and classification_confidence <= 1)),
  exact_duplicate_source_id text references registry.sources(source_id) on delete restrict,
  duplicate_upload_id uuid references public.upload_records(id) on delete set null,
  probable_version_family_key text,
  bundle_state text not null default 'UNKNOWN' check(bundle_state in ('UNKNOWN','SINGLE','PROBABLE_BUNDLE','BUNDLE')),
  page_count integer check(page_count is null or page_count > 0),
  proposed_segment_count integer not null default 0 check(proposed_segment_count >= 0),
  extracted_metadata jsonb not null default '{}'::jsonb,
  exception_codes jsonb not null default '[]'::jsonb check(jsonb_typeof(exception_codes)='array'),
  processor_version text,
  registered_source_id text references registry.sources(source_id) on delete restrict,
  reviewed_by uuid references auth.users(id),
  review_started_at timestamptz,
  reviewed_at timestamptz,
  human_attention_seconds integer not null default 0 check(human_attention_seconds >= 0),
  processed_at timestamptz,
  failure_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.record_intake_jobs enable row level security;
revoke all on public.record_intake_jobs from public,anon;
grant select on public.record_intake_jobs to authenticated;
revoke insert,update,delete,truncate,references,trigger on public.record_intake_jobs from authenticated;
create index if not exists idx_record_intake_jobs_case on public.record_intake_jobs(case_id,status,route);
create index if not exists idx_record_intake_jobs_intake on public.record_intake_jobs(intake_id);
create index if not exists idx_record_intake_jobs_duplicate_source on public.record_intake_jobs(exact_duplicate_source_id);
drop policy if exists record_intake_jobs_staff_select on public.record_intake_jobs;
create policy record_intake_jobs_staff_select on public.record_intake_jobs
for select to authenticated
using (private.is_admin() or (case_id is not null and private.can_work_case(case_id)));

create table if not exists public.record_intake_segments (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.record_intake_jobs(id) on delete cascade,
  segment_index integer not null check(segment_index > 0),
  page_start integer not null check(page_start > 0),
  page_end integer not null check(page_end >= page_start),
  status text not null default 'PROPOSED' check(status in ('PROPOSED','CONFIRMED','REJECTED','REGISTERED')),
  suggested_taxonomy_key text references public.source_taxonomy(taxonomy_key),
  suggested_source_type text,
  suggested_source_role text,
  suggested_client_label text,
  confidence numeric(4,3) check(confidence is null or (confidence >= 0 and confidence <= 1)),
  registered_source_id text references registry.sources(source_id) on delete restrict,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(job_id,segment_index),
  unique(job_id,page_start,page_end)
);
alter table public.record_intake_segments enable row level security;
revoke all on public.record_intake_segments from public,anon;
grant select on public.record_intake_segments to authenticated;
revoke insert,update,delete,truncate,references,trigger on public.record_intake_segments from authenticated;
create index if not exists idx_record_intake_segments_job on public.record_intake_segments(job_id,status);
drop policy if exists record_intake_segments_staff_select on public.record_intake_segments;
create policy record_intake_segments_staff_select on public.record_intake_segments
for select to authenticated
using (
  exists (
    select 1 from public.record_intake_jobs j
    where j.id=record_intake_segments.job_id
      and (private.is_admin() or (j.case_id is not null and private.can_work_case(j.case_id)))
  )
);

create table if not exists registry.source_relationships (
  relationship_id uuid primary key default gen_random_uuid(),
  case_id text not null references registry.cases(case_id) on delete cascade,
  source_id text not null references registry.sources(source_id) on delete cascade,
  related_source_id text not null references registry.sources(source_id) on delete cascade,
  relationship_type text not null
    check(relationship_type in ('DUPLICATE_OF','VERSION_OF','SUPERSEDES','PART_OF_FAMILY','DERIVED_FROM','SEGMENT_OF')),
  confidence numeric(4,3) check(confidence is null or (confidence >= 0 and confidence <= 1)),
  created_by uuid references auth.users(id),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(source_id,related_source_id,relationship_type),
  check(source_id <> related_source_id)
);
create index if not exists idx_source_relationships_case on registry.source_relationships(case_id);
create index if not exists idx_source_relationships_related on registry.source_relationships(related_source_id);

create table if not exists public.record_request_matches (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null references public.document_requests(id) on delete cascade,
  upload_id uuid not null references public.upload_records(id) on delete cascade,
  source_id text references registry.sources(source_id) on delete set null,
  match_confidence numeric(4,3) not null check(match_confidence >= 0 and match_confidence <= 1),
  match_reason text,
  status text not null default 'SUGGESTED' check(status in ('SUGGESTED','CONFIRMED','REJECTED')),
  reviewed_by uuid references auth.users(id),
  reviewed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(request_id,upload_id)
);
alter table public.record_request_matches enable row level security;
revoke all on public.record_request_matches from public,anon;
grant select on public.record_request_matches to authenticated;
revoke insert,update,delete,truncate,references,trigger on public.record_request_matches from authenticated;
create index if not exists idx_record_request_matches_request on public.record_request_matches(request_id,status);
create index if not exists idx_record_request_matches_upload on public.record_request_matches(upload_id);
drop policy if exists record_request_matches_staff_select on public.record_request_matches;
create policy record_request_matches_staff_select on public.record_request_matches
for select to authenticated
using (
  exists (
    select 1 from public.document_requests r
    where r.id=record_request_matches.request_id
      and private.can_work_case(r.case_id)
  )
);

create or replace function private.record_intake_filename_triage_v1(p_filename text,p_mime_type text default null)
returns jsonb
language plpgsql
immutable
set search_path to ''
as $function$
declare
  v_name text := lower(coalesce(p_filename,''));
  v_mime text := lower(coalesce(p_mime_type,''));
  v_label text := regexp_replace(coalesce(p_filename,'Untitled record'), '\.[^.]+$', '');
  v_key text := 'other_unclassified';
  v_conf numeric := 0.400;
  v_bundle text := 'UNKNOWN';
begin
  if v_name ~ '(combined|merged|packet|all[ _-]?documents|production[ _-]?set|document[ _-]?dump|bundle)' then
    v_bundle := 'PROBABLE_BUNDLE';
  elsif v_mime='application/pdf' then
    v_bundle := 'SINGLE';
  end if;

  if v_name ~ '(bank|checking|savings|account).*(statement)' or v_name ~ '(statement).*(bank|checking|savings|account)' then
    v_key := 'financial_bank_statement'; v_conf := 0.930;
  elsif v_name ~ '(credit[ _-]?card|visa|mastercard|amex|discover).*(statement)' then
    v_key := 'financial_credit_card_statement'; v_conf := 0.940;
  elsif v_name ~ '(^|[^a-z])(w-?2|1099|tax[ _-]?(return|record|form))([^a-z]|$)' then
    v_key := 'financial_tax_record'; v_conf := 0.930;
  elsif v_name ~ '(^|[^a-z])(invoice|inv[ _-]?[0-9])([^a-z]|$)' then
    v_key := 'business_invoice'; v_conf := 0.960;
  elsif v_name ~ '(^|[^a-z])(receipt)([^a-z]|$)' then
    v_key := 'business_receipt'; v_conf := 0.960;
  elsif v_name ~ '(email|e-mail|message|gmail|outlook)' then
    v_key := 'correspondence_email'; v_conf := 0.900;
  elsif v_name ~ '(letter|correspondence|memo)' then
    v_key := 'correspondence_letter'; v_conf := 0.880;
  elsif v_name ~ '(contract|agreement|mda|nda|lease)' then
    v_key := 'agreement_contract'; v_conf := 0.900;
  elsif v_name ~ '(court|order|motion|petition|complaint|pleading|decree|subpoena)' then
    v_key := 'court_filing'; v_conf := 0.900;
  elsif v_name ~ '(agency|government|irs|ssa|dmv|police[ _-]?report)' then
    v_key := 'government_record'; v_conf := 0.880;
  elsif v_name ~ '\.(csv|xlsx|xls|ods)$' or v_mime like '%spreadsheet%' or v_mime='text/csv' then
    v_key := 'spreadsheet_data_export'; v_conf := 0.990;
  elsif v_mime like 'image/%' or v_name ~ '\.(png|jpe?g|heic|webp|tiff?)$' then
    v_key := 'photograph_image'; v_conf := 0.990;
  elsif v_mime like 'audio/%' or v_mime like 'video/%' or v_name ~ '\.(mp3|wav|m4a|mp4|mov|avi|mkv)$' then
    v_key := 'audio_video'; v_conf := 0.990;
  elsif v_name ~ '(driver.?s?[ _-]?license|passport|articles[ _-]?of[ _-]?organization|certificate[ _-]?of[ _-]?formation)' then
    v_key := 'identity_organizational'; v_conf := 0.900;
  end if;

  return jsonb_build_object(
    'taxonomy_key',v_key,'confidence',v_conf,
    'suggested_label',nullif(btrim(v_label),''),
    'bundle_state',v_bundle,'classifier','filename_heuristic_v1'
  );
end;
$function$;

create or replace function private.refresh_record_intake_job_v1(p_upload_id uuid)
returns uuid
language plpgsql
security definer
set search_path to ''
as $function$
declare
  u public.upload_records%rowtype;
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

  if u.source_id is not null then
    insert into public.record_intake_jobs(upload_id,case_id,intake_id,status,route,registered_source_id,processed_at,updated_at)
    values(u.id,u.case_id,u.intake_id,'REGISTERED','GREEN',u.source_id,now(),now())
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

create or replace function private.on_upload_record_intake_v1()
returns trigger language plpgsql security definer set search_path to ''
as $function$
begin
  perform private.refresh_record_intake_job_v1(new.id);
  return new;
end;
$function$;

drop trigger if exists trg_upload_record_intake_v1 on public.upload_records;
create trigger trg_upload_record_intake_v1
after insert or update of case_id,sha256,original_filename,mime_type,status,source_id
on public.upload_records
for each row execute function private.on_upload_record_intake_v1();

create or replace function private.attach_intake_uploads_to_case_v1()
returns trigger language plpgsql security definer set search_path to ''
as $function$
declare v_upload record;
begin
  if new.case_id is not null and old.case_id is distinct from new.case_id then
    update public.upload_records set case_id=new.case_id
    where intake_id=new.id and case_id is null;
    for v_upload in
      select id from public.upload_records where intake_id=new.id and case_id=new.case_id
    loop
      perform private.refresh_record_intake_job_v1(v_upload.id);
    end loop;
  end if;
  return new;
end;
$function$;

drop trigger if exists trg_attach_intake_uploads_to_case_v1 on public.intake_submissions;
create trigger trg_attach_intake_uploads_to_case_v1
after update of case_id on public.intake_submissions
for each row execute function private.attach_intake_uploads_to_case_v1();

create or replace function private.confirm_record_intake_job_impl_v1(
  p_job_id uuid,p_taxonomy_key text default null,p_source_role text default null,p_client_label text default null
) returns text
language plpgsql security definer set search_path to ''
as $function$
declare
  j public.record_intake_jobs%rowtype;
  t public.source_taxonomy%rowtype;
  v_key text; v_role text; v_label text; v_source_id text; v_seconds integer := 0;
begin
  if auth.uid() is null or not private.is_staff() then raise exception 'staff authorization required' using errcode='42501'; end if;
  select * into j from public.record_intake_jobs where id=p_job_id for update;
  if not found then raise exception 'intake job not found' using errcode='P0002'; end if;
  if j.case_id is null or not private.can_work_case(j.case_id) then raise exception 'case work authorization required' using errcode='42501'; end if;
  if j.status in ('REGISTERED','RESOLVED_DUPLICATE','REJECTED') then
    if j.registered_source_id is not null then return j.registered_source_id; end if;
    raise exception 'intake job is already closed' using errcode='22023';
  end if;

  v_key := coalesce(nullif(btrim(p_taxonomy_key),''),j.suggested_taxonomy_key);
  select * into t from public.source_taxonomy where taxonomy_key=v_key and active;
  if not found then raise exception 'valid source taxonomy selection required' using errcode='22023'; end if;
  v_role := coalesce(nullif(btrim(p_source_role),''),j.suggested_source_role,t.default_source_role);
  v_label := coalesce(nullif(btrim(p_client_label),''),j.suggested_client_label);

  v_source_id := private.register_upload_as_source_impl_v1(j.upload_id,t.source_type,v_role,v_label);
  if j.review_started_at is not null then
    v_seconds := greatest(0,extract(epoch from (now()-j.review_started_at))::integer);
  end if;

  update public.record_intake_jobs set
    status='REGISTERED',route='GREEN',registered_source_id=v_source_id,
    suggested_taxonomy_key=t.taxonomy_key,suggested_source_type=t.source_type,
    suggested_source_role=v_role,suggested_client_label=v_label,
    reviewed_by=auth.uid(),reviewed_at=now(),
    human_attention_seconds=human_attention_seconds+v_seconds,
    exception_codes='[]'::jsonb,failure_reason=null,updated_at=now()
  where id=p_job_id;
  return v_source_id;
end;
$function$;

create or replace function public.confirm_record_intake_job_v1(
  p_job_id uuid,p_taxonomy_key text default null,p_source_role text default null,p_client_label text default null
) returns text
language sql security definer set search_path to ''
as $function$
  select private.confirm_record_intake_job_impl_v1(p_job_id,p_taxonomy_key,p_source_role,p_client_label);
$function$;
revoke all on function public.confirm_record_intake_job_v1(uuid,text,text,text) from public,anon;
grant execute on function public.confirm_record_intake_job_v1(uuid,text,text,text) to authenticated;

create or replace function public.start_record_intake_review_v1(p_job_id uuid)
returns void
language plpgsql security definer set search_path to ''
as $function$
declare j public.record_intake_jobs%rowtype;
begin
  if auth.uid() is null or not private.is_staff() then raise exception 'staff authorization required' using errcode='42501'; end if;
  select * into j from public.record_intake_jobs where id=p_job_id;
  if not found or j.case_id is null or not private.can_work_case(j.case_id) then raise exception 'intake job not accessible' using errcode='42501'; end if;
  update public.record_intake_jobs
  set review_started_at=coalesce(review_started_at,now()),reviewed_by=auth.uid(),updated_at=now()
  where id=p_job_id;
end;
$function$;
revoke all on function public.start_record_intake_review_v1(uuid) from public,anon;
grant execute on function public.start_record_intake_review_v1(uuid) to authenticated;

create or replace function public.batch_register_green_intake_v1(p_case_id text,p_limit integer default 200)
returns jsonb
language plpgsql security definer set search_path to ''
as $function$
declare j record; v_ok integer := 0; v_failed integer := 0; v_limit integer := least(greatest(coalesce(p_limit,200),1),500);
begin
  if auth.uid() is null or not private.is_staff() or not private.can_work_case(p_case_id) then
    raise exception 'case work authorization required' using errcode='42501';
  end if;
  for j in
    select id from public.record_intake_jobs
    where case_id=p_case_id and status='AUTO_REGISTER_READY' and route='GREEN'
      and exact_duplicate_source_id is null and duplicate_upload_id is null
      and bundle_state in ('SINGLE','UNKNOWN')
    order by created_at limit v_limit for update skip locked
  loop
    begin
      perform private.confirm_record_intake_job_impl_v1(j.id,null,null,null);
      v_ok := v_ok+1;
    exception when others then
      v_failed := v_failed+1;
      update public.record_intake_jobs set
        status='FAILED',route='RED',failure_reason=left(sqlerrm,500),
        exception_codes=exception_codes || jsonb_build_array('BATCH_REGISTRATION_FAILED'),updated_at=now()
      where id=j.id;
    end;
  end loop;
  return jsonb_build_object('registered',v_ok,'failed',v_failed);
end;
$function$;
revoke all on function public.batch_register_green_intake_v1(text,integer) from public,anon;
grant execute on function public.batch_register_green_intake_v1(text,integer) to authenticated;

create or replace function public.mark_record_intake_duplicate_v1(p_job_id uuid)
returns void
language plpgsql security definer set search_path to ''
as $function$
declare j public.record_intake_jobs%rowtype;
begin
  if auth.uid() is null or not private.is_staff() then raise exception 'staff authorization required' using errcode='42501'; end if;
  select * into j from public.record_intake_jobs where id=p_job_id for update;
  if not found or j.case_id is null or not private.can_work_case(j.case_id) then raise exception 'intake job not accessible' using errcode='42501'; end if;
  if j.exact_duplicate_source_id is null and j.duplicate_upload_id is null then raise exception 'no exact duplicate candidate exists' using errcode='22023'; end if;

  update public.upload_records set status='SUPERSEDED' where id=j.upload_id;
  update public.record_intake_jobs set
    status='RESOLVED_DUPLICATE',route='NONE',reviewed_by=auth.uid(),reviewed_at=now(),updated_at=now()
  where id=p_job_id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(auth.uid(),private.current_user_role(),'UPLOAD_RESOLVED_AS_DUPLICATE','upload',j.upload_id::text,j.case_id,
         jsonb_build_object('duplicate_source_id',j.exact_duplicate_source_id,'duplicate_upload_id',j.duplicate_upload_id));
end;
$function$;
revoke all on function public.mark_record_intake_duplicate_v1(uuid) from public,anon;
grant execute on function public.mark_record_intake_duplicate_v1(uuid) to authenticated;

create or replace function public.record_intake_metrics_v1(p_case_id text)
returns jsonb
language plpgsql security definer set search_path to ''
as $function$
declare v jsonb;
begin
  if auth.uid() is null or not private.is_staff() or not private.can_work_case(p_case_id) then
    raise exception 'case work authorization required' using errcode='42501';
  end if;
  select jsonb_build_object(
    'total',count(*),
    'registered',count(*) filter(where status='REGISTERED'),
    'green',count(*) filter(where route='GREEN' and status<>'REGISTERED'),
    'amber',count(*) filter(where route='AMBER'),
    'red',count(*) filter(where route='RED'),
    'waiting_for_case',count(*) filter(where status='WAITING_FOR_CASE'),
    'duplicates',count(*) filter(where exception_codes ? 'EXACT_DUPLICATE'),
    'probable_bundles',count(*) filter(where exception_codes ? 'PROBABLE_MULTI_DOCUMENT_BUNDLE'),
    'failed',count(*) filter(where status='FAILED'),
    'human_attention_seconds',coalesce(sum(human_attention_seconds),0)
  ) into v
  from public.record_intake_jobs where case_id=p_case_id;
  return coalesce(v,'{}'::jsonb);
end;
$function$;
revoke all on function public.record_intake_metrics_v1(text) from public,anon;
grant execute on function public.record_intake_metrics_v1(text) to authenticated;

do $$
declare r record;
begin
  for r in select id from public.upload_records loop
    perform private.refresh_record_intake_job_v1(r.id);
  end loop;
end $$;
