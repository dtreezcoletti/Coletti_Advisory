"""Ensure the Owner workspace sees all open registry cases, not just assigned ones.

Source-level checks are not role-credential browser acceptance or API authorization tests.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"web/assets/app.js").read_text(encoding="utf-8")
PORTAL=(ROOT/"web/assets/portal_integration_v2.js").read_text(encoding="utf-8")


def test_owner_case_list_is_registry_catalog_not_assignments_only():
    refresh=APP.split("async function refreshCases() {",1)[1].split("\nfunction route()",1)[0]
    assert "if (ADMIN_ROLES.includes(state.profile?.role))" in refresh
    assert "supabase.rpc('admin_case_assignment_catalog_v1')" in refresh
    assert "ids=(data||[]).map(x=>x.case_id)" in refresh
    assert "if (error) throw error" in refresh
    assert "Promise.all([q('case_assignments','case_id')" not in refresh
    assert "catch(()=>[[],[]])" not in refresh
    assert "x.eq('staff_user_id',state.user.id).eq('active',true)" in refresh
    assert "x.eq('user_id',state.user.id).eq('active',true)" in refresh


def test_portal_case_selector_uses_same_owner_catalog():
    block=PORTAL.split("async function ensureAdminCaseSelector(ctx) {",1)[1].split("function decorateChrome",1)[0]
    assert "ADMIN_ROLES.has(ctx.role)" in block
    assert "supabase.rpc('admin_case_assignment_catalog_v1')" in block
    assert "if (error) throw error" in block
    assert "(cases||[]).map(x=>x.case_id)" in block
    assert "localStorage.removeItem('coletti.activeCase')" in block
    assert "ctx.caseId=null" in block
    assert "supabase.from('case_memberships')" not in block
    assert "supabase.from('case_assignments')" not in block


def test_assignment_candidates_exclude_inactive_profiles():
    block=APP.split("if(view==='assignments'){",1)[1].split("if(view==='audit')",1)[0]
    assert "x.in('role',['owner','admin','analyst','reviewer']).eq('status','ACTIVE')" in block
    assert "cases.length&&users.length" in block
    assert "confirmed, signed-in, active matching identity" in block
    assert "supabase.rpc('admin_case_assignment_catalog_v1')" in block
    assert "supabase.from('profiles').update" not in block


def test_source_fix_neither_grants_access_nor_modifies_registry_schema():
    assert not list((ROOT/"web").rglob("*.sql"))
    assert not list((ROOT/"supabase/migrations").glob("*owner_case_selector*"))
