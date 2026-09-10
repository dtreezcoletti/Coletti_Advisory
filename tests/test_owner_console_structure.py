from coletti_advisory.owner_console_structure import (
    MORNING_CARD_TITLES,
    OPERATING_ZONES,
    OWNER_PREVIEW_OPTIONS,
    OWNER_SIDEBAR_GROUPS,
    canonical_owner_page,
    operating_zone_names,
    sidebar_labels,
)


def test_owner_morning_zone_has_exactly_the_seven_approved_cards_in_order():
    assert MORNING_CARD_TITLES == (
        "Since Yesterday",
        "Due Today",
        "Decisions",
        "Carryover",
        "Blockers",
        "Capacity",
        "Success Definition",
    )


def test_owner_operating_zone_order_matches_approved_hierarchy():
    assert operating_zone_names() == (
        "Start My Day",
        "Business Operations",
        "Back Office",
        "People & Administration",
        "Company Control",
        "Build & Fix",
    )


def test_owner_sidebar_groups_and_labels_match_approved_structure():
    assert OWNER_SIDEBAR_GROUPS == (
        ("TODAY", (("Start My Day", "☀"), ("My Workspace", "⌂"), ("Decisions", "✓"), ("Notifications", "●"))),
        ("BUSINESS", (("Clients", "♙"), ("Cases", "▣"), ("Records", "◇"), ("Reports", "▤"), ("Referrals", "↗"))),
        ("BACK OFFICE", (("Finance", "$"), ("Billing", "¤"), ("Contracts", "§"), ("Pricing", "◫"), ("Documents", "▧"))),
        ("PEOPLE", (("Team", "♙"), ("Capacity", "◔"), ("Assignments", "↳"), ("Access", "⌾"))),
        ("CONTROL", (("DARI", "◌"), ("Dispatcher", "⌘"), ("Knowledge", "◧"), ("Docket", "▥"), ("Implementation", "◆"), ("System Health", "◉"))),
        ("BUILD & FIX", (("Fix Center", "⊕"), ("Integrations", "⌁"), ("Deployments", "↑"), ("System Lab", "◈"))),
    )
    assert len(sidebar_labels()) == 28


def test_new_owner_labels_reuse_existing_authoritative_surfaces_where_available():
    assert canonical_owner_page("Decisions") == "Approvals"
    assert canonical_owner_page("Cases") == "Case Queue"
    assert canonical_owner_page("Records") == "Evidence"
    assert canonical_owner_page("Finance") == "Financials"
    assert canonical_owner_page("Knowledge") == "Knowledge Base"


def test_production_owner_preview_contract_is_non_impersonating_by_design():
    assert OWNER_PREVIEW_OPTIONS == ("Owner", "Client", "Employee", "Admin")
