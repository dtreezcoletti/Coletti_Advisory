from __future__ import annotations

from typing import Any


DEMO_CASES: tuple[dict[str, Any], ...] = (
    {
        "engagement_id": "eng-synthetic-demo",
        "case_id": "JRC-1145-01",
        "client": "Apex Construction",
        "name": "Vendor Records Reconciliation",
        "service": "Full Reconstruction",
        "stage": "Human Review",
        "priority": "High",
        "due_date": "Sep 14, 2026",
        "assignment": "Primary Analyst",
        "next_action": "Resolve the amount variance and prepare the reviewer packet.",
        "sources": 18,
        "propositions": 27,
        "contradictions": 4,
        "workload_points": 8,
    },
    {
        "engagement_id": "eng-jrc-1145-02",
        "case_id": "JRC-1145-02",
        "client": "Northfield Services",
        "name": "Payroll & Expense Reconstruction",
        "service": "Diagnostic / Scoped Reconstruction",
        "stage": "Analysis",
        "priority": "High",
        "due_date": "Sep 16, 2026",
        "assignment": "Primary Analyst",
        "next_action": "Compare payroll registers to expense reimbursements and isolate unresolved periods.",
        "sources": 14,
        "propositions": 21,
        "contradictions": 2,
        "workload_points": 7,
    },
    {
        "engagement_id": "eng-jrc-1145-03",
        "case_id": "JRC-1145-03",
        "client": "Meridian Supply Group",
        "name": "Contract & Invoice Gap Review",
        "service": "Document Gap & Contradiction Review",
        "stage": "Evidence",
        "priority": "Normal",
        "due_date": "Sep 18, 2026",
        "assignment": "Supporting Analyst",
        "next_action": "Finish source indexing and identify missing contract amendments.",
        "sources": 11,
        "propositions": 7,
        "contradictions": 1,
        "workload_points": 4,
    },
    {
        "engagement_id": "eng-jrc-1145-04",
        "case_id": "JRC-1145-04",
        "client": "Bellwether Operations",
        "name": "Operational Timeline Reconstruction",
        "service": "Full Reconstruction",
        "stage": "Record Ingestion",
        "priority": "Normal",
        "due_date": "Sep 22, 2026",
        "assignment": "Primary Analyst",
        "next_action": "Review the intake manifest and begin controlled source registration.",
        "sources": 0,
        "propositions": 0,
        "contradictions": 0,
        "workload_points": 3,
    },
    {
        "engagement_id": "eng-jrc-1145-05",
        "case_id": "JRC-1145-05",
        "client": "Harbor Point Holdings",
        "name": "Insurance Records Reconstruction",
        "service": "Full Reconstruction",
        "stage": "Report Preparation",
        "priority": "High",
        "due_date": "Sep 12, 2026",
        "assignment": "Reviewer Support",
        "next_action": "Reconcile reviewer changes and prepare the controlled draft report.",
        "sources": 22,
        "propositions": 34,
        "contradictions": 3,
        "workload_points": 6,
    },
    {
        "engagement_id": "eng-jrc-1145-06",
        "case_id": "JRC-1145-06",
        "client": "Crescent Field Partners",
        "name": "HR Process Reconstruction",
        "service": "Diagnostic / Scoped Reconstruction",
        "stage": "Reconciliation",
        "priority": "Low",
        "due_date": "Sep 25, 2026",
        "assignment": "Secondary Analyst",
        "next_action": "Resolve the remaining chronology conflict and document the reconciliation basis.",
        "sources": 16,
        "propositions": 19,
        "contradictions": 2,
        "workload_points": 4,
    },
)

DEMO_CASE_BY_ENGAGEMENT = {item["engagement_id"]: item for item in DEMO_CASES}
DEMO_ALL_ENGAGEMENT_IDS = tuple(item["engagement_id"] for item in DEMO_CASES)
DEMO_EMPLOYEE_ENGAGEMENT_IDS = tuple(item["engagement_id"] for item in DEMO_CASES[:4])
DEMO_CLIENT_ENGAGEMENT_ID = DEMO_CASES[0]["engagement_id"]


