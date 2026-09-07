# Coletti & Co. Operational Website

This directory contains the browser-based operational front end for Coletti & Co. It is designed to coexist with the existing Python/Streamlit commercial application while providing a public website, Secure Client Gateway, employee operations workspace, and owner/admin command center backed by Supabase.

## Surfaces

### Public
- Home
- Services
- How It Works
- About
- Professional Referral Partners
- Pricing & Engagement
- Security & Privacy
- FAQ
- Contact / Request Consultation
- Privacy Notice
- Terms
- Professional Services Disclaimer

### Client portal
- Passwordless secure sign-in
- Intake
- Identity/contact profile
- Engagement acknowledgment / e-sign placeholder
- Private document upload
- Document requests
- Client-visible case timeline
- Client messaging
- Meeting requests
- Invoices/payment links
- Published reports with short-lived signed download URLs
- Support requests

### Employee workspace
- Assigned cases
- Intake review
- Document completeness
- Evidence/provenance work items
- Contradiction and reconciliation queues
- Review narratives
- Client document requests/deadlines
- Private case notes
- QA checklist
- Publication handoff

### Owner/admin command center
- Users and roles
- Case assignment
- Application audit trail
- Access model
- Services/pricing
- Template catalog
- Publication controls
- Analytics/KPIs
- Billing overview
- Referral pipeline
- Capacity/workload
- System health
- Security alerts
- Backup/recovery status
- Settings

## Backend

Supabase project: `Colettico` (`lepdppbygnevzcquvmtt`)

Applied migrations:
- `20260907024453 operational_frontend_v1`
- `20260907024722 operational_frontend_hardening_v1`
- `20260907024940 operational_frontend_admin_role_rpc_v1`
- `role_rpc_security_invoker_v1` (applied immediately after the RPC migration; run `Supabase.list_migrations` for its generated version)

The operational website does **not** replace the authoritative ColettiOS institutional registry. The existing registry remains the source of truth for CLIENT → CASE → SOURCE → PROPOSITION → REVIEW → FINDING → REPORT. The website adds workflow and delivery state around that ladder.

## Security model

- Browser code uses only the Supabase publishable key.
- Never put a service-role or `sb_secret_` key in `web/`.
- Client data is protected by row-level security, case membership, and authenticated identity.
- Staff case work is protected by case assignment.
- Internal case notes, internal evidence work items, review narratives, QA, and publication handoff are not available through client policies.
- Final client downloads come only from the private `published-reports` bucket and use short-lived signed URLs.
- Client documents use the private `client-documents` bucket.
- Operational mutations create audit events with sensitive free-text fields removed from the safe audit snapshot.
- The mirrored `profiles.role` value is for UI display. Authorization truth remains in `private.user_roles`.
- Admin role changes use the `admin_set_user_role` RPC as `SECURITY INVOKER`; admin-only RLS on the private role table remains the enforcement boundary and the last active owner cannot be demoted.

## Important activation note

At the time this frontend was created, the Supabase project contained zero Auth users. New Auth users default to the `client` role. The first real owner account must therefore be created and explicitly promoted to `owner` through an authorized administrative step before the owner/admin command center can be used. Do not implement a public “first user becomes owner” bootstrap flow.

## Sites/static deployment

The site is intentionally build-free: serve `web/` as the static document root with `index.html` as the entry point. It uses hash-based routes so it does not require server-side route rewrites. If a site builder/importer expects a static source directory, use the contents of `web/`.

Before external commercial launch, complete these gates:
1. Create and promote the real owner Auth account.
2. Verify Supabase Auth email/magic-link configuration and allowed redirect URLs for the production domain.
3. Replace the engagement acknowledgment placeholder with the approved controlled engagement/e-sign workflow.
4. Configure the actual payment provider URLs/webhooks.
5. Connect Google Calendar/Gmail/Drive only after authorization and audit boundaries are approved.
6. Finalize controlled privacy, retention, incident-response, terms, and jurisdiction-specific legal language.
7. Perform browser/role acceptance tests with separate client, analyst, reviewer, and owner accounts.

## Service boundary

Coletti & Co. is not a law firm, accounting firm, or investigative agency. The website must not imply otherwise. No certification, regulatory designation, security certification, or compliance status should be claimed unless it has actually been established and documented.
