from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "infra" / "gcp" / "bootstrap_storage.sh"
VERIFY = ROOT / "infra" / "gcp" / "verify_storage.sh"
ROLE = ROOT / "infra" / "gcp" / "storage-runtime-role.yaml"


def test_bootstrap_requires_explicit_project_bucket_and_location():
    text = BOOTSTRAP.read_text()
    assert '${PROJECT_ID:?' in text
    assert '${BUCKET_NAME:?' in text
    assert '${BUCKET_LOCATION:?' in text


def test_bootstrap_enforces_required_bucket_controls_and_does_not_flip_production():
    text = BOOTSTRAP.read_text()
    assert "--uniform-bucket-level-access" in text
    assert "--public-access-prevention" in text
    assert "--versioning" in text
    assert 'APP_MODE="production"' not in text
    assert "export APP_MODE=production" not in text
    assert "CREATE_SERVICE_ACCOUNT_KEY" in text
    assert 'CREATE_SERVICE_ACCOUNT_KEY:-0' in text


def test_runtime_role_is_bucket_scoped_least_privilege_contract():
    text = ROLE.read_text()
    expected = {
        "storage.buckets.get",
        "storage.objects.create",
        "storage.objects.get",
        "storage.objects.list",
        "storage.objects.update",
        "storage.objects.delete",
    }
    permissions = {
        line.strip().removeprefix("- ")
        for line in text.splitlines()
        if line.strip().startswith("- ")
    }
    assert permissions == expected
    assert "storage.buckets.setIamPolicy" not in text
    assert "storage.buckets.update" not in text


def test_verifier_checks_security_controls_public_principals_and_runtime_binding():
    text = VERIFY.read_text()
    assert "uniform bucket-level access is not enabled" in text
    assert "public access prevention" in text
    assert "object versioning is not enabled" in text
    assert "allUsers" in text
    assert "allAuthenticatedUsers" in text
    assert "runtime service-account binding" in text
