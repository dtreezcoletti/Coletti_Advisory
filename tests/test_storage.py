import base64
import hashlib
import os

from coletti_advisory.storage import EncryptedLocalDemoStorage


def test_storage_encrypts_bytes_and_preserves_plaintext_hash(tmp_path):
    key = os.urandom(32)
    storage = EncryptedLocalDemoStorage(tmp_path, key)
    data = b"synthetic confidential payload"
    result = storage.put(
        organization_id="org-1",
        engagement_id="eng-1",
        source_id="SRC-1",
        filename="record.txt",
        data=data,
    )
    stored = (tmp_path / "org-1" / "eng-1" / "SRC-1.blob").read_bytes()
    assert data not in stored
    assert result.encrypted is True
    assert result.content_hash == hashlib.sha256(data).hexdigest()
