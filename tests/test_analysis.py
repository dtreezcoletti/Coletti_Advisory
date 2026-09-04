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
    assert corroborated["Review status"] == "Corroborated"
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
    assert "SRC-DEMO-001" in row["Sources A"]
    assert "SRC-DEMO-002" in row["Sources B"]
    assert row["Review status"] == "Requires review"
    assert "Independent third-party verification recommended" in row["Verification recommendation"]
    assert "professional" in row["Verification recommendation"].lower()
    assert row["Potential verifier"]


def test_analytical_issues_use_boundary_safe_classifications_and_verification_routing():
    rows = build_analytical_issues(SYNTHETIC_MANIFEST)
    classifications = {row["Classification"] for row in rows}
    assert classifications == {"Inconsistency", "Unresolved Question"}
    assert all(row["Supporting sources"] for row in rows)
    assert all(row["Verification recommendation"] for row in rows)
    assert all(row["Potential verifier"] for row in rows)
    assert any("record custodian" in row["Potential verifier"] for row in rows)
    assert any("professional" in row["Potential verifier"] for row in rows)


def test_state_counts_are_operator_readable():
    rows = build_state_counts(SYNTHETIC_MANIFEST)
    assert {row["Evidence state"] for row in rows} == {"CORROBORATED", "DISPUTED"}
