from coletti_advisory.core_adapter import SyntheticCoreAdapter
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


AUTH = {
    "user_id": "usr-1",
    "organization_id": "org-1",
    "engagement_id": "eng-synthetic-demo",
    "role": "owner",
    "session_id": "sess-1",
    "authenticated_at": "now",
}


def test_source_registration_records_authenticated_actor_context():
    adapter = SyntheticCoreAdapter()
    adapter.register_source(
        {"source_id": "SRC-NEW", "content_hash": "abc", "metadata": {}}, AUTH
    )
    event = adapter.manifest("eng-synthetic-demo")["audit_log"][-1]
    assert event["actor"] == "usr-1"
    assert event["session_id"] == "sess-1"
    assert event["engagement_id"] == "eng-synthetic-demo"


def test_proposition_contradiction_and_reconciliation_are_explicit_and_audited():
    adapter = SyntheticCoreAdapter()
    adapter.register_source({"source_id": "SRC-A", "content_hash": "a", "metadata": {}}, AUTH)
    adapter.register_source({"source_id": "SRC-B", "content_hash": "b", "metadata": {}}, AUTH)

    adapter.add_proposition(
        {"proposition_id": "PROP-A", "text": "Record A says 100", "source_ids": ["SRC-A"]},
        AUTH,
    )
    adapter.add_proposition(
        {"proposition_id": "PROP-B", "text": "Record B says 120", "source_ids": ["SRC-B"]},
        AUTH,
    )
    adapter.record_contradiction(
        {
            "contradiction_id": "CON-A",
            "proposition_a": "PROP-A",
            "proposition_b": "PROP-B",
            "reason": "The amounts differ",
        },
        AUTH,
    )
    adapter.record_reconciliation(
        {
            "reconciliation_id": "REC-A",
            "proposition_ids": ["PROP-A", "PROP-B"],
            "contradiction_ids": ["CON-A"],
            "outcome": "Variance remains unresolved",
            "rationale": "Neither source is silently promoted over the other.",
        },
        AUTH,
    )

    manifest = adapter.manifest("eng-synthetic-demo")
    assert manifest["propositions"]["PROP-A"]["source_ids"] == ["SRC-A"]
    assert manifest["contradictions"]["CON-A"]["proposition_b"] == "PROP-B"
    assert manifest["reconciliations"]["REC-A"]["actor"] == "usr-1"
    assert [event["event_type"] for event in manifest["audit_log"][-4:]] == [
        "PROPOSITION_ADDED",
        "PROPOSITION_ADDED",
        "CONTRADICTION_RECORDED",
        "RECONCILIATION_RECORDED",
    ]


def test_reset_demo_data_restores_canonical_synthetic_manifest():
    adapter = SyntheticCoreAdapter()
    adapter.register_source(
        {"source_id": "SRC-TEMP", "content_hash": "temporary", "metadata": {}}, AUTH
    )
    assert "SRC-TEMP" in adapter.manifest("eng-synthetic-demo")["sources"]

    adapter.reset_demo_data()
    manifest = adapter.manifest("eng-synthetic-demo")

    assert "SRC-TEMP" not in manifest["sources"]
    assert manifest["sources"] == SYNTHETIC_MANIFEST["sources"]
    assert manifest["propositions"] == SYNTHETIC_MANIFEST["propositions"]
    assert manifest["contradictions"] == SYNTHETIC_MANIFEST["contradictions"]