def is_portfolio_engagement(engagement_id: str) -> bool:
    return engagement_id in DEMO_CASE_BY_ENGAGEMENT


def portfolio_case(engagement_id: str) -> dict[str, Any] | None:
    return DEMO_CASE_BY_ENGAGEMENT.get(engagement_id)


def portfolio_label(engagement_id: str) -> str:
    item = portfolio_case(engagement_id)
    if item is None:
        return engagement_id
    return f"{item['case_id']} · {item['name']}"


def empty_manifest_for_case(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_meta": dict(item),
        "sources": {},
        "source_states": {},
        "propositions": {},
        "contradictions": {},
        "escalations": {},
        "reconciliations": {},
        "reviewer_conclusions": {},
        "state_history": [],
        "audit_log": [],
    }


def build_manifest_for_case(item: dict[str, Any]) -> dict[str, Any]:
    manifest = empty_manifest_for_case(item)
    slug = item["case_id"].replace("JRC-", "").replace("-", "")

    for index in range(1, int(item["sources"]) + 1):
        source_id = f"SRC-{slug}-{index:03d}"
        manifest["sources"][source_id] = {
            "source_id": source_id,
            "content_hash": f"synthetic-{slug}-hash-{index:03d}",
            "metadata": {
                "filename": f"synthetic_{item['case_id'].lower()}_{index:03d}.pdf",
                "classification": "Business Record" if index % 2 else "Operational Record",
                "synthetic": True,
            },
        }
        manifest["source_states"][source_id] = (
            "DISPUTED" if index <= int(item["contradictions"]) * 2 and index % 2 == 0 else "CORROBORATED"
        )

    source_ids = list(manifest["sources"])
    for index in range(1, int(item["propositions"]) + 1):
        proposition_id = f"PROP-{slug}-{index:03d}"
        source_id = source_ids[(index - 1) % len(source_ids)] if source_ids else None
        manifest["propositions"][proposition_id] = {
            "proposition_id": proposition_id,
            "text": f"Synthetic proposition {index} for {item['case_id']}.",
            "source_ids": [source_id] if source_id else [],
        }

    proposition_ids = list(manifest["propositions"])
    for index in range(1, int(item["contradictions"]) + 1):
        if len(proposition_ids) < 2:
            break
        a_index = ((index - 1) * 2) % len(proposition_ids)
        b_index = (a_index + 1) % len(proposition_ids)
        contradiction_id = f"CON-{slug}-{index:03d}"
        manifest["contradictions"][contradiction_id] = {
            "contradiction_id": contradiction_id,
            "proposition_a": proposition_ids[a_index],
            "proposition_b": proposition_ids[b_index],
            "reason": f"Synthetic conflict {index} requires controlled review.",
        }
        task_id = f"TASK-{slug}-{index:03d}"
        manifest["escalations"][task_id] = {
            "task_id": task_id,
            "subject": f"Resolve synthetic conflict {index}",
            "reason": "Two source-linked propositions conflict.",
            "source_ids": source_ids[a_index : a_index + 2],
            "status": "OPEN",
        }

    if item["stage"] in {"Reconciliation", "Human Review", "Report Preparation"} and proposition_ids:
        reconciliation_id = f"REC-{slug}-001"
        manifest["reconciliations"][reconciliation_id] = {
            "reconciliation_id": reconciliation_id,
            "proposition_ids": proposition_ids[: min(3, len(proposition_ids))],
            "contradiction_ids": list(manifest["contradictions"])[:1],
            "outcome": "Synthetic reconciliation prepared for review.",
            "actor": "usr-synthetic-employee",
            "rationale": "Demonstration-only reconciliation used to exercise employee workflow.",
        }

    if item["stage"] in {"Human Review", "Report Preparation"}:
        manifest["reviewer_conclusions"][f"REV-{slug}-001"] = {
            "review_id": f"REV-{slug}-001",
            "status": "PENDING" if item["stage"] == "Human Review" else "APPROVED",
            "summary": "Synthetic reviewer disposition for employee-portfolio testing.",
        }

    return manifest


DEMO_MANIFESTS = {
    item["engagement_id"]: build_manifest_for_case(item)
    for item in DEMO_CASES
}
