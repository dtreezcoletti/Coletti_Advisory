-- Source-control reconciliation of the already-applied live migration
-- 20261006165144 record_collection_source_registration_v1.
-- Canonical source registration preserves provenance and separates registration
-- from authenticity verification and publication approval.

alter table registry.sources add column if not exists source_code text;
alter table registry.sources add column if not exists client_label text;
alter table registry.sources add column if not exists source_role text;
alter table registry.sources add column if not exists authenticity_status text;
alter table registry.sources add column if not exists received_at timestamptz;
alter table registry.sources add column if not exists version_family_key text;
alter table registry.sources add column if not exists access_classification text;
alter table registry.sources add column if not exists publication_status text;

alter table public.upload_records add column if not exists source_id text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid='public.upload_records'::regclass
      and conname='upload_records_source_id_fkey'
  ) then
    alter table public.upload_records
      add constraint upload_records_source_id_fkey
      foreign key(source_id) references registry.sources(source_id);
  end if;
end $$;

create or replace function private.register_upload_as_source_impl_v1(
  p_upload_id uuid,
  p_source_type text,
  p_source_role text default 'NATIVE_SOURCE',
  p_client_label text default null
) returns text
language plpgsql
security definer
set search_path to ''
as $function$
declare
  u public.upload_records%rowtype;
  v_record uuid;
  v_type_code text;
  v_source_code text;
  v_source_id text;
begin
  select * into u
  from public.upload_records
  where id=p_upload_id
  for update;

  if not found then raise exception 'upload not found' using errcode='P0002'; end if;
  if auth.uid() is null or not private.is_staff() or u.case_id is null or not private.can_access_case(u.case_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if u.source_id is not null then return u.source_id; end if;
  if u.status in ('REJECTED','SUPERSEDED') then
    raise exception 'upload cannot be registered from status %',u.status using errcode='22023';
  end if;
  if u.sha256 is null or length(u.sha256)<>64 then
    raise exception 'complete SHA-256 required before source registration' using errcode='22023';
  end if;
  if nullif(btrim(p_source_type),'') is null then
    raise exception 'source type required' using errcode='22023';
  end if;
  if p_source_role not in ('NATIVE_SOURCE','DERIVATIVE','WORKING_ANALYSIS','EXHIBIT','PRODUCTION_COPY','SUPPLEMENTAL_COPY','CORRECTED_RECORD','OTHER') then
    raise exception 'invalid source role' using errcode='22023';
  end if;

  v_type_code:=registry.source_type_code(p_source_type);
  v_source_code:=registry.allocate_source_code(u.case_id,v_type_code);
  v_source_id:=u.case_id||'/'||v_source_code;

  insert into registry.records(
    scope,record_key,record_type,title,content,epistemic_classification,status,
    authority,source_type,source_ref,metadata
  ) values (
    'client',
    'upload-source:'||u.id::text,
    'SOURCE',
    u.original_filename,
    jsonb_build_object(
      'upload_record_id',u.id,
      'storage_bucket',u.storage_bucket,
      'storage_path',u.storage_path,
      'original_filename',u.original_filename,
      'mime_type',u.mime_type,
      'size_bytes',u.size_bytes,
      'sha256',u.sha256,
      'received_at',u.created_at
    ),
    'FACT','ACTIVE','CLIENT_PROVIDED_RECORD','UPLOAD',u.id::text,
    jsonb_build_object('registered_via','register_upload_as_source_v1','case_id',u.case_id)
  )
  returning record_id into v_record;

  insert into registry.sources(
    source_id,record_id,case_id,source_type,original_filename,ingested_at,sha256,
    version,status,metadata,source_code,client_label,source_role,authenticity_status,
    received_at,version_family_key,access_classification,publication_status
  ) values (
    v_source_id,v_record,u.case_id,btrim(p_source_type),u.original_filename,now(),u.sha256,
    1,'ACTIVE',
    jsonb_build_object('upload_record_id',u.id,'uploaded_by',u.uploaded_by),
    v_source_code,nullif(btrim(p_client_label),''),p_source_role,'NOT_TESTED',
    u.created_at,v_source_id,'ORDINARY','APPROVAL_REQUIRED'
  );

  update public.upload_records
  set source_id=v_source_id,status='INGESTED'
  where id=u.id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(
    auth.uid(),private.current_user_role(),'UPLOAD_REGISTERED_AS_SOURCE','source',v_source_id,u.case_id,
    jsonb_build_object(
      'upload_id',u.id,'source_type',btrim(p_source_type),'source_role',p_source_role,
      'authenticity_status','NOT_TESTED'
    )
  );

  perform private.set_lifecycle_signal(
    u.case_id,'RECORD_COLLECTION','IN_PROGRESS',
    'A client upload was registered as a source with provenance and hash preserved.',
    'SOURCE_REGISTRATION'
  );

  return v_source_id;
end;
$function$;

create or replace function public.register_upload_as_source_v1(
  p_upload_id uuid,
  p_source_type text,
  p_source_role text default 'NATIVE_SOURCE',
  p_client_label text default null
) returns text
language sql
security definer
set search_path to ''
as $function$
  select private.register_upload_as_source_impl_v1(
    p_upload_id,p_source_type,p_source_role,p_client_label
  );
$function$;

create or replace function private.set_document_request_status_impl_v1(
  p_request_id uuid,
  p_status text
) returns void
language plpgsql
security definer
set search_path to ''
as $function$
declare
  r public.document_requests%rowtype;
begin
  if p_status not in ('OPEN','UPLOADED','UNDER_REVIEW','SATISFIED','WAIVED') then
    raise exception 'invalid document request status' using errcode='22023';
  end if;

  select * into r
  from public.document_requests
  where id=p_request_id
  for update;

  if not found then raise exception 'document request not found' using errcode='P0002'; end if;
  if auth.uid() is null or not private.is_staff() or not private.can_access_case(r.case_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;

  update public.document_requests
  set status=p_status
  where id=p_request_id;

  insert into public.audit_events(actor_user_id,actor_role,action,object_type,object_id,case_id,metadata)
  values(
    auth.uid(),private.current_user_role(),'DOCUMENT_REQUEST_STATUS_CHANGED',
    'document_request',p_request_id::text,r.case_id,
    jsonb_build_object('from_status',r.status,'to_status',p_status)
  );
end;
$function$;

create or replace function public.set_document_request_status_v1(
  p_request_id uuid,
  p_status text
) returns void
language sql
security definer
set search_path to ''
as $function$
  select private.set_document_request_status_impl_v1(p_request_id,p_status);
$function$;

revoke all on function private.register_upload_as_source_impl_v1(uuid,text,text,text) from public,anon,authenticated;
revoke all on function private.set_document_request_status_impl_v1(uuid,text) from public,anon,authenticated;
revoke all on function public.register_upload_as_source_v1(uuid,text,text,text) from public,anon;
revoke all on function public.set_document_request_status_v1(uuid,text) from public,anon;
grant execute on function public.register_upload_as_source_v1(uuid,text,text,text) to authenticated,service_role;
grant execute on function public.set_document_request_status_v1(uuid,text) to authenticated,service_role;
