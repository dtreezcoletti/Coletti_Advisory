from coletti_advisory.app_shell import _workspace_pages
from coletti_advisory.models import Principal, Role
from coletti_advisory.system_lab import SYSTEM_LAB_SECTIONS, can_access_system_lab


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
        "Audit & Diagnostics",
    )
