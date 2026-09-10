from dataclasses import replace
from types import SimpleNamespace

import pytest

from coletti_advisory.core_adapter import SyntheticCoreAdapter
from coletti_advisory.demo_controls import (
    DEMO_EXPERIENCES,
    demo_experience_switching_available,
    principal_for_demo_experience,
    render_demo_experience_switcher,
)
from coletti_advisory.experience_shell import _experience, _visible_pages
from coletti_advisory.models import Permission, Principal, Role


def synthetic_principal() -> Principal:
    return Principal(
        user_id="demo-session",
        email="demo@synthetic.invalid",
        display_name="Synthetic Demo",
        organization_id="org-synthetic",
        role=Role.OWNER,
        engagement_ids=("eng-synthetic-demo",),
        session_id="demo-session",
        authenticated_at="2026-09-10T00:00:00+00:00",
        authenticated=False,
    )


def test_switcher_is_available_only_for_anonymous_synthetic_demo():
    core = SyntheticCoreAdapter()
    principal = synthetic_principal()
    assert demo_experience_switching_available(app_mode="demo", principal=principal, core=core)
    assert not demo_experience_switching_available(
        app_mode="production",
        principal=principal,
        core=core,
    )
    assert not demo_experience_switching_available(
        app_mode="demo",
        principal=replace(principal, authenticated=True),
        core=core,
    )
    assert not demo_experience_switching_available(
        app_mode="demo",
        principal=replace(principal, organization_id="org-live"),
        core=core,
    )
    assert not demo_experience_switching_available(
        app_mode="demo",
        principal=principal,
        core=object(),
    )


def test_switcher_exposes_the_four_requested_interface_classes():
    labels = [label for label, _role, _description in DEMO_EXPERIENCES]
    assert labels == [
        "Owner Console",
        "Admin Workspace",
        "Employee Workspace",
        "Client Portal",
    ]


def test_each_demo_persona_uses_real_role_permissions_and_real_interface_routing():
    principal = synthetic_principal()

    owner = principal_for_demo_experience(principal, "Owner Console")
    assert owner.role == Role.OWNER
    assert _experience(owner) == "owner"
    assert owner.can(Permission.MANAGE_USERS)

    admin = principal_for_demo_experience(principal, "Admin Workspace")
    assert admin.role == Role.ADMIN
    assert _experience(admin) == "employee"
    assert admin.can(Permission.MANAGE_USERS)
    assert "Administration" in _visible_pages(admin)

    employee = principal_for_demo_experience(principal, "Employee Workspace")
    assert employee.role == Role.ANALYST
    assert _experience(employee) == "employee"
    assert employee.can(Permission.ANALYZE)
    assert "Administration" not in _visible_pages(employee)

    client = principal_for_demo_experience(principal, "Client Portal")
    assert client.role == Role.CLIENT
    assert _experience(client) == "client"
    assert client.can(Permission.UPLOAD)
    assert "My Case" in _visible_pages(client)
    assert "Analysis" not in _visible_pages(client)

    for simulated in (owner, admin, employee, client):
        assert simulated.authenticated is False
        assert simulated.organization_id == principal.organization_id
        assert simulated.engagement_ids == principal.engagement_ids
        assert simulated.session_id == principal.session_id


def test_persona_resolver_reads_authorized_workspace_interface_state_without_rendering_second_switcher():
    shell = SimpleNamespace(
        st=SimpleNamespace(session_state={"_coletti_demo_experience": "Client Portal"})
    )
    resolved = render_demo_experience_switcher(
        shell,
        app_mode="demo",
        principal=synthetic_principal(),
        core=SyntheticCoreAdapter(),
    )
    assert resolved.role == Role.CLIENT
    assert resolved.display_name == "Synthetic Client"


def test_invalid_saved_interface_falls_back_to_owner_console():
    state = {"_coletti_demo_experience": "Removed Interface"}
    shell = SimpleNamespace(st=SimpleNamespace(session_state=state))
    resolved = render_demo_experience_switcher(
        shell,
        app_mode="demo",
        principal=synthetic_principal(),
        core=SyntheticCoreAdapter(),
    )
    assert resolved.role == Role.OWNER
    assert state["_coletti_demo_experience"] == "Owner Console"


def test_authenticated_principal_cannot_be_recast_as_demo_persona():
    with pytest.raises(PermissionError):
        principal_for_demo_experience(
            replace(synthetic_principal(), authenticated=True),
            "Client Portal",
        )
