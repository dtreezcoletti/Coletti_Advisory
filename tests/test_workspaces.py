from coletti_advisory.workspaces import (
    LIVE_WORKSPACE_ID,
    live_workspace_gate_errors,
    workspace_environment,
    workspace_label,
)


def test_live_workspace_has_stable_operator_label():
    assert LIVE_WORKSPACE_ID == "eng-coletti-co-live"
    assert workspace_label(LIVE_WORKSPACE_ID) == "Coletti & Co. Live"
    assert workspace_environment(LIVE_WORKSPACE_ID) == "LIVE"


def test_live_workspace_fails_closed_outside_production():
    errors = live_workspace_gate_errors(
        LIVE_WORKSPACE_ID,
        app_mode="demo",
        storage_backend="local_demo",
        core_backend="synthetic",
        authenticated=False,
    )
    assert "Live workspace requires an authenticated identity." in errors
    assert "Live workspace requires APP_MODE=production." in errors
    assert "Live workspace requires the durable encrypted GCS storage backend." in errors
    assert "Live workspace requires the private authenticated ColettiOS HTTP service." in errors


def test_live_workspace_opens_only_for_production_runtime():
    assert live_workspace_gate_errors(
        LIVE_WORKSPACE_ID,
        app_mode="production",
        storage_backend="gcs",
        core_backend="http",
        authenticated=True,
    ) == []


def test_non_live_engagement_is_not_subject_to_live_gate():
    assert live_workspace_gate_errors(
        "eng-client-001",
        app_mode="demo",
        storage_backend="local_demo",
        core_backend="synthetic",
        authenticated=False,
    ) == []
