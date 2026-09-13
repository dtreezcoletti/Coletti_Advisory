-- Owner Workspace / Continuity v0.1
-- ADDITIVE ONLY. Do not expose these schemas through the Data API.
-- Operational rollback is performed by disabling capture/retrieval/promotion,
-- not by dropping schemas or deleting imported history.

create schema if not exists continuity_private;
create schema if not exists legal_private;

revoke all on schema continuity_private from public, anon, authenticated;
revoke all on schema legal_private from public, anon, authenticated;

create table if not exists continuity_private.settings (
    singleton boolean primary key default true check (singleton),
    capture_enabled boolean not null default false,
    retrieval_enabled boolean not null default false,
    promotion_enabled boolean not null default false,
    updated_at timestamptz not null default now()
);

insert into continuity_private.settings (singleton)
values (true)
on conflict (singleton) do nothing;

create table if not exists continuity_private.raw_archives (
    archive_id uuid primary key default gen_random_uuid(),
    owner_user_id text not null,
    source_system text not null,
    source_filename text not null,
    archive_sha256 text not null,
    byte_size bigint not null check (byte_size >= 0),
    storage_ref text,
    status text not null default 'STAGED' check (status in ('STAGED','PROCESSING','PROCESSED','FAILED','ARCHIVED')),
    created_at timestamptz not null default now(),
    unique (owner_user_id, archive_sha256)
);

create table if not exists continuity_private.import_jobs (
    import_job_id uuid primary key default gen_random_uuid(),
    archive_id uuid not null references continuity_private.raw_archives(archive_id),
    owner_user_id text not null,
    state text not null default 'QUEUED' check (state in ('QUEUED','PROCESSING','REVIEW','COMPLETE','FAILED','CANCELLED')),
    conversations_discovered integer not null default 0 check (conversations_discovered >= 0),
    messages_discovered integer not null default 0 check (messages_discovered >= 0),
    messages_processed integer not null default 0 check (messages_processed >= 0),
    last_completed_batch integer not null default 0 check (last_completed_batch >= 0),
    error text,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists continuity_private.messages (
    message_row_id uuid primary key default gen_random_uuid(),
    import_job_id uuid not null references continuity_private.import_jobs(import_job_id) on delete cascade,
    owner_user_id text not null,
    source_conversation_id text not null,
    source_conversation_title text,
    source_message_id text not null,
    source_role text not null,
    source_created_at timestamptz,
    content_hash text not null,
    content text not null,
    proposed_domain text not null check (proposed_domain in ('institutional','owner_private','legal_private','archive_only','ambiguous')),
    proposed_kind text not null check (proposed_kind in ('decision','rule','open_issue','fact','working_note')),
    confidence numeric(5,4) not null check (confidence >= 0 and confidence <= 1),
    sensitivity text not null check (sensitivity in ('normal','private','restricted')),
    needs_review boolean not null default false,
    created_at timestamptz not null default now(),
    unique (import_job_id, source_conversation_id, source_message_id)
);

create table if not exists continuity_private.candidates (
    candidate_id uuid primary key default gen_random_uuid(),
    message_row_id uuid not null references continuity_private.messages(message_row_id) on delete cascade,
    owner_user_id text not null,
    proposed_domain text not null,
    proposed_kind text not null,
    normalized_text text not null,
    status text not null default 'CANDIDATE' check (status in ('CANDIDATE','REVIEWED','APPROVED','REJECTED','SUPERSEDED','CONFLICT')),
    promoted_record_id uuid,
    reviewed_by text,
    reviewed_at timestamptz,
    review_note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists continuity_private.audit_events (
    event_id uuid primary key default gen_random_uuid(),
    owner_user_id text not null,
    import_job_id uuid references continuity_private.import_jobs(import_job_id),
    candidate_id uuid references continuity_private.candidates(candidate_id),
    event_type text not null,
    actor text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists legal_private.matters (
    matter_id uuid primary key default gen_random_uuid(),
    owner_user_id text not null,
    matter_key text not null,
    title text not null,
    status text not null default 'ACTIVE',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (owner_user_id, matter_key)
);

create table if not exists legal_private.records (
    legal_record_id uuid primary key default gen_random_uuid(),
    matter_id uuid not null references legal_private.matters(matter_id),
    owner_user_id text not null,
    source_ref text,
    authority_class text not null check (authority_class in (
        'COURT_ORDER','EXECUTED_AGREEMENT','TRANSCRIPT','FILED_DOCUMENT','FINANCIAL_RECORD',
        'COMMUNICATION','DRAFT','OWNER_ASSERTION','ANALYTICAL_INFERENCE'
    )),
    record_state text not null,
    statement text not null,
    status text not null default 'CANDIDATE' check (status in ('CANDIDATE','CURRENT','SUPERSEDED','REJECTED','CONFLICT')),
    supersedes_record_id uuid references legal_private.records(legal_record_id),
    effective_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists continuity_messages_job_idx on continuity_private.messages(import_job_id);
create index if not exists continuity_messages_domain_idx on continuity_private.messages(owner_user_id, proposed_domain, needs_review);
create index if not exists continuity_candidates_status_idx on continuity_private.candidates(owner_user_id, status, proposed_domain);
create index if not exists continuity_audit_job_idx on continuity_private.audit_events(import_job_id, created_at);
create index if not exists legal_records_matter_idx on legal_private.records(matter_id, status, effective_at);

comment on schema continuity_private is 'Owner-private AI/chat continuity source, staging, review, and audit data. Not exposed to client or employee Data API paths.';
comment on schema legal_private is 'Owner-private legal matter reconstruction. Conversational material is not controlling legal authority without promotion under source-authority rules.';
comment on table continuity_private.settings is 'Kill switches. Retrieval and promotion default OFF.';
