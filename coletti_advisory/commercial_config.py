from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class CommercialDomainConfig:
    """Coletti & Co.-owned terminology and policy configuration.

    ColettiOS Core must never depend on these labels or policies. This object
    owns commercial presentation, source-classification vocabulary,
    verification routing, review policy, risk vocabulary, and report naming.
    Domain adapters translate source-specific records into the Core schema;
    this config controls how Coletti & Co. presents and reviews the results.
    """

    source_classifications: tuple[str, ...]
    report_labels: Mapping[str, str]
    report_purposes: Mapping[str, str]
    report_boundaries: Mapping[str, str]
    verification_targets_by_record_class: Mapping[str, str]
    default_verification_target: str
    verification_recommendations_by_issue_type: Mapping[str, str]
    default_verification_recommendation: str
    risk_taxonomy: Mapping[str, str]
    escalation_review_roles: tuple[str, ...] = field(default_factory=tuple)
    review_trigger_states: frozenset[str] = frozenset({"DISPUTED", "CONTRADICTED", "QUARANTINED"})
    corroborated_state: str = "CORROBORATED"
    publication_ready_resolution_states: frozenset[str] = frozenset({"CORROBORATED_RESOLUTION"})
    resolution_rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("OPEN_AFTER_REVIEW", ("unresolved", "remains open", "pending confirmation")),
        ("CORROBORATED_RESOLUTION", ("independent", "custodian confirmed", "verified", "corroborat")),
        ("EXPLAINED", ("client", "clarif", "provided context", "missing context")),
    )
    default_reconciled_state: str = "REVIEWER_RESOLVED"


DEFAULT_COMMERCIAL_CONFIG = CommercialDomainConfig(
    source_classifications=(
        "Operational Record",
        "Business Record",
        "Financial Record",
        "Correspondence",
        "Other",
    ),
    report_labels={
        "records": "Records Reconstruction Report",
        "operations": "Operations Reconstruction Report",
        "findings": "Findings Report",
    },
    report_purposes={
        "records": (
            "Reconstruct the supplied record set, show what record-derived statements are supported by which "
            "sources, identify coverage or source-support limitations, and preserve unresolved record questions."
        ),
        "operations": (
            "Reconstruct record-supported operational activity, identify process inconsistencies and unresolved "
            "follow-up, and distinguish documented operational observations from reviewer or client explanations."
        ),
        "findings": (
            "Present engagement-level record-supported observations, material inconsistencies, unresolved questions, "
            "review status, and verification needs in one source-linked summary."
        ),
    },
    report_boundaries={
        "records": (
            "This report describes the condition, content, linkage, and limitations of the supplied record set. "
            "It does not infer intent or motive and does not make legal, accounting, investigative, regulatory, "
            "or other licensed/professional determinations."
        ),
        "operations": (
            "Operational observations remain tied to the supplied records. A client or reviewer explanation is "
            "reported as an explanation unless independently supported. Questions requiring professional judgment "
            "are routed for appropriate third-party or professional verification."
        ),
        "findings": (
            "A finding in this draft describes what the supplied record set supports, conflicts on, or leaves "
            "unresolved. It is not a finding of fraud, illegality, liability, professional negligence, regulatory "
            "violation, or any other conclusion requiring licensed or professional judgment."
        ),
    },
    verification_targets_by_record_class={
        "Financial Record": "independent record custodian or qualified financial/accounting professional",
        "Operational Record": "independent record custodian, process owner, or relevant subject-matter professional",
        # Backward-compatible legacy label. New intake uses Operational Record.
        "Operational Audit": "independent record custodian, process owner, or relevant subject-matter professional",
        "Business Record": "independent record custodian, process owner, or relevant subject-matter professional",
        "Correspondence": "originating third party or records custodian",
    },
    default_verification_target="independent source/custodian or appropriate qualified professional",
    verification_recommendations_by_issue_type={
        "Inconsistency": (
            "Independent third-party verification recommended where available. "
            "If resolving the issue requires licensed or professional judgment, refer the question and supporting "
            "records to the appropriate professional."
        ),
        "Unresolved Question": (
            "Seek independent source or custodian confirmation when available. Escalate to an appropriate qualified "
            "professional when the unresolved question requires professional determination."
        ),
    },
    default_verification_recommendation=(
        "External verification may be appropriate if the current record set cannot resolve the issue; "
        "professional review is reserved for questions requiring professional judgment."
    ),
    risk_taxonomy={
        "CRITICAL": "Immediate material harm, operational failure, safety risk, regulatory exposure, or major financial consequence.",
        "HIGH": "Significant impact requiring priority review or action.",
        "MODERATE": "Meaningful inconsistency or exposure that should be resolved but is not immediately destabilizing.",
        "LOW": "Limited-impact discrepancy, documentation weakness, or minor control issue.",
        "CLEAR": "No material issue currently identified under the configured engagement criteria.",
    },
    escalation_review_roles=("Owner", "Authorized Reviewer"),
)


def verification_target_for(
    record_classes: set[str],
    config: CommercialDomainConfig = DEFAULT_COMMERCIAL_CONFIG,
) -> str:
    targets = [
        target
        for record_class, target in config.verification_targets_by_record_class.items()
        if record_class in record_classes
    ]
    if not targets:
        return config.default_verification_target
    return "; ".join(dict.fromkeys(targets))


def resolution_state_for(
    reconciliation_text: str,
    config: CommercialDomainConfig = DEFAULT_COMMERCIAL_CONFIG,
) -> str:
    normalized = str(reconciliation_text or "").lower()
    for state, indicators in config.resolution_rules:
        if any(token in normalized for token in indicators):
            return state
    return config.default_reconciled_state
