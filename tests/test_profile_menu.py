from coletti_advisory.models import Principal, Role
from coletti_advisory.profile_menu import (
    profile_permissions,
    profile_role_label,
    profile_work_stats,
)


def principal(role: Role, engagements=("eng-1", "eng-2")) -> Principal:
    return Principal(
        user_id=f"usr-{role.value}",
        email=f"{role.value}@example.test",
        display_name=role.value.title(),
        organization_id="org-test",
        role=role,
        engagement_ids=engagements,
        session_id="sess-test",
        authenticated_at="now",
        authenticated=True,
    )


def manifest():
    return {
        "sources": {"SRC-1": {"source_id": "SRC-1"}, "SRC-2": {"source_id": "SRC-2"}},
        "propositions": {"PROP-1": {"proposition_id": "PROP-1"}},
        "contradictions": {"CON-1": {"contradiction_id": "CON-1"}},
        "escalations": {"TASK-1": {"status": "OPEN"}},
    }


def test_internal_profile_stats_are_personal_assignment_and_current_case_counts():
    stats = profile_work_stats(principal(Role.ANALYST), manifest())
    assert stats["Assigned cases"] == "2"
    assert stats["Current-case sources"] == "2"
    assert stats["Current-case record statements"] == "1"
    assert stats["Current-case inconsistencies"] == "1"
    assert stats["Current-case open issues"] == "2"


def test_client_profile_stats_do_not_expose_internal_analysis_counts():
    stats = profile_work_stats(principal(Role.CLIENT), manifest(), {})
    assert stats["Assigned cases"] == "2"
    assert stats["Documents submitted"] == "2"
    assert "Current-case record statements" not in stats
    assert "Current-case inconsistencies" not in stats
    assert "Current-case open issues" not in stats


def test_profile_permissions_follow_real_role_permissions():
    client_permissions = profile_permissions(principal(Role.CLIENT))
    analyst_permissions = profile_permissions(principal(Role.ANALYST))
    admin_permissions = profile_permissions(principal(Role.ADMIN))

    assert "Upload records" in client_permissions
    assert "Analyze records" not in client_permissions
    assert "Human review" not in client_permissions
    assert "Analyze records" in analyst_permissions
    assert "Manage users" not in analyst_permissions
    assert "Manage users" in admin_permissions
    assert "Manage cases" in admin_permissions


def test_role_labels_distinguish_admin_employee_owner_and_client():
    assert profile_role_label(principal(Role.OWNER)) == "Owner"
    assert profile_role_label(principal(Role.ADMIN)) == "Administrator"
    assert profile_role_label(principal(Role.ANALYST)) == "Employee · Analyst"
    assert profile_role_label(principal(Role.REVIEWER)) == "Employee · Reviewer"
    assert profile_role_label(principal(Role.CLIENT)) == "Client"
