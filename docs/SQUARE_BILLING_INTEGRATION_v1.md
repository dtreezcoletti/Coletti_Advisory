# Square Billing Integration v1

Status: **IMPLEMENTING — not operational**

Owner: Coletti & Co. Billing  
Processor: Square  
Institutional ledger: Colettico Supabase (`public.invoices`, `public.payments`, `public.payment_refunds`)  
Commercial surface: Coletti & Co. owner/admin + client portal

## Boundary

Square is the payment processor and hosted checkout surface. It is **not** the institutional billing ledger.

The canonical flow is:

```
Owner/Admin Billing
  -> square-create-payment-link
  -> Square-hosted Checkout
  -> client invoice.payment_url
  -> Square payment/refund webhook
  -> square-webhook
  -> payments / payment_refunds
  -> invoice paid-state
  -> Billing / Finance views
```

No PAN, CVV, raw card data, or raw Square webhook payload is stored in ColettiOS/Colettico.

## Why hosted Square Checkout

Coletti & Co. already exposes an authorized `payment_url` on the client invoice screen. Square Checkout creates a hosted payment link, which lets Square own the card-entry surface while the existing portal remains the client entry point.

## Supabase deployment

Migration:

- `supabase/migrations/20261002210000_square_billing_v1.sql`

Functions:

- `square-create-payment-link` — authenticated owner/admin action.
- `square-webhook` — public webhook receiver with Square HMAC validation and internal idempotency.

Both functions must deploy with platform JWT verification disabled because:
- the create-link function performs its own Supabase user-session validation; and
- the webhook is called by Square, not by a Supabase-authenticated user.

## Required secrets

Set these only in the Supabase Edge Function secret store. Never commit them.

```
SQUARE_ACCESS_TOKEN=
SQUARE_LOCATION_ID=
SQUARE_ENVIRONMENT=sandbox|production
SQUARE_WEBHOOK_SIGNATURE_KEY=
SQUARE_WEBHOOK_URL=
SQUARE_RETURN_URL=
```

`SQUARE_WEBHOOK_URL` must exactly equal the HTTPS notification URL configured in Square because the notification URL participates in signature validation.

`SQUARE_RETURN_URL` is optional. When set, Square redirects the buyer there after checkout.

## Square application configuration

Checkout/payment-link permissions:

- `ORDERS_READ`
- `ORDERS_WRITE`
- `PAYMENTS_WRITE`

Webhook read permission:

- `PAYMENTS_READ`

Subscribe the webhook endpoint to:

- `payment.created`
- `payment.updated`
- `refund.created`
- `refund.updated`

The integration targets Square API version `2026-09-16`.

## Correlation model

Coletti invoice UUID is written to Square `Order.reference_id`.

After a payment link is created, Coletti stores:

- `invoices.provider = 'square'`
- `invoices.provider_order_id = Square PaymentLink.order_id`
- `invoices.provider_payment_link_id = Square PaymentLink.id`
- `invoices.payment_url = Square PaymentLink.url`

Webhook payments are matched back to the invoice by Square `payment.order_id`.

## Idempotency and replay behavior

- Payment-link creation uses a stable per-invoice Square idempotency key.
- Every webhook notification is ledgered by `(provider, event_id)`.
- Terminal `PROCESSED` or `IGNORED` events are no-ops on retry.
- Failed events can be retried.
- Payment records are unique by `(provider, provider_payment_id)`.
- Refund records are unique by `(provider, provider_refund_id)`.

## Status mapping

Square payment:

- `COMPLETED -> SUCCEEDED`
- `FAILED/CANCELED -> FAILED`
- `APPROVED/PENDING -> PENDING`

Square refund:

- `COMPLETED -> SUCCEEDED`
- `FAILED/REJECTED -> FAILED`
- `PENDING -> PENDING`

A Coletti invoice is promoted to `PAID` only when recorded successful Square payments meet or exceed the invoice amount.

A refund updates the payment to `PARTIALLY_REFUNDED` or `REFUNDED`. v1 intentionally does **not** automatically reopen the invoice after a refund; that receivable decision remains controlled.

## Acceptance / promotion gates

Do not call the integration operational merely because the branch is merged.

1. **CODED** — migration, functions, and owner/admin action merged.
2. **DATA_WIRED** — migration applied and Square sandbox secrets installed.
3. **PERMISSION_TESTED** — client cannot issue links; owner/admin can.
4. **DRILL_THROUGH_VERIFIED** — owner issues link -> client sees Pay securely -> sandbox payment completes -> webhook records payment -> invoice becomes PAID.
5. **CROSS_INTERFACE_VERIFIED** — client Billing and owner/admin Billing agree on invoice/payment state.
6. **GOLDEN_PATH_PASSED** — controlled synthetic engagement completes the full billing path.
7. **PRODUCTION READY** — production Square credentials and production webhook subscription configured, with an authorized production smoke test.
8. **OPERATIONAL** — only after evidence for all required gates is retained.

## Required evidence

Retain IDs/timestamps, not card data:

- internal invoice ID / invoice number
- Square payment-link ID
- Square order ID
- Square webhook event ID
- Square payment ID
- resulting Coletti payment ID
- before/after invoice status
- sandbox/production environment
- test timestamp and reviewer

## Failure behavior

If Square link creation succeeds but the local invoice update fails, the function returns a controlled error and surfaces the provider payment-link ID in the response for reconciliation.

If a valid webhook cannot be processed, the event is marked `FAILED` and the endpoint returns a non-2xx status so Square can retry.

Webhook events unrelated to a Coletti-linked Square order are marked `IGNORED`; they do not mutate Coletti billing data.
