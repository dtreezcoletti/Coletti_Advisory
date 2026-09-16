from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260914142500_case_lifecycle_evidence_backed_completion_v1.sql"


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_lifecycle_completion_requires_authoritative_evidence():
    sql = _sql()
    assert "case_lifecycle_completion_evidence_v1" in sql
    for evidence_surface in (
        "public.intake_submissions",
        "public.client_user_links",
        "public.contract_records",
        "registry.sources",
        "registry.propositions",
        "registry.findings",
        "registry.reviews",
        "registry.reports",
        "public.publication_handoffs",
        "public.published_reports",
        "public.document_requests",
    ):
        assert evidence_surface in sql
    assert "completion evidence missing" in sql


def test_publication_completion_requires_first_truth_and_professional_boundary():
    sql = _sql()
    assert "first_truth_preflight_status = 'PASSED'" in sql
    assert "first_truth_notice_present" in sql
    assert "professional_boundary_passed" in sql
    assert "publication_status in ('PUBLISHED','DELIVERED')" in sql


def test_required_real_case_checkpoint_cannot_be_skipped_as_not_applicable():
    sql = _sql()
    assert "p_target_status='NOT_APPLICABLE' and cat.required" in sql
    assert "required lifecycle checkpoint cannot be marked not applicable for a real Case" in sql


def test_closeout_and_archive_are_evidence_ordered():
    sql = _sql()
    assert "dr.status not in ('SATISFIED','WAIVED')" in sql
    assert "cp.checkpoint_key = 'PUBLICATION_HANDOFF' and cp.status = 'COMPLETE'" in sql
    assert "upper(coalesce(v_case_status,'')) = 'CLOSED'" in sql
    assert "cp.checkpoint_key = 'CLOSEOUT' and cp.status = 'COMPLETE'" in sql


def test_evidence_helper_is_not_exposed_to_browser_roles():
    sql = _sql()
    assert "revoke all on function private.case_lifecycle_completion_evidence_v1(text,text) from public, anon, authenticated" in sql
    assert "grant execute on function private.case_lifecycle_completion_evidence_v1(text,text) to service_role" in sql
