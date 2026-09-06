import hashlib
import os

from coletti_advisory.storage import (
    EncryptedLocalDemoStorage,
    decrypt_bytes,
    encrypt_bytes,
    gcs_bucket_security_errors,
    verify_gcs_storage_roundtrip,
)


class _FakeIAM:
    def __init__(self, *, uniform: bool, public_access_prevention: str):
        self.uniform_bucket_level_access_enabled = uniform
        self.public_access_prevention = public_access_prevention


class _FakeBlob:
    def __init__(self, bucket, name: str, generation=None):
        self.bucket = bucket
        self.name = name
        self.generation = generation
        self.metadata = {}
        self.cache_control = None

    def upload_from_string(self, data, *, content_type, if_generation_match):
        assert content_type == "application/octet-stream"
        assert if_generation_match == 0
        if self.name in self.bucket.objects:
            raise RuntimeError("object already exists")
        self.generation = self.bucket.next_generation
        self.bucket.next_generation += 1
        self.bucket.objects[self.name] = {
            "data": bytes(data),
            "metadata": dict(self.metadata),
            "generation": self.generation,
        }
        self.bucket.uploaded_history.append(bytes(data))

    def reload(self, client=None):
        record = self.bucket.objects[self.name]
        self.metadata = dict(record["metadata"])
        self.generation = record["generation"]

    def download_as_bytes(self):
        return self.bucket.objects[self.name]["data"]

    def delete(self, *, if_generation_match):
        record = self.bucket.objects[self.name]
        assert int(record["generation"]) == int(if_generation_match)
        del self.bucket.objects[self.name]


class _FakeBucket:
    def __init__(
        self,
        *,
        uniform: bool = True,
        public_access_prevention: str = "enforced",
        versioning_enabled: bool = True,
        reload_error: Exception | None = None,
    ):
        self.name = "synthetic-production-bucket"
        self.iam_configuration = _FakeIAM(
            uniform=uniform,
            public_access_prevention=public_access_prevention,
        )
        self.versioning_enabled = versioning_enabled
        self.reload_error = reload_error
        self.reload_calls = 0
        self.objects = {}
        self.uploaded_history = []
        self.next_generation = 1

    def reload(self, client=None):
        self.reload_calls += 1
        if self.reload_error:
            raise self.reload_error

    def blob(self, name: str, generation=None):
        return _FakeBlob(self, name, generation=generation)


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


def test_encrypt_decrypt_roundtrip_authenticates_aad():
    key = os.urandom(32)
    payload = b"synthetic payload"
    aad = b"org|eng|source|file|hash"
    encrypted = encrypt_bytes(payload, key, aad)
    assert payload not in encrypted
    assert decrypt_bytes(encrypted, key, aad) == payload


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


def test_live_storage_roundtrip_verifies_encryption_integrity_metadata_and_cleanup():
    bucket = _FakeBucket()
    key = os.urandom(32)
    result = verify_gcs_storage_roundtrip(
        bucket=bucket,
        client=object(),
        master_key=key,
        organization_id="org-production-test",
        engagement_id="eng-production-test",
    )

    assert result.status == "PASS"
    assert all(result.checks.values())
    assert result.evidence["bucket"] == bucket.name
    assert result.evidence["probe_object"].startswith(
        "org-production-test/eng-production-test/__system_lab__/"
    )
    assert len(result.evidence["sha256_plaintext"]) == 64
    assert bucket.objects == {}
    assert len(bucket.uploaded_history) == 1
    assert b"COLETTI & CO. SYNTHETIC PRODUCTION STORAGE PROBE" not in bucket.uploaded_history[0]


def test_live_storage_roundtrip_fails_closed_before_write_when_bucket_controls_fail():
    bucket = _FakeBucket(public_access_prevention="inherited")
    result = verify_gcs_storage_roundtrip(
        bucket=bucket,
        client=object(),
        master_key=os.urandom(32),
        organization_id="org-production-test",
        engagement_id="eng-production-test",
    )

    assert result.status == "FAIL"
    assert result.checks["bucket_security_controls"] is False
    assert result.checks["encrypted_write"] is False
    assert bucket.uploaded_history == []
