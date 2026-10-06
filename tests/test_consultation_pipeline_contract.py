from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_consultation_ui_contract():
    app = read("web/assets/app.js")
    required = [
        "Pre-Consultation Assignment",
        "admin_consultation_queue_v1",
        "submit_preconsultation_assignment_v1",
        "admin_decide_consultation_v1",
        "admin_link_square_booking_v1",
        "admin_prepare_consultation_invoice_v1",
        "square-create-payment-link",
        "consultation-confirmation-email",
        "admin_mark_consultation_completed_v1",
        "admin_complete_consultation_qualification_v1",
    ]
    for token in required:
        assert token in app

def test_consultation_backend_contract():
    migration = read("supabase/migrations/20261006203000_consultation_pipeline_v1.sql")
    for token in [
        "preconsultation_assignments",
        "consultation_workflows",
        "consultation_notifications",
        "APPROVED_FOR_CONSULTATION",
        "completed financially-cleared consultation required before qualification",
        "admin_consultation_queue_v1",
    ]:
        assert token in migration

def test_provider_functions_contract():
    square_link = read("supabase/functions/square-create-payment-link/index.ts")
    square_webhook = read("supabase/functions/square-webhook/index.ts")
    confirmation = read("supabase/functions/consultation-confirmation-email/index.ts")

    assert "SQUARE_ACCESS_TOKEN" in square_link
    assert "SQUARE_LOCATION_ID" in square_link
    assert "x-square-hmacsha256-signature" in square_webhook.lower()
    assert 'eventType === "booking.created"' in square_webhook
    assert "RESEND_API_KEY" in confirmation
    assert "owner_authorization_required" in confirmation
    assert "The consultation fee is due in full before the consultation" in confirmation
