# Coletti & Co. — Client Lifecycle SOP v1

**Status:** APPROVED / ADOPTED under Clients Operating Specification v1  
**Owner:** Coletti & Co. Owner / delegated Client Administration  
**System authority:** Supabase Registry + controlled Client RPCs  

## Purpose

This SOP governs how a prospective relationship becomes, remains, changes, and eventually closes as a Coletti & Co. Client relationship. It does not replace Case Opening, Contract, Pricing, Records, Billing, Reporting, Referral, or Document Control procedures.

## 1. Prospect / referral received

A prospect may enter through intake, referral, or an authorized administrative pathway. A prospect is not a Client merely because contact information exists.

Required action:
- create or locate intake/referral record;
- capture requested service and relationship contact information;
- preserve referral source when known;
- do not issue a permanent Client ID yet.

## 2. Intake submitted

The prospective Client submits or staff records the intake. Intake state becomes `SUBMITTED`.

Required checks:
- identity/contact completeness appropriate to the requested service;
- requested service is within Coletti & Co. scope;
- obvious professional-boundary issues;
- referral-source accuracy;
- duplicate Client relationship check.

## 3. Screening / review

Authorized staff may move an intake into `IN_REVIEW`, gather missing information, and prepare an acceptance recommendation.

Staff may not independently set a final `ACCEPTED` or `DECLINED` decision unless their role has explicit Owner/Admin authority.

DARI may summarize intake information and surface missing data, but may not make the final decision.

## 4. Final decision

### Accepted
Owner/Admin records the final acceptance. The system then creates or reuses the permanent Client relationship.

### Declined
Owner/Admin records `DECLINED`. No Client ID is generated merely from the declined intake.

### Withdrawn
The intake may be marked `WITHDRAWN` according to the client/staff workflow. Withdrawal does not create a Client relationship.

## 5. Client relationship creation

For a new accepted relationship:
- create the institutional Client identity record;
- let the authoritative identifier allocator issue the immutable `CYY-NN` Client ID;
- set initial Client relationship state to `ONBOARDING`;
- create the relationship profile;
- link the primary authenticated portal user;
- preserve the original intake relationship;
- write the audit event.

If the accepted person is already the primary user of an existing Client relationship, reuse the existing Client relationship unless a human-controlled exception says otherwise.

## 6. Duplicate handling

Before creating a new Client relationship, review system-surfaced duplicate candidates. Exact matching email or normalized phone may block automatic creation.

A potential duplicate must never be autonomously merged. Canonical identity merges/corrections require human authorization and preservation of both prior identifiers/history in the audit trail.

## 7. Onboarding queue

Acceptance creates controlled onboarding work items:
1. confirm Pricing pathway;
2. prepare the controlled engagement Contract;
3. confirm Client portal access;
4. hold Case creation in `WAITING` until contract/scope/pricing gates are satisfied.

Acceptance itself does not create a live Case.

No onboarding step may claim an email/message/notification was sent unless the communications system records actual transmission/delivery state.

## 8. Portal access

The primary Client user is linked to the Client relationship. Additional users may be added only by Owner/Admin authority using one of the controlled relationship roles:
- primary;
- authorized contact;
- billing contact;
- contract contact;
- read only.

Client relationship access does not automatically authorize every Case under that Client. Case access remains separately controlled by Case membership.

Revocation preserves the relationship record, timestamp, actor, and reason. Revocation does not delete the Client.

## 9. Active relationship

A Client may be promoted from `ONBOARDING` to `ACTIVE` once the appropriate engagement/onboarding conditions are satisfied. Client status is relationship state, not Case state.

Multiple Cases may exist under one Client over time. Each Case retains its own immutable Case ID, scope, staff assignments, Records, Reports, Contract links and closeout state.

## 10. Relationship information changes

Owner/Admin may correct controlled relationship information such as contact information, preferred name, communication preference, referral source, next action and authorized pricing classification.

The permanent Client ID must not be casually edited. Material identity correction or future merge follows a controlled human process and preserves audit history.

## 11. Staff access

Staff access follows minimum-necessary principles:
- Owner/Admin: institution-wide as authorized;
- Analyst/Reviewer/Case staff: only Client relationships tied to assigned Cases;
- financial/contract/portal/audit details remain separately restricted;
- clients: their own relationship and only explicitly authorized Cases.

DARI must use the same scoped Client/Case functions and may not expand access.

## 12. Client status transitions

Controlled Client relationship states:
- `ONBOARDING`
- `ACTIVE`
- `INACTIVE`
- `ARCHIVED`

A status change must record actor, old state, new state and reason where the state actually changes.

`INACTIVE` means the relationship is retained but no longer actively operating. `ARCHIVED` means the institutional relationship is retained as historical record. Neither state authorizes hard deletion.

## 13. Cross-system handoff rules

- Pricing classification is confirmed in Pricing.
- Engagement authority/scope is controlled in Contracts.
- Case work begins only in Cases.
- Source/client material is managed under Case-scoped Records.
- deliverables are controlled in Reports.
- professional handoffs route to Referrals.
- client charges/payments route to Billing.
- firm economics route to Finance.
- institutional policies/templates route to Documents.

Clients may summarize and link these systems but does not silently become their authority.

## 14. Audit / closeout

The Client relationship remains auditable through its full life. Closing a Case does not delete or archive the Client automatically. When the relationship itself becomes inactive or archived, historical Cases, Reports, Contracts, Billing and audit records remain preserved according to their own retention controls.

## 15. Exceptions

Any exception that would change canonical identity, merge Clients, broaden access beyond ordinary RBAC, bypass Contract/Pricing/Case gates, or delete historical relationship data requires explicit human authorization and must be auditable.
