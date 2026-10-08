"""V1 Owner/Admin staff assignment authority regression checks.

These source-level tests protect the minimal live Supabase repair and do not
assert successful interactive browser acceptance or actual employee onboarding.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"
ROLE_SQL = MIGRATIONS / "20261008204741_repair_owner_admin_role_assignment_rpc_guard_20261008.sql"
STAFF_SQL = MIGRATIONS / "20261008204900_enforce_staff_identity_on_case_access_and_assignment_20261008.sql"
WRAPPER_SQL = MIGRATIONS / "20261008205001_repair_staff_workspace_and_owner_override_authenticated_rpcs_20261008.sql"
APP_JS = ROOT / "web" / "assets" / "app.js"


def normalized(path):
    return " ".join(path.read_text(encoding="utf-8").lower().split())


def test_role_management_is_scoped_to_actual_owner_admin_authority():
    sql = normalized(ROLE_SQL)
    assert "security definer" in sql
    assert "caller_role not in ('owner','admin')" in sql
    assert "target_role='owner' or previous_role='owner'" in sql
    assert "cannot demote the last active owner" in sql
    assert "from private.user_roles" in sql
    assert "grant execute on function public.admin_set_user_role(uuid,text) to authenticated;" in sql
    assert "from public,anon;" in sql


def test_active_case_assignments_require_actual_staff_identity():
    sql = normalized(STAFF_SQL)
    assert "validate_active_case_staff_assignment_v1" in sql
    assert "before insert or update on public.case_assignments" in sql
    assert "p.status='active'" in sql
    assert "p.role=r.role" in sql
    assert "r.active=true" in sql
    assert "r.role in ('owner','admin','analyst','reviewer')" in sql
    assert "active staff identity required for case assignment" in sql


def test_demoted_staff_lose_assignment_based_case_access():
    sql = normalized(STAFF_SQL)
    for function in ["private.can_access_case", "private.can_work_case"]:
        begin = sql.index("create or replace function " + function)
        end = sql.find("create or replace function", begin + 1)
        definition = sql[begin:end if end != -1 else None]
        assert "private.is_staff()" in definition
        assert "public.case_assignments" in definition
        assert "a.active" in definition
    assert "public.case_memberships" in sql  # clients retain legitimate memberships


def test_workspace_rpc_remains_authenticated_with_private_authorization():
    sql = normalized(WRAPPER_SQL)
    assert "security definer" in sql
    assert "private.staff_case_workspace_impl_v1(p_case_id)" in sql
    assert "private.owner_override_assignment_impl_v1(" in sql
    assert "grant execute on function public.staff_case_workspace_v1(text) to authenticated;" in sql
    assert "grant execute on function public.owner_override_assignment_v1(text,uuid,text,text,boolean) to authenticated;" in sql
    assert sql.count("from public,anon;") == 2


def test_existing_admin_ui_uses_canonical_role_and_assignment_surfaces():
    code = APP_JS.read_text(encoding="utf-8")
    assert "admin_set_user_role" in code
    assert "admin_case_assignment_catalog_v1" in code
    assert "case_assignments" in code
    assert "CASE_ASSIGNMENT_ROLES" in code
