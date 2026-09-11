from coletti_advisory.connection_architecture import (
    CLIENT_EMPLOYEE_WIRING_CONTRACT,
    role_has_capability,
)
from coletti_advisory.models import Permission, Principal, Role


def principal(role: Role) -> Principal:
    return Principal(
        user_id=f"user-{role.value}",
        email=f"{role.value}@example.com",
        display_name=role.value.title(),
        organization_id="org-coletti",
        role=role,
        engagement_ids=("REC-260906-01",),
        session_id="sess-test",
        authenticated_at="2026-09-11T15:00:00+00:00",
    )


def test_explicit_client_and_employee_role_families():
    assert principal(Role.CLIENT).is_client
    for role in (Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.EXECUTIVE, Role.OWNER):
        assert principal(role).is_employee


def test_staff_manager_executive_permissions_are_distinct():
    staff = principal(Role.STAFF)
    manager = principal(Role.MANAGER)
    executive = principal(Role.EXECUTIVE)

    assert staff.can(Permission.MANAGE_WORK)
    assert not staff.can(Permission.REVIEW)
    assert manager.can(Permission.REVIEW)
    assert manager.can(Permission.MANAGE_WORK)
    assert executive.can(Permission.EXECUTIVE_OVERSIGHT)
    assert not executive.can(Permission.UPLOAD)


def test_capability_matrix_matches_interface_boundaries():
    assert role_has_capability(Role.CLIENT, "records_upload")
    assert role_has_capability(Role.STAFF, "staff_workflow")
    assert role_has_capability(Role.MANAGER, "team_oversight")
    assert role_has_capability(Role.EXECUTIVE, "executive_oversight")
    assert not role_has_capability(Role.CLIENT, "human_review")
    assert not role_has_capability(Role.STAFF, "deployment_control")
    assert role_has_capability(Role.OWNER, "deployment_control")


def test_wiring_contract_requires_end_to_end_verification():
    normalized = CLIENT_EMPLOYEE_WIRING_CONTRACT.lower()
    assert "authentication" in normalized
    assert "role capabilities" in normalized
    assert "review/approval gates" in normalized
    assert "audit attribution" in normalized
    assert "failure handling" in normalized
    assert "screen presence alone is not completion" in normalized
