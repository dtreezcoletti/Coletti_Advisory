# Stage 4.5 Delivery-Failure Alerting Design
Status: DESIGN ONLY — NONPRODUCTION

## Trigger
Source of truth: public.cfab_email_status.
Alert candidate when:
- needs_attention = true; and
- status in (bounced, complained, failed); or
- delivery_delayed remains unresolved beyond the operational threshold.

## Idempotency
Unique alert key:
  provider_email_id + ':' + status + ':' + status_event_timestamp

Repeated webhook delivery must not create duplicate alerts.

## Alert payload
Minimum necessary fields only:
- provider email ID
- department
- record_id
- normalized delivery status
- event timestamp
- reason/error class when supplied by provider
- source = cfab-resend-webhook

Do not include full email body, recipient list, signing material, or provider secret.

## Routing
1. Insert append-only delivery event.
2. Update materialized/current email status.
3. When needs_attention becomes true, enqueue one internal incident notification.
4. Owner-facing alert surface reads the notification.
5. Resolution records acknowledgement and remediation; original delivery evidence remains immutable.

## Acceptance tests
- bounced => one needs_attention alert
- complained => one needs_attention alert
- failed => one needs_attention alert
- duplicate provider event => no second alert
- delivered after delayed => delayed alert closes/no new failure alert
- unauthorized roles cannot create/alter alert state
