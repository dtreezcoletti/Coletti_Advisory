from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class CommercialDomainConfig:
    """Coletti & Co.-owned terminology and policy configuration.

    ColettiOS Core must not depend on these labels. They control commercial
    presentation, verification routing, risk vocabulary, and reviewer workflow.
    """

    report_labels: Mapping[str, str]
    report_purposes: Mapping[str, str]
    report_boundaries: Mapping[str, str]
    verification_targets_by_record_class: Mapping[str, str]
    default_verification_target: str
    risk_taxonomy: Mapping[str, str]
    escalation_review_roles: tuple[str, ...] = field(default_factory=tuple)


DEFAULT_COMMERCIAL_CONFIG = CommercialDomainConfig(
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
        "Operational Audit": "independent record custodian, process owner, or relevant subject-matter professional",
        "Business Record": "independent record custodian, process owner, or relevant subject-matter professional",
        "Correspondence": "originating third party or records custodian",
    },
    default_verification_target="independent source/custodian or appropriate qualified professional",
    risk_taxonomy={
        "CRITICAL": "Immediate material harm, operational failure, safety risk, regulatory exposure, or major financial consequence.",
        "HIGH": "Significant impact requiring priority review or action.",
        "MODERATE": "Meaningful inconsistency or exposure that should be resolved but is not immediately destabilizing.",
        "LOW": "Limited-impact discrepancy, documentation weakness, or minor control issue.",
        "CLEAR": "No material issue currently identified under the configured engagement criteria.",
    },
    escalation_review_roles=("Owner", "Authorized Reviewer"),
)


def verification_target_for(record_classes: set[str], config: CommercialDomainConfig = DEFAULT_COMMERCIAL_CONFIG) -> str:
    targets = [
        target
        for record_class, target in config.verification_targets_by_record_class.items()
        if record_class in record_classes
    ]
    if not targets:
        return config.default_verification_target
    return "; ".join(dict.fromkeys(targets))
