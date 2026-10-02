-- Production truth / security hardening closure, 2026-10-02.
-- Keeps database authority aligned with the latest release manifest and preserves
-- fail-closed internal function resolution.

alter function archive.prevent_immutable_change() set search_path = '';
alter function search.hybrid_message_candidates(text, integer) set search_path = '';

CREATE OR REPLACE FUNCTION public.owner_implementation_snapshot()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'private', 'registry', 'dispatcher', 'pg_catalog'
AS $function$
declare
  result jsonb;
begin
  if not private.has_role(array['owner']::text[]) then
    raise exception 'Owner role required';
  end if;

  select jsonb_build_object(
    'production_profile', jsonb_build_object(
      'target_tier', 'ELITE',
      'feature_state', 'ELITE_FEATURE_COMPLETE_CANDIDATE',
      'production_authorized', coalesce((
        select rm.production_authorized
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ), false),
      'human_release_gate_required', coalesce((
        select rm.human_approval_required
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ), true),
      'environment', (
        select rm.environment
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ),
      'release_status', (
        select rm.release_status
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ),
      'owner_only_production', coalesce((
        select (rm.metadata->>'owner_only_production')::boolean
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ), false),
      'external_client_access', coalesce((
        select (rm.metadata->>'external_client_access')::boolean
        from registry.release_manifests rm
        order by rm.created_at desc
        limit 1
      ), false),
      'security_gate', 'CLOSED',
      'security_mode', 'SYNTHETIC_DEMO_ONLY',
      'governing_rule', 'AI is allowed to think. Authority is not automatic.'
    ),
    'implementation', jsonb_build_object(
      'items', coalesce((
        select jsonb_agg(jsonb_build_object(
          'implementation_id', i.implementation_id,
          'requirement_title', i.requirement_title,
          'implementation_state', i.implementation_state,
          'policy_status', i.policy_status,
          'database_status', i.database_status,
          'code_status', i.code_status,
          'workflow_status', i.workflow_status,
          'human_control_status', i.human_control_status,
          'test_status', i.test_status,
          'documentation_status', i.documentation_status,
          'verification_ready', i.verification_ready,
          'drift', i.drift,
          'blocker', i.blocker,
          'next_action', i.next_action,
          'updated_at', i.updated_at,
          'source_record_key', i.source_record_key
        ) order by i.implementation_no)
        from registry.implementation_matrix i
      ), '[]'::jsonb),
      'state_counts', coalesce((
        select jsonb_object_agg(implementation_state,cnt)
        from (
          select implementation_state,count(*)::int cnt
          from registry.implementation_matrix
          group by implementation_state
        ) x
      ), '{}'::jsonb)
    ),
    'controls', jsonb_build_object(
      'active', (select count(*)::int from registry.controls where lifecycle_state='ACTIVE'),
      'verified', (select count(*)::int from registry.control_verifications cv
                   join registry.controls c on c.control_id=cv.control_id
                   where c.lifecycle_state='ACTIVE'),
      'drift', (select count(*)::int from registry.control_drift_records where status in ('OPEN','ACTIVE')),
      'remediation_open', (select count(*)::int from registry.control_remediations where status in ('OPEN','IN_PROGRESS'))
    ),
    'matter_review_pipeline', jsonb_build_object(
      'cases', (select count(*)::int from registry.cases),
      'sources', (select count(*)::int from registry.sources),
      'snapshots', (select count(*)::int from registry.source_snapshots),
      'reconstructions', (select count(*)::int from registry.reconstructions),
      'fresh_eyes_audits', (select count(*)::int from registry.reconstruction_audits where review_mode='ADVERSARIAL'),
      'open_variances', (select count(*)::int from registry.reconstruction_variances where resolution_status is distinct from 'RESOLVED'),
      'reconciliations', (select count(*)::int from registry.reconciliation_runs),
      'findings', (select count(*)::int from registry.findings),
      'publication_gates', (select count(*)::int from registry.publication_gates),
      'reports', (select count(*)::int from registry.reports)
    ),
    'case_lifecycle_catalog', coalesce((
      select jsonb_agg(jsonb_build_object(
        'checkpoint_key', c.checkpoint_key,
        'sequence_no', c.sequence_no,
        'label', c.label,
        'automation_mode', c.automation_mode,
        'gate_type', c.gate_type,
        'next_checkpoint_key', c.next_checkpoint_key,
        'required', c.required,
        'protected_gate', c.protected_gate
      ) order by c.sequence_no)
      from public.case_lifecycle_checkpoint_catalog c
    ), '[]'::jsonb),
    'active_case_state', coalesce((
      select jsonb_agg(jsonb_build_object(
        'case_id', cp.case_id,
        'checkpoint_key', cp.checkpoint_key,
        'status', cp.status,
        'blocking_reason', cp.blocking_reason,
        'last_transition_at', cp.last_transition_at
      ) order by cp.case_id, cp.checkpoint_key)
      from public.case_lifecycle_checkpoints cp
      where cp.status not in ('COMPLETED','CLOSED','ARCHIVED')
    ), '[]'::jsonb),
    'owner_attention', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', w.id,
        'category', w.category,
        'title', w.title,
        'description', w.description,
        'status', w.status,
        'priority', w.priority,
        'due_at', w.due_at,
        'case_id', w.case_id
      ) order by w.due_at nulls last, w.priority)
      from public.owner_work_items w
      where w.owner_required = true
        and w.status not in ('COMPLETED','CLOSED','DONE')
    ), '[]'::jsonb),
    'dispatcher', jsonb_build_object(
      'pending', (select count(*)::int from dispatcher.execution_requests where state in ('PENDING','ROUTED','RUNNING')),
      'blocked', (select count(*)::int from dispatcher.execution_requests where state='BLOCKED'),
      'failed', (select count(*)::int from dispatcher.execution_requests where state='FAILED'),
      'workers_enabled', (select count(*)::int from dispatcher.workers where enabled=true)
    ),
    'domain_paths', jsonb_build_object(
      'open', (select count(*)::int from registry.domain_pathways where status='OPEN'),
      'authorized', (select count(*)::int from registry.domain_pathways where status='AUTHORIZED'),
      'expired', (select count(*)::int from registry.domain_pathways where status='EXPIRED')
    ),
    'release', coalesce((
      select jsonb_build_object(
        'release_id', rm.release_id,
        'release_key', rm.release_key,
        'status', rm.release_status,
        'stage', rm.environment,
        'production_authorized', rm.production_authorized,
        'human_approval_required', rm.human_approval_required,
        'accepted_at', rm.accepted_at,
        'metadata', rm.metadata
      )
      from registry.release_manifests rm
      order by rm.created_at desc
      limit 1
    ), '{}'::jsonb),
    'lifecycle_order', jsonb_build_array(
      'INTAKE','SCREENING','ACCEPTANCE','CLIENT_ONBOARDING','ENGAGEMENT_GATES',
      'CASE_OPENING','RECORD_COLLECTION','RECONSTRUCTION','HUMAN_REVIEW',
      'REPORT_PREPARATION','PUBLICATION_HANDOFF','CLOSEOUT','ARCHIVE'
    ),
    'implementation_lifecycle', jsonb_build_array('PROPOSED','APPROVED','IMPLEMENTING','VERIFIED','OPERATIONAL')
  )
  into result;

  return result;
