from pathlib import Path

from coletti_advisory.business_model import (
    BUSINESS_MODEL_KEY,
    BUSINESS_MODEL_NAME,
    BUSINESS_MODEL_VERSION,
    IntakeBoundaryRequest,
    IntakeDisposition,
    SERVICE_CATALOG,
    screen_intake,
)


ROOT = Path(__file__).resolve().parents[1]


def test_controlling_business_model_identity_and_catalog():
    assert BUSINESS_MODEL_KEY == "CCO-RRDA-001"
    assert BUSINESS_MODEL_VERSION == "1.0"
    assert BUSINESS_MODEL_NAME == "Records Reconstruction & Documentation Analysis"
    assert "Diagnostic Records Review" in SERVICE_CATALOG
    assert "Professional Handoff" in SERVICE_CATALOG
    assert "Organized Source Production" in SERVICE_CATALOG


def test_intake_accepts_authorized_record_reconstruction():
    result = screen_intake(IntakeBoundaryRequest(records_authorized=True))
    assert result.disposition is IntakeDisposition.ACCEPT


def test_intake_modifies_protected_conclusion_request():
    result = screen_intake(
        IntakeBoundaryRequest(records_authorized=True, asks_protected_conclusion=True)
    )
    assert result.disposition is IntakeDisposition.MODIFY_SCOPE
    assert "PROTECTED_PROFESSIONAL_CONCLUSION_REQUIRES_SCOPE_MODIFICATION" in result.reasons


def test_intake_declines_investigative_method_request():
    result = screen_intake(
        IntakeBoundaryRequest(records_authorized=True, asks_investigative_method=True)
    )
    assert result.disposition is IntakeDisposition.DECLINE_REFER


def test_intake_routes_state_clearance_to_professional_review():
    result = screen_intake(
        IntakeBoundaryRequest(
            records_authorized=True,
            state_clearance_required=True,
            jurisdictions=("PA", "TX"),
        )
    )
    assert result.disposition is IntakeDisposition.PROFESSIONAL_REVIEW
    assert "JURISDICTIONS:PA,TX" in result.reasons


def test_public_site_uses_rrda_positioning_and_removes_intelligence_positioning():
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    services = (ROOT / "web" / "services.html").read_text(encoding="utf-8")
    boundaries = (ROOT / "web" / "boundaries.html").read_text(encoding="utf-8")
    public_language = (ROOT / "web" / "assets" / "public_language_v1.js").read_text(encoding="utf-8")

    assert "Records Reconstruction &amp;<br/>Documentation Analysis" in index
    assert "Diagnostic Records Review" in services
    assert "Organized Source Production" in services
    assert "do not independently investigate individuals" in boundaries
    assert "Records Reconstruction & Documentation Analysis" in public_language
    assert "Records Reconstruction & Operational Intelligence" not in index
    assert "Business Records Intelligence" not in index


def test_service_scope_memorializes_source_universe_and_four_way_gate():
    scope = (ROOT / "services" / "SERVICE_SCOPE_v1.md").read_text(encoding="utf-8")
    assert "CCO-RRDA-001" in scope
    assert "versioned **Source Universe**" in scope
    for disposition in ("ACCEPT", "MODIFY_SCOPE", "PROFESSIONAL_REVIEW", "DECLINE_REFER"):
        assert f"`{disposition}`" in scope
