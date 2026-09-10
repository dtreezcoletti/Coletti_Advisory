from __future__ import annotations

from dataclasses import dataclass


LIFECYCLE_STAGES = (
    "DESIGNED",
    "CODED",
    "DATA_WIRED",
    "PERMISSION_TESTED",
    "DRILL_THROUGH_VERIFIED",
    "CROSS_INTERFACE_VERIFIED",
    "GOLDEN_PATH_PASSED",
    "MESSY_PATH_PASSED",
    "OPERATIONAL",
)

DISPLAY_LABELS = {
    "DESIGNED": "Designed",
    "CODED": "Coded",
    "DATA_WIRED": "Data Wired",
    "PERMISSION_TESTED": "Permission Tested",
    "DRILL_THROUGH_VERIFIED": "Drill-Through Verified",
    "CROSS_INTERFACE_VERIFIED": "Cross-Interface Verified",
    "GOLDEN_PATH_PASSED": "Golden Path Passed",
    "MESSY_PATH_PASSED": "Messy Path Passed",
    "OPERATIONAL": "Operational",
}

STAGE_LANGUAGE = {
    "DESIGNED": {
        "allowed": ("designed", "approved design", "planned implementation"),
        "not_yet": ("built", "implemented", "connected", "working", "operational"),
        "definition": "Behavior, architecture, UX, rules, and acceptance criteria are defined and approved.",
    },
    "CODED": {
        "allowed": ("coded", "implemented in code", "build exists"),
        "not_yet": ("data connected", "verified", "operational"),
        "definition": "Executable implementation exists in the repository.",
    },
    "DATA_WIRED": {
        "allowed": ("data wired", "connected to authoritative data", "using the system of record"),
        "not_yet": ("permission verified", "fully connected", "operational"),
        "definition": "The feature reads/writes the correct authoritative systems and required persistent state is not session-only or duplicated.",
    },
    "PERMISSION_TESTED": {
        "allowed": ("permission tested", "RBAC verified", "access boundaries verified"),
        "not_yet": ("cross-interface verified", "production ready", "operational"),
        "definition": "Positive and negative access cases have been tested for the applicable roles.",
    },
    "DRILL_THROUGH_VERIFIED": {
        "allowed": ("drill-through verified", "connected", "canonical routing verified"),
        "not_yet": ("fully operational across all interfaces", "operational"),
        "definition": "Every meaningful card, KPI, alert, notification, DARI result, count, or summary can open the authoritative object or canonical workspace that produced it.",
    },
    "CROSS_INTERFACE_VERIFIED": {
        "allowed": ("cross-interface verified", "role views reconciled", "single authoritative state confirmed"),
        "not_yet": ("end-to-end proven", "operational"),
        "definition": "The same underlying object and state behave consistently across authorized Owner, Admin, Employee, and Client views.",
    },
    "GOLDEN_PATH_PASSED": {
        "allowed": ("Golden Path passed", "standard end-to-end workflow verified"),
        "not_yet": ("edge-case hardened", "operational"),
        "definition": "The intended clean end-to-end workflow succeeds without manual workaround.",
    },
    "MESSY_PATH_PASSED": {
        "allowed": ("Messy Path passed", "real-world resilience verified", "edge cases verified"),
        "not_yet": ("operational until deployment and post-deployment smoke verification complete",),
        "definition": "Real-world and adversarial conditions either succeed or fail safely without silent state corruption or permission leakage.",
    },
    "OPERATIONAL": {
        "allowed": ("operational", "live", "active", "available for normal use"),
        "not_yet": (),
        "definition": "All prior gates passed, the intended environment is deployed/activated, post-deployment smoke verification passed, and normal use is supported.",
    },
}


@dataclass(frozen=True)
class LifecycleState:
    stage: str
    deployment_verified: bool = False

    def __post_init__(self) -> None:
        if self.stage not in LIFECYCLE_STAGES:
            raise ValueError(f"Unknown lifecycle stage: {self.stage}")
        if self.stage == "OPERATIONAL" and not self.deployment_verified:
            raise ValueError("Operational requires deployment/post-deployment verification")

    @property
    def label(self) -> str:
        return DISPLAY_LABELS[self.stage]

    @property
    def rank(self) -> int:
        return LIFECYCLE_STAGES.index(self.stage)


def can_promote(current: str, target: str, *, deployment_verified: bool = False) -> bool:
    if current not in LIFECYCLE_STAGES or target not in LIFECYCLE_STAGES:
        return False
    current_index = LIFECYCLE_STAGES.index(current)
    target_index = LIFECYCLE_STAGES.index(target)
    if target_index != current_index + 1:
        return False
    if target == "OPERATIONAL" and not deployment_verified:
        return False
    return True


def lifecycle_display() -> str:
    return " → ".join(DISPLAY_LABELS[stage] for stage in LIFECYCLE_STAGES)


def language_for(stage: str) -> dict[str, tuple[str, ...] | str]:
    if stage not in STAGE_LANGUAGE:
        raise ValueError(f"Unknown lifecycle stage: {stage}")
    return STAGE_LANGUAGE[stage]
