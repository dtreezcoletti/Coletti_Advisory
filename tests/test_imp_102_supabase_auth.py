from __future__ import annotations

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


def test_supabase_auth_reads_hosted_environment(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    assert supabase_auth.configured() is True
    assert supabase_auth._headers()["apikey"] == "sb_publishable_test"


def test_supabase_role_mapping_uses_canonical_roles() -> None:
    assert Role("owner") is Role.OWNER
    assert Role("admin") is Role.ADMIN
    assert Role("analyst") is Role.ANALYST
    assert Role("reviewer") is Role.REVIEWER
    assert Role("client") is Role.CLIENT
