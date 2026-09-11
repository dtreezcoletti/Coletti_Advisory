from coletti_advisory.record_governance import (
    FIRST_TRUTH_NOTICE,
    FIRST_TRUTH_NOTICE_VERSION,
    FIRST_TRUTH_POLICY_KEY,
    FIRST_TRUTH_POLICY_VERSION,
    IDENTIFIED_PATTERN_DEFINITION,
    PROTECTED_PROFESSION_RULE,
    RECORD_STATES,
    DariTier,
    canonical_path,
    route_dari_command,
    valid_case_id,
    valid_client_id,
    valid_source_code,
)
from coletti_advisory.reporting import build_records_report
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


def test_canonical_record_states_include_identified_pattern():
    assert len(RECORD_STATES) == 10
    assert RECORD_STATES[-1] == "Identified Pattern"
    assert "two or more records or events" in IDENTIFIED_PATTERN_DEFINITION


def test_canonical_identifier_contract():
    assert valid_client_id("C26-92")
    assert valid_case_id("REC-260906-01")
    assert valid_source_code("SRB-001")
    assert canonical_path("C26-92", "REC-260906-01", "SRB-001") == "C26-92 / REC-260906-01 / SRB-001"
    assert not valid_client_id("client-1")
    assert not valid_case_id("case-1")
    assert not valid_source_code("SRC-001")


def test_dari_routes_no_ai_then_luna_terra_sol_and_blocks_protected_effect():
    assert route_dari_command("status", deterministic=True).tier is DariTier.NO_AI
    assert route_dari_command("draft a bounded record summary").tier is DariTier.LUNA
    assert route_dari_command("reconstruct the pattern across records").tier is DariTier.TERRA
    assert route_dari_command("deep synthesis across all records and all domains").tier is DariTier.SOL

    blocked = route_dari_command("determine the legal effect and liability")
    assert blocked.blocked is True
    assert blocked.referral_required is True
    assert blocked.tier is DariTier.NO_AI
    assert blocked.reason == PROTECTED_PROFESSION_RULE


def test_reports_embed_first_truth_v2_and_professional_firewall():
    report = build_records_report(dict(SYNTHETIC_MANIFEST))
    first_truth = report["first_truth"]
    assert first_truth["policy_key"] == FIRST_TRUTH_POLICY_KEY
    assert first_truth["policy_version"] == FIRST_TRUTH_POLICY_VERSION == "1.2"
    assert first_truth["notice_version"] == FIRST_TRUTH_NOTICE_VERSION == "2.0"
    assert first_truth["notice"] == FIRST_TRUTH_NOTICE
    assert first_truth["protected_profession_rule"] == PROTECTED_PROFESSION_RULE
    assert first_truth["record_states"] == list(RECORD_STATES)
    assert report["record_state_summary"] == report["evidence_state_summary"]
