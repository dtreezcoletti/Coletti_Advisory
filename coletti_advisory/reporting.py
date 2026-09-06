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
from .commercial_config import DEFAULT_COMMERCIAL_CONFIG


REPORT_RECORDS = DEFAULT_COMMERCIAL_CONFIG.report_labels["records"]
REPORT_OPERATIONS = DEFAULT_COMMERCIAL_CONFIG.report_labels["operations"]
REPORT_FINDINGS = DEFAULT_COMMERCIAL_CONFIG.report_labels["findings"]
REPORT_VERSION = "1.0-client-ready"


def _verification_rows(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        if str(issue.get("Verification state") or "").upper() == "COMPLETE":
            continue
        recommendation = str(issue.get("Verification recommendation") or "").strip()
        verifier = str(issue.get("Potential verifier") or "").strip()
        if recommendation and verifier and verifier != "—":
            rows.append(
                {
                    "Issue": issue.get("Issue", ""),
                    "Classification": issue.get("Classification", ""),
                    "Resolution state": issue.get("Resolution state", "OPEN"),
                    "Recommendation": recommendation,
                    "Potential verifier": verifier,
                    "Supporting sources": issue.get("Supporting sources", ""),
                }
            )
    return rows


def _corroboration_blockers(manifest: dict[str, Any]) -> list[str]:
    sources = manifest.get("sources") or {}
    if isinstance(sources, list):
        sources = {
            str(item.get("source_id")): item
            for item in sources
            if isinstance(item, dict) and item.get("source_id")
        }
    states = manifest.get("source_states") or {}
    blockers: list[str] = []
    for source_id, state in states.items():
        if str(state).upper() != "CORROBORATED":
            continue
        source = sources.get(str(source_id), {}) if isinstance(sources, dict) else {}
        metadata = source.get("metadata") or {}
        filename = str(metadata.get("filename") or "").lower()
        role = str(metadata.get("source_role") or metadata.get("record_role") or "").upper()
        if role in {"CONTROL_RECORD", "SYSTEM_METADATA", "MANIFEST", "AUDIT_CONTROL"} or filename.endswith("manifest.json"):
            continue
        basis = metadata.get("corroborating_source_ids") or metadata.get("corroboration_basis")
        if not basis:
            blockers.append(f"{source_id}: CORROBORATED state has no recorded corroboration basis")
    return blockers


def _report_header(report_type: str, purpose: str) -> dict[str, Any]:
    return {
        "report_type": report_type,
        "report_version": REPORT_VERSION,
        "document_status": "DRAFT — NOT PUBLISHED",
        "purpose": purpose,
        "methodology_note": (
            "This draft is generated from source-linked engagement data. System/control metadata is excluded "
            "from substantive analysis, duplicate comparison pairs are canonicalized, and reviewer explanations "
            "remain distinct from independently verified record conclusions."
        ),
    }


def build_publication_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a non-destructive client-publication readiness assessment."""

    issues = build_analytical_issues(manifest)
    unresolved = [
        item
        for item in issues
        if str(item.get("Resolution state") or "OPEN").upper()
        not in {"CORROBORATED_RESOLUTION"}
    ]
    corroboration_blockers = _corroboration_blockers(manifest)
    blockers = [
        f"{item.get('Issue', 'Issue')}: {item.get('Classification', 'Unclassified')} — "
        f"{item.get('Resolution state', 'OPEN')}"
        for item in unresolved
    ] + corroboration_blockers
    status = "REVIEW REQUIRED" if blockers else "READY FOR FINAL HUMAN APPROVAL"

    return {
        "status": status,
        "published": False,
        "review_required_count": len(unresolved),
        "corroboration_control_count": len(corroboration_blockers),
        "verification_recommendation_count": len(_verification_rows(issues)),
        "blockers": blockers,
        "rule": (
            "Draft generation never authorizes client delivery. Publication requires explicit final human approval "
            "of the exact report version after all material blockers are reviewed."
        ),
    }


def build_records_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    report = _report_header(REPORT_RECORDS, DEFAULT_COMMERCIAL_CONFIG.report_purposes["records"])
    report.update(
        {
            "engagement_record_summary": build_summary(manifest),
            "evidence_state_summary": build_state_counts(manifest),
            "records_reconstruction": build_records_reconstruction(manifest),
            "unresolved_record_issues": issues,
            "verification_referrals": _verification_rows(issues),
            "publication_gate": build_publication_gate(manifest),
            "boundary": DEFAULT_COMMERCIAL_CONFIG.report_boundaries["records"],
        }
    )
    return report


def build_operations_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    report = _report_header(REPORT_OPERATIONS, DEFAULT_COMMERCIAL_CONFIG.report_purposes["operations"])
    report.update(
        {
            "operations_reconstruction": build_operations_reconstruction(manifest),
            "cross_record_comparison": build_cross_record_comparison(manifest),
            "operational_issues": issues,
            "verification_referrals": _verification_rows(issues),
            "publication_gate": build_publication_gate(manifest),
            "boundary": DEFAULT_COMMERCIAL_CONFIG.report_boundaries["operations"],
        }
    )
    return report


def build_findings_report(manifest: dict[str, Any]) -> dict[str, Any]:
    issues = build_analytical_issues(manifest)
    report = _report_header(REPORT_FINDINGS, DEFAULT_COMMERCIAL_CONFIG.report_purposes["findings"])
    report.update(
        {
            "engagement_summary": build_summary(manifest),
            "record_supported_observations": build_records_reconstruction(manifest),
            "record_comparisons": build_cross_record_comparison(manifest),
            "findings": issues,
            "verification_referrals": _verification_rows(issues),
            "publication_gate": build_publication_gate(manifest),
            "boundary": DEFAULT_COMMERCIAL_CONFIG.report_boundaries["findings"],
        }
    )
    return report


def build_report_bundle(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        REPORT_RECORDS: build_records_report(manifest),
        REPORT_OPERATIONS: build_operations_report(manifest),
        REPORT_FINDINGS: build_findings_report(manifest),
    }
