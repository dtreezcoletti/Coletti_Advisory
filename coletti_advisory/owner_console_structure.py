from __future__ import annotations

from collections.abc import Mapping

# Authoritative Owner Console information architecture approved 2026-09-10.
# Keep labels/order stable unless a later approved structure explicitly supersedes it.
MORNING_CARD_TITLES = (
    "Since Yesterday",
    "Due Today",
    "Decisions",
    "Carryover",
    "Blockers",
    "Capacity",
    "Success Definition",
)

OWNER_SIDEBAR_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "TODAY",
        (
            ("Start My Day", "☀"),
            ("My Workspace", "⌂"),
            ("Decisions", "✓"),
            ("Notifications", "●"),
        ),
    ),
    (
        "BUSINESS",
        (
            ("Clients", "♙"),
            ("Cases", "▣"),
            ("Records", "◇"),
            ("Reports", "▤"),
            ("Referrals", "↗"),
        ),
    ),
    (
        "BACK OFFICE",
        (
            ("Finance", "$"),
            ("Billing", "¤"),
            ("Contracts", "§"),
            ("Pricing", "◫"),
            ("Documents", "▧"),
        ),
    ),
    (
        "PEOPLE",
        (
            ("Team", "♙"),
            ("Capacity", "◔"),
            ("Assignments", "↳"),
            ("Access", "⌾"),
        ),
    ),
    (
        "CONTROL",
        (
            ("DARI", "◌"),
            ("Dispatcher", "⌘"),
            ("Knowledge", "◧"),
            ("Docket", "▥"),
            ("Implementation", "◆"),
            ("System Health", "◉"),
        ),
    ),
    (
        "BUILD & FIX",
        (
            ("Fix Center", "⊕"),
            ("Integrations", "⌁"),
            ("Deployments", "↑"),
            ("System Lab", "◈"),
        ),
    ),
)

OPERATING_ZONES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Start My Day", ("Start My Day", "Decisions", "Notifications")),
    ("Business Operations", ("Clients", "Cases", "Records", "Reports", "Referrals")),
    ("Back Office", ("Finance", "Billing", "Contracts", "Pricing", "Documents")),
    ("People & Administration", ("Team", "Capacity", "Assignments", "Access")),
    ("Company Control", ("DARI", "Dispatcher", "Knowledge", "Docket", "Implementation", "System Health")),
    ("Build & Fix", ("Fix Center", "Integrations", "Deployments", "System Lab")),
)

# Compatibility routes let the new information architecture reuse already-built
# operating surfaces instead of duplicating data or authority.
OWNER_PAGE_ALIASES: Mapping[str, str] = {
    "Decisions": "Approvals",
    "Cases": "Case Queue",
    "Records": "Evidence",
    "Finance": "Financials",
    "Knowledge": "Knowledge Base",
}

# These pages have a real presentation surface but still need an authoritative
# service or dedicated subsystem before they can be called operational.
BACKEND_REQUIRED_PAGES: Mapping[str, str] = {
    "Referrals": "Referral pipeline/service is not connected yet.",
    "Billing": "Authoritative billing and invoice service is not connected yet.",
    "Contracts": "Contract lifecycle backend is not connected yet.",
    "Pricing": "Authoritative pricing/catalog service is not connected yet.",
    "Documents": "Firm document/Docket storage service is not connected yet.",
    "Capacity": "Dedicated people-capacity service is not connected yet; Dispatcher remains the current operational source for workload posture.",
    "Assignments": "Dedicated assignment service is not connected yet; current case authorization and Dispatcher tasks remain authoritative.",
    "Docket": "Authoritative Judiciary/Docket service is not connected to this Streamlit surface yet.",
    "Implementation": "Implementation Matrix has no dedicated owner API on this Streamlit surface yet.",
    "Fix Center": "Dedicated Fix Center workflow is not connected yet; System Lab remains the verified diagnostic surface.",
    "Integrations": "Integration registry/control service is not connected yet.",
    "Deployments": "Deployment control plane is not connected to this Streamlit surface yet.",
}

OWNER_PREVIEW_OPTIONS = ("Owner", "Client", "Employee", "Admin")


def canonical_owner_page(page: str) -> str:
    return OWNER_PAGE_ALIASES.get(page, page)


def sidebar_labels() -> tuple[str, ...]:
    return tuple(label for _group, items in OWNER_SIDEBAR_GROUPS for label, _icon in items)


def operating_zone_names() -> tuple[str, ...]:
    return tuple(name for name, _items in OPERATING_ZONES)
