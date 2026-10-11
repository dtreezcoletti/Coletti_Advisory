"""Universal portal auth callback deferral and ACTIVE profile gates.

Static source regression tests; do not count as credential/browser acceptance.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def source(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_main_application_defers_auth_api_reads():
    js=source("assets/app.js")
    assert "supabase.auth.onAuthStateChange(()=>scheduleAuthRefresh());" in js
    assert "setTimeout(async()=>{" in js
    assert "await refreshAuth();" in js
    assert "supabase.auth.onAuthStateChange(async" not in js
    assert "profile.status !== 'ACTIVE'" in js
    assert "state.caseIds=[];" in js
    assert "localStorage.removeItem('coletti.activeCase')" in js


def test_login_callback_routes_from_next_task_and_denies_inactive_profile():
    html=source("login/index.html")
    assert "select('role,status')" in html
    assert "profile?.status !== 'ACTIVE'" in html
    assert "setTimeout(()=>void routeAuthenticatedSession(),0)" in html
    assert "queueMicrotask(()=>void routeAuthenticatedSession())" not in html


def test_role_router_defers_auth_api_reads_and_denies_inactive_profile():
    js=source("assets/portal_routing_v1.js")
    assert "select('role,status')" in js
    assert "profile.status !== 'ACTIVE'" in js
    assert "onAuthStateChange(() => setTimeout(" in js
    assert "queueMicrotask(" not in js


def test_unified_portal_enhancement_is_deferred_and_fail_closed():
    js=source("assets/portal_integration_v2.js")
    assert "select('id,role,display_name,status')" in js
    assert "profile.status !== 'ACTIVE'" in js
    assert "if(enhanceScheduled) return;" in js
    assert "setTimeout(()=>{" in js
    assert "function scheduleEnhance() { queueMicrotask" not in js


def test_owner_and_registry_navigation_respect_active_profile_status():
    owner=source("assets/owner_governance_v1.js")
    registry=source("assets/registry_lookup.js")
    assert "profile?.status === 'ACTIVE'" in owner
    assert "data?.status !== 'ACTIVE'" in registry
    assert "select('role,status')" in owner
    assert "select('role,status')" in registry
    assert "onAuthStateChange((event) => scheduleAuthRefresh(event))" in registry


def test_fix_does_not_introduce_new_auth_issuer_or_privileged_key():
    for f in ["assets/app.js","assets/portal_routing_v1.js","assets/portal_integration_v2.js","assets/owner_governance_v1.js","assets/registry_lookup.js","login/index.html"]:
        js=source(f)
        assert "SUPABASE_SERVICE_ROLE_KEY" not in js
        assert "sb_secret_" not in js
        assert "@supabase/supabase-js@2.115.0/+esm" in js
