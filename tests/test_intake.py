import hashlib
import os

from coletti_advisory.core_adapter import SyntheticCoreAdapter
from coletti_advisory.intake import ingest_file
from coletti_advisory.models import Principal, Role
from coletti_advisory.storage import EncryptedLocalDemoStorage


def test_synthetic_intake_path_encrypts_hashes_registers_and_audits(tmp_path):
    principal = Principal(
        "usr-owner",
        "owner@example.com",
        "Owner",
        "org-test",
        Role.OWNER,
        ("eng-test",),
        "session-test",
        "2026-09-05T00:00:00+00:00",
    )
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    core = SyntheticCoreAdapter()
    payload = b"synthetic intake acceptance payload"

    result = ingest_file(
        principal=principal,
        engagement_id="eng-test",
        filename="synthetic_probe.txt",
        data=payload,
        classification="Synthetic Diagnostic Record",
        storage=storage,
        core=core,
    )

    source_id = result["source"]["source_id"]
    manifest = core.manifest("eng-test")

    assert result["storage"]["encrypted"] is True
    assert result["storage"]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert source_id in manifest["sources"]
    assert manifest["sources"][source_id]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert manifest["sources"][source_id]["metadata"]["classification"] == "Synthetic Diagnostic Record"
    assert manifest["source_states"][source_id] == "INGESTED"

    matching_events = [
        event
        for event in manifest["audit_log"]
        if event.get("event_type") == "SOURCE_REGISTERED" and event.get("subject_id") == source_id
    ]
    assert len(matching_events) == 1
    event = matching_events[0]
    assert event["actor"] == principal.user_id
    assert event["session_id"] == principal.session_id
    assert event["organization_id"] == principal.organization_id
    assert event["engagement_id"] == "eng-test"
