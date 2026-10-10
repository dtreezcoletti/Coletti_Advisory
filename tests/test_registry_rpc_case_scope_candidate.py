"""Staged Registry SQL authorization review, not a live permission grant."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/security-review/STAFF_REGISTRY_LOOKUP_ACTIVATION.sql"


def test_staged_rpc_has_active_staff_and_case_scope_guards():
    sql = " ".join(CANDIDATE.read_text(encoding="utf-8").lower().split())
    assert "not deployed" in sql
    assert sql.count("if not private.is_staff()") == 2
    assert sql.count("a.staff_user_id = auth.uid()") >= 3
    assert sql.count("and a.active") >= 3
    assert "private.is_admin()" in sql
    assert "count(distinct a.case_id)" in sql
    assert "from registry.cases c where c.client_id = btrim(p_client_id)" in sql
    assert "or exists ( select 1 from public.case_assignments a where a.case_id = c.case_id" in sql
    assert "security definer set search_path = ''" in sql


def test_rpc_uses_authorized_facade_not_table_permissions():
    sql = " ".join(CANDIDATE.read_text(encoding="utf-8").lower().split())
    assert "revoke all on function public.staff_registry_lookup(text, integer) from public, anon" in sql
    assert "revoke all on function public.staff_registry_client_cases(text) from public, anon" in sql
    assert "grant execute on function public.staff_registry_lookup(text, integer) to authenticated" in sql
    assert "grant execute on function public.staff_registry_client_cases(text) to authenticated" in sql
    assert "grant select on registry." not in sql
    assert "grant all on registry." not in sql
    assert not (ROOT / "web/STAFF_REGISTRY_LOOKUP_ACTIVATION.sql").exists()
    assert not list((ROOT / "supabase/migrations").glob("*registry_lookup_activation*"))


def test_only_owner_admin_can_see_all_cases_and_staff_count_is_scoped():
    sql = " ".join(CANDIDATE.read_text(encoding="utf-8").lower().split())
    assert "when private.is_admin() then r.case_count" in sql
    assert "where private.is_admin() or exists" in sql
    assert "and ( private.is_admin() or exists" in sql
