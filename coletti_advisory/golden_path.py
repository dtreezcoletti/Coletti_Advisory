from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass

from .publication import (
    PublicationStatus,
    approve_report,
    published_reports,
    report_fingerprint,
    send_to_review,
    sync_drafts,
)
from .reporting import build_report_bundle


JRC_CASE_ID = "JRC-1145-01"
JRC_ENGAGEMENT_ID = "eng-jrc-1145-01"


JRC_MANIFEST = {
    "case_id": JRC_CASE_ID,
    "sources": {
        "SRB-001": {
            "source_id": "SRB-001",
            "content_hash": "sha256:jrc-ledger-001",
            "metadata": {
                "filename": "jrc_ledger.csv",
                "classification": "Operational Record",
                "synthetic": True,
                "corroboration_basis": "Synthetic blind-control fixture",
            },
        },
        "SRB-002": {
            "source_id": "SRB-002",
            "content_hash": "sha256:jrc-invoice-002",
            "metadata": {
                "filename": "jrc_invoice.pdf",
                "classification": "Business Record",
                "synthetic": True,
            },
        },
    },
    "source_states": {
        "SRB-001": "CORROBORATED",
        "SRB-002": "DISPUTED",
    },
    "propositions": {
        "PROP-001": {
            "proposition_id": "PROP-001",
            "text": "The ledger records a payment on the stated date.",
            "source_ids": ["SRB-001"],
        },
        "PROP-002": {
            "proposition_id": "PROP-002",
            "text": "The invoice records a different amount for the same reference.",
            "source_ids": ["SRB-002"],
        },
    },
    "contradictions": {
        "CON-001": {
            "contradiction_id": "CON-001",
            "proposition_a": "PROP-001",
            "proposition_b": "PROP-002",
            "reason": "The synthetic records disagree on amount for the same reference.",
        }
    },
    "reconciliations": {
        "REC-001": {
            "reconciliation_id": "REC-001",
            "proposition_ids": ["PROP-001", "PROP-002"],
            "contradiction_ids": ["CON-001"],
            "outcome": "Variance remains unresolved pending independent confirmation.",
            "actor": "reviewer-1",
            "rationale": (
                "The available records support documenting the inconsistency, "
                "not choosing one amount as authoritative."
            ),
        }
    },
    "reviewer_conclusions": {
        "REV-001": {
            "conclusion_id": "REV-001",
            "text": "The records establish a variance, but the exact amount remains unresolved.",
            "reviewer": "reviewer-1",
            "proposition_ids": ["PROP-001", "PROP-002"],
            "rationale": (
                "Human review accepted the existence of the conflict and rejected "
                "silent promotion of either record."
            ),
        }
    },
    "escalations": {
        "TASK-001": {
            "task_id": "TASK-001",
            "subject": "Obtain independent confirmation",
            "reason": "The amount variance remains unresolved.",
            "source_ids": ["SRB-001", "SRB-002"],
            "status": "OPEN",
        }
    },
    "state_history": [],
    "audit_log": [
        {
            "event_type": "JRC_GOLDEN_PATH_INPUT",
            "subject_id": JRC_CASE_ID,
            "actor": "golden-path",
            "detail": "Blind synthetic fixture loaded for commercial/report acceptance.",
        }
    ],
}


@dataclass(frozen=True)
class CommercialGoldenPathResult:
    case_id: str
    report_types: tuple[str, ...]
    report_fingerprints: dict[str, str]
    publication_gate_statuses: dict[str, str]
    publication_records: dict[str, dict]
    published_report_types: tuple[str, ...]
    human_review_staged: bool
    exact_report_publication_invoked: bool


def run_jrc_1145_01_delivery() -> CommercialGoldenPathResult:
    """Build client-facing drafts from JRC-1145-01 and stop before publication.

    The harness proves report generation, readiness assessment, version hashing,
    review/approval state, and the final publication boundary without publishing
    or delivering anything externally.
    """

    manifest = deepcopy(JRC_MANIFEST)
    reports = build_report_bundle(manifest)
    records = sync_drafts({}, reports)

    # Exercise the human-review lifecycle on the synthetic fixture without
    # calling publish_report. Approval is not publication.
    for report_type, record in records.items():
        send_to_review(
            record,
            actor="synthetic-reviewer",
            note="JRC-1145-01 controlled Golden Path review",
        )
        approve_report(record, actor="synthetic-approver")
        if record.status != PublicationStatus.APPROVED:
            raise AssertionError(f"report did not reach approved state: {report_type}")

    visible = published_reports(records)
    fingerprints = {
        report_type: report_fingerprint(report)
        for report_type, report in reports.items()
    }
    gate_statuses = {
        report_type: str(report["publication_gate"]["status"])
        for report_type, report in reports.items()
    }

    return CommercialGoldenPathResult(
        case_id=JRC_CASE_ID,
        report_types=tuple(reports.keys()),
        report_fingerprints=fingerprints,
        publication_gate_statuses=gate_statuses,
        publication_records={
            report_type: asdict(record)
            for report_type, record in records.items()
        },
        published_report_types=tuple(visible.keys()),
        human_review_staged=True,
        exact_report_publication_invoked=False,
    )
