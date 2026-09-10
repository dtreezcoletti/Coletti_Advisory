from coletti_advisory.models import Principal, Role
from coletti_advisory.profile_menu import (
    profile_permissions,
    profile_role_label,
    profile_stat_targets,
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
        "sources": {
            "SRC-1": {"source_id": "SRC-1", "metadata": {"filename": "record-a.pdf"}},
            "SRC-2": {"source_id": "SRC-2", "metadata": {"filename": "record-b.pdf"}},
        },
        "propositions": {
            "PROP-1": {"proposition_id": "PROP-1", "text": "Record A states one value.", "source_ids": ["SRC-1"]},
            "PROP-2": {"proposition_id": "PROP-2", "text": "Record B states a different value.", "source_ids": ["SRC-2"]},
        },
        "contradictions": {
            "CON-1": {
                "contradiction_id": "CON-1",
                "proposition_a": "PROP-1",
                "proposition_b": "PROP-2",
                "reason": "The two records state different values.",
            }
        },
        "escalations": {"TASK-1": {"status": "OPEN", "source_ids": ["SRC-1"]}},
    }


def test_internal_profile_stats_are_personal_assignment_and_current_case_counts():
    stats = profile_work_stats(principal(Role.ANALYST), manifest())
    assert stats["Assigned cases"] == "2"
    assert stats["Current-case sources"] == "2"
    assert stats["Current-case record statements"] == "2"
    assert stats["Current-case inconsistencies"] == "1"
    assert stats["Current-case open issues"] == "1"


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


def test_every_profile_stat_has_a_connected_destination():
    for role in (Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER, Role.CLIENT, Role.READ_ONLY):
        p = principal(role)
        stats = profile_work_stats(p, manifest(), {})
        targets = profile_stat_targets(p)
        assert set(stats) <= set(targets)
        assert all(targets[label] for label in stats)


def test_owner_profile_routes_work_and_issues_into_owner_surfaces():
    targets = profile_stat_targets(principal(Role.OWNER))
    assert targets["Assigned cases"] == "Case Queue"
    assert targets["Current-case sources"] == "Evidence"
    assert targets["Current-case record statements"] == "Analysis"
    assert targets["Current-case open issues"] == "Human Review"


def test_client_profile_destinations_remain_client_safe():
    targets = profile_stat_targets(principal(Role.CLIENT))
    assert set(targets.values()) <= {"My Case", "Reports"}
    assert "Evidence" not in targets.values()
    assert "Analysis" not in targets.values()
    assert "Human Review" not in targets.values()
