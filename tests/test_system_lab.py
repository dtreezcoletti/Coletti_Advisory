from coletti_advisory.app_shell import _workspace_pages
from coletti_advisory.models import Principal, Role
from coletti_advisory.system_lab import (
    PRODUCTION_READINESS_CAVEAT,
    SYSTEM_LAB_SECTIONS,
    _live_gate_label,
    _overall_production_readiness,
    _production_readiness_rows,
    _short_sha,
    can_access_system_lab,
)


def _principal(role: Role) -> Principal:
    return Principal(
        "usr-test",
        "test@example.com",
        "Test User",
        "org-test",
        role,
        ("eng-test",),
        "session-test",
        "2026-09-04T00:00:00+00:00",
    )


def test_owner_and_admin_can_access_system_lab():
    for role in (Role.OWNER, Role.ADMIN):
        principal = _principal(role)
        assert can_access_system_lab(principal)
        assert "System Lab" in _workspace_pages(principal)


def test_non_admin_roles_cannot_see_system_lab():
    for role in (Role.ANALYST, Role.REVIEWER, Role.CLIENT, Role.READ_ONLY):
        principal = _principal(role)
        assert not can_access_system_lab(principal)
        assert "System Lab" not in _workspace_pages(principal)


def test_system_lab_contains_expected_diagnostic_sections():
    assert SYSTEM_LAB_SECTIONS == (
        "Core Test Lab",
        "Clean Room",
        "CI & Releases",
        "Security Gate",
        "Production Readiness",
        "Audit & Diagnostics",
    )


def test_live_gate_label_maps_success_and_running_states():
    assert _live_gate_label({"status": "completed", "conclusion": "success"}) == "PASS"
    assert _live_gate_label({"status": "in_progress", "conclusion": None}) == "IN_PROGRESS"


def test_live_gate_label_maps_failure_and_unavailable_states():
    assert _live_gate_label({"status": "completed", "conclusion": "failure"}) == "FAIL · FAILURE"
    assert _live_gate_label(None) == "UNAVAILABLE"
    assert _live_gate_label({"error": "Timeout"}) == "UNAVAILABLE"


def test_short_sha_is_safe_for_missing_or_full_values():
    assert _short_sha(None) == "—"
    assert _short_sha({"sha": ""}) == "—"
    assert _short_sha({"sha": "0123456789abcdef"}) == "0123456789"


def test_production_readiness_does_not_treat_ci_or_demo_as_production_ready():
    rows = _production_readiness_rows(
        app_mode="demo",
        storage_backend="local_demo",
        core_backend="synthetic",
        storage_probe=None,
    )
    assert _overall_production_readiness(rows) == "NOT PRODUCTION READY"
    assert all(row["Status"] == "NOT VERIFIED" for row in rows)


def test_live_storage_pass_does_not_silently_promote_other_production_controls():
    rows = _production_readiness_rows(
        app_mode="production",
        storage_backend="gcs",
        core_backend="http",
        storage_probe={"status": "PASS"},
    )
    by_control = {row["Control"]: row["Status"] for row in rows}
    assert by_control["Production storage"] == "PASS"
    assert by_control["Production mode"] == "PASS"
    assert by_control["Private deployment"] == "NOT VERIFIED"
    assert by_control["Production authentication"] == "NOT VERIFIED"
    assert by_control["Finished production report flow"] == "NOT VERIFIED"
    assert by_control["Complete production E2E"] == "NOT VERIFIED"
    assert _overall_production_readiness(rows) == "NOT PRODUCTION READY"


def test_production_readiness_caveat_preserves_unverified_basis_rule():
    text = PRODUCTION_READINESS_CAVEAT.lower()
    assert "no verified basis" in text
    assert "production storage" in text
    assert "production auth" in text
    assert "production e2e" in text
