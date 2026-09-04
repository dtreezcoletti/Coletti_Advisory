from coletti_advisory.core_adapter import SyntheticCoreAdapter


def test_source_registration_records_authenticated_actor_context():
    adapter = SyntheticCoreAdapter()
    auth = {
        "user_id": "usr-1",
        "organization_id": "org-1",
        "engagement_id": "eng-synthetic-demo",
        "role": "owner",
        "session_id": "sess-1",
        "authenticated_at": "now",
    }
    adapter.register_source(
        {"source_id": "SRC-NEW", "content_hash": "abc", "metadata": {}}, auth
    )
    event = adapter.manifest("eng-synthetic-demo")["audit_log"][-1]
    assert event["actor"] == "usr-1"
    assert event["session_id"] == "sess-1"
    assert event["engagement_id"] == "eng-synthetic-demo"
