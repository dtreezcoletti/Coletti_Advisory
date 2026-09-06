from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class StoredObject:
    storage_uri: str
    content_hash: str
    encrypted: bool


@dataclass(frozen=True)
class StorageVerificationResult:
    status: str
    checks: dict[str, bool]
    evidence: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checks": dict(self.checks),
            "evidence": dict(self.evidence),
        }


class SecureStorage(Protocol):
    def put(self, *, organization_id: str, engagement_id: str, source_id: str, filename: str, data: bytes) -> StoredObject: ...


def _safe(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    if not cleaned:
        raise ValueError("Unsafe storage path component")
    return cleaned


def decode_master_key(value: str) -> bytes:
    raw = base64.urlsafe_b64decode(value.encode())
    if len(raw) != 32:
        raise ValueError("STORAGE_MASTER_KEY must decode to exactly 32 bytes")
    return raw


def encrypt_bytes(data: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, data, aad)
    return nonce + ciphertext


def decrypt_bytes(data: bytes, key: bytes, aad: bytes) -> bytes:
    if len(data) < 13:
        raise ValueError("Encrypted payload is too short")
    return AESGCM(key).decrypt(data[:12], data[12:], aad)


def gcs_bucket_security_errors(bucket, *, client=None) -> list[str]:
    """Return fail-closed production bucket errors without exposing credentials."""
    try:
        bucket.reload(client=client)
    except Exception:
        return ["GCS bucket could not be inspected with the configured service account"]

    errors: list[str] = []
    iam = getattr(bucket, "iam_configuration", None)
    if not bool(getattr(iam, "uniform_bucket_level_access_enabled", False)):
        errors.append("GCS bucket must enforce uniform bucket-level access")

    public_access_prevention = str(getattr(iam, "public_access_prevention", "") or "").lower()
    if public_access_prevention != "enforced":
        errors.append("GCS bucket must enforce public access prevention")

    if not bool(getattr(bucket, "versioning_enabled", False)):
        errors.append("GCS bucket versioning must be enabled for recovery and overwrite protection")

    return errors


def verify_gcs_storage_roundtrip(
    *,
    bucket,
    client,
    master_key: bytes,
    organization_id: str,
    engagement_id: str,
) -> StorageVerificationResult:
    """Exercise the live production bucket with synthetic bytes only.

    A PASS proves that the configured runtime can inspect the required bucket
    controls, write a client-side encrypted object, read it back, authenticate
    and decrypt it with the configured key, verify the plaintext SHA-256 and
    metadata, and remove the exact probe generation. It intentionally does not
    claim that authentication, Core persistence, reports, backups, or complete
    production E2E acceptance have passed.
    """

    source_id = f"SYS-STORAGE-PROBE-{uuid4().hex}"
    filename = "SYNTHETIC_PRODUCTION_STORAGE_PROBE.txt"
    payload = (
        b"COLETTI & CO. SYNTHETIC PRODUCTION STORAGE PROBE\n"
        b"No real client, legal, medical, financial, or identifying data.\n"
        + source_id.encode()
    )
    digest = hashlib.sha256(payload).hexdigest()
    object_name = "/".join(
        (
            _safe(organization_id),
            _safe(engagement_id),
            "__system_lab__",
            f"{_safe(source_id)}.blob",
        )
    )
    aad = f"{organization_id}|{engagement_id}|{source_id}|{filename}|{digest}".encode()
    encrypted = encrypt_bytes(payload, master_key, aad)
    blob = bucket.blob(object_name)

    checks: dict[str, bool] = {
        "bucket_security_controls": False,
        "encrypted_write": False,
        "encrypted_read": False,
        "plaintext_integrity": False,
        "integrity_metadata": False,
        "probe_cleanup": False,
    }
    evidence: dict[str, str] = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "bucket": str(getattr(bucket, "name", "")),
        "probe_object": object_name,
        "sha256_plaintext": digest,
    }

    uploaded_generation = None
    try:
        security_errors = gcs_bucket_security_errors(bucket, client=client)
        checks["bucket_security_controls"] = not security_errors
        if security_errors:
            evidence["bucket_gate"] = " | ".join(security_errors)
            return StorageVerificationResult("FAIL", checks, evidence)

        blob.cache_control = "no-store"
        blob.metadata = {
            "sha256_plaintext": digest,
            "organization_id": organization_id,
            "engagement_id": engagement_id,
            "source_id": source_id,
            "encryption": "AES-256-GCM-client-side",
            "probe": "system-lab-production-storage",
        }
        blob.upload_from_string(
            encrypted,
            content_type="application/octet-stream",
            if_generation_match=0,
        )
        checks["encrypted_write"] = True

        blob.reload(client=client)
        uploaded_generation = getattr(blob, "generation", None)
        stored_metadata = dict(getattr(blob, "metadata", {}) or {})
        checks["integrity_metadata"] = (
            stored_metadata.get("sha256_plaintext") == digest
            and stored_metadata.get("organization_id") == organization_id
            and stored_metadata.get("engagement_id") == engagement_id
            and stored_metadata.get("source_id") == source_id
            and stored_metadata.get("encryption") == "AES-256-GCM-client-side"
        )

        downloaded = blob.download_as_bytes()
        checks["encrypted_read"] = downloaded == encrypted and payload not in downloaded
        recovered = decrypt_bytes(downloaded, master_key, aad)
        checks["plaintext_integrity"] = (
            recovered == payload and hashlib.sha256(recovered).hexdigest() == digest
        )
    except Exception as exc:
        evidence["error_type"] = exc.__class__.__name__
    finally:
        if uploaded_generation is not None:
            try:
                generation_blob = bucket.blob(object_name, generation=uploaded_generation)
                generation_blob.delete(if_generation_match=int(uploaded_generation))
                checks["probe_cleanup"] = True
            except Exception as exc:
                evidence["cleanup_error_type"] = exc.__class__.__name__

    required = (
        "bucket_security_controls",
        "encrypted_write",
        "encrypted_read",
        "plaintext_integrity",
        "integrity_metadata",
        "probe_cleanup",
    )
    status = "PASS" if all(checks[name] for name in required) else "FAIL"
    return StorageVerificationResult(status, checks, evidence)


