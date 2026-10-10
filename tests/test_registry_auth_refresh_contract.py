"""Registry authentication stability and fail-closed display contracts.

Source-level regression checks only; staff browser acceptance remains separate.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "web/assets/registry_lookup.js"


def test_registry_auth_event_defers_supabase_calls_outside_callback():
    source = REGISTRY.read_text(encoding="utf-8")
    assert "supabase.auth.onAuthStateChange((event) => scheduleAuthRefresh(event));" in source
    assert "setTimeout(() => {" in source
    assert "void refresh().catch(error => {" in source
    assert "supabase.auth.onAuthStateChange(refresh)" not in source
    assert "await supabase.auth.getSession()" in source


def test_registry_refresh_cannot_reinstate_stale_profile_after_sign_out():
    source = REGISTRY.read_text(encoding="utf-8")
    assert "let authRefreshGeneration = 0;" in source
    assert "const generation = ++authRefreshGeneration;" in source
    assert source.count("if (generation !== authRefreshGeneration) return;") == 2
    assert "event === 'SIGNED_OUT'" in source
    assert "profile = null;" in source
    assert "hide();" in source


def test_registry_ui_remains_read_only_and_server_authorized():
    source = REGISTRY.read_text(encoding="utf-8")
    assert "STAFF_ROLES.has(profile.role)" in source
    assert "supabase.rpc('staff_registry_lookup'" in source
    assert "supabase.rpc('staff_registry_client_cases'" in source
    assert "from('registry.clients')" not in source
    assert ".insert(" not in source
    assert ".update(" not in source
    assert ".delete(" not in source
