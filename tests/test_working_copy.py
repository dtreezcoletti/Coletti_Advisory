import os

import pytest

from coletti_advisory.storage import EncryptedLocalDemoStorage
from coletti_advisory.working_copy import WorkingCopyUnavailable, read_source_for_working_copy


def _stored_source(tmp_path):
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    payload = b"synthetic source payload for ColettiOS working copy"
    stored = storage.put(
        organization_id="org-1",
        engagement_id="REC-260906-01",
        source_id="SRC-TEST-1",
        filename="record.txt",
        data=payload,
    )
    return storage, payload, stored


def test_working_copy_reads_and_verifies_encrypted_source(tmp_path):
    storage, payload, stored = _stored_source(tmp_path)

    recovered = read_source_for_working_copy(
        storage,
        organization_id="org-1",
        engagement_id="REC-260906-01",
        source_id="SRC-TEST-1",
        filename="record.txt",
        content_hash=stored.content_hash,
    )

    assert recovered == payload


def test_working_copy_fails_closed_on_wrong_digest(tmp_path):
    storage, _, _ = _stored_source(tmp_path)

    with pytest.raises(WorkingCopyUnavailable):
        read_source_for_working_copy(
            storage,
            organization_id="org-1",
            engagement_id="REC-260906-01",
            source_id="SRC-TEST-1",
            filename="record.txt",
            content_hash="0" * 64,
        )


def test_working_copy_fails_closed_on_wrong_case_scope(tmp_path):
    storage, _, stored = _stored_source(tmp_path)

    with pytest.raises(WorkingCopyUnavailable):
        read_source_for_working_copy(
            storage,
            organization_id="org-1",
            engagement_id="REC-260906-99",
            source_id="SRC-TEST-1",
            filename="record.txt",
            content_hash=stored.content_hash,
        )
