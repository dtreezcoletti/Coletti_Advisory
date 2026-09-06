from copy import deepcopy

from coletti_advisory.analysis import (
    build_analytical_issues,
    build_cross_record_comparison,
    build_operations_reconstruction,
    build_records_reconstruction,
    build_state_counts,
    build_summary,
)
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


def test_analysis_summary_counts_current_manifest():
    summary = build_summary(SYNTHETIC_MANIFEST)
    assert summary == {
        "sources": 2,
        "propositions": 2,
        "inconsistencies": 1,
        "open_issues": 1,
    }


def test_records_reconstruction_is_source_linked_and_review_aware():
    rows = build_records_reconstruction(SYNTHETIC_MANIFEST)
    assert len(rows) == 2
    corroborated = next(row for row in rows if row["Proposition"] == "PROP-DEMO-001")
    disputed = next(row for row in rows if row["Proposition"] == "PROP-DEMO-002")
    assert "SRC-DEMO-001" in corroborated["Supporting sources"]
    assert "synthetic_ledger.csv" in corroborated["Supporting sources"]
    assert corroborated["Review status"] == "Corroboration basis not recorded"
    assert disputed["Review status"] == "Requires review"


def test_operations_reconstruction_surfaces_follow_up_without_inventing_deviation():
    rows = build_operations_reconstruction(SYNTHETIC_MANIFEST)
    assert len(rows) == 2
    assert all("Record class" in row for row in rows)
    assert any("Resolve amount variance" in row["Open operational follow-up"] for row in rows)
    flagged = next(row for row in rows if row["Open operational follow-up"] != "None")
    assert "Verification recommendation" in flagged
    assert "Potential verifier" in flagged


def test_cross_record_comparison_preserves_both_statements_and_sources():
    rows = build_cross_record_comparison(SYNTHETIC_MANIFEST)
    assert len(rows) == 1
    row = rows[0]
    assert row["Classification"] == "Inconsistency"
    assert row["Record statement A"] != row["Record statement B"]
    assert "SRC-DEMO-001" in row["Sources A"] or "SRC-DEMO-001" in row["Sources B"]
    assert "SRC-DEMO-002" in row["Sources A"] or "SRC-DEMO-002" in row["Sources B"]
    assert row["Review status"] == "Human review required"
    assert row["Resolution state"] == "OPEN"
    assert "Independent third-party verification recommended" in row["Verification recommendation"]


def test_reconciliation_is_visible_but_client_context_is_not_treated_as_verified_resolution():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["reconciliations"] = {
        "REC-1": {
            "reconciliation_id": "REC-1",
            "proposition_ids": ["PROP-DEMO-001", "PROP-DEMO-002"],
            "contradiction_ids": ["CON-DEMO-001"],
            "outcome": "Reconciled",
            "actor": "usr-reviewer",
            "rationale": "Client provided missing context.",
        }
    }
    comparison = build_cross_record_comparison(manifest)[0]
    assert comparison["Review status"] == "Human review recorded"
    assert comparison["Resolution state"] == "EXPLAINED"
    assert comparison["Verification state"] == "RECOMMENDED"
    assert comparison["Record statement A"] != comparison["Record statement B"]

    issue = next(row for row in build_analytical_issues(manifest) if row["Issue"] == "CON-DEMO-001")
    assert issue["Resolution state"] == "EXPLAINED"
    assert issue["Reviewed by"] == "usr-reviewer"


def test_independently_verified_reconciliation_suppresses_redundant_referral():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["reconciliations"] = {
        "REC-1": {
            "reconciliation_id": "REC-1",
            "proposition_ids": ["PROP-DEMO-001", "PROP-DEMO-002"],
            "contradiction_ids": ["CON-DEMO-001"],
            "outcome": "Verified resolution",
            "actor": "usr-reviewer",
            "rationale": "Independent custodian confirmed the corrected amount.",
        }
    }
    comparison = build_cross_record_comparison(manifest)[0]
    assert comparison["Resolution state"] == "CORROBORATED_RESOLUTION"
    assert comparison["Verification state"] == "COMPLETE"
    assert comparison["Potential verifier"] == "—"


def test_control_manifest_and_json_pointer_propositions_never_enter_client_analysis():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["sources"]["SRC-CONTROL"] = {
        "source_id": "SRC-CONTROL",
        "content_hash": "hash-control",
        "metadata": {
            "filename": "colettios_synthetic_manifest.json",
            "classification": "Operational Audit",
        },
    }
    manifest["source_states"]["SRC-CONTROL"] = "INGESTED"
    manifest["propositions"]["PROP-CONTROL"] = {
        "proposition_id": "PROP-CONTROL",
        "text": '[$.sources.SRC-DEMO-001.content_hash] $.sources.SRC-DEMO-001.content_hash = "demo-hash-001"',
        "source_ids": ["SRC-CONTROL"],
    }
    manifest["contradictions"]["CON-CONTROL"] = {
        "contradiction_id": "CON-CONTROL",
        "proposition_a": "PROP-DEMO-002",
        "proposition_b": "PROP-CONTROL",
        "reason": "Should never appear in a client report",
    }

    assert build_summary(manifest)["sources"] == 2
    assert build_summary(manifest)["propositions"] == 2
    assert len(build_records_reconstruction(manifest)) == 2
    assert len(build_operations_reconstruction(manifest)) == 2
    assert len(build_cross_record_comparison(manifest)) == 1
    assert all("SRC-CONTROL" not in row.get("Supporting sources", "") for row in build_analytical_issues(manifest))


def test_reverse_duplicate_contradictions_collapse_to_one_canonical_issue():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["contradictions"]["CON-REVERSE"] = {
        "contradiction_id": "CON-REVERSE",
        "proposition_a": "PROP-DEMO-002",
        "proposition_b": "PROP-DEMO-001",
        "reason": "Duplicate reverse representation",
    }
    comparisons = build_cross_record_comparison(manifest)
    inconsistencies = [row for row in build_analytical_issues(manifest) if row["Classification"] == "Inconsistency"]
    assert len(comparisons) == 1
    assert len(inconsistencies) == 1
    assert "CON-DEMO-001" in comparisons[0]["Related comparison IDs"]
    assert "CON-REVERSE" in comparisons[0]["Related comparison IDs"]


def test_analytical_issues_use_boundary_safe_classifications_and_verification_routing():
    rows = build_analytical_issues(SYNTHETIC_MANIFEST)
    classifications = {row["Classification"] for row in rows}
    assert classifications == {"Inconsistency", "Unresolved Question"}
    assert all(row["Supporting sources"] for row in rows)
    assert all(row["Verification recommendation"] for row in rows)
    assert all(row["Potential verifier"] for row in rows)


def test_state_counts_are_operator_readable_and_exclude_control_sources():
    rows = build_state_counts(SYNTHETIC_MANIFEST)
    assert {row["Evidence state"] for row in rows} == {"CORROBORATED", "DISPUTED"}
