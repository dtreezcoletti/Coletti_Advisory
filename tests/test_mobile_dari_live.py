import pytest

from coletti_advisory.dari_client import (
    DariBackendUnavailable,
    HttpDariClient,
    execute_mobile_dari,
)
from coletti_advisory.models import Principal, Role


CASE_ID = "JRC-1145-01"


def principal(role=Role.ANALYST):
    return Principal(
        user_id="usr-test",
        email="analyst@example.test",
        display_name="Analyst",
        organization_id="org-test",
        role=role,
        engagement_ids=(CASE_ID,),
        session_id="session-test",
        authenticated_at="2026-09-09T00:00:00+00:00",
    )


class FakeDariClient:
    def __init__(self, *, status=None, tool_result=None, reasoning_result=None):
        self._status = status or {
            "status": "ready",
            "reasoning_provider": "openai",
        }
        self._tool_result = tool_result or {
            "allowed": True,
            "requires_human_gate": False,
            "reason": "ok",
            "result": {"CON-001": {"reason": "amount mismatch"}},
        }
        self._reasoning_result = reasoning_result or {
            "disposition": "PENDING_HUMAN_REVIEW",
            "uncertainty": "LOW",
            "structured_output": {
                "narrative_draft": "The authorized records support a bounded answer.",
                "uncertainty": "LOW",
            },
        }
        self.tool_calls = []
        self.reason_calls = []

    def status(self):
        return self._status

    def tool(self, **kwargs):
        self.tool_calls.append(kwargs)
        return self._tool_result

    def reason(self, **kwargs):
        self.reason_calls.append(kwargs)
        return self._reasoning_result


def test_mobile_dari_prefers_deterministic_conflict_tool(monkeypatch):
    fake = FakeDariClient()
    monkeypatch.setattr(HttpDariClient, "from_core", classmethod(lambda cls, core: fake))

    reply = execute_mobile_dari(
        core=object(),
        principal=principal(),
        engagement_id=CASE_ID,
        command="Show me the conflicts in this case",
        manifest={"sources": {"SRB-001": {}}},
    )

    assert reply.mode == "DETERMINISTIC"
    assert reply.status == "COMPLETE"
    assert "1 recorded conflict" in reply.message
    assert fake.tool_calls[0]["tool_name"] == "identify_conflicts"
    assert fake.reason_calls == []


def test_mobile_dari_uses_live_reasoning_only_after_deterministic_miss(monkeypatch):
    fake = FakeDariClient()
    monkeypatch.setattr(HttpDariClient, "from_core", classmethod(lambda cls, core: fake))

    reply = execute_mobile_dari(
        core=object(),
        principal=principal(),
        engagement_id=CASE_ID,
        command="Explain what these records mean together",
        manifest={"sources": {"SRB-001": {}, "SRB-002": {}}},
    )

    assert reply.mode == "AI_REASONING"
    assert reply.human_review_required is True
    assert reply.message == "The authorized records support a bounded answer."
    assert fake.reason_calls[0]["source_ids"] == ["SRB-001", "SRB-002"]
    assert fake.reason_calls[0]["payload"]["user_query"] == "Explain what these records mean together"


def test_mobile_dari_does_not_call_model_when_provider_is_degraded(monkeypatch):
    fake = FakeDariClient(status={"status": "degraded", "reasoning_provider": "unconfigured"})
    monkeypatch.setattr(HttpDariClient, "from_core", classmethod(lambda cls, core: fake))

    with pytest.raises(DariBackendUnavailable, match="live AI reasoning is not configured"):
        execute_mobile_dari(
            core=object(),
            principal=principal(),
            engagement_id=CASE_ID,
            command="Explain this unusual pattern",
            manifest={"sources": {"SRB-001": {}}},
        )
    assert fake.reason_calls == []


def test_mobile_dari_requires_narrowing_before_large_case_reasoning(monkeypatch):
    fake = FakeDariClient()
    monkeypatch.setattr(HttpDariClient, "from_core", classmethod(lambda cls, core: fake))
    manifest = {"sources": {f"SRB-{index:03d}": {} for index in range(1, 52)}}

    with pytest.raises(DariBackendUnavailable, match="Narrow the request"):
        execute_mobile_dari(
            core=object(),
            principal=principal(),
            engagement_id=CASE_ID,
            command="Analyze everything",
            manifest=manifest,
        )
    assert fake.reason_calls == []


def test_http_dari_client_rejects_non_https_and_missing_service_auth():
    with pytest.raises(DariBackendUnavailable):
        HttpDariClient("http://core.example.test", {"Authorization": "Bearer token"})
    with pytest.raises(DariBackendUnavailable):
        HttpDariClient("https://core.example.test", {})
