from __future__ import annotations

from types import SimpleNamespace

import coletti_advisory.client_operations as clients
from coletti_advisory.owner_console_structure import OWNER_SIDEBAR_GROUPS


def test_clients_is_canonical_business_sidebar_destination():
    business = dict(next(items for group, items in OWNER_SIDEBAR_GROUPS if group == "BUSINESS"))
    assert "Clients" in business


def test_client_directory_uses_authenticated_scoped_rpc(monkeypatch):
    calls = []
    monkeypatch.setattr(clients.supabase_auth, "current_access_token", lambda: "token")

    def fake_rpc(name, *, access_token, payload):
        calls.append((name, access_token, payload))
        return [{"client_id": "C26-92", "display_name": "Example Client"}]

    monkeypatch.setattr(clients.supabase_auth, "_rpc", fake_rpc)
    rows = clients.list_clients(query="Example", status="ACTIVE", limit=50)
    assert rows[0]["client_id"] == "C26-92"
    assert calls == [
        (
            "client_directory_v1",
            "token",
            {"p_query": "Example", "p_status": "ACTIVE", "p_limit": 50},
        )
    ]


def test_client_actions_do_not_generate_identifiers_in_ui(monkeypatch):
    monkeypatch.setattr(clients.supabase_auth, "current_access_token", lambda: "token")
    seen = []

    def fake_rpc(name, *, access_token, payload):
        seen.append((name, payload))
        return "C26-92"

    monkeypatch.setattr(clients.supabase_auth, "_rpc", fake_rpc)
    value = clients.accept_intake("11111111-1111-1111-1111-111111111111", client_type="INDIVIDUAL")
    assert value == "C26-92"
    assert seen[0][0] == "admin_accept_intake_v1"
    assert "client_id" not in seen[0][1]


def test_status_change_requires_authoritative_rpc(monkeypatch):
    monkeypatch.setattr(clients.supabase_auth, "current_access_token", lambda: "token")
    seen = []

    def fake_rpc(name, *, access_token, payload):
        seen.append((name, payload))
        return None

    monkeypatch.setattr(clients.supabase_auth, "_rpc", fake_rpc)
    clients.set_client_status("C26-92", "INACTIVE", reason="No active engagement")
    assert seen == [
        (
            "admin_set_client_status_v1",
            {"p_client_id": "C26-92", "p_status": "INACTIVE", "p_reason": "No active engagement"},
        )
    ]


def test_portal_access_is_controlled_by_rpc(monkeypatch):
    monkeypatch.setattr(clients.supabase_auth, "current_access_token", lambda: "token")
    seen = []

    def fake_rpc(name, *, access_token, payload):
        seen.append((name, payload))
        return "22222222-2222-2222-2222-222222222222"

    monkeypatch.setattr(clients.supabase_auth, "_rpc", fake_rpc)
    clients.set_portal_user(
        "C26-92",
        "client@example.com",
        role="authorized_contact",
        active=False,
        reason="Access withdrawn",
    )
    assert seen[0][0] == "admin_set_client_portal_user_v1"
    assert seen[0][1]["p_active"] is False
    assert seen[0][1]["p_reason"] == "Access withdrawn"


def test_clients_patch_owns_only_clients_route(monkeypatch):
    events = []

    def original(shell, page, **kwargs):
        events.append(("original", page))
        return page

    runtime = SimpleNamespace(_render_owner_page=original)
    monkeypatch.setattr(
        clients,
        "render_clients_operating_surface",
        lambda shell, **kwargs: events.append(("clients", kwargs["principal"])),
    )
    clients.patch_clients_operating_surface(runtime)
    principal = SimpleNamespace(user_id="owner")
    runtime._render_owner_page(None, "Clients", principal=principal)
    runtime._render_owner_page(None, "Cases", principal=principal)
    assert events[0] == ("clients", principal)
    assert events[1] == ("original", "Cases")
    assert runtime._clients_operating_spec_v1_patched is True
