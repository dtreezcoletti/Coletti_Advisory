from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class StoredObject:
    storage_uri: str
    content_hash: str
    encrypted: bool


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
