from types import SimpleNamespace

import pytest

from coletti_advisory import dari_personal_profile as profile
from coletti_advisory.models import Role


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Work Rhythm", "user.work.rhythm"),
        ("  Decision / Tradeoffs! ", "user.decision.tradeoffs"),
        ("A" * 150, "user." + ("a" * 90)),
    ],
)
def test_personal_key_is_stable_and_bounded(title, expected):
    assert profile.profile_key_from_title(title) == expected


def test_personal_key_requires_real_title():
    with pytest.raises(ValueError):
        profile.profile_key_from_title("   !!!")


def test_personal_profile_denies_non_owner_and_demo(monkeypatch):
    monkeypatch.setattr(profile.supabase_auth, "current_access_token", lambda: "jwt")
    monkeypatch.setattr(profile.st, "session_state", {"_coletti_supabase_user": {"id": "owner-1"}})
    for principal in [
        SimpleNamespace(role=Role.ADMIN, authenticated=True, user_id="owner-1"),
        SimpleNamespace(role=Role.OWNER, authenticated=False, user_id="owner-1"),
        SimpleNamespace(role=Role.OWNER, authenticated=True, user_id="other-owner"),
    ]:
        with pytest.raises(PermissionError):
            profile._owner_token(principal)


def test_owner_session_must_match_principal(monkeypatch):
    monkeypatch.setattr(profile.supabase_auth, "current_access_token", lambda: "jwt")
    monkeypatch.setattr(profile.st, "session_state", {"_coletti_supabase_user": {"id": "owner-1"}})
    principal = SimpleNamespace(role=Role.OWNER, authenticated=True, user_id="owner-1")
    assert profile._owner_token(principal) == "jwt"


def test_domus_context_uses_only_approved_scoped_rpc(monkeypatch):
    principal = SimpleNamespace(role=Role.OWNER, authenticated=True, user_id="owner-1")
    calls = []
    def fake_rpc(_principal, name, values):
        calls.append((name, values))
        return [{"profile_key": "decision.style", "statement": "Show tradeoffs", "category": "DECISION_SUPPORT"}]
    monkeypatch.setattr(profile, "_rpc", fake_rpc)
    packet = profile.confirmed_domus_context(principal, realm="DOMUS")
    assert packet["realm"] == "DOMUS"
    assert packet["authority"] == "ADVISORY_ONLY"
    assert packet["requires_human_approval"] is True
    assert packet["preferences"] == [{"key": "decision.style", "statement": "Show tradeoffs", "category": "DECISION_SUPPORT"}]
    assert calls == [("dari_personal_profile_context_v1", {})]


def test_domus_context_rejects_officium_and_employee(monkeypatch):
    monkeypatch.setattr(profile, "_rpc", lambda *args, **kwargs: pytest.fail("Never call private RPC"))
    owner = SimpleNamespace(role=Role.OWNER, authenticated=True, user_id="owner-1")
    employee = SimpleNamespace(role=Role.ADMIN, authenticated=True, user_id="admin-1")
    with pytest.raises(PermissionError):
        profile.confirmed_domus_context(owner, realm="OFFICIUM")
    with pytest.raises(PermissionError):
        profile.confirmed_domus_context(employee, realm="DOMUS")
