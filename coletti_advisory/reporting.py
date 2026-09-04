from __future__ import annotations

from typing import Any

from .analysis import (
    build_analytical_issues,
    build_cross_record_comparison,
    build_operations_reconstruction,
    build_records_reconstruction,
    build_state_counts,
    build_summary,
)


REPORT_RECORDS = "Records Reconstruction Report"
REPORT_OPERATIONS = "Operations Reconstruction Report"
REPORT_FINDINGS = "Findings Report"


def _verification_rows(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        recommendation = str(issue.get("Verification recommendation") or "").strip()
        verifier = str(issue.get("Potential verifier") or "").strip()
        if recommendation and verifier and verifier != "—":
            rows.append(
                {
                    "Issue": issue.get("Issue", ""),
                    "Classification": issue.get("Classification", ""),
                    "Recommendation": recommendation,
                    "Potential verifier": verifier,
                    "Supporting sources": issue.get("Supporting sources", ""),
                }
            )
    return rows


def build_publication_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a non-destructive publishing readiness assessment.

    Analysis can populate report drafts, but drafts are never treated as client-
    published output. Any open analytical issue requires explicit human review.
    The current commercial layer does not yet persist final reviewer approval,
    so the gate can become READY FOR REVIEW but never self-authorizes publication.
    """

    issues = build_analytical_issues(manifest)
    if issues:
        status = "REVIEW REQUIRED"
        blockers = [
            f"{item.get('Issue', 'Issue')}: {item.get('Classification', 'Unclassified')}"
            for item in issues
        ]
    else:
        status = "READY FOR REVIEW"
        blockers = []

    return {
        "status": status,
        "published": False,
        "review_required_count": len(issues),
        "verification_recommendation_count": len(_verification_rows(issues)),
        "blockers": blockers,
        "rule": (
            "Report drafts may be generated from reviewed analytical structures, "
            "but client publication requires an explicit human publishing decision."
        ),
    }


def build_records_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    return {
        "report_type": REPORT_RECORDS,
        "document_status": "DRAFT — NOT PUBLISHED",
        "purpose": (
            "Reconstruct what the supplied records establish, with source traceability, "
            "evidence-state context, and unresolved record issues preserved."
        ),
        "summary": build_summary(manifest),
        "evidence_state_summary": build_state_counts(manifest),
        "records_reconstruction": build_records_reconstruction(manifest),
        "unresolved_record_issues": issues,
        "verification_referrals": _verification_rows(issues),
        "boundary": (
            "This report organizes and reconstructs records. It does not convert record-derived "
            "observations into legal, accounting, investigative, or other licensed determinations."
        ),
    }


def build_operations_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    return {
        "report_type": REPORT_OPERATIONS,
        "document_status": "DRAFT — NOT PUBLISHED",
        "purpose": (
            "Reconstruct the operational record set, surface unresolved follow-up, and preserve "
            "record-supported process questions without inventing unsupported process conclusions."
        ),
        "operations_reconstruction": build_operations_reconstruction(manifest),
        "cross_record_comparison": build_cross_record_comparison(manifest),
        "operational_issues": issues,
        "verification_referrals": _verification_rows(issues),
        "boundary": (
            "Operational observations remain tied to the supplied records. Questions requiring "
            "professional judgment are routed for appropriate third-party or professional verification."
        ),
    }


def build_findings_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    return {
        "report_type": REPORT_FINDINGS,
        "document_status": "DRAFT — NOT PUBLISHED",
        "purpose": (
            "Present the engagement-level record findings, inconsistencies, unresolved questions, "
            "and verification/referral needs in one source-linked summary."
        ),
        "engagement_summary": build_summary(manifest),
        "record_comparisons": build_cross_record_comparison(manifest),
        "findings": issues,
        "verification_referrals": _verification_rows(issues),
        "boundary": (
            "A finding describes what the record set establishes, conflicts on, or leaves unresolved. "
            "It is not a finding of fraud, illegality, liability, professional negligence, or other "
            "licensed/professional conclusion."
        ),
    }


def build_report_bundle(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        REPORT_RECORDS: build_records_report(manifest),
        REPORT_OPERATIONS: build_operations_report(manifest),
        REPORT_FINDINGS: build_findings_report(manifest),
    }
