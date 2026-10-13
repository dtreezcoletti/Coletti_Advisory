# ColettiOS Unified V1 2027 — Departmental Ownership and Identity-Scoped DARI

**Status: Proposed pre-lock architecture contract — not a role migration, staff restructuring, deployment, access grant or external-client production authorization.**
**October 13, 2026 correction:** DARI serves **the individual who is authenticated**, not exclusively the Owner and staff. It applies that person's verified institutional role, assigned case positions, approved realm permissions, scope, consent and intended operation to every tool call and context retrieval. No unrestricted sharing based on being the same organization.

## Principle

Coletti & Co. owns business departments and workflows. **DARI is the common intelligence service operating within each authenticated person's permission envelope; departments do not sit under DARI as autonomous authorities.** Dispatcher owns deterministic work scheduling and escalation. C-FAB owns correspondence history, state and delivery. ColettiOS Core owns record reconstruction, source integrity and First Truth. Supabase Auth/Registry is authoritative for identity, authorization and institutional state.

The proposed receptionist unit is named simply **Reception & Communications** (user-facing **Reception**); retire the working name ATRIUM. Do not invent another independent AI personality, database, login, brand, model runtime, task scheduler or delivery engine.

## Functional departmental charters (logical units, not 8 staffed teams or apps)

| Domain ID | Department | Owns business responsibility | Must not own |
| --- | --- | --- | --- |
| GROWTH | Growth & Partnerships | Marketing, referrals, lead sources, audience, approved campaigns, acquisition measurement | Case truth or contractual acceptance |
| CLIENT | Client Relations & Engagement | Qualification, consultation, contracts/onboarding readiness, client relationships, service support | Reconstruction conclusions, source state or QA release |
| CASEOPS | Case Operations | Case coordination, dependencies, capacity, human assignments, service milestones | Independently mutate Dispatcher authoritative timers or protected publication |
| RECORDS | Records & Reconstruction | Source registration, Evidence Passport, timeline, entity and transaction reconciliation, contradiction register, preliminary analyses | Human reviewer status or publishing its own claims |
| REVIEW | Quality & Publication | Adversarial Review Pair, Fresh Eyes coordination, QA evidence, approved reports and Professional Handoff Capsule preparation | Self-certification by AI, cross-client sharing or unapproved sends |
| COMMS | Reception & Communications | Business phone, SMS, voicemail, human correspondence routing, portal message lifecycle, template previews/notes, provider delivery/receipt reconciliation | Client acceptance, privileged case conclusions, private DOMUS context, autonomous contract amendments |
| FINADMIN | Finance & Administration | Invoicing, payment reconciliation, service pricing administration, operating cost analysis, HR admin | Move money or waive contract terms without separate authority |
| TECHGOV | Technology & Governance | Deployment, identity/security, compliance controls, backups, runbooks, provider integration observability, release manifests | Unilateral production or identity privilege promotion |

Departments may share staff and case participants. Financial/system operators are authorized via scoped roles, not implied by a navigation tab.

## DARI persona resolution

**One DARI model/orchestrator and collaboration standard**, with isolated per-user context. DARI's identity-aware policy gateway computes:

`authenticated_principal + verified_identity_roles + case_membership_and_positions + resource_classification + domain/realm + purpose + current_authorization + consent/delegation + message_origin -> allowable tools, context and actions`.

Never trust client-supplied role, email, case ID, front-end tabs, prompt-provided “I am the Owner” or assistant instruction as authorization. JWT/session and database RLS/RPCs verify each request. Privileges recalculate on each operation, not just once at login. Role revocation and session deactivation invalidate access and previously cached context.

### Audience experiences

- **Owner:** all explicitly authorized company modules, controls, institutional scope and private person-scoped DOMUS. Owner override is logged and never bypasses First Truth, independent human QA or external-disclosure controls.
- **Executive:** authorized institutional oversight, decisions and reporting; no private Owner DOMUS.
- **Admin:** authorized intake, people, finance administration and communications; no blanket protected source access.
- **Employee and assigned Analyst/Case Manager/Reviewer:** permitted role responsibilities and assigned-case sources; independent-review separation remains enforced.
- **Contractor:** time-bounded and case/position-limited scope, no tenant-wide directory or private Owner/employee data, immediate revocation on assignment termination.
- **Client:** their accepted contracts, their own case information approved for client view, portal messages, source requests, released reports and approved self-service tools; no employee/internal deliberations, unapproved draft findings or other clients' cases. DARI is an authenticated client assistant, not an internal employee proxy.
- **Outside professional:** an authenticated temporary, recipient-scoped Professional Handoff Capsule and related approved communication functions only; no ability to browse the internal DARI corpus or registry.
- **Anonymous website visitor / unauthenticated phone caller:** reception/intake FAQ only, no authenticated DARI memory, no case record access. Caller ID alone is not identity.

