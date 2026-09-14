from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


BUSINESS_MODEL_KEY = "CCO-RRDA-001"
BUSINESS_MODEL_VERSION = "1.0"
BUSINESS_MODEL_NAME = "Records Reconstruction & Documentation Analysis"
CORE_PROMISE = (
    "Give us the records and the question you are trying to understand; we reconstruct "
    "what the records document, what they conflict with, what is missing, and what remains unresolved."
)

SERVICE_CATALOG = (
    "Diagnostic Records Review",
    "Full Records Reconstruction",
    "Transaction Reconciliation",
    "Timeline & Narrative Reconstruction",
    "Process & Operations Reconstruction",
    "Record Conditions & Pattern Analysis",
    "Professional Handoff",
    "Organized Source Production",
    "Recurring Records Review",
)


class IntakeDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    MODIFY_SCOPE = "MODIFY_SCOPE"
    PROFESSIONAL_REVIEW = "PROFESSIONAL_REVIEW"
    DECLINE_REFER = "DECLINE_REFER"


@dataclass(frozen=True)
class IntakeBoundaryRequest:
    records_authorized: bool
    asks_external_information: bool = False
    administrative_retrieval_authorized: bool = False
    asks_protected_conclusion: bool = False
    asks_investigative_method: bool = False
    state_clearance_required: bool = False
    jurisdictions: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntakeBoundaryResult:
    disposition: IntakeDisposition
    reasons: tuple[str, ...]
    model_key: str = BUSINESS_MODEL_KEY
    model_version: str = BUSINESS_MODEL_VERSION


def screen_intake(request: IntakeBoundaryRequest) -> IntakeBoundaryResult:
    if not request.records_authorized:
        return IntakeBoundaryResult(
            IntakeDisposition.DECLINE_REFER,
            ("SOURCE_AUTHORIZATION_REQUIRED",),
        )

    if request.asks_investigative_method:
        return IntakeBoundaryResult(
            IntakeDisposition.DECLINE_REFER,
            ("INVESTIGATIVE_METHOD_OUTSIDE_STANDARD_SERVICE",),
        )

    if request.state_clearance_required:
        reasons = ["STATE_SERVICE_BOUNDARY_REVIEW_REQUIRED"]
        if request.jurisdictions:
            reasons.append("JURISDICTIONS:" + ",".join(sorted(set(request.jurisdictions))))
        return IntakeBoundaryResult(
            IntakeDisposition.PROFESSIONAL_REVIEW,
            tuple(reasons),
        )

    reasons: list[str] = []
    if request.asks_protected_conclusion:
        reasons.append("PROTECTED_PROFESSIONAL_CONCLUSION_REQUIRES_SCOPE_MODIFICATION")
    if request.asks_external_information and not request.administrative_retrieval_authorized:
        reasons.append("EXTERNAL_INFORMATION_REQUEST_REQUIRES_SCOPE_MODIFICATION")

    if reasons:
        return IntakeBoundaryResult(IntakeDisposition.MODIFY_SCOPE, tuple(reasons))

    return IntakeBoundaryResult(
        IntakeDisposition.ACCEPT,
        ("AUTHORIZED_RECORD_RECONSTRUCTION_SCOPE",),
    )