end;
$function$
;


-- Reconcile Implementation Control to the current component-status vocabulary.
create or replace function private.refresh_implementation_control_queue_v1(p_implementation_id text)
returns jsonb
language plpgsql
security definer
set search_path to 'pg_catalog', 'public', 'private'
as $function$
declare
  im registry.implementation_matrix%rowtype;
  action_name text;
  reason_text text;
  created_count integer := 0;
  resolved_count integer := 0;
begin
  select * into im
  from registry.implementation_matrix
  where implementation_id::text = p_implementation_id;

  if not found then
    return jsonb_build_object('status','NOT_FOUND','implementation_id',p_implementation_id);
  end if;

  update registry.implementation_control_queue
  set status='RESOLVED', resolved_at=now()
  where implementation_id=p_implementation_id
    and status in ('OPEN','IN_PROGRESS','BLOCKED')
    and (
      im.verification_ready = true
      or (
        action_type='DATABASE_RECONCILIATION'
        and im.database_status in ('VERIFIED','NOT_REQUIRED')
      )
    );
  get diagnostics resolved_count = row_count;

  if im.implementation_state = 'OPERATIONAL' and coalesce(im.verification_ready,false) = false then
    action_name := case
      when coalesce(im.database_status,'UNASSESSED') not in ('VERIFIED','NOT_REQUIRED')
        then 'DATABASE_RECONCILIATION'
      else 'VERIFICATION'
    end;

    reason_text := case
      when action_name = 'DATABASE_RECONCILIATION'
        then 'Operational implementation requires authoritative database reconciliation.'
      else 'Operational implementation requires remaining verification evidence.'
    end;

    insert into registry.implementation_control_queue
      (implementation_id, action_type, reason, source_snapshot)
    values
      (p_implementation_id, action_name, reason_text, to_jsonb(im))
    on conflict (implementation_id, action_type) where status in ('OPEN','IN_PROGRESS','BLOCKED')
    do nothing;

    get diagnostics created_count = row_count;
  end if;

  insert into registry.implementation_control_events
    (implementation_id, event_type, resulting_state, evidence)
  values
    (p_implementation_id, 'CONTROL_RECONCILIATION',
     jsonb_build_object(
       'implementation_state', im.implementation_state,
       'database_status', im.database_status,
       'verification_ready', im.verification_ready,
       'code_status', im.code_status
     ),
     jsonb_build_object(
       'queue_items_created',created_count,
       'queue_items_resolved',resolved_count,
       'status_vocabulary','VERIFIED_NOT_REQUIRED'
     ));

  return jsonb_build_object(
    'status','RECONCILED',
    'implementation_id',p_implementation_id,
    'queue_items_created',created_count,
    'queue_items_resolved',resolved_count
  );
end;
$function$;

-- Close the EO-0004 record at its own scope. Runtime login/recovery proof remains
-- owned by the separate runtime acceptance gates.
update registry.implementation_matrix
set policy_status='NOT_REQUIRED',
    blocker=null,
    updated_at=now()
where implementation_id='IMP-113';

-- Owner-only production authority and database truth are proven. Runtime/browser
-- dimensions remain IN_PROGRESS until deployment and identity acceptance pass.
update registry.implementation_matrix
set policy_status='NOT_REQUIRED',
    database_status='VERIFIED',
    code_status=case when code_status='UNASSESSED' then 'IN_PROGRESS' else code_status end,
    workflow_status=case when workflow_status='UNASSESSED' then 'IN_PROGRESS' else workflow_status end,
    human_control_status='VERIFIED',
    test_status=case when test_status='UNASSESSED' then 'IN_PROGRESS' else test_status end,
    documentation_status='VERIFIED',
    blocker='Owner-only production authority is valid and database truth is verified. Remaining proof is current deployment/browser authentication-recovery acceptance plus live runtime verification.',
    next_action='Verify current Render deployments, Owner login/session routing, password recovery, live DARI/provider path, and recovery evidence before promoting remaining runtime dimensions.',
    updated_at=now()
where implementation_id='IMP-152';

select private.refresh_implementation_control_queue_v1('IMP-113');
select private.refresh_implementation_control_queue_v1('IMP-152');
