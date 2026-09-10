# Coletti Ecosystem Design-to-Operational Lifecycle

Authoritative lifecycle:

**Designed → Coded → Data Wired → Permission Tested → Drill-Through Verified → Cross-Interface Verified → Golden Path Passed → Messy Path Passed → Operational**

This lifecycle applies to ColettiOS, Coletti & Co. interfaces, DARI, Dispatcher-facing capabilities, back-office functions, integrations, portals, and material system features.

## Stage language

| Stage | Meaning | Allowed language | Not allowed yet |
| --- | --- | --- | --- |
| Designed | Behavior, architecture, UX, rules, and acceptance criteria are defined and approved. | Designed; approved design; planned implementation. | Built; implemented; connected; working; operational. |
| Coded | Executable implementation exists in the repository. | Coded; implemented in code; build exists. | Data connected; verified; operational. |
| Data Wired | The capability reads/writes the correct authoritative systems and required persistent state is not session-only or duplicated. | Data wired; connected to authoritative data; using the system of record. | Permission verified; fully connected; operational. |
| Permission Tested | Positive and negative role/access cases have passed. | Permission tested; RBAC verified; access boundaries verified. | Cross-interface verified; production ready; operational. |
| Drill-Through Verified | Every meaningful card, KPI, alert, notification, DARI result, count, status, or summary reaches the authoritative object or canonical workspace that produced it. | Drill-through verified; connected; canonical routing verified. | Fully operational across all interfaces; operational. |
| Cross-Interface Verified | The same underlying object/state behaves consistently across authorized Owner, Admin, Employee, and Client views. | Cross-interface verified; role views reconciled; single authoritative state confirmed. | End-to-end proven; operational. |
| Golden Path Passed | The intended clean end-to-end workflow succeeds without manual workaround. | Golden Path passed; standard end-to-end workflow verified. | Edge-case hardened; operational. |
| Messy Path Passed | Real-world/adversarial conditions succeed or fail safely without silent corruption, permission leakage, or lost lineage. | Messy Path passed; real-world resilience verified; edge cases verified. | Operational until deployment and post-deployment smoke verification pass. |
| Operational | Every prior gate passed, intended-environment deployment/activation succeeded, post-deployment smoke verification passed, and the capability is available for normal use. | Operational; live; active; available for normal use. | N/A. |

## Connection Law / Drill-Through Interface Contract

> Every meaningful dashboard card, DARI result, notification, KPI, alert, count, status, and actionable summary must resolve to the authoritative object or filtered canonical workspace that produced it. A display-only duplicate of operational state is not connected and cannot be marked Operational.

**Connected** is reserved for capabilities at **Drill-Through Verified** or later. A database call alone is not enough.

## Dashboard rule

**Dashboard = summary of canonical workspaces, never a second system.**

A dashboard may aggregate or summarize authoritative state, but it must not create an independent copy of that state or require a second workflow to resolve the same item.

Examples:

- Decisions count → the exact Review Center / owner-decision records.
- Blocker count → the exact Fix Center/case blockers.
- Carryover → the exact Dispatcher work items.
- Receivables → the invoices/payments that calculate the receivable total.
- Contract-awaiting-action count → those contract records.
- Team capacity → the workload/case assignments used in the capacity calculation.
- Knowledge health → the exact Knowledge/Docket items producing the count.

## Deployment

Deployment is an activation action rather than a separate lifecycle stage:

**Messy Path Passed → Deploy → post-deployment smoke verification → Operational**

A merged PR, successful build, or deployed page does not by itself qualify a capability as Operational.