**Personal DARI:** Owner's DOMUS must be tied to a person-specific authenticated identity, not the “Owner” role. Offering personal memory to other staff or clients later requires explicit privacy architecture, person-scoped storage and consent, never automatic cross-employment profiling. Institutional working preferences can be remembered only with an eligible user opt-in and no private organizational information leakage.

## Department routing and cross-domain handoffs

DARI selects a specialist **capability/skill**, not a new agent personality or separate department-level database. Tools are namespaced by domain and statically authorized. A department acts only via its restricted app/RPC adapter and may not directly impersonate another.

Every handoff requires: origin/principal, destination, domain and case/client scope, specific purpose, allowed fields or source references, expiry, authorization/delegation, security classification, correlation ID, idempotency and audit. Default deny for unknown case/recipient; neither DARI nor communications messages may expand the handoff.

Examples:
- Phone call -> COMMS records untrusted caller request -> CLIENT assesses eligible lead -> Dispatcher creates approved callback job. No caller privileges to case records.
- Client message about missing evidence -> COMMS case-scoped event -> CASEOPS follow-up -> RECORDS updates missing-source register only after proper source registration. Client assertion is not a fact.
- Records challenge -> RECORDS fixed source snapshot -> REVIEW adversarial pair and independently authorized human QA -> publication only with policy approval -> COMMS sends authorized report-ready notice and logs provider results.
- Owner private availability issue -> DOMUS proposes neutral availability block -> explicit person-authorized minimal transfer -> OFFICIUM scheduling. Never reveal sensitive personal cause to staff.
- Contractor opens assigned case -> resource access per role, assignment and effective dates; opening unrelated case must be denied even if record is linked elsewhere in Registry.

## Separation of ownership and execution

- **The department** owns outcome/accountability and scoped working UI.
- **DARI** explains, reasons, drafts, assists or requests authorized tool action.
- **Dispatcher** leases/schedules/records real tasks and exceptions.
- **C-FAB** records communication payload references, recipients, views, acknowledgements and send states.
- **Core** classifies/validates records and authorized reconstructions.
- **Registry/Auth** enforces and records institutional truths, roles and release state.
- **Human** accepts protected cases, makes professional judgments, approves independent review, disclosure and publication.
- **Provider adapters** transport, never independently create authoritative institutional state.

## V1 design and implementation minimum

1. Department registry with identifiers, capabilities, owners, allowed data/resource types, policy gates, adapters, no parallel datastore and revision history.
2. Person-based DARI session with roles/assignments resolved from authenticated server claims and RLS-backed authoritative scopes. Client and contractor views are distinct from internal staff and Owner. Anonymous public chatbot is reception only.
3. Single browser app with role-based departmental navigation; departments are **functional organization of views**, not proof of permission.
4. DARI tool gateway enforces department + case + actor + purpose; labels all results with visibility level; prohibits raw DOMUS export to business.
5. Human cross-department handoffs with minimal fields and source references; no implicit AI approval.
6. Separate functional templates/reception scripts without an additional persona, model, or voice-brand entity.
7. Supervisor/Owner controls: audit every consequential action, review denied-access reports, pause delegations/agents per function, display exceptions. No standing permission from role wording alone.

### Required adversarial acceptance

- Every class of principal: Owner, Executive, Admin, Employee, Analyst, QA, Contractor, Client, Professional and anonymous visitor.
- Each attempts permitted and **forbidden** department tools, cross-client cases, source/download endpoints, DOMUS memory, stale session, expired assignment, forged request metadata and client-origin prompt injection.
- Verify client receives a helpful DARI explanation limited to released materials; contractor DARI sees only active contracted assignments; Owner DOMUS never appears in staff notes or external reports.
- A COMMS/Reception request cannot authorize a case finding or disclosure. REVIEW AI pair cannot be reviewer of record, and cannot approve publication or Professional Handoff Capsule send.
- Revoke assignment while session active: case docs, DARI retrieval cache and link access fail closed immediately.
- Role and permission changes persist in Auth/Registry, never model memory alone.
- Ensure real-client, real-staff and optional outside-professional acceptance before calling user-specific DARI production-ready.

**Evidence requirement:** implementation source SHA(s), schema migrations, owner/staff/client/contractor/professional test traces, policy audit, production URL and release manifest. DESIGN != CODED != TESTED != DEPLOYED != OPERATIONAL.
