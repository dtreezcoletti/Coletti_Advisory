import hashlib
import os

from coletti_advisory.storage import EncryptedLocalDemoStorage, gcs_bucket_security_errors


class _FakeIAM:
    def __init__(self, *, uniform: bool, public_access_prevention: str):
        self.uniform_bucket_level_access_enabled = uniform
        self.public_access_prevention = public_access_prevention


class _FakeBucket:
    def __init__(
        self,
        *,
        uniform: bool = True,
        public_access_prevention: str = "enforced",
        versioning_enabled: bool = True,
        reload_error: Exception | None = None,
    ):
        self.iam_configuration = _FakeIAM(
            uniform=uniform,
            public_access_prevention=public_access_prevention,
        )
        self.versioning_enabled = versioning_enabled
        self.reload_error = reload_error
        self.reload_calls = 0

    def reload(self, client=None):
        self.reload_calls += 1
        if self.reload_error:
            raise self.reload_error


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


def test_production_gcs_gate_accepts_required_bucket_controls():
    bucket = _FakeBucket()
    assert gcs_bucket_security_errors(bucket, client=object()) == []
    assert bucket.reload_calls == 1


def test_production_gcs_gate_rejects_public_or_nonversioned_bucket():
    bucket = _FakeBucket(
        uniform=False,
        public_access_prevention="inherited",
        versioning_enabled=False,
    )
    errors = gcs_bucket_security_errors(bucket)
    assert "GCS bucket must enforce uniform bucket-level access" in errors
    assert "GCS bucket must enforce public access prevention" in errors
    assert "GCS bucket versioning must be enabled for recovery and overwrite protection" in errors


def test_production_gcs_gate_fails_closed_when_bucket_cannot_be_inspected():
    bucket = _FakeBucket(reload_error=RuntimeError("permission denied"))
    assert gcs_bucket_security_errors(bucket) == [
        "GCS bucket could not be inspected with the configured service account"
    ]
