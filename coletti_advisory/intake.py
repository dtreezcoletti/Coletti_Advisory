from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

from .core_adapter import CoreAdapter
from .models import Permission, Principal
from .storage import SecureStorage


def ingest_file(
    *,
    principal: Principal,
    engagement_id: str,
    filename: str,
    data: bytes,
    classification: str,
    storage: SecureStorage,
    core: CoreAdapter,
) -> dict:
    if not principal.can(Permission.UPLOAD):
        raise PermissionError("Role is not permitted to upload sources")
    if not principal.can_access(engagement_id):
        raise PermissionError("Principal is not authorized for this engagement")
    if not data:
        raise ValueError("Cannot ingest an empty file")

    source_id = f"SRC-{uuid4().hex[:12].upper()}"
    stored = storage.put(
        organization_id=principal.organization_id,
        engagement_id=engagement_id,
        source_id=source_id,
        filename=filename,
        data=data,
    )
    source = core.register_source(
        {
            "source_id": source_id,
            "content_hash": stored.content_hash,
            "metadata": {
                "filename": filename,
                "classification": classification,
                "storage_uri": stored.storage_uri,
                "encrypted": stored.encrypted,
            },
        },
        principal.auth_context(engagement_id),
    )
    return {"source": source, "storage": asdict(stored)}
