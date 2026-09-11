from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import requests

from .models import Principal
from .record_governance import PROTECTED_PROFESSION_RULE, DariTier, route_dari_command


class DariBackendUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class MobileDariReply:
    mode: str
    status: str
    message: str
    payload: Mapping[str, Any]
    human_review_required: bool = False


class HttpDariClient:
    """Thin commercial-app client for the private ColettiOS DARI boundary.

    It reuses the already-authenticated Core adapter transport and never owns
    identity, permissions, Record State, or reasoning authority itself.
    """

    def __init__(self, base_url: str, headers: Mapping[str, str], timeout: float = 20.0) -> None:
        if not str(base_url).startswith("https://"):
            raise DariBackendUnavailable("Live DARI requires the private HTTPS ColettiOS backend")
        authorization = str(headers.get("Authorization", ""))
        if not authorization.startswith("Bearer "):
            raise DariBackendUnavailable("Live DARI requires the existing ColettiOS service credential")
        self.base_url = str(base_url).rstrip("/")
        self.headers = {"Authorization": authorization}
        self.timeout = float(timeout)

    @classmethod
    def from_core(cls, core: Any) -> "HttpDariClient":
        base_url = getattr(core, "base_url", None)
        headers = getattr(core, "headers", None)
        timeout = getattr(core, "timeout", 20.0)
        if not base_url or not isinstance(headers, Mapping):
            raise DariBackendUnavailable(
                "Live DARI is unavailable until this workspace is using the private HTTP ColettiOS backend"
            )
        return cls(base_url, headers, timeout)

    def _get(self, path: str) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DariBackendUnavailable("DARI backend could not be reached") from exc
        return response.json()

    def _post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=dict(payload),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                try:
                    body = exc.response.json()
                    detail = str(body.get("detail") or "")
                except Exception:
                    detail = ""
            suffix = f": {detail}" if detail else ""
            raise DariBackendUnavailable(f"DARI request failed{suffix}") from exc
        return response.json()

    def status(self) -> dict[str, Any]:
        return self._get("/v1/dari/status")

    def tool(
        self,
        *,
        principal: Principal,
        engagement_id: str,
        tool_name: str,
        subject_id: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/dari/tool",
            {
                "tool_name": tool_name,
                "subject_id": subject_id,
                "query": query,
                "auth_context": principal.auth_context(engagement_id),
            },
        )

    def reason(
        self,
        *,
        principal: Principal,
        engagement_id: str,
        operation_type: str,
        source_ids: list[str],
        proposition_ids: list[str] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/dari/reason",
            {
                "operation_type": operation_type,
                "source_ids": source_ids,
                "proposition_ids": proposition_ids or [],
                "payload": dict(payload or {}),
                "auth_context": principal.auth_context(engagement_id),
            },
        )


_DETERMINISTIC_INTENTS = (
    (("conflict", "contradiction", "disagree"), "identify_conflicts"),
    (("missing", "gap", "need document", "needs document"), "identify_missing_docs"),
    (("status", "summary", "attention", "case", "what's going on", "what is going on"), "summarize_case_state"),
)


def _deterministic_tool(command: str) -> str | None:
    normalized = " ".join(str(command).lower().split())
    for phrases, tool_name in _DETERMINISTIC_INTENTS:
        if any(phrase in normalized for phrase in phrases):
            return tool_name
    return None


def _deterministic_message(tool_name: str, result: Any) -> str:
    if tool_name == "identify_conflicts":
        count = len(result or {})
        return f"I found {count} recorded conflict{'s' if count != 1 else ''} in this authorized case."
    if tool_name == "identify_missing_docs":
        count = len(result or {})
        return f"I found {count} missing-documentation item{'s' if count != 1 else ''} in this authorized case."
    if tool_name == "summarize_case_state" and isinstance(result, Mapping):
        return (
            "Current authorized case state: "
            f"{len(result.get('sources') or {})} sources, "
            f"{len(result.get('propositions') or {})} record statements, "
            f"{len(result.get('contradictions') or {})} conflicts, and "
            f"{len(result.get('reconciliations') or {})} reconciliations."
        )
    return "DARI completed the deterministic request."


def execute_mobile_dari(
    *,
    core: Any,
    principal: Principal,
    engagement_id: str,
    command: str,
    manifest: Mapping[str, Any],
    max_reasoning_sources: int = 50,
) -> MobileDariReply:
    text = str(command).strip()
    if not text:
        raise ValueError("DARI command text is required")

    client = HttpDariClient.from_core(core)
    tool_name = _deterministic_tool(text)
    if tool_name:
        routing = route_dari_command(text, deterministic=True)
        response = client.tool(
            principal=principal,
            engagement_id=engagement_id,
            tool_name=tool_name,
        )
        response = {**response, "dari_routing": {"tier": routing.tier.value, "operation_class": routing.operation_class}}
        if not response.get("allowed"):
            return MobileDariReply(
                mode="NO_AI",
                status="DENIED",
                message=str(response.get("reason") or "DARI denied the request."),
                payload=response,
                human_review_required=bool(response.get("requires_human_gate")),
            )
        result = response.get("result")
        return MobileDariReply(
            mode="NO_AI",
            status="COMPLETE",
            message=_deterministic_message(tool_name, result),
            payload=response,
            human_review_required=False,
        )

    routing = route_dari_command(text)
    if routing.blocked:
        return MobileDariReply(
            mode="PROFESSIONAL_HANDOFF",
            status="REFERRAL_REQUIRED",
            message=PROTECTED_PROFESSION_RULE,
            payload={
                "dari_routing": {
                    "tier": DariTier.NO_AI.value,
                    "operation_class": routing.operation_class,
                    "blocked": True,
                    "referral_required": True,
                },
                "record_state": "Referral Required",
                "professional_boundary": PROTECTED_PROFESSION_RULE,
            },
            human_review_required=True,
        )

    provider_status = client.status()
    if provider_status.get("reasoning_provider") != "openai" or provider_status.get("status") != "ready":
        raise DariBackendUnavailable(
            "DARI's NO_AI tools are available, but live AI reasoning is not configured or available yet"
        )

    source_ids = list((manifest.get("sources") or {}).keys())
    if not source_ids:
        raise DariBackendUnavailable(
            "DARI needs at least one authorized source before it can perform record reasoning"
        )
    if len(source_ids) > max_reasoning_sources:
        raise DariBackendUnavailable(
            f"This case has {len(source_ids)} sources. Narrow the request before live mobile reasoning."
        )

    response = client.reason(
        principal=principal,
        engagement_id=engagement_id,
        operation_type="analysis",
        source_ids=source_ids,
        payload={
            "user_query": text,
            "surface": "coletti_mobile",
            "dari_routing_tier": routing.tier.value,
            "dari_operation_class": routing.operation_class,
            "human_review_required": True,
            "protected_profession_rule": PROTECTED_PROFESSION_RULE,
        },
    )
    structured = response.get("structured_output") or {}
    narrative = str(structured.get("narrative_draft") or "").strip()
    uncertainty = str(response.get("uncertainty") or structured.get("uncertainty") or "UNSPECIFIED")
    message = narrative or "DARI completed the reasoning request and queued it for human review."
    return MobileDariReply(
        mode=routing.tier.value,
        status=str(response.get("disposition") or "PENDING_HUMAN_REVIEW"),
        message=message,
        payload={
            **response,
            "display_uncertainty": uncertainty,
            "dari_routing": {
                "tier": routing.tier.value,
                "operation_class": routing.operation_class,
                "human_review_required": True,
            },
        },
        human_review_required=True,
    )
