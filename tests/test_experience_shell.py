from coletti_advisory.experience_shell import _experience, _visible_pages
from coletti_advisory.models import Principal, Role


def principal(role: Role) -> Principal:
    return Principal(
        user_id=f"usr-{role.value}",
        email=f"{role.value}@example.com",
        display_name=role.value.title(),
        organization_id="org-test",
        role=role,
        engagement_ids=("eng-test",),
        session_id="sess-test",
        authenticated_at="2026-09-06T00:00:00+00:00",
        authenticated=True,
    )


def test_client_portal_does_not_expose_internal_workspaces():
    p = principal(Role.CLIENT)
    assert _experience(p) == "client"
    pages = _visible_pages(p)
    assert "Dashboard" in pages
    assert "My Case" in pages
    assert "Upload Documents" in pages
    assert "Reports" in pages
    assert "Evidence" not in pages
    assert "Analysis" not in pages
    assert "Review Center" not in pages
    assert "Administration" not in pages
    assert "System Lab" not in pages


def test_read_only_client_does_not_get_upload():
    p = principal(Role.READ_ONLY)
    assert _experience(p) == "client"
    assert "Upload Documents" not in _visible_pages(p)


def test_employee_workspace_is_permission_filtered():
    analyst = principal(Role.ANALYST)
    assert _experience(analyst) == "employee"
    analyst_pages = _visible_pages(analyst)
    assert "Secure Intake" in analyst_pages
    assert "Evidence" in analyst_pages
    assert "Review Center" in analyst_pages
    assert "Analysis" in analyst_pages
    assert "Administration" not in analyst_pages
    assert "System Lab" not in analyst_pages

    reviewer = principal(Role.REVIEWER)
    reviewer_pages = _visible_pages(reviewer)
    assert "Evidence" in reviewer_pages
    assert "Review Center" in reviewer_pages
    assert "Analysis" not in reviewer_pages
    assert "Secure Intake" not in reviewer_pages


def test_admin_stays_employee_facing_and_system_lab_is_owner_only():
    admin = principal(Role.ADMIN)
    assert _experience(admin) == "employee"
    pages = _visible_pages(admin)
    assert "Administration" in pages
    assert "System Lab" not in pages


def test_owner_console_has_full_navigation():
    owner = principal(Role.OWNER)
    assert _experience(owner) == "owner"
    pages = _visible_pages(owner)
    for expected in (
        "Dashboard",
        "Engagements",
        "Secure Intake",
        "Evidence",
        "Review Center",
        "Analysis",
        "Reports",
        "System Lab",
        "Administration",
    ):
        assert expected in pages
