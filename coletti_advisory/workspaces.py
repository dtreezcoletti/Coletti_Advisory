from __future__ import annotations

from .synthetic import SYNTHETIC_ENGAGEMENT


LIVE_WORKSPACE_ID = "eng-coletti-co-live"
LIVE_WORKSPACE_NAME = "Coletti & Co. Live"


def workspace_label(engagement_id: str) -> str:
    if engagement_id == SYNTHETIC_ENGAGEMENT["engagement_id"]:
        return SYNTHETIC_ENGAGEMENT["name"]
    if engagement_id == LIVE_WORKSPACE_ID:
        return LIVE_WORKSPACE_NAME
    return engagement_id


def workspace_environment(engagement_id: str) -> str:
    if engagement_id == SYNTHETIC_ENGAGEMENT["engagement_id"]:
        return "DEMO"
    if engagement_id == LIVE_WORKSPACE_ID:
        return "LIVE"
    return "ENGAGEMENT"


def live_workspace_gate_errors(
    engagement_id: str,
    *,
    app_mode: str,
    storage_backend: str,
    core_backend: str,
    authenticated: bool,
) -> list[str]:
    if engagement_id != LIVE_WORKSPACE_ID:
        return []

    errors: list[str] = []
    if not authenticated:
        errors.append("Live workspace requires an authenticated identity.")
    if app_mode != "production":
        errors.append("Live workspace requires APP_MODE=production.")
    if storage_backend != "gcs":
        errors.append("Live workspace requires the durable encrypted GCS storage backend.")
    if core_backend != "http":
        errors.append("Live workspace requires the private authenticated ColettiOS HTTP service.")
    return errors
