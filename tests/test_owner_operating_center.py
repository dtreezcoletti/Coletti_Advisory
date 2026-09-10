from coletti_advisory.owner_operating_center import OWNER_NAV_GROUPS, OPERATING_ZONES, START_DAY_CARDS


def test_start_my_day_cards_match_owner_standard():
    assert START_DAY_CARDS == (
        "Since Yesterday",
        "Due Today",
        "Decisions",
        "Carryover",
        "Blockers",
        "Capacity",
        "Success Definition",
    )


def test_owner_navigation_is_grouped_and_complete():
    groups = {name: tuple(label for label, _icon in items) for name, items in OWNER_NAV_GROUPS}
    assert groups["TODAY"] == ("Start My Day", "My Workspace", "Decisions", "Notifications")
    assert groups["BUSINESS"] == ("Clients", "Cases", "Records", "Reports", "Referrals", "Communications")
    assert groups["BACK OFFICE"] == ("Finance", "Billing", "Contracts", "Pricing", "Documents")
    assert groups["PEOPLE"] == ("Team", "Capacity", "Assignments", "Access")
    assert groups["CONTROL"] == ("DARI", "Dispatcher", "Knowledge", "Docket", "Implementation", "System Health")
    assert groups["BUILD & FIX"] == ("Fix Center", "Integrations", "Deployments", "System Lab")


def test_owner_navigation_has_no_duplicate_pages():
    pages = [label for _group, items in OWNER_NAV_GROUPS for label, _icon in items]
    assert len(pages) == len(set(pages))


def test_six_operating_zones_are_present():
    assert tuple(title for title, _icon, _items in OPERATING_ZONES) == (
        "Start My Day",
        "Business Operations",
        "Back Office",
        "People & Administration",
        "Company Control",
        "Build & Fix",
    )


def test_fix_center_covers_required_fix_classes():
    zones = {title: items for title, _icon, items in OPERATING_ZONES}
    assert set((
        "broken",
        "degraded",
        "incomplete",
        "policy drift",
        "failed tests",
        "needs approval",
        "auto-repairable",
        "code change",
        "database change",
        "human decision",
    )).issubset(set(zones["Build & Fix"]))
