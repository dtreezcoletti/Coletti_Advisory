import pytest

from coletti_advisory.auth import AuthorizationRegistry
from coletti_advisory.models import Permission, Principal, Role


def test_registry_resolves_role_and_engagements():
    registry = AuthorizationRegistry.from_json(
        '{"owner@example.com":{"display_name":"Owner","organization_id":"org-1","role":"owner","engagement_ids":["eng-1"]}}'
    )
    record = registry.resolve("OWNER@example.com")
    assert record is not None
    assert record.role is Role.OWNER
    assert record.engagement_ids == ("eng-1",)


def test_principal_cannot_access_unassigned_engagement():
    principal = Principal("u", "u@example.com", "U", "org", Role.CLIENT, ("eng-1",), "s", "now")
    assert principal.can(Permission.UPLOAD)
    with pytest.raises(PermissionError):
        principal.auth_context("eng-2")
