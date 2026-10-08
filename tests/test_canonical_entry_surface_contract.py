"""Regression tests for existing Owner/Admin/Employee entrypoint routing.

The surface hint is presentation-only; authenticated profile checks govern
access. This is not evidence of real credential/browser acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
JS = WEB / "assets" / "portal_integration_v2.js"


def test_existing_role_entrypoints_preserve_the_chosen_surface():
    for role, expected in (
        ("owner", "#/admin/home"),
        ("admin", "#/admin/home"),
        ("employee", "#/workspace/home"),
    ):
        text = (WEB / role / "index.html").read_text(encoding="utf-8")
        assert "new URL('/workspace/', location.origin)" in text
        assert "new URLSearchParams(location.search)" in text
        assert f"params.set('surface', '{role}')" in text
        assert f"location.hash || '{expected}'" in text


def test_role_verified_surface_hint_does_not_grant_access():
    code = JS.read_text(encoding="utf-8")
    assert "new URLSearchParams(location.search).get('surface')" in code
    assert "const ADMIN_ROLES = new Set(['owner','admin'])" in code
    assert "const STAFF_ROLES = new Set(['owner','admin','analyst','reviewer'])" in code
    assert "if (role === 'owner' && ENTRY_SURFACE === 'owner')" in code
    assert "else if (ADMIN_ROLES.has(role))" in code
    assert "else if (STAFF_ROLES.has(role))" in code
    assert "supabase.from('profiles').select('id,role,display_name')" in code


def test_employee_entry_does_not_bypass_router_or_create_identity():
    shell = (WEB / "workspace" / "index.html").read_text(encoding="utf-8")
    assert "portal_routing_v1.js" in shell
    assert "portal_integration_v2.js" in shell
    route = (WEB / "assets" / "portal_routing_v1.js").read_text(encoding="utf-8")
    assert "if (!profile?.role)" in route
    assert "WORKSPACE_AUTHORITY_UNRESOLVED" in route
