from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .storage import (
    DEFAULT_STORAGE_KEY_VERSION,
    EncryptedLocalDemoStorage,
    GoogleCloudEncryptedStorage,
    _safe,
    decrypt_bytes,
    derive_scoped_key,
    source_aad,
)


class WorkingCopyUnavailable(RuntimeError):
    """Raised when an authorized workspace copy cannot be reconstructed safely."""


def _verify_digest(data: bytes, expected_digest: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_digest:
        raise WorkingCopyUnavailable("Source integrity verification failed; working copy was not opened.")


def _decrypt_source_payload(
    encrypted: bytes,
    *,
    storage: Any,
    organization_id: str,
    engagement_id: str,
    source_id: str,
    filename: str,
    content_hash: str,
) -> bytes:
    key_version = str(getattr(storage, "key_version", DEFAULT_STORAGE_KEY_VERSION))
    data_key = derive_scoped_key(
        storage.master_key,
        purpose="source-object",
        organization_id=organization_id,
        engagement_id=engagement_id,
        object_id=source_id,
        key_version=key_version,
    )
    aad = source_aad(
        organization_id=organization_id,
        engagement_id=engagement_id,
        source_id=source_id,
        filename=filename,
        digest=content_hash,
        key_version=key_version,
    )
    try:
        plaintext = decrypt_bytes(encrypted, data_key, aad)
    except Exception as exc:
        raise WorkingCopyUnavailable("Source decryption/authentication failed; working copy was not opened.") from exc
    _verify_digest(plaintext, content_hash)
    return plaintext


def read_source_for_working_copy(
    storage: Any,
    *,
    organization_id: str,
    engagement_id: str,
    source_id: str,
    filename: str,
    content_hash: str,
) -> bytes:
    """Read an immutable encrypted source into a transient, integrity-checked workspace copy.

    This function never modifies the authoritative object and never persists decrypted
    bytes. The caller is responsible for enforcing the user's engagement permission
    before invoking it.
    """
    if not content_hash:
        raise WorkingCopyUnavailable("The source record has no content hash, so a verified working copy cannot be created.")

    if isinstance(storage, EncryptedLocalDemoStorage):
        target = (
            Path(storage.root)
            / _safe(organization_id)
            / _safe(engagement_id)
            / f"{_safe(source_id)}.blob"
        )
        try:
            encrypted = target.read_bytes()
        except OSError as exc:
            raise WorkingCopyUnavailable("The encrypted source object is unavailable in local workspace storage.") from exc
        return _decrypt_source_payload(
            encrypted,
            storage=storage,
            organization_id=organization_id,
            engagement_id=engagement_id,
            source_id=source_id,
            filename=filename,
            content_hash=content_hash,
        )

    if isinstance(storage, GoogleCloudEncryptedStorage):
        object_name = "/".join(
            (_safe(organization_id), _safe(engagement_id), f"{_safe(source_id)}.blob")
        )
        blob = storage.bucket.blob(object_name)
        try:
            blob.reload(client=storage.client)
            metadata = dict(getattr(blob, "metadata", {}) or {})
        except Exception as exc:
            raise WorkingCopyUnavailable("The encrypted source object could not be read from protected storage.") from exc

        expected = {
            "sha256_plaintext": content_hash,
            "organization_id": organization_id,
            "engagement_id": engagement_id,
            "source_id": source_id,
            "key_version": str(getattr(storage, "key_version", DEFAULT_STORAGE_KEY_VERSION)),
        }
        if any(str(metadata.get(key) or "") != str(value) for key, value in expected.items()):
            raise WorkingCopyUnavailable("Protected storage metadata does not match the requested source scope.")

        try:
            encrypted = blob.download_as_bytes()
        except Exception as exc:
            raise WorkingCopyUnavailable("The encrypted source payload could not be downloaded from protected storage.") from exc
        return _decrypt_source_payload(
            encrypted,
            storage=storage,
            organization_id=organization_id,
            engagement_id=engagement_id,
            source_id=source_id,
            filename=filename,
            content_hash=content_hash,
        )

    reader = getattr(storage, "get", None)
    if callable(reader):
        try:
            data = reader(
                organization_id=organization_id,
                engagement_id=engagement_id,
                source_id=source_id,
                filename=filename,
                content_hash=content_hash,
            )
        except Exception as exc:
            raise WorkingCopyUnavailable("The configured storage reader could not open this source.") from exc
        if not isinstance(data, (bytes, bytearray)):
            raise WorkingCopyUnavailable("The configured storage reader returned an invalid source payload.")
        payload = bytes(data)
        _verify_digest(payload, content_hash)
        return payload

    raise WorkingCopyUnavailable("This storage backend does not expose a controlled source-read capability yet.")
