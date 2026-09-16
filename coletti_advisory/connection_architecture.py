from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .models import Role


@dataclass(frozen=True)
class Destination:
    object_type: str
    page: str
    subview: str | None = None
    owner_page: str | None = None
    description: str = ""

    def page_for(self, role: Role) -> str:
        if role == Role.OWNER and self.owner_page:
            return self.owner_page
        return self.page


DESTINATION_REGISTRY: Mapping[str, Destination] = {
    "decision": Destination("decision", "Review Center", "Needs Decision", "Decisions", "Human/owner decision queue"),
    "approval": Destination("approval", "Review Center", "Needs Decision", "Decisions", "Protected or ordinary approval"),
    "blocker": Destination("blocker", "Review Center", "Blocked", "Fix Center", "Blocked work or case issue"),
    "carryover": Destination("carryover", "Dashboard", "Carryover", "Dispatcher", "Open work carried from a prior day"),
    "due_today": Destination("due_today", "Dashboard", "Due Today", "Dispatcher", "Work due today"),
    "source": Destination("source", "Evidence", "Source", "Records", "Registered source record"),
    "record": Destination("record", "Evidence", "Record", "Records", "Record/source workspace"),
    "case": Destination("case", "Engagements", "Case", "Cases", "Canonical case workspace"),
    "report": Destination("report", "Reports", "Report", "Reports", "Report/review publication object"),
    "invoice": Destination("invoice", "Billing", "Invoices", "Billing", "Invoice record"),
    "receivable": Destination("receivable", "Billing", "Receivables", "Billing", "Outstanding receivable"),
    "payment": Destination("payment", "Billing", "Payments", "Billing", "Payment record"),
    "contract": Destination("contract", "Contracts", "Contract", "Contracts", "Contract/agreement record"),
    "expense": Destination("expense", "Finance", "Expenses", "Finance", "Operating expense"),
    "revenue": Destination("revenue", "Finance", "Revenue", "Finance", "Revenue view"),
    "capacity": Destination("capacity", "Administration", "Workload", "Capacity", "Capacity/workload state"),
    "employee": Destination("employee", "Administration", "Person", "Team", "Team member work state"),
    "assignment": Destination("assignment", "Administration", "Assignments", "Assignments", "Case/task assignment"),
    "knowledge": Destination("knowledge", "Help & Support", "Guides & Resources", "Knowledge", "Authorized knowledge item"),
    "policy": Destination("policy", "Administration", "Policy", "Docket", "Controlling governance artifact"),
    "implementation": Destination("implementation", "Administration", "Implementation", "Implementation", "Implementation Matrix item"),
    "notification": Destination("notification", "Dashboard", "Notifications", "Notifications", "Operational notification"),
    "integration": Destination("integration", "Administration", "Integrations", "Integrations", "Integration state"),
    "deployment": Destination("deployment", "Administration", "Deployments", "Deployments", "Deployment state/failure"),
    "fix": Destination("fix", "Administration", "Fix", "Fix Center", "Structured repair item"),
    "referral": Destination("referral", "Administration", "Referrals", "Referrals", "Referral opportunity/partner"),
    "communication": Destination("communication", "Messages", "Message", "Notifications", "Communication thread/message"),
}


CAPABILITY_ROLES: Mapping[str, frozenset[Role]] = {
    "records_upload": frozenset({Role.CLIENT, Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "google_drive_import": frozenset({Role.CLIENT, Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "zip_archive_import": frozenset({Role.CLIENT, Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "records_review": frozenset({Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "human_review": frozenset({Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "reports": frozenset({Role.CLIENT, Role.READ_ONLY, Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "client_messages": frozenset({Role.CLIENT, Role.READ_ONLY, Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "staff_workflow": frozenset({Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.OWNER}),
    "team_oversight": frozenset({Role.MANAGER, Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "executive_oversight": frozenset({Role.EXECUTIVE, Role.OWNER}),
    "finance": frozenset({Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "billing": frozenset({Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "contracts": frozenset({Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "knowledge_internal": frozenset({Role.STAFF, Role.ANALYST, Role.REVIEWER, Role.MANAGER, Role.ADMIN, Role.EXECUTIVE, Role.OWNER}),
    "knowledge_client": frozenset({Role.CLIENT, Role.READ_ONLY}),
    "docket": frozenset({Role.OWNER}),
    "implementation_control": frozenset({Role.OWNER}),
    "fix_center": frozenset({Role.OWNER}),
    "deployment_control": frozenset({Role.OWNER}),
    "owner_preview": frozenset({Role.OWNER}),
}


DRILL_THROUGH_CONTRACT = (
    "Every meaningful dashboard card, DARI result, notification, KPI, alert, count, status, and actionable summary "
    "must resolve to the authoritative object or filtered canonical workspace that produced it. A display-only duplicate "
    "of operational state is not connected and cannot be marked Operational."
)

CLIENT_EMPLOYEE_WIRING_CONTRACT = (
    "Client and employee interfaces are Operational only when authentication, engagement scope, role capabilities, "
    "authoritative data access, workflow transitions, review/approval gates, publishing controls, notifications, "
    "audit attribution, and failure handling are connected end-to-end and verified. Screen presence alone is not completion."
)


def destination_for(object_type: str) -> Destination:
    try:
        return DESTINATION_REGISTRY[object_type]
    except KeyError as exc:
        raise KeyError(f"No canonical destination registered for object type: {object_type}") from exc


def page_for(object_type: str, role: Role) -> str:
    return destination_for(object_type).page_for(role)


def role_has_capability(role: Role, capability: str) -> bool:
    return role in CAPABILITY_ROLES.get(capability, frozenset())


def assert_drill_through_registered(object_types: tuple[str, ...] | list[str]) -> None:
    missing = [object_type for object_type in object_types if object_type not in DESTINATION_REGISTRY]
    if missing:
        raise RuntimeError(f"Missing canonical destination(s): {', '.join(sorted(missing))}")
