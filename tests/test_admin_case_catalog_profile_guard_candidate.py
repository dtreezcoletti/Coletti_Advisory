"""Source contract for Owner/Admin case-catalog RPC safety candidate.

This is NOT proof that the SQL was applied or browser sessions were tested.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/"docs/security-review/ADMIN_CASE_CATALOG_ACTIVE_PROFILE_GUARD.sql"


def test_admin_catalog_candidate_requires_authoritative_active_profile():
    sql=" ".join(CANDIDATE.read_text(encoding="utf-8").lower().split())
    assert "review required before production application" in sql
    assert "not a deployed migration" in sql
    assert "if auth.uid() is null or not private.is_admin()" in sql
    assert "raise exception 'not authorized' using errcode = '42501'" in sql
    assert "private.current_user_role()" not in sql.split("as $function$",1)[1]


def test_admin_catalog_candidate_preserves_case_scope_and_privilege_boundary():
    sql=" ".join(CANDIDATE.read_text(encoding="utf-8").lower().split())
    assert "public.admin_case_assignment_catalog_v1()" in sql
    assert "security definer set search_path = ''" in sql
    assert "from registry.cases c" in sql
    assert "where upper(c.status) not in ('archived','closed')" in sql
    assert "count(ca.id) filter (where ca.active)" in sql
    assert "from public, anon" in sql
    assert "to authenticated" in sql
    assert "grant select on registry." not in sql
    assert not list((ROOT/"web").rglob("*.sql"))
    assert not list((ROOT/"supabase/migrations").glob("*catalog_active_profile*"))
