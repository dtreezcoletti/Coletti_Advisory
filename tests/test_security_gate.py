from coletti_advisory.security import validate_runtime


def test_production_fails_closed_without_real_backends():
    errors = validate_runtime(
        app_mode="production",
        storage_backend="local_demo",
        core_backend="synthetic",
        authenticated=False,
    )
    assert len(errors) == 3


def test_production_gate_passes_with_auth_gcs_and_private_core_adapter():
    assert validate_runtime(
        app_mode="production",
        storage_backend="gcs",
        core_backend="http",
        authenticated=True,
    ) == []
