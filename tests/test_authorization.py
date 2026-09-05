from datetime import datetime, timezone

import pytest

from coletti_advisory.auth import (
    AuthorizationRegistry,
    validate_oidc_claim_times,
    validate_oidc_identity_claims,
)
from coletti_advisory.models import Permission, Principal, Role


def test_registry_resolves_role_and_engagements():
    registry = AuthorizationRegistry.from_json(
        '{"owner@example.com":{"display_name":"Owner","organization_id":"org-1","role":"owner","engagement_ids":["eng-1"],"enabled":true}}'
    )
    record = registry.resolve("OWNER@example.com")
    assert record is not None
    assert record.role is Role.OWNER
    assert record.engagement_ids == ("eng-1",)
    assert record.enabled is True


def test_registry_supports_account_revocation():
    registry = AuthorizationRegistry.from_json(
        '{"disabled@example.com":{"organization_id":"org-1","role":"client","engagement_ids":["eng-1"],"enabled":false}}'
    )
    record = registry.resolve("disabled@example.com")
    assert record is not None
    assert record.enabled is False


def test_valid_oidc_claim_times_are_accepted():
    now = datetime.fromtimestamp(2_000, tz=timezone.utc)
    validate_oidc_claim_times({"iat": 1_000, "exp": 3_000}, now=now)


def test_expired_oidc_token_is_rejected():
    now = datetime.fromtimestamp(3_001, tz=timezone.utc)
    with pytest.raises(ValueError, match="expired"):
        validate_oidc_claim_times({"iat": 1_000, "exp": 3_000}, now=now, clock_skew_seconds=0)


def test_invalid_oidc_claim_times_are_rejected():
    now = datetime.fromtimestamp(2_000, tz=timezone.utc)
    with pytest.raises(ValueError):
        validate_oidc_claim_times({"iat": 3_000, "exp": 4_000}, now=now)
    with pytest.raises(ValueError):
        validate_oidc_claim_times({"iat": 1_000}, now=now)


def test_verified_oidc_identity_is_accepted():
    now = datetime.fromtimestamp(2_000, tz=timezone.utc)
    validate_oidc_identity_claims(
        {
            "iat": 1_000,
            "exp": 3_000,
            "sub": "google-subject-123",
            "email": "owner@example.com",
            "email_verified": True,
        },
        now=now,
    )


def test_oidc_identity_requires_subject_email_and_verified_email():
    now = datetime.fromtimestamp(2_000, tz=timezone.utc)
    base = {
        "iat": 1_000,
        "exp": 3_000,
        "sub": "google-subject-123",
        "email": "owner@example.com",
        "email_verified": True,
    }

    for missing in ("sub", "email"):
        claims = dict(base)
        claims.pop(missing)
        with pytest.raises(ValueError):
            validate_oidc_identity_claims(claims, now=now)

    claims = dict(base)
    claims["email_verified"] = False
    with pytest.raises(ValueError, match="not verified"):
        validate_oidc_identity_claims(claims, now=now)


def test_oidc_verified_email_accepts_provider_string_true():
    now = datetime.fromtimestamp(2_000, tz=timezone.utc)
    validate_oidc_identity_claims(
        {
            "iat": 1_000,
            "exp": 3_000,
            "sub": "google-subject-123",
            "email": "owner@example.com",
            "email_verified": "true",
        },
        now=now,
    )


def test_principal_cannot_access_unassigned_engagement():
    principal = Principal("u", "u@example.com", "U", "org", Role.CLIENT, ("eng-1",), "s", "now")
    assert principal.can(Permission.UPLOAD)
    with pytest.raises(PermissionError):
        principal.auth_context("eng-2")
