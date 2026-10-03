from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "render.yaml"
LOGIN = ROOT / "web/login/index.html"
CONFIG = ROOT / "web/assets/config.js"
APP = ROOT / "web/assets/app.js"
OWNER = ROOT / "web/owner/index.html"
PORTAL = ROOT / "web/portal/index.html"
WORKSPACE = ROOT / "web/workspace/index.html"
OWNER_PWA = ROOT / "owner_pwa_server.py"


def test_render_declares_one_static_production_surface():
    text = RENDER.read_text(encoding="utf-8")
    assert text.count("- type: web") == 1
    assert "runtime: static" in text
    assert "runtime: python" not in text
    assert "streamlit run" not in text


def test_canonical_origin_and_auth_redirect_are_https_only():
    config = CONFIG.read_text(encoding="utf-8")
    login = LOGIN.read_text(encoding="utf-8")
    assert "APP_ORIGIN = 'https://colettico.com'" in config
    assert "resetPasswordForEmail(email,{redirectTo:`${APP_ORIGIN}/login/`})" in login
    assert "emailRedirectTo:`${APP_ORIGIN}/login/`" in login
    assert "location.origin}/login/" not in login


def test_all_roles_land_in_one_workspace_shell():
    login = LOGIN.read_text(encoding="utf-8")
    assert "${APP_ORIGIN}/workspace/#/admin/home" in login
    assert "${APP_ORIGIN}/workspace/#/workspace/home" in login
    assert "${APP_ORIGIN}/workspace/#/portal/home" in login
    assert "/owner/#/" not in login
    assert "/portal/#/" not in login


def test_owner_and_portal_paths_are_redirects_not_separate_apps():
    owner = OWNER.read_text(encoding="utf-8")
    portal = PORTAL.read_text(encoding="utf-8")
    workspace = WORKSPACE.read_text(encoding="utf-8")
    assert "location.replace('/workspace/' + location.search + location.hash)" in owner
    assert "location.replace('/workspace/' + location.search + location.hash)" in portal
    assert 'data-portal="unified"' in workspace
    assert "/assets/app.js" in workspace


def test_embedded_second_auth_flow_is_removed():
    app = APP.read_text(encoding="utf-8")
    assert "location.replace('/login/')" in app
    assert 'id="signin-form"' not in app
    assert 'id="contact-signin-form"' not in app
    assert "signInWithOtp({email,options" not in app


def test_competing_owner_pwa_recovery_server_is_removed():
    assert not OWNER_PWA.exists()
