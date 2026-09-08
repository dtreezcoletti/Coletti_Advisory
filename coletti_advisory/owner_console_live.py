from __future__ import annotations

from typing import Any

import requests


class OwnerControlPlaneUnavailable(RuntimeError):
    pass


class OwnerControlPlaneClient:
    """Authenticated Streamlit-to-ColettiOS owner control-plane client.

    The Streamlit process never receives a Supabase database credential. It reuses
    the existing private ColettiOS service URL and bearer token, while the service
    performs owner-only Dispatcher reads/writes against authoritative PostgreSQL.
    """

    def __init__(self, core: Any) -> None:
        base_url = str(getattr(core, "base_url", "") or "").rstrip("/")
        headers = dict(getattr(core, "headers", {}) or {})
        timeout = float(getattr(core, "timeout", 20.0) or 20.0)
        if not base_url.startswith("https://"):
            raise OwnerControlPlaneUnavailable("Live owner control plane requires the HTTPS ColettiOS service")
        if not str(headers.get("Authorization") or "").startswith("Bearer "):
            raise OwnerControlPlaneUnavailable("ColettiOS service authentication is not configured")
        self.base_url = base_url
        self.headers = headers
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OwnerControlPlaneUnavailable("The private ColettiOS owner service is not reachable") from exc
        data = response.json()
        if not isinstance(data, dict):
            raise OwnerControlPlaneUnavailable("Owner service returned an invalid response")
        return data

    @staticmethod
    def _auth(principal, engagement_id: str) -> dict[str, str]:
        if not principal.authenticated:
            raise OwnerControlPlaneUnavailable("Live owner controls require an authenticated owner session")
        return principal.auth_context(engagement_id)

    def snapshot(self, principal, engagement_id: str) -> dict[str, Any]:
        return self._post(
            "/v1/owner/snapshot",
            {"auth_context": self._auth(principal, engagement_id)},
        )

    def route_command(
        self,
        principal,
        engagement_id: str,
        command_text: str,
        *,
        origin_domain: str = "colettios",
        context: dict[str, Any] | None = None,
        target_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/owner/command",
            {
                "command_text": command_text,
                "auth_context": self._auth(principal, engagement_id),
                "origin_domain": origin_domain,
                "context": dict(context or {}),
                "target_domains": target_domains,
            },
        )

    def decide(
        self,
        principal,
        engagement_id: str,
        *,
        approval_key: str,
        decision: str,
        reason: str | None = None,
        domain_payload: dict[str, Any] | None = None,
        confirm_protected_gate: bool = False,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/owner/decision",
            {
                "approval_key": approval_key,
                "decision": decision,
                "auth_context": self._auth(principal, engagement_id),
                "reason": reason,
                "domain_payload": dict(domain_payload or {}),
                "confirm_protected_gate": bool(confirm_protected_gate),
            },
        )
