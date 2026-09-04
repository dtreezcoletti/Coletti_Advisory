import os

import pytest

from coletti_advisory.publication import (
    EncryptedLocalPublicationStore,
    PublicationStatus,
    approve_report,
    publish_report,
    published_reports,
    revoke_report,
    send_to_review,
    sync_drafts,
)
from coletti_advisory.reporting import build_report_bundle
from coletti_advisory.synthetic import SYNTHETIC_MANIFEST


ORG = "org-demo"
ENGAGEMENT = "eng-synthetic-demo"


def _bundle():
    return build_report_bundle(SYNTHETIC_MANIFEST)


def test_publication_state_persists_encrypted(tmp_path):
    key = os.urandom(32)
    store = EncryptedLocalPublicationStore(tmp_path, key)
    bundle = _bundle()
    records = sync_drafts({}, bundle)

    report_name = next(iter(bundle))
    send_to_review(records[report_name], actor="reviewer-1", note="Reviewed source links")
    store.save(organization_id=ORG, engagement_id=ENGAGEMENT, records=records)

    state_path = tmp_path / ORG / ENGAGEMENT / "publication-state.enc"
    payload = state_path.read_bytes()
    assert report_name.encode() not in payload

    loaded = store.load(organization_id=ORG, engagement_id=ENGAGEMENT)
    assert loaded[report_name].status == PublicationStatus.IN_REVIEW
    assert loaded[report_name].review_note == "Reviewed source links"


def test_demo_store_resets_if_old_session_key_cannot_decrypt(tmp_path):
    first_store = EncryptedLocalPublicationStore(tmp_path, os.urandom(32))
    records = sync_drafts({}, _bundle())
    first_store.save(organization_id=ORG, engagement_id=ENGAGEMENT, records=records)

    restarted_store = EncryptedLocalPublicationStore(tmp_path, os.urandom(32))
    assert restarted_store.load(organization_id=ORG, engagement_id=ENGAGEMENT) == {}


def test_report_requires_review_then_approval_before_publish():
    bundle = _bundle()
    records = sync_drafts({}, bundle)
    report_name, report = next(iter(bundle.items()))
    record = records[report_name]

    with pytest.raises(ValueError):
        publish_report(record, actor="owner", report=report)

    send_to_review(record, actor="owner")
    approve_report(record, actor="owner")
    publish_report(record, actor="owner", report=report)

    assert record.status == PublicationStatus.PUBLISHED
    assert record.published_snapshot["document_status"] == "PUBLISHED"
    assert record.published_snapshot["publication"]["revision"] == 1
    assert report_name in published_reports(records)


def test_new_draft_preserves_last_published_client_snapshot():
    bundle = _bundle()
    records = sync_drafts({}, bundle)
    report_name, report = next(iter(bundle.items()))
    record = records[report_name]

    send_to_review(record, actor="owner")
    approve_report(record, actor="owner")
    publish_report(record, actor="owner", report=report)
    first_snapshot = record.published_snapshot.copy()

    changed_bundle = _bundle()
    changed_bundle[report_name] = dict(changed_bundle[report_name])
    changed_bundle[report_name]["purpose"] = changed_bundle[report_name]["purpose"] + " Updated draft."
    sync_drafts(records, changed_bundle)

    assert record.status == PublicationStatus.DRAFT
    assert record.revision == 2
    assert record.published_snapshot == first_snapshot
    assert published_reports(records)[report_name] == first_snapshot


def test_changed_draft_requires_fresh_review_and_approval():
    bundle = _bundle()
    records = sync_drafts({}, bundle)
    report_name, report = next(iter(bundle.items()))
    record = records[report_name]

    send_to_review(record, actor="owner")
    approve_report(record, actor="owner")

    changed_report = dict(report)
    changed_report["purpose"] = changed_report["purpose"] + " Changed after approval."
    with pytest.raises(ValueError, match="Approved draft changed"):
        publish_report(record, actor="owner", report=changed_report)


def test_revocation_removes_client_visibility_but_preserves_snapshot():
    bundle = _bundle()
    records = sync_drafts({}, bundle)
    report_name, report = next(iter(bundle.items()))
    record = records[report_name]

    send_to_review(record, actor="owner")
    approve_report(record, actor="owner")
    publish_report(record, actor="owner", report=report)
    revoke_report(record, actor="owner")

    assert record.status == PublicationStatus.REVOKED
    assert record.published_snapshot is not None
    assert report_name not in published_reports(records)


def test_revoked_snapshot_stays_hidden_when_new_draft_is_generated():
    bundle = _bundle()
    records = sync_drafts({}, bundle)
    report_name, report = next(iter(bundle.items()))
    record = records[report_name]

    send_to_review(record, actor="owner")
    approve_report(record, actor="owner")
    publish_report(record, actor="owner", report=report)
    revoke_report(record, actor="owner")

    changed_bundle = _bundle()
    changed_bundle[report_name] = dict(changed_bundle[report_name])
    changed_bundle[report_name]["purpose"] = changed_bundle[report_name]["purpose"] + " New post-revocation draft."
    sync_drafts(records, changed_bundle)

    assert record.status == PublicationStatus.DRAFT
    assert record.revoked_at is not None
    assert report_name not in published_reports(records)
