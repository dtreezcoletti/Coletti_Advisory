-- Cover foreign keys introduced by Automated Records Intake & Exception Routing v1.
create index if not exists idx_record_intake_jobs_duplicate_upload on public.record_intake_jobs(duplicate_upload_id);
create index if not exists idx_record_intake_jobs_registered_source on public.record_intake_jobs(registered_source_id);
create index if not exists idx_record_intake_jobs_reviewed_by on public.record_intake_jobs(reviewed_by);
create index if not exists idx_record_intake_jobs_taxonomy on public.record_intake_jobs(suggested_taxonomy_key);
create index if not exists idx_record_intake_segments_registered_source on public.record_intake_segments(registered_source_id);
create index if not exists idx_record_intake_segments_taxonomy on public.record_intake_segments(suggested_taxonomy_key);
create index if not exists idx_record_request_matches_reviewed_by on public.record_request_matches(reviewed_by);
create index if not exists idx_record_request_matches_source on public.record_request_matches(source_id);
create index if not exists idx_source_relationships_created_by on registry.source_relationships(created_by);
