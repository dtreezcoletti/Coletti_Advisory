-- Update approved Records Receipt & Source Registration SOP truth state after
-- advanced intake implementation. Real-file processor acceptance remains pending.

update registry.records
set
  content=jsonb_set(
    jsonb_set(
      jsonb_set(
        content,
        '{implementation_status}',
        to_jsonb('ADVANCED_INTAKE_IMPLEMENTED_CONTENT_PROCESSOR_ACCEPTANCE_PENDING'::text),
        true
      ),
      '{verified_components}',
      jsonb_build_array(
        'controlled source taxonomy',
        'automatic Source ID allocation',
        'staging and case attachment',
        'Green/Amber/Red exception routing',
        'exact SHA-256 duplicate detection and resolution',
        'content-aware PDF classification processor deployed',
        'proposed PDF page-boundary segmentation architecture',
        'reviewed bundle-to-child-Source registration with page-level provenance',
        'probable version-family detection and VERSION_OF confirmation',
        'automated document-request match suggestions with human confirmation',
        'batch Green registration',
        'secure preview and manual content reprocessing',
        'client-facing record-request completeness summary',
        'intake complexity index and human-attention metrics',
        'core and hard-case transactional smoke tests'
      ),
      true
    ),
    '{pending_activation}',
    jsonb_build_array(
      'real-file browser acceptance of record-intake-process against production uploads',
      'OCR or vision processing for image-only/scanned PDFs that yield sparse text',
      'content extraction for rich non-PDF formats beyond current text/metadata handling',
      'calibration of intake complexity index to actual turnaround estimates after production engagement data exists'
    ),
    true
  ),
  metadata=coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
    'advanced_intake_implemented',true,
    'content_processor_deployed',true,
    'content_processor_version','record_content_processor_v1.0.1',
    'hard_case_transactional_smoke_test',true,
    'content_processor_real_file_acceptance_pending',true,
    'updated_on','2026-10-06'
  ),
  updated_at=now()
where scope='coletti_admin'
  and record_key='coletti_admin.procedure.records_receipt_source_registration.v1'
  and version=1;

update registry.artifacts a
set
  metadata=coalesce(a.metadata,'{}'::jsonb) || jsonb_build_object(
    'implementation_status','ADVANCED_INTAKE_IMPLEMENTED_CONTENT_PROCESSOR_ACCEPTANCE_PENDING',
    'advanced_intake_implemented',true,
    'content_processor_deployed',true,
    'content_processor_real_file_acceptance_pending',true
  ),
  updated_at=now()
where a.record_id in (
  select record_id from registry.records
  where scope='coletti_admin'
    and record_key='coletti_admin.procedure.records_receipt_source_registration.v1'
    and version=1
);
