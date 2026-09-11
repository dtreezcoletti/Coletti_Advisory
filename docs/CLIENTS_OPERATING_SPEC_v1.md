# Coletti & Co. — Clients Operating Specification v1

**Status:** APPROVED / ADOPTED / AUTHORIZED THROUGH DEPLOYMENT  
**Authority:** Owner approval in operating session  
**Applies to:** Coletti & Co. Client relationship management, ColettiOS, DARI, Dispatcher, Owner/Admin/Staff interfaces  
**Production effect:** This specification does not by itself authorize overall production. `production_authorized = false` remains controlling until the production gates pass.

## 1. Purpose

Clients is the authoritative institutional record of whom Coletti & Co. has accepted into a professional relationship. It preserves identity and relationship continuity across engagements while keeping case work, records, contracts, billing, reporting, referrals, and institutional documents in their respective authoritative systems.

Clients is not a generic CRM, not a lead list, and not a Case workspace.

## 2. Lifecycle

The canonical relationship path is:

`Prospect / Referral → Intake → Screening → Acceptance → Client → Contract → Case`

Intake states remain:

`DRAFT → SUBMITTED → IN_REVIEW → ACCEPTED / DECLINED / WITHDRAWN`

Client relationship states are:

`ONBOARDING → ACTIVE → INACTIVE → ARCHIVED`

A declined or withdrawn intake is not an inactive Client; it never became a Client relationship.

## 3. Identity

- One permanent Client ID is retained across all engagements.
- Client IDs follow the canonical `CYY-NN` format and are immutable once issued.
- Auth User is not equivalent to Client.
- One Client, especially an organization, may have multiple authorized portal users.
- Portal identities therefore connect to Clients through a controlled relationship mapping rather than a `user_id` column on the canonical Client record.
- Case and Source identifiers remain separately scoped and immutable.

## 4. Authoritative data boundaries

Clients owns:
- Client ID and canonical relationship identity.
- Client type: individual or organization.
- relationship status and enrollment date/year.
- relationship contact details and communication preferences.
- referral source and relationship owner.
- authorized Client portal identities.
- relationship-level next action and attention state.
- pointers to Cases, Contracts, Billing, Reports, and Referrals.
- Client relationship audit history.

Clients does not own:
- Case findings or Case scope.
- uploaded source records.
- report drafting.
- institutional financial ledgers.
- editable pricing architecture.
- institutional policies or templates.
- Chapter 2 information.
- unrelated client/case information.

## 5. Screen contract

### Directory
The Clients landing screen must support:
- search by Client ID and relationship name;
- Owner/Admin search by email and phone;
- Case ID search only where the viewer can access that Case;
- status filters;
- Active / Onboarding / Needs Attention / Inactive-Archived metrics;
- relationship owner, active Case count, portal state, next action/date;
- drill-through to Client Detail, Cases, and DARI.

### Client Detail
The Client Detail screen contains:
- permanent Client ID, name, type and relationship status;
- relationship contact information according to role;
- Case history according to Case authorization;
- Contracts, Billing, authorized portal users, and full audit for Owner/Admin only;
- Reports according to Case authorization;
- relationship-level next action;
- controlled edit/status/portal-access actions for Owner/Admin.

### Intake & Acceptance
Owner/Admin must be able to review submitted/in-review intake, see duplicate candidates, classify individual/organization, and explicitly accept the relationship. Acceptance must not automatically open a Case.

## 6. Permissions

### Owner
Institution-wide Client relationship visibility and controlled mutation authority.

### Admin / delegated management
Broad Client relationship operations subject to Owner policy and protected gates.

### Analyst / Reviewer / Case worker
May see Client identity only where an active Case assignment gives access. Minimum-necessary relationship metadata applies. No institution-wide Client browsing, pricing visibility, portal-user administration, contract details, invoices, or full Client audit.

### Client / authorized portal user
May see only their own Client relationship and only Cases where explicit Case membership gives access. Being an authorized Client relationship user does not automatically grant access to every Case under an organizational Client.

## 7. Acceptance authority

