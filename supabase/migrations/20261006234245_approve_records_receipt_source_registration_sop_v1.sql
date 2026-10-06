-- Owner approval of Records Receipt & Source Registration SOP v1.
-- Core exception-driven intake is verified; advanced content-aware processing remains pending.

with target as (
  select record_id
  from registry.records
  where scope='coletti_admin'
    and record_key='coletti_admin.procedure.records_receipt_source_registration.v1'
    and version=1
)
update registry.records r
set
  status='APPROVED',
  authority='USER_APPROVED',
  effective_at=coalesce(r.effective_at,now()),
  content=jsonb_build_object(
    'purpose','Move received records through staging, automated administrative triage, exception review, canonical Source registration and request reconciliation without confusing receipt or registration with verification.',
    'trigger','A case-authorized upload or record-request response is received. Pre-case intake uploads remain staged and attach to the case when the case is formally opened.',
    'operating_model','EXCEPTION_DRIVEN_SOLO_FIRST_STAFF_SCALABLE',
    'governing_principles',jsonb_build_array(
      'Human attention is reserved for ambiguity, exception and judgment; routine source administration should be automated wherever the record supports it.',
      'Record volume does not determine workload by itself; human-attention demand does.',
      'One person may perform multiple operational roles, but one action may not silently collapse multiple evidentiary states.',
      'Receipt, registration, verification, evidence fitness and publication are separate states.'
    ),
    'steps',jsonb_build_array(
      'Preserve the untouched original upload, storage location, uploader, received timestamp, MIME type, size and SHA-256 hash.',
      'Create an intake-processing job and attach intake-stage uploads to the canonical case when the case is opened.',
      'Use the controlled Source Taxonomy. Automation may propose source type, source role, client-facing label and confidence; staff should not manually invent Source IDs.',
      'Route ordinary administrative classifications Green, quick confirmations Amber, and ambiguous/duplicate/bundle/high-risk records Red.',
      'Detect exact duplicates by hash before Source creation. Probable versions, source families and multi-document bundles remain visible until confirmed.',
      'For multi-document bundles, preserve the original bundle and create traceable child Sources only through page-boundary segmentation; child lineage must retain original upload and exact page ranges.',
      'Allocate canonical Source ID/code automatically through the controlled source-registration action.',
      'Default authenticity to NOT_TESTED unless separately established through Evidence Fitness. Default publication status to APPROVAL_REQUIRED.',
      'Match received records to open document requests, but never mark a request SATISFIED merely because something was uploaded.',
      'Track intake throughput, exception counts, duplicate/bundle burden and human-attention time so turnaround estimates are based on actual complexity rather than raw file count.',
      'Once the Record Universe is locked, later source additions require impact review and re-locking before reconstruction can continue against the changed universe.'
    ),
    'routing',jsonb_build_object(
      'GREEN','Routine administrative classification eligible for batch registration; this is not authenticity verification.',
      'AMBER','Quick human confirmation required before registration.',
      'RED','Human exception review required because of ambiguity, duplicate risk, probable bundle, unreadability or other blocking condition.'
    ),
    'exit_criteria',jsonb_build_array(
      'Each accepted upload is either linked to a canonical Source or intentionally rejected/superseded.',
      'Hash, provenance and original upload lineage are retained.',
      'Related document-request status accurately reflects any remaining obligation.',
      'No intake exception that blocks Record Universe lock remains unresolved.'
    ),
    'audit_evidence',jsonb_build_array(
      'UPLOAD_REGISTERED_AS_SOURCE',
      'UPLOAD_RESOLVED_AS_DUPLICATE',
      'DOCUMENT_REQUEST_STATUS_CHANGED',
      'upload_records',
      'record_intake_jobs',
      'record_intake_segments',
      'registry.sources',
      'registry.source_relationships'
    ),
    'implementation_status','CORE_EXCEPTION_ROUTING_VERIFIED_ADVANCED_CONTENT_PROCESSOR_PENDING',
    'verified_components',jsonb_build_array(
      'controlled source taxonomy',
      'automatic Source ID allocation',
      'staging and case attachment',
      'Green/Amber/Red routing',
      'exact SHA-256 duplicate detection',
      'probable bundle exception routing',
      'batch Green registration',
      'secure preview and controlled confirmation',
      'intake metrics',
      'transactional smoke test'
    ),
    'pending_activation',jsonb_build_array(
      'content-aware document classification beyond filename/metadata signals',
      'PDF page-boundary segmentation processor',
      'probable version/source-family detection and confirmation workflow',
      'automated document-request matching',
      'client-facing completeness dashboard',
      'intake complexity score tied to turnaround estimation'
    )
  ),
  metadata=coalesce(r.metadata,'{}'::jsonb) || jsonb_build_object(
    'document_state','APPROVED_SOP',
    'approved_on','2026-10-06',
    'owner_approved',true,
    'core_exception_routing_verified',true,
    'transactional_smoke_test',true,
    'advanced_content_processor_pending',true,
    'verified_against_live_workflow',true
  ),
  updated_at=now()
from target t
where r.record_id=t.record_id;

update registry.artifacts a
set
  status='APPROVED',
  effective_at=coalesce(a.effective_at,now()),
  metadata=coalesce(a.metadata,'{}'::jsonb) || jsonb_build_object(
    'document_state','APPROVED_SOP',
    'owner_approved',true,
    'core_exception_routing_verified',true,
    'advanced_content_processor_pending',true,
    'implementation_status','CORE_EXCEPTION_ROUTING_VERIFIED_ADVANCED_CONTENT_PROCESSOR_PENDING'
  ),
  updated_at=now()
where a.record_id in (
  select record_id
  from registry.records
  where scope='coletti_admin'
    and record_key='coletti_admin.procedure.records_receipt_source_registration.v1'
    and version=1
);

update registry.sops s
set
  status='APPROVED',
  approved_by='OWNER',
  approved_at=coalesce(s.approved_at,now()),
  updated_at=now()
where s.artifact_id in (
  select a.artifact_id
  from registry.artifacts a
  join registry.records r on r.record_id=a.record_id
  where r.scope='coletti_admin'
    and r.record_key='coletti_admin.procedure.records_receipt_source_registration.v1'
    and r.version=1
);
