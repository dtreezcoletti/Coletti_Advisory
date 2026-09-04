from __future__ import annotations


def validate_runtime(*, app_mode: str, storage_backend: str, core_backend: str, authenticated: bool) -> list[str]:
    errors: list[str] = []
    if app_mode == "production":
        if not authenticated:
            errors.append("Production mode requires authenticated identity")
        if storage_backend != "gcs":
            errors.append("Production mode requires durable encrypted GCS storage")
        if core_backend != "http":
            errors.append("Production mode requires the private ColettiOS service adapter")
    return errors


SECURITY_CONTROLS = [
    ("Secrets excluded from Git", True),
    ("Audit actors exist in ColettiOS", True),
    ("Commercial repo owns authentication", True),
    ("Streamlit browser session separation", True),
    ("Real login via OIDC", True),
    ("Password verification delegated to identity provider", True),
    ("Signed identity/session validation via OIDC", True),
    ("Application session expiration", True),
    ("Re-authentication lifecycle", True),
    ("Logout", True),
    ("RBAC enforcement", True),
    ("Engagement-level authorization", True),
    ("Authenticated upload pipeline", True),
    ("AES-256-GCM encrypted storage implementation", True),
    ("Verified SHA-256 file hashing", True),
    ("Authenticated audit actor propagation", True),
]
