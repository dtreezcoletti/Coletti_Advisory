from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_square_billing_portal_contract() -> None:
    app = read("web/assets/app.js")
    assert "Invoices & Payments" in app
    assert "payment_url" in app
    assert 'data-action="issue-square-link"' in app
    assert "square-create-payment-link" in app


def test_square_billing_persistence_contract() -> None:
    migration = read("supabase/migrations/20261002210000_square_billing_v1.sql")
    assert "provider_order_id" in migration
    assert "provider_payment_link_id" in migration
    assert "payments_provider_payment_uidx" in migration
    assert "payment_refunds" in migration
    assert "payment_provider_events" in migration
    assert "primary key (provider, event_id)" in migration
    assert "revoke all on public.payment_provider_events from anon, authenticated" in migration


def test_square_webhook_security_and_idempotency_contract() -> None:
    webhook = read("supabase/functions/square-webhook/index.ts")
    assert "x-square-hmacsha256-signature" in webhook
    assert "SQUARE_WEBHOOK_SIGNATURE_KEY" in webhook
    assert "SQUARE_WEBHOOK_URL" in webhook
    assert "constantTimeEqual" in webhook
    assert 'eventType === "payment.created"' in webhook
    assert 'eventType === "payment.updated"' in webhook
    assert 'eventType === "refund.created"' in webhook
    assert 'eventType === "refund.updated"' in webhook
    assert "payment_provider_events" in webhook
    assert "raw webhook payload" not in webhook.lower()


def test_square_create_link_is_server_side_and_role_gated() -> None:
    function = read("supabase/functions/square-create-payment-link/index.ts")
    assert "SQUARE_ACCESS_TOKEN" in function
    assert "SQUARE_LOCATION_ID" in function
    assert '["owner", "admin"]' in function
    assert "/v2/online-checkout/payment-links" in function
    assert "reference_id: invoice.id" in function
    assert "provider_payment_link_id" in function
    assert "access-control-allow-origin" in function


def test_square_secrets_are_not_embedded_in_browser_source() -> None:
    app = read("web/assets/app.js")
    assert "SQUARE_ACCESS_TOKEN" not in app
    assert "SQUARE_WEBHOOK_SIGNATURE_KEY" not in app
