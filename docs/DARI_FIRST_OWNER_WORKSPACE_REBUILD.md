# DARI-First Unified Owner Workspace Rebuild

Status: IMPLEMENTING on `owner-console-rebuild`

## Product rule

The owner does not receive a separate executive application. The owner signs into the same core internal workspace as employees, with owner authority layered on top of that experience.

**Owner = employee workspace + owner capabilities.**

Role expands capability; it does not replace the operating experience.

## Required morning flow

For an authenticated internal user, the workday entry flow is:

`Login → Start My Day → acknowledge brief → DARI-first workspace`

The Start My Day brief is the first operating screen and is modeled after the 9 a.m. execution brief. It must surface:

1. update / carryover from yesterday;
2. everything explicitly due today from connected authoritative systems;
3. decisions and approvals requiring the human user;
4. blockers and dependency warnings;
5. capacity signal when the protected capacity adapter is available;
6. a concrete success definition for the day.

The user must acknowledge the brief before entering the normal internal workspace for that day/session.

## Main workspace hierarchy

After acknowledgment, the primary operating surface is DARI, not a KPI dashboard.

Permanent high-priority DARI commands:

- What needs my decision?
- What should I work on next?
- Find anything

Secondary commands:

- Show production blockers
- Continue where I left off

The supporting workspace should then surface, in order:

1. DARI command/chat entry;
2. Needs Your Decision / Needs Your Review;
3. Continue Working;
4. Workspace / Firm Pulse;
5. owner-only controls when role permits.

Metrics are context. They are not the primary operating surface.

## Owner-only capability layer

The owner retains the same normal case and evidence workflow as employees and additionally receives access to owner-controlled capabilities such as:

- System Lab;
- Administration & Security;
- publication and human approval controls;
- production readiness;
- governance / audit surfaces;
- future Dispatcher, Implementation Matrix, firm capacity, and financial-control surfaces.

These capabilities must never create a second owner identity or a separate owner-only day-to-day workflow.

## Desktop target

Desktop uses the existing ivory / brass Coletti visual system with:

- left navigation;
- unified internal profile treatment;
- DARI centered in the main working area;
- owner powers integrated lower in the same workspace;
- responsive work cards instead of a wall of analytics tiles.

## Mobile target

Mobile preserves the same information hierarchy and provides a persistent bottom shortcut dock with DARI visually centered. The first mobile screen remains Start My Day until acknowledged.

## Safety / authority constraints

This rebuild is a presentation and operating-flow change only. It does not weaken or bypass:

- authentication / RBAC;
- engagement isolation;
- source lineage or provenance;
- human review;
- publication gates;
- production authorization;
- security controls.

DARI must prefer deterministic system state before generated reasoning and must not manufacture missing deadlines, approvals, blockers, or capacity data.

## Current implementation boundary

The first implementation slice wires the new shell to currently connected engagement, evidence, review, report, and production-gate data. A complete cross-system Start My Day brief still requires authoritative Dispatcher / Google Calendar due-today wiring and the protected capacity adapter. Until those adapters exist, the UI must explicitly disclose that those signals are not yet connected rather than inventing them.
