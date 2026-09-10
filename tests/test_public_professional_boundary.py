from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_site_loads_dedicated_professional_boundary_styles():
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'professional_boundary_v1.css' in index


def test_public_language_layer_defines_universal_boundary_and_public_routes():
    script = (ROOT / "web" / "assets" / "public_language_v1.js").read_text(encoding="utf-8")
    assert 'professional-boundary-band' in script
    assert 'Professional Boundary' in script
    assert 'A reconstruction engagement does not authorize Coletti &amp; Co. to act as your attorney, accountant, auditor, investigator, fiduciary, or other licensed professional.' in script
    for route in (
        "home", "services", "how-it-works", "about", "referral-partners", "pricing",
        "security", "faq", "contact", "disclaimer", "privacy", "terms", "sign-in",
    ):
        assert f"'{route}'" in script


def test_services_scope_copy_is_separated_from_professional_boundary_at_render_time():
    script = (ROOT / "web" / "assets" / "public_language_v1.js").read_text(encoding="utf-8")
    assert "splitServicesScopeNotice" in script
    assert "notice.textContent = 'Engagement scope is confirmed before substantive work begins.'" in script
    assert "footer.parentNode.insertBefore(boundary, footer)" in script
