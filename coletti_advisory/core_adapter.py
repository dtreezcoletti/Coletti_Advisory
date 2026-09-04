from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any

import requests

from .synthetic import SYNTHETIC_MANIFEST


class CoreAdapter(ABC):
    @abstractmethod
    def register_source(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]: ...

    @abstractmethod
    def manifest(self, engagement_id: str) -> dict[str, Any]: ...


class SyntheticCoreAdapter(CoreAdapter):
    """Synthetic-only adapter. It is not a substitute for the private ColettiOS core."""

    def __init__(self) -> None:
        self._manifest = copy.deepcopy(SYNTHETIC_MANIFEST)

    def register_source(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        source_id = str(payload["source_id"])
        if source_id in self._manifest["sources"]:
            raise ValueError("Duplicate source ID")
        record = {
            "source_id": source_id,
            "content_hash": str(payload["content_hash"]),
            "metadata": dict(payload.get("metadata", {})),
        }
        self._manifest["sources"][source_id] = record
        self._manifest["source_states"][source_id] = "INGESTED"
        self._manifest["audit_log"].append(
            {
                "event_type": "SOURCE_REGISTERED",
                "subject_id": source_id,
                "actor": auth_context["user_id"],
                "session_id": auth_context["session_id"],
                "organization_id": auth_context["organization_id"],
                "engagement_id": auth_context["engagement_id"],
                "detail": f"hash={record['content_hash']}",
            }
        )
        return record

    def manifest(self, engagement_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._manifest)


class HttpColettiOSAdapter(CoreAdapter):
    """Commercial-to-core contract for a separately deployed private ColettiOS service."""

    def __init__(self, base_url: str, service_token: str, timeout: float = 20.0) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("Production ColettiOS API must use HTTPS")
        if not service_token:
            raise ValueError("ColettiOS service token is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {service_token}"}

    def register_source(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/v1/sources",
            json={"source": payload, "auth_context": auth_context},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def manifest(self, engagement_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/v1/engagements/{engagement_id}/manifest",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
