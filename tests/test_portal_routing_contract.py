from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_role_aware_portal_routing_layer_is_loaded():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "./assets/portal_routing_v1.js" in index


def test_role_aware_portal_routing_contract():
    js = (WEB / "assets" / "portal_routing_v1.js").read_text(encoding="utf-8")
    assert "owner" in js
    assert "admin" in js
    assert "analyst" in js
    assert "reviewer" in js
    assert "/admin/home" in js
    assert "/workspace/home" in js
    assert "/portal/home" in js
    assert "route.startsWith('/portal/')" in js


def test_canonical_portal_and_owner_paths_redirect_to_secure_sign_in():
    for relative in ("portal/index.html", "owner/index.html"):
        html = (WEB / relative).read_text(encoding="utf-8")
        assert "https://colettico.com/#/sign-in" in html
        assert "location.replace('/#/sign-in')" in html


def test_docs_do_not_claim_portal_subdomain_is_operational():
    readme = (WEB / "README.md").read_text(encoding="utf-8")
    assert "portal.colettico.com" in readme
    assert "must not be published or treated as operational" in readme
    assert "contained zero Auth users" not in readme
