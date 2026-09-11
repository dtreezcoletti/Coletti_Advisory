from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


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


def test_four_operational_portal_entrypoints_load_the_shared_authoritative_app():
    expected = {
        "portal/index.html": "client",
        "employee/index.html": "employee",
        "admin/index.html": "admin",
        "owner/index.html": "owner",
    }
    for relative, surface in expected.items():
        html = (WEB / relative).read_text(encoding="utf-8")
        assert f"COLETTI_ENTRY_SURFACE = '{surface}'" in html
        assert "/assets/styles.css" in html
        assert "/assets/portal_integration_v2.css" in html
        assert "/assets/portal_routing_v1.js" in html
        assert "/assets/app.js" in html
        assert "/assets/portal_integration_v2.js" in html
        assert 'id="main"' in html
        assert 'id="toast-region"' in html
        assert "location.hash = '#/sign-in'" in html
        assert "location.replace('/#/sign-in')" not in html


def test_portal_integration_is_read_model_not_second_case_system():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    for checkpoint in (
        "Intake",
        "Engagement",
        "Source Collection",
        "Reconstruction",
        "Human Review",
        "Report Preparation",
        "Publication",
        "Close / Reopen",
    ):
        assert checkpoint in js
    assert "one authoritative case state" in js
    assert "Dashboard status is derived from canonical records" in js
    assert ".insert(" not in js
    assert ".update(" not in js
    assert ".delete(" not in js


def test_client_progress_does_not_query_internal_review_tables():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    start = js.index("async function clientProgress")
    end = js.index("async function internalProgress")
    client_block = js[start:end]
    for internal_table in (
        "evidence_work_items",
        "review_narratives",
        "qa_checklists",
        "publication_handoffs",
    ):
        assert internal_table not in client_block


def test_public_home_remains_separate_from_authenticated_operational_shell():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "/assets/site.css" in index
    assert "/assets/site.js" in index
    assert "/assets/app.js" not in index
