from __future__ import annotations

from types import SimpleNamespace

from coletti_advisory import auth, supabase_auth
from coletti_advisory.models import Principal, Role


def _principal() -> Principal:
    return Principal(
        user_id="00000000-0000-0000-0000-000000000001",
        email="owner@example.test",
        display_name="Owner",
        organization_id="coletti-co",
        role=Role.OWNER,
        engagement_ids=(),
        session_id="sess-test",
        authenticated_at="2026-09-11T00:00:00+00:00",
        authenticated=True,
    )


def test_supabase_auth_is_primary_when_configured(monkeypatch) -> None:
    expected = _principal()
    monkeypatch.setattr(auth.supabase_auth, "configured", lambda: True)
    monkeypatch.setattr(
        auth.supabase_auth,
        "require_principal",
        lambda *, app_mode: expected,
    )
    actual = auth.require_authenticated_principal(
        app_mode="production",
        session_ttl_minutes=60,
    )
    assert actual == expected


def test_supabase_role_mapping_uses_canonical_roles() -> None:
    assert Role("owner") is Role.OWNER
    assert Role("admin") is Role.ADMIN
    assert Role("analyst") is Role.ANALYST
    assert Role("reviewer") is Role.REVIEWER
    assert Role("client") is Role.CLIENT


def test_password_sign_in_uses_supabase_password_grant(monkeypatch) -> None:
    monkeypatch.setattr(
        supabase_auth,
        "_secret",
        lambda name, default="": {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "anon-test",
        }.get(name, default),
    )
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "user": {"id": "user-1", "email": "owner@example.test"},
            },
        )

    monkeypatch.setattr(supabase_auth.requests, "post", fake_post)
    session = supabase_auth.sign_in_password(" Owner@Example.Test ", "secret")

    assert session.user["email"] == "owner@example.test"
    assert calls[0][0].endswith("/auth/v1/token?grant_type=password")
    assert calls[0][2] == {"email": "owner@example.test", "password": "secret"}


def test_password_reset_uses_recovery_endpoint_without_account_disclosure(monkeypatch) -> None:
    monkeypatch.setattr(
        supabase_auth,
        "_secret",
        lambda name, default="": {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "anon-test",
            "PASSWORD_RESET_REDIRECT_URL": "https://owner.example.test/reset-password",
        }.get(name, default),
    )
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(supabase_auth.requests, "post", fake_post)
    supabase_auth.request_password_reset(" Owner@Example.Test ")

    assert calls[0][0].endswith("/auth/v1/recover")
    assert calls[0][2] == {
        "email": "owner@example.test",
        "redirect_to": "https://owner.example.test/reset-password",
    }
