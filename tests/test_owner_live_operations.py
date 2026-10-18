"""Owner live-source contracts: presentation never manufactures source records."""
from types import SimpleNamespace

from coletti_advisory.models import Role
from coletti_advisory.owner_live_operations import (
    DEPARTMENTS, PAGE_SOURCE, _display_rows, _is_owner, _money,
)


def test_exact_nine_department_identifiers():
    assert tuple(name for name, _ in DEPARTMENTS) == (
        "FABER", "VOX", "QUAERO", "MONETA", "SCRIBA",
        "CURA", "CIVIS", "AUGEO", "ACQUIRO",
    )


def test_all_operating_routes_have_registered_data_sources():
    for key in ("Billing", "Contracts", "Pricing", "Assignments",
                "Integrations", "Documents", "Referrals", "Deployments",
                "Fix Center", "Finance", "Workers"):
        assert key in PAGE_SOURCE
        assert PAGE_SOURCE[key][0]


def test_financial_format_uses_cents_and_explicit_missing_data():
    assert _money(1300) == "$13.00"
    assert _money(250050) == "$2,500.50"
    assert _money(None) == "—"
    assert _money("bad") == "Unverified"


def test_rows_preserve_source_values_and_never_mutate_inputs():
    original = [{"amount_cents": 25050, "invoice_number": "INV-1"}]
    view = _display_rows("Billing", original)
    assert view == [{"invoice_number": "INV-1", "Amount": "$250.50"}]
    assert original[0]["amount_cents"] == 25050


def test_owner_role_and_authentication_are_both_required():
    assert _is_owner(SimpleNamespace(role=Role.OWNER, authenticated=True))
    assert not _is_owner(SimpleNamespace(role=Role.OWNER, authenticated=False))
    assert not _is_owner(SimpleNamespace(role=Role.EMPLOYEE, authenticated=True))