class EncryptedLocalDemoStorage:
    """Encrypted ephemeral storage for synthetic/demo use only."""

    def __init__(self, root: str | Path, master_key: bytes) -> None:
        self.root = Path(root)
        self.master_key = master_key

    def put(self, *, organization_id: str, engagement_id: str, source_id: str, filename: str, data: bytes) -> StoredObject:
        digest = hashlib.sha256(data).hexdigest()
        rel = Path(_safe(organization_id)) / _safe(engagement_id) / f"{_safe(source_id)}.blob"
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        aad = f"{organization_id}|{engagement_id}|{source_id}|{filename}|{digest}".encode()
        target.write_bytes(encrypt_bytes(data, self.master_key, aad))
        return StoredObject(storage_uri=f"local-demo://{rel.as_posix()}", content_hash=digest, encrypted=True)


class GoogleCloudEncryptedStorage:
    """Client-side AES-GCM encryption plus a fail-closed private GCS bucket."""

    def __init__(self, *, bucket_name: str, service_account_json: str, master_key: bytes) -> None:
        from google.cloud import storage
        from google.oauth2 import service_account

        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        self.client = storage.Client(project=info.get("project_id"), credentials=credentials)
        self.bucket = self.client.bucket(bucket_name)
        self.master_key = master_key

        errors = gcs_bucket_security_errors(self.bucket, client=self.client)
        if errors:
            raise RuntimeError("Production GCS security gate closed: " + " | ".join(errors))

    def put(self, *, organization_id: str, engagement_id: str, source_id: str, filename: str, data: bytes) -> StoredObject:
        digest = hashlib.sha256(data).hexdigest()
        object_name = "/".join((_safe(organization_id), _safe(engagement_id), f"{_safe(source_id)}.blob"))
        aad = f"{organization_id}|{engagement_id}|{source_id}|{filename}|{digest}".encode()
        encrypted = encrypt_bytes(data, self.master_key, aad)
        blob = self.bucket.blob(object_name)
        blob.cache_control = "no-store"
        blob.metadata = {
            "sha256_plaintext": digest,
            "organization_id": organization_id,
            "engagement_id": engagement_id,
            "source_id": source_id,
            "encryption": "AES-256-GCM-client-side",
        }
        blob.upload_from_string(
            encrypted,
            content_type="application/octet-stream",
            if_generation_match=0,
        )
        return StoredObject(storage_uri=f"gs://{self.bucket.name}/{object_name}", content_hash=digest, encrypted=True)

    def verify_operational(self, *, organization_id: str, engagement_id: str) -> StorageVerificationResult:
        return verify_gcs_storage_roundtrip(
            bucket=self.bucket,
            client=self.client,
            master_key=self.master_key,
            organization_id=organization_id,
            engagement_id=engagement_id,
        )
