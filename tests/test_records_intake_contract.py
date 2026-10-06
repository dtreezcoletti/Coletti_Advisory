from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_records_intake_architecture_contract():
    migration = read("supabase/migrations/20261006233624_automated_records_intake_exception_routing_v1.sql")
    source_registration = read("supabase/migrations/20261006165144_record_collection_source_registration_v1.sql")
    approval = read("supabase/migrations/20261006234245_approve_records_receipt_source_registration_sop_v1.sql")
    architecture = source_registration + "\n" + migration + "\n" + approval
    required = [
        "public.source_taxonomy",
        "public.record_intake_jobs",
        "public.record_intake_segments",
        "registry.source_relationships",
        "public.record_request_matches",
        "record_intake_filename_triage_v1",
        "refresh_record_intake_job_v1",
        "batch_register_green_intake_v1",
        "confirm_record_intake_job_v1",
        "mark_record_intake_duplicate_v1",
        "record_intake_metrics_v1",
        "trg_attach_intake_uploads_to_case_v1",
        "NOT_TESTED",
        "APPROVAL_REQUIRED",
    ]
    for item in required:
        assert item in architecture

def test_records_intake_ui_is_exception_driven():
    app = read("web/assets/app.js")
    required = [
        "Records Intake & Source Registration",
        "source_taxonomy",
        "record_intake_jobs",
        "record_intake_metrics_v1",
        "Register Green Batch",
        "Quick confirmations",
        "Exceptions",
        "confirm-intake-job",
        "mark-intake-duplicate",
        "preview-intake-upload",
        "Content-aware document segmentation",
    ]
    for item in required:
        assert item in app

def test_owner_has_records_intake_route():
    app = read("web/assets/app.js")
    assert "['records','Records Intake']" in app
    assert "if(view==='records'){ go('/workspace/documents')" in app


def test_content_processor_and_bundle_registration_contract():
    processor = read("supabase/functions/record-intake-process/index.ts")
    analysis = read("supabase/migrations/20261006235028_record_content_analysis_application_v1.sql")
    segments = read("supabase/migrations/20261006235446_record_intake_segment_registration_v1.sql")
    versions = read("supabase/migrations/20261006235813_record_intake_version_and_request_match_confirmation_v1.sql")
    app = read("web/assets/app.js")

    for item in [
        "npm:unpdf@1.8.1",
        "record_content_processor_v1.0.1",
        "raw_text_persisted: false",
        "MAX_PDF_PAGES",
        "proposeSegments",
        "probable_version_job_id",
        "requestMatches",
    ]:
        assert item in processor

    for item in [
        "apply_record_intake_analysis_v1",
        "to service_role",
        "intake_complexity_index",
        "UNCALIBRATED_V1",
    ]:
        assert item in analysis

    for item in [
        "replace_record_intake_segments_v1",
        "confirm_record_intake_segments_v1",
        "UPLOAD_SEGMENT_REGISTERED_AS_SOURCE",
        "page_start",
        "page_end",
        "NOT_TESTED",
        "APPROVAL_REQUIRED",
    ]:
        assert item in segments

    for item in [
        "SOURCE_VERSION_FAMILY_CONFIRMED",
        "VERSION_OF",
        "confirm_record_request_match_v1",
        "reject_record_request_match_v1",
        "UNDER_REVIEW",
    ]:
        assert item in versions

    for item in [
        "reprocess-intake-content",
        "save-intake-segments",
        "confirm-intake-segments",
        "confirm-request-match",
        "reject-request-match",
        "intake_complexity_index",
        "Your files received",
    ]:
        assert item in app
