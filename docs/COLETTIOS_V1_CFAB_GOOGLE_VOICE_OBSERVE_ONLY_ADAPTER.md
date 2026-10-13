# ColettiOS V1 — Google Voice observe-only C-FAB adapter

**Status: PROPOSED DESIGN ONLY (2026-10-13). No migration, connector authorization, Gmail access, telephone number or external send authorized.**
**Related:** IMP-153 Communications Fabric, IMP-162 business identity, issue #96 read receipts/reception/phone provider, identity-scoped DARI and departmental governance.

## Purpose

Offer a Google Voice Basic **human-operated** telephone line with compliant workflow assistance within C-FAB. This is **not** an API connection to Google Voice, a programmable phone number, a live DARI telephone agent, a reliable business multi-user PBX, or guaranteed permanent free telephony. Google officially prohibits scripted/automated calls or messaging on consumer Voice, disallows forwarding calls to automated systems, and disallows unauthorized commercial exploitation; Basic is marketed for individuals and is not a reliable substitute for a business-grade line. Treat business-use appropriateness as subject to the applicable terms and no-go policy checks. Google Voice Basic may reclaim inactive numbers. Paid standalone Voice Starter/Standard are separate ($10/$20 monthly list price at the time checked), but are not programmable Voice API equivalents.

Sources: https://support.google.com/voice/answer/9230450 ; https://support.google.com/voice/answer/165221 ; https://support.google.com/voice/answer/16515632 ; https://workspace.google.com/products/voice/ .

## Allowed / unsupported boundary

**Allowed to evaluate:** Opt-in Google Voice notification forwarding to a specifically authorized Gmail mailbox: missed-call alerts, voicemail/transcripts and SMS email forwards (availability per edition and settings), processed solely via **authorized Gmail API**. Create an internal non-send C-FAB event, label provenance as *Gmail forwarded notice referencing Google Voice*, propose human follow-up, and audit. Gmail read scopes require OAuth consent and possibly restricted-scope verification/security assessment when stored on server, per https://developers.google.com/workspace/gmail/api/auth/scopes .

**Human-only through official Voice app/web:** Pick up calls, call back, send individual SMS replies, set voicemail greeting, maintain number and caller settings, confirm actual outcomes. DARI may draft text for a human to copy. Do not attempt to bypass the Google Voice app, use unofficial APIs, screen/UI scraping, click-bots, inbound-to-AI voice forwarding, browser automation, email-to-SMS transport hacks, or bulk/automated SMS.

**Independent from Google Voice:** Fully automated Resend email notices and authenticated ColettiOS portal messaging may operate under their own lawful terms and separately verified provider connections. Do not disguise an email or portal message as a Google Voice SMS.

## Minimum C-FAB additive change list

| Structure | Proposed change | Control |
| --- | --- | --- |
| `c_fab.identities` | Model the institution's reception identity and authorized person, not personal DOMUS owner as shared mailbox | Principal/auth + tenant/case isolation |
| `c_fab.provider_accounts` | Provider adapter `google_voice_manual` is **external-unlinked**; real linked provider is separately `gmail_google_voice_notices` after explicit OAuth. `capabilities` describes `observe_forwarded_notices: true, voice_answer:false, voice_dial:false, sms_send:false, voice_webhook:false, receipt_verification:false` | Never mark Google Voice API connected |
| `c_fab.endpoints` | Expand check constraint from EMAIL, PORTAL, INTERNAL, NOTIFICATION, OTHER to support explicit PHONE and SMS; phone E.164 and verified-account ownership | No global disclosure, identity verification |
| `c_fab.communication_events` | Add notice event types `GV_MISSED_CALL_NOTICE`, `GV_VOICEMAIL_NOTICE`, `GV_SMS_FORWARD_NOTICE`, `MANUAL_CALL_OUTCOME`, `MANUAL_SMS_OUTCOME` with provider origin GMAIL vs SELF_REPORTED, Gmail message ID, received time, content hash, evidence tier | **No false SENT/DELIVERED/READ** from forwarded emails; no treating notice as authoritative VoIP webhook |
| `c_fab.communication_events` current schema bug | Default `transmission_state = 'RECEIVED'` but CHECK permits only CREATED, QUEUED, SENDING, SENT, DELIVERED, FAILED, UNKNOWN; reconcile in an additive migration, preserving semantics for inbound events | Run existing regression checks first |
| `c_fab.conversations` | Case/client/prospect matching requires explicit validation, and unknown caller remains unverified | Caller ID/forwarded email isn't identity |
| `c_fab.obligations` | Callback/reply follow-ups, due windows and human disposition through Dispatcher | DARI does not independently execute a Google Voice send |
| `c_fab.audit_events` | Import evidence, original Gmail reference, dedupe, reclassification and manual outcome actor | Append-only, defensible trace |
| C-FAB RLS and gateway | Existing owner-scoped authenticated ALL policies do not implement current DARI principle of every signed-in user; add server-enforced role + assignment + case membership and user-scoped retrieval. Contractor/client/other user cannot view business mailbox by default. | Test each staff/client/contractor denial, revocation, DOMUS boundary |
| UI | External line status, source = email notification, "Open Google Voice", "Copy DARI draft", "Mark callback completed" after manual outcome confirmation, notification freshness and linked follow-up | No Send SMS / Answer Call button wired to Google Voice |
| C-FAB delivery receipts | Human-sourced manual outcome is not carrier delivered; notifications received via Gmail are not opened/read by caller, and never an in-portal recipient receipt | Reconcile portal read/ack separately |

