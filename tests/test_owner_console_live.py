from __future__ import annotations

from coletti_advisory.owner_console_live import OwnerControlPlaneClient
from coletti_advisory.owner_console_live_ui import _decision_items, _deterministic_dari_answer


class FakeCore:
    base_url = "https://core.example.test"
    headers = {"Authorization": "Bearer service-token"}
    timeout = 5.0


class FakePrincipal:
    authenticated = True

    def auth_context(self, engagement_id: str):
        return {
            "user_id": "usr-owner",
            "organization_id": "org-coletti",
            "engagement_id": engagement_id,
            "role": "owner",
            "session_id": "sess-1",
            "authenticated_at": "2026-09-08T15:00:00+00:00",
        }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_owner_control_plane_snapshot_uses_private_core_service(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse({"counts": {"approvals": 2}})

    monkeypatch.setattr("coletti_advisory.owner_console_live.requests.post", fake_post)
    client = OwnerControlPlaneClient(FakeCore())
    result = client.snapshot(FakePrincipal(), "eng-live")

    assert result["counts"]["approvals"] == 2
    assert seen["url"].endswith("/v1/owner/snapshot")
    assert seen["json"]["auth_context"]["role"] == "owner"
    assert seen["headers"]["Authorization"].startswith("Bearer ")


def test_owner_decision_preserves_explicit_protected_gate_confirmation(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update({"url": url, "json": json})
        return FakeResponse({"decision": "APPROVED"})

    monkeypatch.setattr("coletti_advisory.owner_console_live.requests.post", fake_post)
    client = OwnerControlPlaneClient(FakeCore())
    result = client.decide(
        FakePrincipal(),
        "eng-live",
        approval_key="PROJECT_CONTROL:ColettiOS",
        decision="APPROVE",
        reason="Reviewed",
        confirm_protected_gate=True,
    )

    assert result["decision"] == "APPROVED"
    assert seen["json"]["confirm_protected_gate"] is True
    assert seen["json"]["reason"] == "Reviewed"


def test_live_decision_items_keep_authoritative_gate_metadata():
    items = _decision_items(
        {
            "approvals": [
                {
                    "approval_key": "RELEASE_MANIFEST:1",
                    "source_type": "RELEASE_MANIFEST",
                    "source_id": "1",
                    "owning_domain": "dispatcher",
                    "title": "Release authorization",
                    "detail": {"release_status": "CANDIDATE"},
                    "protected_gate": True,
                    "current_state": "CANDIDATE",
                    "created_at": "2026-09-08T15:00:00+00:00",
                }
            ]
        }
    )

    assert items[0]["approval_key"] == "RELEASE_MANIFEST:1"
    assert items[0]["protected_gate"] is True
    assert items[0]["status"] == "Protected Approval"


def test_dari_answers_common_owner_questions_without_model_call():
    snapshot = {
        "approvals": [{"title": "Security gate"}],
        "tasks": [
            {
                "title": "Run acceptance test",
                "project": "ColettiOS",
                "due_today": True,
                "overdue": False,
                "next_action": "Run JRC-1145-01",
            }
        ],
        "for_human": {"Problems / Conflicts": [], "What Matters Next": [], "Important Changes": []},
    }

    decision_answer = _deterministic_dari_answer("What needs my decision?", snapshot)
    next_answer = _deterministic_dari_answer("What should I work on next?", snapshot)

    assert "Security gate" in decision_answer
    assert "Run acceptance test" in next_answer
    assert "Run JRC-1145-01" in next_answer
