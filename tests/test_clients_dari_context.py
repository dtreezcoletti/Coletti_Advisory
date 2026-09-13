from __future__ import annotations

from types import SimpleNamespace

import coletti_advisory.client_dari_context as bridge


class FakeClientOperations:
    def __init__(self):
        self.rows = [
            {
                "client_id": "C26-92",
                "display_name": "Example Client",
                "client_status": "ACTIVE",
                "active_case_count": 1,
                "next_action": "Review contract",
                "next_action_date": None,
            }
        ]

    def list_clients(self, **kwargs):
        query = str(kwargs.get("query") or "")
        if query and query not in {"C26-92", "Example Client"}:
            return []
        return self.rows

    def client_detail(self, client_id):
        assert client_id == "C26-92"
        return {
            "client": {
                "client_id": "C26-92",
                "display_name": "Example Client",
                "status": "ACTIVE",
                "referral_source": "Attorney Smith",
                "next_action": "Review contract",
            },
            "cases": [{"case_id": "REC-260906-01", "status": "ACTIVE"}],
            "reports": [],
        }


def test_dari_can_answer_canonical_client_id_query(monkeypatch):
    monkeypatch.setattr(bridge.st, "session_state", {})
    answer = bridge._client_answer(FakeClientOperations(), "Find C26-92")
    assert "C26-92" in answer
    assert "1 active" in answer


def test_dari_uses_selected_client_context_for_referral(monkeypatch):
    monkeypatch.setattr(
        bridge.st,
        "session_state",
        {bridge.CLIENT_CONTEXT_KEY: {"client_id": "C26-92", "display_name": "Example Client"}},
    )
    answer = bridge._client_answer(FakeClientOperations(), "Who referred this client?")
    assert "Attorney Smith" in answer


def test_proxy_adds_context_without_replacing_existing_context(monkeypatch):
    monkeypatch.setattr(
        bridge.st,
        "session_state",
        {bridge.CLIENT_CONTEXT_KEY: {"client_id": "C26-92", "display_name": "Example Client"}},
    )
    calls = []

    class Base:
        def route_command(self, principal, engagement_id, command_text, **kwargs):
            calls.append((principal, engagement_id, command_text, kwargs))
            return {"routing_state": "ROUTED"}

    proxy = bridge._ClientContextProxy(Base())
    principal = SimpleNamespace(user_id="owner")
    result = proxy.route_command(
        principal,
        "REC-260906-01",
        "Draft a client note",
        context={"requested_capability": "owner_console_dari", "existing": "kept"},
    )
    assert result["routing_state"] == "ROUTED"
    context = calls[0][3]["context"]
    assert context["existing"] == "kept"
    assert context["selected_client_id"] == "C26-92"
    assert context["source_surface"] == "Clients"


def test_proxy_does_not_inject_client_context_into_non_dari_routes(monkeypatch):
    monkeypatch.setattr(
        bridge.st,
        "session_state",
        {bridge.CLIENT_CONTEXT_KEY: {"client_id": "C26-92", "display_name": "Example Client"}},
    )
    calls = []

    class Base:
        def route_command(self, principal, engagement_id, command_text, **kwargs):
            calls.append(kwargs)
            return {}

    bridge._ClientContextProxy(Base()).route_command(
        SimpleNamespace(user_id="owner"),
        "REC-260906-01",
        "reconcile",
        context={"requested_capability": "owner_dispatcher"},
    )
    assert "selected_client_id" not in calls[0]["context"]
