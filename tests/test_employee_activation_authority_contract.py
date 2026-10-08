"""Golden Path role activation and suspension regression checks.

Source-level tests only. Live Supabase rollback-only positive/negative checks
are documented separately in the WBS; none are browser acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"
ACTIVATION = MIGRATIONS / "20261008234632_enforce_active_signed_in_staff_for_golden_path_20261008.sql"
ROLE_RPC = MIGRATIONS / "20261008234702_require_active_profile_for_owner_admin_role_rpc_20261008.sql"


def normalized(path):
    return " ".join(path.read_text(encoding="utf-8").lower().split())


def function_text(sql, name):
    start = sql.index(f"create or replace function {name}")
    end = sql.find("create or replace function", start + 1)
    return sql[start:end if end >= 0 else None]


def test_active_profile_and_protected_role_control_staff_and_admin():
    sql = normalized(ACTIVATION)
    for name in ("private.is_admin()", "private.is_staff()"):
        body = function_text(sql, name)
        assert "private.user_roles r join public.profiles p" in body
        assert "p.status='active'" in body
        assert "p.role=r.role" in body
        assert "r.active" in body
        assert "auth.uid()" in body


def test_clients_and_staff_lose_case_access_on_suspension():
    sql = normalized(ACTIVATION)
    body = function_text(sql, "private.can_access_case(target_case_id text)")
    assert "p.status='active'" in body
    assert "r.role=p.role" in body
    assert "private.is_admin()" in body
    assert "private.is_staff()" in body
    assert "public.case_memberships" in body
    assert "public.case_assignments" in body


def test_auto_assignment_requires_signed_in_confirmed_staff():
    sql = normalized(ACTIVATION)
    body = function_text(sql, "private.admin_open_case_from_intake_impl_v1(")
    assert "join private.user_roles r" in body
    assert "join auth.users u" in body
    assert "r.active=true and r.role=p.role" in body
    assert "u.confirmed_at is not null" in body
    assert "u.last_sign_in_at is not null" in body
    assert "private.has_controlled_engagement_acceptance_v1" in body
    assert "insert into public.case_memberships" in body
    assert "insert into public.case_assignments" in body


def test_manual_assignment_rejects_unactivated_staff():
    sql = normalized(ACTIVATION)
    body = function_text(sql, "private.validate_active_case_staff_assignment_v1()")
    assert "join private.user_roles r" in body
    assert "join auth.users u" in body
    assert "u.confirmed_at is not null" in body
    assert "u.last_sign_in_at is not null" in body
    assert "active staff identity required for case assignment" in body


def test_role_change_rpc_requires_active_admin_profile():
    sql = normalized(ROLE_RPC)
    assert "private.current_user_role()" in sql
    assert "or not private.is_admin()" in sql
    assert "owner authority required for owner role changes" in sql
    assert "cannot demote the last active owner" in sql
    assert "from private.user_roles" in sql
