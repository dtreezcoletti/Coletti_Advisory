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


def test_owner_navigation_contains_all_nine_departments_and_real_operating_surfaces():
    groups = dict(OWNER_SIDEBAR_GROUPS)
    assert "THE COLLEGIUM" in groups
    departments = tuple(label.split(" · ", 1)[1] for label, _ in groups["THE COLLEGIUM"])
    assert departments == (
        "FABER", "VOX", "QUAERO", "MONETA", "SCRIBA",
        "CURA", "CIVIS", "AUGEO", "ACQUIRO",
    )
    labels = set(sidebar_labels())
    for page in ("Billing", "Contracts", "Pricing", "Assignments",
                 "Integrations", "Implementation", "Procedures", "Service Catalog"):
        assert page in labels
    assert "My Workspace" in labels
    assert "Cases" in labels
    assert "Records" in labels


def test_new_owner_labels_reuse_existing_authoritative_surfaces_where_available():
    assert canonical_owner_page("Decisions") == "Approvals"
    assert canonical_owner_page("Cases") == "Case Queue"
    assert canonical_owner_page("Records") == "Evidence"
    assert canonical_owner_page("Finance") == "Financials"
    assert canonical_owner_page("Knowledge") == "Knowledge Base"


def test_production_owner_preview_contract_is_non_impersonating_by_design():
    assert OWNER_PREVIEW_OPTIONS == ("Owner", "Client", "Employee", "Admin")
