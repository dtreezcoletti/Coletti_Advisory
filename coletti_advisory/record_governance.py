from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


FIRST_TRUTH_POLICY_KEY = "CCO-FTL-001"
FIRST_TRUTH_POLICY_VERSION = "1.2"
FIRST_TRUTH_NOTICE_VERSION = "2.0"
PROTECTED_PROFESSION_RULE = (
    "ColettiOS can determine the condition of the records; it cannot independently "
    "determine the protected professional effect of that condition."
)

IDENTIFIED_PATTERN_DEFINITION = (
    "A recurring, clustered, repeated, correlated, sequential, or otherwise materially "
    "consistent relationship observed across two or more records or events. It describes "
    "the relationship shown by the records and does not by itself establish motive, intent, "
    "illegality, liability, causation, or protected professional effect."
)

FIRST_TRUTH_NOTICE = """Coletti & Co. provides records reconstruction and records-intelligence services.

Our work may include records organization, source indexing, chronology building, record reconciliation, identification of inconsistencies and missing documentation, record-state labeling, process reconstruction, and preparation of records for professional review.

We report what the available records support, what conflicts, what is missing, and what remains unresolved.

A Coletti & Co. finding does not automatically constitute a legal, accounting, tax, appraisal, medical, investigative, or other regulated professional opinion. We do not convert incomplete or conflicting records into certainty and do not substitute our work for professional judgment that requires a license or other statutory authority.

Coletti & Co. does not determine whether client materials are admissible evidence, their evidentiary weight, legal sufficiency, or legal effect. Client statements, third-party conclusions, unresolved questions, and missing documentation are identified according to their actual record status under the Coletti & Co. methodology rather than presented as independently established facts.

When an issue requires regulated professional judgment, Coletti & Co. may organize and reconstruct the relevant record for referral to an appropriately qualified professional.

First truth means the record comes first.

ColettiOS can determine the condition of the records; it cannot independently determine the protected professional effect of that condition.

An Identified Pattern describes a materially consistent relationship shown across two or more records or events; it does not by itself establish motive, intent, illegality, liability, causation, or another protected professional effect."""

RECORD_STATES: tuple[str, ...] = (
    "Documented Fact",
    "Reconciliation Result",
    "Inconsistency",
    "Missing Documentation",
    "Process Deviation",
    "Unresolved Question",
    "Client Assertion",
    "Third-Party Conclusion",
    "Referral Required",
    "Identified Pattern",
)

CLIENT_ID_RE = re.compile(r"^C\d{2}-\d{2}$")
CASE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-\d{6}-\d{2}$")
SOURCE_CODE_RE = re.compile(r"^SR[A-Z0-9]{1,8}-\d{3}$")


def valid_client_id(value: str) -> bool:
    return bool(CLIENT_ID_RE.fullmatch(str(value or "").strip()))


def valid_case_id(value: str) -> bool:
    return bool(CASE_ID_RE.fullmatch(str(value or "").strip()))


def valid_source_code(value: str) -> bool:
    return bool(SOURCE_CODE_RE.fullmatch(str(value or "").strip()))


def canonical_path(client_id: str, case_id: str, source_code: str) -> str:
    if not valid_client_id(client_id):
        raise ValueError("client_id must match CYY-NN")
    if not valid_case_id(case_id):
        raise ValueError("case_id must match {PREFIX}-YYMMDD-NN")
    if not valid_source_code(source_code):
        raise ValueError("source_code must match SR{TYPE}-NNN")
    return f"{client_id} / {case_id} / {source_code}"


class DariTier(str, Enum):
    NO_AI = "NO_AI"
    LUNA = "LUNA"
    TERRA = "TERRA"
    SOL = "SOL"


@dataclass(frozen=True)
class DariRoutingDecision:
    tier: DariTier
    operation_class: str
    human_review_required: bool
    blocked: bool = False
    referral_required: bool = False
    reason: str = ""


_PROTECTED_EFFECT_PHRASES = (
    "legal effect",
    "legal sufficiency",
    "admissible",
    "admissibility",
    "liable",
    "liability",
    "guilty",
    "illegal",
    "fraud",
    "negligence",
    "tax treatment",
    "tax liability",
    "audit opinion",
    "medical diagnosis",
    "diagnose",
    "appraisal value",
    "investigative conclusion",
)

_TERRA_PHRASES = (
    "pattern",
    "reconstruct",
    "reconciliation",
    "contradiction",
    "inconsistency",
    "cross-record",
    "cross record",
    "timeline",
    "chronology",
    "compare all",
)

_SOL_PHRASES = (
    "highest complexity",
    "complex synthesis",
    "synthesize everything",
    "all records and all",
    "multi-domain",
    "multi domain",
    "deep synthesis",
)


def route_dari_command(command: str, *, deterministic: bool = False) -> DariRoutingDecision:
    normalized = " ".join(str(command or "").lower().split())
    if deterministic:
        return DariRoutingDecision(
            DariTier.NO_AI,
            "DETERMINISTIC_RECORD_OPERATION",
            False,
            reason="No generative reasoning is required.",
        )
    if any(phrase in normalized for phrase in _PROTECTED_EFFECT_PHRASES):
        return DariRoutingDecision(
            DariTier.NO_AI,
            "PROTECTED_PROFESSIONAL_EFFECT",
            True,
            blocked=True,
            referral_required=True,
            reason=PROTECTED_PROFESSION_RULE,
        )
    if any(phrase in normalized for phrase in _SOL_PHRASES):
        return DariRoutingDecision(
            DariTier.SOL,
            "HIGH_COMPLEXITY_SYNTHESIS",
            True,
            reason="Highest-complexity authorized synthesis; human review remains mandatory.",
        )
    if any(phrase in normalized for phrase in _TERRA_PHRASES):
        return DariRoutingDecision(
            DariTier.TERRA,
            "COMPLEX_RECONSTRUCTION",
            True,
            reason="Complex cross-record reconstruction or Identified Pattern analysis.",
        )
    return DariRoutingDecision(
        DariTier.LUNA,
        "ROUTINE_RECORD_REASONING",
        True,
        reason="Routine bounded reasoning over authorized records.",
    )