Final `ACCEPTED` and `DECLINED` decisions are human-controlled. At launch, Owner/Admin authority is required. DARI and ordinary staff may surface, summarize, and recommend but may not independently accept or decline.

## 8. Acceptance automation

When an intake is accepted, the system must:
1. create or reuse the permanent Client relationship;
2. generate the canonical Client ID through the authoritative allocator when a new Client is required;
3. link the primary authenticated Client user;
4. create the relationship profile;
5. preserve the accepted intake link and audit event;
6. queue pricing confirmation;
7. queue controlled contract preparation;
8. queue portal-access confirmation;
9. queue Case-opening readiness behind contract/scope/pricing gates;
10. avoid claiming any external notification was sent unless a real communications channel records delivery.

## 9. Duplicate control

The system must warn on likely duplicates using, at minimum:
- exact email;
- normalized phone;
- exact canonical/preferred relationship name.

Duplicate detection may block creation, but the system and DARI may not autonomously merge Client relationships. Human confirmation is required for any merge/correction affecting canonical identity.

## 10. DARI behavior

DARI may:
- find accessible Clients by Client ID/name;
- summarize accessible relationship history;
- surface due Client relationship actions;
- find active Clients with no active accessible Case;
- identify referral source when the user is authorized to see it;
- list accessible Cases for a selected Client;
- draft or route ordinary work while preserving human gates.

DARI may not:
- expand the viewer's Client or Case permissions;
- accept/decline a Client autonomously;
- grant/revoke portal access autonomously;
- change pricing or contracts;
- publish reports;
- delete or merge canonical Client history;
- make protected professional determinations.

Client context passed from Clients to DARI is context only. Authorization remains independently enforced by the Client/Case RPCs and the current principal.

## 11. Cross-system handoffs

- **Cases:** Clients answers who; Cases answers what engagement is being performed. Case creation remains separately gated.
- **Records:** Records are Case-scoped. Clients may aggregate counts/links but does not own free-floating records.
- **Reports:** Reports remain Case-bound; Clients displays authorized relationship history.
- **Referrals:** incoming referral source and outgoing professional handoff are linked but remain authoritative in Referrals.
- **Finance:** Clients may display summaries; Finance remains authoritative for firm economics.
- **Billing:** invoices/payments/receivables remain authoritative in Billing.
- **Contracts:** authority and engagement scope remain authoritative in Contracts.
- **Pricing:** Clients stores only the approved classification/treatment; Pricing owns the price rules.
- **Documents:** institutional policies/templates belong in Documents; client source material does not.

## 12. Audit requirements

The audit trail must preserve actor/time and relevant before/after state for:
- intake decision;
- Client relationship creation;
- status changes;
- relationship/profile edits;
- portal access grant/update/revocation;
- onboarding workflow creation;
- canonical identity correction or future merge;
- archival or reactivation.

No hard deletion or silent historical overwrite is permitted for canonical Client history.

## 13. Acceptance criteria

Clients v1 is not Operational merely because the page renders. Verification requires:
- declined/withdrawn intake cannot generate a Client ID through acceptance;
- accepted new intake creates exactly one canonical Client relationship;
- repeated/existing primary identity reuses the Client rather than creating another silently;
- likely duplicate email/phone blocks automatic new relationship creation;
- Client ID is generated by the authoritative database allocator, not UI code;
- analysts/reviewers cannot browse unrelated Clients;
- Clients may not see another Client relationship;
- organizational relationship access does not expose unauthorized Cases;
- Cases, Reports, Billing, Contracts and Portal Access respect their separate authority boundaries;
- Client status changes and portal-access actions are audited;
- acceptance queues onboarding work instead of auto-opening a Case;
- DARI Client lookup obeys the same Client/Case permissions;
- archive preserves history.

## 14. Cost / operating posture

Clients v1 uses the existing Supabase, ColettiOS, Streamlit Owner Console, Dispatcher/Owner work-item system and DARI integration. No new paid platform is required for implementation. Provider-dependent DARI reasoning may remain unavailable while OpenAI API credits are not funded; deterministic Client lookup does not require paid model use.
