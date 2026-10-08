"""Regression guard for WBA-2026-10-08-01 / RB-01.

This contract test checks the checked-in permission migration and the existing
case authorization guard. It is not a substitute for live authenticated
browser, assigned-employee, or negative cross-case acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRANT_MIGRATION = ROOT / "supabase" / "migrations" / (
    "20261008165617_restore_authenticated_case_lifecycle_snapshot_execute_20261008.sql"
)
LIFECYCLE_MIGRATION = ROOT / "supabase" / "migrations" / (
    "20260911203500_case_lifecycle_portal_integration_v1.sql"
)
PORTAL = ROOT / "web" / "assets" / "portal_integration_v2.js"


def test_lifecycle_rpc_grant_is_explicitly_authenticated_only():
    sql = GRANT_MIGRATION.read_text(encoding="utf-8").lower()
    normalized = " ".join(sql.split())
    assert (
        "revoke all on function public.case_lifecycle_snapshot_v1(text) "
        "from public, anon;" in normalized
    )
    assert (
        "grant execute on function public.case_lifecycle_snapshot_v1(text) "
        "to authenticated;" in normalized
    )
    assert (
        "grant execute on function public.case_lifecycle_snapshot_v1(text) "
        "to anon;" not in normalized
    )


def test_case_lifecycle_snapshot_still_has_authorization_predicate():
    sql = LIFECYCLE_MIGRATION.read_text(encoding="utf-8")
    start = sql.lower().index(
        "create or replace function public.case_lifecycle_snapshot_v1("
    )
    end = sql.lower().find("$$;", start)
    assert end != -1
    body = sql[start:end]
    assert "auth.uid() is null" in body
    assert "private.can_access_case(p_case_id)" in body
    assert "raise exception 'not authorized'" in body


def test_browser_reads_canonical_authorized_snapshot():
    js = PORTAL.read_text(encoding="utf-8")
    assert ".rpc('case_lifecycle_snapshot_v1',{p_case_id:caseId})" in js
