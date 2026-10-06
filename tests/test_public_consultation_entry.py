from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_public_consultation_entry_is_visible():
    site = read("web/assets/site.js")
    home = read("web/index.html")
    contact = read("web/contact.html")
    consultation = read("web/consultation.html")

    assert 'Consultation","/consultation.html' in site
    assert 'Request Consultation' in site
    assert 'href="/consultation.html">Request a Consultation' in home
    assert 'Start Consultation Request' in contact
    assert 'Start Secure Consultation Request' in consultation

def test_consultation_entry_creates_secure_client_access():
    consultation = read("web/consultation.html")
    login = read("web/login/index.html")
    workspace = read("web/assets/app.js")

    assert "signInWithOtp" in consultation
    assert "shouldCreateUser:true" in consultation
    assert "next=consultation" in consultation
    assert "next==='consultation'" in login
    assert "/workspace/#/portal/intake" in login
    assert "go('/portal/preconsultation')" in workspace
    assert "Pre-Consultation Assignment" in workspace
