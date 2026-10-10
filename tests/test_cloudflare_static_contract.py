"""Cloudflare static deployment readiness for the existing single browser app.

This is a source contract, NOT Cloudflare deployment or browser acceptance evidence.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def test_single_cloudflare_static_output_root_and_routes():
    for rel in (
        "index.html",
        "login/index.html",
        "workspace/index.html",
        "owner/index.html",
        "admin/index.html",
        "employee/index.html",
        "portal/index.html",
        "assets/config.js",
        "assets/app.js",
    ):
        assert (WEB / rel).is_file(), rel
    assert (WEB / "workspace/index.html").read_text(encoding="utf-8").count(
        'data-portal="unified"'
    ) == 1


def test_cloudflare_auth_and_workspace_responses_do_not_cache():
    headers = (WEB / "_headers").read_text(encoding="utf-8")
    for route in (
        "/login/*",
        "/workspace/*",
        "/owner/*",
        "/admin/*",
        "/employee/*",
        "/portal/*",
        "/recovery/*",
        "/reset-password/*",
    ):
        assert f"{route}\n  Cache-Control: no-store" in headers
    assert "X-Content-Type-Options: nosniff" in headers
    assert "X-Frame-Options: DENY" in headers
    assert "Referrer-Policy: strict-origin-when-cross-origin" in headers


def test_cloudflare_preview_does_not_change_canonical_auth_origin():
    config = (WEB / "assets/config.js").read_text(encoding="utf-8")
    assert "APP_ORIGIN = 'https://colettico.com'" in config
    assert "onrender.com" not in config
    assert "sb_secret_" not in config
    assert "service_role" not in config
