from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping


def validate_runtime(*, app_mode: str, storage_backend: str, core_backend: str, authenticated: bool) -> list[str]:
    errors: list[str] = []
    if app_mode == "production":
        if not authenticated:
            errors.append("Production mode requires authenticated identity")
        if storage_backend != "supabase":
            errors.append("Production mode requires durable encrypted Supabase Storage")
        if core_backend != "http":
            errors.append("Production mode requires the private ColettiOS service adapter")
    return errors


def validate_production_configuration(*, app_mode: str, config: Mapping[str, str]) -> list[str]:
    """Validate production secrets/config before constructing external backends.

    This is intentionally fail-closed. It validates presence and safe structure,
    but never logs or returns secret values. Split-plane cryptographic profile
    v1 is hard-pinned in the initial release; accepting a future profile is a
    code+test migration, not a configuration-only change.
    """
    if app_mode != "production":
        return []

    errors: list[str] = []

    supabase_url = str(config.get("SUPABASE_URL", "")).strip()
    if not supabase_url.startswith("https://"):
        errors.append("SUPABASE_URL must use HTTPS")

    supabase_key = str(config.get("SUPABASE_ANON_KEY", "")).strip()
    if not supabase_key:
        errors.append("SUPABASE_ANON_KEY is required")

    storage_bucket = str(config.get("SUPABASE_STORAGE_BUCKET", "")).strip()
    if not storage_bucket:
        errors.append("SUPABASE_STORAGE_BUCKET is required")

    master_key = str(config.get("STORAGE_MASTER_KEY", "")).strip()
    if not master_key:
        errors.append("STORAGE_MASTER_KEY is required")
    else:
        try:
            decoded = base64.urlsafe_b64decode(master_key.encode())
            if len(decoded) != 32:
                errors.append("STORAGE_MASTER_KEY must decode to exactly 32 bytes")
        except Exception:
            errors.append("STORAGE_MASTER_KEY is not valid URL-safe base64")

    key_version = str(config.get("STORAGE_KEY_VERSION", "v1")).strip() or "v1"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", key_version):
        errors.append("STORAGE_KEY_VERSION contains unsupported characters")
    elif key_version != "v1":
        errors.append("STORAGE_KEY_VERSION must be v1 for this release")

    core_url = str(config.get("COLETTIOS_API_URL", "")).strip()
    if not core_url:
        errors.append("COLETTIOS_API_URL is required")
    elif not core_url.startswith("https://"):
        errors.append("COLETTIOS_API_URL must use HTTPS")

    core_token = str(config.get("COLETTIOS_API_TOKEN", "")).strip()
    if not core_token:
        errors.append("COLETTIOS_API_TOKEN is required")

    ttl_raw = str(config.get("SESSION_TTL_MINUTES", "480")).strip()
    try:
        ttl = int(ttl_raw)
        if not 5 <= ttl <= 1440:
            errors.append("SESSION_TTL_MINUTES must be between 5 and 1440")
    except ValueError:
        errors.append("SESSION_TTL_MINUTES must be an integer")

    return errors


SECURITY_CONTROLS = [
    ("Canonical split-plane security architecture v2", True),
    ("Secrets excluded from Git", True),
    ("Audit actors exist in ColettiOS", True),
    ("Commercial repo owns authentication and encrypted client-data plane", True),
    ("ColettiOS owns provenance/audit control plane", True),
    ("Streamlit browser session separation", True),
    ("Real login via OIDC", True),
    ("Password verification delegated to identity provider", True),
    ("Signed OIDC identity processing delegated to Streamlit/Authlib", True),
    ("OIDC iat/exp token lifetime enforcement", True),
    ("Application session expiration", True),
    ("Re-authentication lifecycle", True),
    ("Logout and application authorization revocation", True),
    ("RBAC enforcement", True),
    ("Engagement-level authorization", True),
    ("Authenticated upload pipeline", True),
    ("AES-256-GCM encrypted storage implementation", True),
    ("HKDF-SHA256 scoped source-object data keys", True),
    ("Cryptographic profile v1 hard-pinned for initial release", True),
    ("Verified SHA-256 plaintext source hashing", True),
    ("Authenticated audit actor propagation", True),
    ("Production configuration preflight", True),
]
