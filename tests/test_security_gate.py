import base64

from coletti_advisory.security import validate_production_configuration, validate_runtime


def test_production_fails_closed_without_real_backends():
    errors = validate_runtime(
        app_mode="production",
        storage_backend="local_demo",
        core_backend="synthetic",
        authenticated=False,
    )
    assert len(errors) == 3


def test_production_gate_passes_with_auth_supabase_and_private_core_adapter():
    assert validate_runtime(
        app_mode="production",
        storage_backend="supabase",
        core_backend="http",
        authenticated=True,
    ) == []


def valid_production_config() -> dict[str, str]:
    return {
        "SUPABASE_URL": "https://project-ref.supabase.co",
        "SUPABASE_ANON_KEY": "synthetic-publishable-key",
        "SUPABASE_STORAGE_BUCKET": "client-documents",
        "STORAGE_MASTER_KEY": base64.urlsafe_b64encode(b"x" * 32).decode(),
        "STORAGE_KEY_VERSION": "v1",
        "COLETTIOS_API_URL": "https://core.example.invalid",
        "COLETTIOS_API_TOKEN": "synthetic-test-token",
        "SESSION_TTL_MINUTES": "480",
    }


def test_production_configuration_preflight_accepts_complete_configuration():
    assert validate_production_configuration(
        app_mode="production",
        config=valid_production_config(),
    ) == []


def test_production_configuration_preflight_defaults_to_initial_v1_profile():
    config = valid_production_config()
    config.pop("STORAGE_KEY_VERSION")
    assert validate_production_configuration(app_mode="production", config=config) == []


def test_production_configuration_preflight_rejects_missing_secrets():
    errors = validate_production_configuration(app_mode="production", config={})
    assert "SUPABASE_URL must use HTTPS" in errors
    assert "SUPABASE_ANON_KEY is required" in errors
    assert "SUPABASE_STORAGE_BUCKET is required" in errors
    assert "STORAGE_MASTER_KEY is required" in errors
    assert "COLETTIOS_API_URL is required" in errors
    assert "COLETTIOS_API_TOKEN is required" in errors


def test_production_configuration_preflight_rejects_insecure_supabase_url():
    config = valid_production_config()
    config["SUPABASE_URL"] = "http://project-ref.supabase.co"
    errors = validate_production_configuration(app_mode="production", config=config)
    assert "SUPABASE_URL must use HTTPS" in errors


def test_production_configuration_preflight_rejects_insecure_core_url():
    config = valid_production_config()
    config["COLETTIOS_API_URL"] = "http://core.example.invalid"
    errors = validate_production_configuration(app_mode="production", config=config)
    assert "COLETTIOS_API_URL must use HTTPS" in errors


def test_production_configuration_preflight_rejects_invalid_key_version():
    config = valid_production_config()
    config["STORAGE_KEY_VERSION"] = "v1 unsafe"
    errors = validate_production_configuration(app_mode="production", config=config)
    assert "STORAGE_KEY_VERSION contains unsupported characters" in errors


def test_production_configuration_preflight_rejects_unwired_future_key_version():
    config = valid_production_config()
    config["STORAGE_KEY_VERSION"] = "v2"
    errors = validate_production_configuration(app_mode="production", config=config)
    assert "STORAGE_KEY_VERSION must be v1 for this release" in errors


def test_demo_mode_does_not_require_production_secrets():
    assert validate_production_configuration(app_mode="demo", config={}) == []