Only a subset requires SQL: the endpoint type constraint, corrected event-state check/default, and possibly identity-aware role-scoped event projection and supporting provenance/idempotency fields. Existing `provider_accounts.capabilities`, `communication_events.provenance` and `metadata`, and `obligations` can hold preliminary integration data without large schema changes. Plan migrations using Supabase apply_migration and verify before any DB updates.

## Concrete inbound path

1. Human turns on forwarding in their own Voice settings, with consent: Settings -> Messages -> Forward messages to email; Calls -> Get email alerts for missed calls; Voicemail -> Get voicemail via email. Settings availability and actual notifications must be verified with synthetic tests.
2. A specifically authorized account grants scoped Gmail read access; **do not implicitly connect personal Gmail**, and ensure mailbox scope, retention, access visibility, token encryption and revocation. Gmail `gmail.readonly` is restricted scope, and a public app storing its data may require Google's verification/security assessment. Alternative initial route: user manually forwards relevant notices to a dedicated company mailbox for manual intake; no automatic consumer Voice controls.
3. Parse only allowlisted, corroborated Google Voice notification headers/content types; preserve Gmail message ID and original raw reference where legally authorized. Treat third-party and forwarded content as untrusted.
4. In C-FAB create `INBOUND` email-derived notification, with original notification timestamp, system ingested timestamp, provenance, dedupe and confidence. No manufactured voice provider webhook or delivery state. Incomplete data -> `UNKNOWN`.
5. Contact/engagement match is tentative until validated; phone number is a locator not authentication. No auto-reveal of case status in response to unverified inbound phone/SMS.
6. DARI (identity- and role-scoped) may summarize, label, and draft a *suggested* response. Dispatcher schedules and follows up on human callback.
7. Human calls/replies in official Google Voice app, then optionally marks outcome in ColettiOS; C-FAB labels as user-reported, not independently provider-verified. Optional related message goes via separate lawful Resend/portal connector with its own source and send evidence.

## Acceptance / stop gates

- Gmail forwarding test for missed call, voicemail, inbound SMS with dedupe, ambiguous/no caller data, malformatted content and disabled forwarding.
- Gmail OAuth scope consent and privacy impact, least permission, token refresh/revoke, Google restricted-scope security requirements review, employee isolation.
- No Google Voice automated call, outbound SMS, web-driver integration, group messaging or auto receptionist route, including if DARI requests it.
- Human confirms callback/SMS outcome; provider status remains unverified rather than "delivered"; read receipt only for authenticated ColettiOS messages.
- Rate/usage/number reclaim policy, no unwarranted business suitability claim; paid provider fallback path remains provider neutral.
- Regulated recording/transcription consent, retention, audit and confidentiality; do not record outside Voice's supported settings.
- Real account, genuine user authentication, and actual notification acceptance **before** operational status.

**Release disposition:** proposal only. Current C-FAB 10 tables have RLS but no provider accounts, communication events or delivered notifications as last inspected; existing `public.portal_messages` is separate. Any migration/provider integration or external-client production requires its own authorization, QA and release evidence.
