from copy import deepcopy

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
    assert all(report["report_version"] == "1.0-client-ready" for report in bundle.values())
    assert all("publication_gate" in report for report in bundle.values())


def test_records_report_is_source_linked_and_boundary_safe():
    report = build_records_report(SYNTHETIC_MANIFEST)
    assert len(report["records_reconstruction"]) == 2
    assert any("SRC-DEMO-001" in row["Supporting sources"] for row in report["records_reconstruction"])
    assert report["unresolved_record_issues"]
    assert report["verification_referrals"]
    assert "does not infer intent or motive" in report["boundary"]


def test_operations_report_receives_canonical_operational_analysis():
    report = build_operations_report(SYNTHETIC_MANIFEST)
    assert len(report["operations_reconstruction"]) == 2
    assert len(report["cross_record_comparison"]) == 1
    assert report["verification_referrals"]
    comparison = report["cross_record_comparison"][0]
    assert comparison["Resolution state"] == "OPEN"
    assert comparison["Verification state"] == "RECOMMENDED"


def test_findings_report_preserves_issue_boundary_and_source_linked_observations():
    report = build_findings_report(SYNTHETIC_MANIFEST)
    assert report["record_supported_observations"]
    assert report["findings"]
    assert report["verification_referrals"]
    assert "not a finding of fraud" in report["boundary"]


def test_publication_gate_blocks_open_review_and_missing_corroboration_basis():
    gate = build_publication_gate(SYNTHETIC_MANIFEST)
    assert gate["status"] == "REVIEW REQUIRED"
    assert gate["published"] is False
    assert gate["review_required_count"] >= 1
    assert gate["verification_recommendation_count"] >= 1
    assert gate["corroboration_control_count"] == 1
    assert any("CORROBORATED state has no recorded corroboration basis" in blocker for blocker in gate["blockers"])


def test_client_explanation_remains_a_publication_blocker_until_independently_supported():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["reconciliations"] = {
        "REC-1": {
            "reconciliation_id": "REC-1",
            "proposition_ids": ["PROP-DEMO-001", "PROP-DEMO-002"],
            "contradiction_ids": ["CON-DEMO-001"],
            "outcome": "Reconciled",
            "actor": "demo-session",
            "rationale": "Client provided missing context.",
        }
    }
    gate = build_publication_gate(manifest)
    assert gate["status"] == "REVIEW REQUIRED"
    assert any("EXPLAINED" in blocker for blocker in gate["blockers"])


def test_verified_resolution_drops_redundant_verification_referral():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["sources"]["SRC-DEMO-001"]["metadata"]["corroborating_source_ids"] = ["SRC-DEMO-002"]
    manifest["reconciliations"] = {
        "REC-1": {
            "reconciliation_id": "REC-1",
            "proposition_ids": ["PROP-DEMO-001", "PROP-DEMO-002"],
            "contradiction_ids": ["CON-DEMO-001"],
            "outcome": "Verified resolution",
            "actor": "demo-session",
            "rationale": "Independent custodian confirmed the corrected amount.",
        }
    }
    manifest["escalations"] = {}
    report = build_operations_report(manifest)
    assert report["verification_referrals"] == []
    assert report["publication_gate"]["status"] == "READY FOR FINAL HUMAN APPROVAL"
    assert report["publication_gate"]["published"] is False


def test_control_manifest_never_appears_in_any_client_report():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["sources"]["SRC-CONTROL"] = {
        "source_id": "SRC-CONTROL",
        "content_hash": "hash-control",
        "metadata": {"filename": "colettios_synthetic_manifest.json", "classification": "Operational Audit"},
    }
    manifest["source_states"]["SRC-CONTROL"] = "INGESTED"
    manifest["propositions"]["PROP-CONTROL"] = {
        "proposition_id": "PROP-CONTROL",
        "text": '[$.sources.SRC-DEMO-001.source_id] $.sources.SRC-DEMO-001.source_id = "SRC-DEMO-001"',
        "source_ids": ["SRC-CONTROL"],
    }
    manifest["contradictions"]["CON-CONTROL"] = {
        "contradiction_id": "CON-CONTROL",
        "proposition_a": "PROP-DEMO-002",
        "proposition_b": "PROP-CONTROL",
        "reason": "Metadata contamination",
    }

    bundle = build_report_bundle(manifest)
    serialized = str(bundle)
    assert "SRC-CONTROL · colettios_synthetic_manifest.json" not in serialized
    assert "Metadata contamination" not in serialized
    assert "$.sources.SRC-DEMO-001.source_id" not in serialized


def test_clean_manifest_becomes_ready_for_final_human_approval_but_never_self_publishes():
    manifest = {
        "sources": {},
        "source_states": {},
        "propositions": {},
        "contradictions": {},
        "escalations": {},
        "audit_log": [],
    }
    gate = build_publication_gate(manifest)
    assert gate["status"] == "READY FOR FINAL HUMAN APPROVAL"
    assert gate["published"] is False
