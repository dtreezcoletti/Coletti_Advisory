from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from coletti_advisory.analysis import build_analytical_issues, build_operations_reconstruction
from coletti_advisory.commercial_config import DEFAULT_COMMERCIAL_CONFIG
from coletti_advisory.reporting import build_report_bundle
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


ROOT = Path(__file__).resolve().parents[1]


def _clinical_config():
    return replace(
        DEFAULT_COMMERCIAL_CONFIG,
        source_classifications=("Lab Result", "Authorization Record", "Encounter Note", "Other"),
        report_labels={
            "records": "Source Review",
            "operations": "Process Review",
            "findings": "Exception Summary",
        },
        report_purposes={
            "records": "Summarize source-linked clinical record statements and unresolved source questions.",
            "operations": "Summarize record-supported process activity and open follow-up.",
            "findings": "Summarize source-supported exceptions and unresolved review needs.",
        },
        report_boundaries={
            "records": "Source-linked review only; no clinical diagnosis is made.",
            "operations": "Process reconstruction only; no clinical diagnosis is made.",
            "findings": "Exception summary only; no clinical diagnosis is made.",
        },
        verification_targets_by_record_class={
            "Lab Result": "qualified clinical reviewer or originating laboratory",
            "Authorization Record": "authorization owner or originating custodian",
            "Encounter Note": "originating clinician or records custodian",
        },
        default_verification_target="appropriate source owner or qualified domain reviewer",
        escalation_review_roles=("Clinical Reviewer", "Program Owner"),
    )


def _clinical_manifest():
    manifest = deepcopy(SYNTHETIC_MANIFEST)
    manifest["sources"]["SRC-DEMO-001"]["metadata"] = {
        "filename": "synthetic_lab_result.csv",
        "classification": "Lab Result",
    }
    manifest["sources"]["SRC-DEMO-002"]["metadata"] = {
        "filename": "synthetic_authorization.pdf",
        "classification": "Authorization Record",
    }
    manifest["propositions"]["PROP-DEMO-001"]["text"] = "The laboratory source records value A."
    manifest["propositions"]["PROP-DEMO-002"]["text"] = "The authorization source records value B."
    manifest["contradictions"]["CON-DEMO-001"]["reason"] = "The two sources record different values."
    return manifest


def test_unrelated_domain_runs_through_analysis_and_reporting_without_builder_changes():
    config = _clinical_config()
    manifest = _clinical_manifest()

    issues = build_analytical_issues(manifest, config=config)
    assert issues
    assert any("qualified clinical reviewer" in row["Potential verifier"] for row in issues)

    operations = build_operations_reconstruction(manifest, config=config)
    assert {row["Record class"] for row in operations} == {"Lab Result", "Authorization Record"}

    bundle = build_report_bundle(manifest, config=config)
    assert set(bundle) == {"Source Review", "Process Review", "Exception Summary"}
    assert bundle["Source Review"]["boundary"] == "Source-linked review only; no clinical diagnosis is made."
    assert bundle["Exception Summary"]["report_type"] == "Exception Summary"


def test_domain_specific_source_classes_are_not_hardcoded_in_active_analysis_or_reporting_code():
    prohibited_literals = (
        '"Operational Audit"',
        '"Operational Record"',
        '"Business Record"',
        '"Financial Record"',
        '"Correspondence"',
    )
    for relative in (
        "coletti_advisory/analysis.py",
        "coletti_advisory/reporting.py",
        "coletti_advisory/app_shell.py",
    ):
        text = (ROOT / relative).read_text()
        for literal in prohibited_literals:
            assert literal not in text, f"{literal} leaked into {relative}; move it to commercial config or an adapter"


def test_report_names_are_configuration_owned_not_reporting_builder_literals():
    text = (ROOT / "coletti_advisory/reporting.py").read_text()
    for label in (
        "Records Reconstruction Report",
        "Operations Reconstruction Report",
        "Findings Report",
    ):
        assert label not in text


def test_risk_taxonomy_is_separate_from_evidence_state_policy():
    assert set(DEFAULT_COMMERCIAL_CONFIG.risk_taxonomy) == {
        "CRITICAL",
        "HIGH",
        "MODERATE",
        "LOW",
        "CLEAR",
    }
    assert "CORROBORATED" not in DEFAULT_COMMERCIAL_CONFIG.risk_taxonomy
    assert DEFAULT_COMMERCIAL_CONFIG.corroborated_state == "CORROBORATED"
