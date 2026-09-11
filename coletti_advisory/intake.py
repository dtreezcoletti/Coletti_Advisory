from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping
from uuid import uuid4

from . import supabase_auth
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
    metadata: Mapping[str, Any] | None = None,
    source_type_code: str = "D",
    source_id: str | None = None,
) -> dict:
    if not principal.can(Permission.UPLOAD):
        raise PermissionError("Role is not permitted to upload records")
    if not principal.can_access(engagement_id):
        raise PermissionError("Principal is not authorized for this case")
    if not data:
        raise ValueError("Cannot ingest an empty file")

    if source_id is not None:
        source_id = str(source_id).strip().upper()
    elif principal.authenticated and supabase_auth.configured():
        source_id = supabase_auth.allocate_source_id(engagement_id, source_type_code)
    else:
        # Compatibility-only fallback for synthetic/demo or legacy OIDC runtime.
        source_id = f"SRC-{uuid4().hex[:12].upper()}"

    stored = storage.put(
        organization_id=principal.organization_id,
        engagement_id=engagement_id,
        source_id=source_id,
        filename=filename,
        data=data,
    )
    source_metadata = {
        "filename": filename,
        "classification": classification,
        "storage_uri": stored.storage_uri,
        "encrypted": stored.encrypted,
        "source_type_code": str(source_type_code).strip().upper(),
    }
    if metadata:
        for key, value in dict(metadata).items():
            if key in {"filename", "classification", "storage_uri", "encrypted"}:
                continue
            source_metadata[key] = value

    source = core.register_source(
        {
            "source_id": source_id,
            "content_hash": stored.content_hash,
            "metadata": source_metadata,
        },
        principal.auth_context(engagement_id),
    )
    return {"source": source, "storage": asdict(stored)}
