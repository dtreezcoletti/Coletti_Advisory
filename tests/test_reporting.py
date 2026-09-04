from coletti_advisory.reporting import (
    REPORT_FINDINGS,
    REPORT_OPERATIONS,
    REPORT_RECORDS,
    build_findings_report,
    build_operations_report,
    build_publication_gate,
    build_records_report,
    build_report_bundle,
)
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


def test_report_bundle_contains_all_three_client_deliverables():
    bundle = build_report_bundle(SYNTHETIC_MANIFEST)
    assert set(bundle) == {REPORT_RECORDS, REPORT_OPERATIONS, REPORT_FINDINGS}
    assert all(report["document_status"] == "DRAFT — NOT PUBLISHED" for report in bundle.values())


def test_records_report_is_populated_from_source_linked_analysis():
    report = build_records_report(SYNTHETIC_MANIFEST)
    assert len(report["records_reconstruction"]) == 2
    assert any("SRC-DEMO-001" in row["Supporting sources"] for row in report["records_reconstruction"])
    assert report["unresolved_record_issues"]
    assert report["verification_referrals"]


def test_operations_report_receives_operational_and_comparison_analysis():
    report = build_operations_report(SYNTHETIC_MANIFEST)
    assert len(report["operations_reconstruction"]) == 2
    assert len(report["cross_record_comparison"]) == 1
    assert report["verification_referrals"]


def test_findings_report_preserves_issue_boundary_and_verification_route():
    report = build_findings_report(SYNTHETIC_MANIFEST)
    assert report["findings"]
    assert report["verification_referrals"]
    assert "not a finding of fraud" in report["boundary"]


def test_publication_gate_blocks_automatic_client_release_when_review_is_open():
    gate = build_publication_gate(SYNTHETIC_MANIFEST)
    assert gate["status"] == "REVIEW REQUIRED"
    assert gate["published"] is False
    assert gate["review_required_count"] >= 1
    assert gate["verification_recommendation_count"] >= 1


def test_clean_manifest_becomes_ready_for_review_but_never_self_publishes():
    manifest = {
        "sources": {},
        "source_states": {},
        "propositions": {},
        "contradictions": {},
        "escalations": {},
        "audit_log": [],
    }
    gate = build_publication_gate(manifest)
    assert gate["status"] == "READY FOR REVIEW"
    assert gate["published"] is False
