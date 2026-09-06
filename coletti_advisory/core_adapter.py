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
    def add_proposition(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]: ...

    @abstractmethod
    def record_contradiction(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]: ...

    @abstractmethod
    def record_reconciliation(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]: ...

    @abstractmethod
    def manifest(self, engagement_id: str) -> dict[str, Any]: ...


class SyntheticCoreAdapter(CoreAdapter):
    """Synthetic-only adapter. It is not a substitute for the private ColettiOS core."""

    def __init__(self) -> None:
        self.reset_demo_data()

    def reset_demo_data(self) -> None:
        """Restore the canonical synthetic manifest for a clean demonstration.

        This method exists only on the synthetic adapter. Production/HTTP Core
        adapters intentionally expose no equivalent reset operation.
        """
        self._manifest = copy.deepcopy(SYNTHETIC_MANIFEST)
        self._manifest.setdefault("reconciliations", {})
        self._manifest.setdefault("reviewer_conclusions", {})
        self._manifest.setdefault("state_history", [])

    def _audit(self, event_type: str, subject_id: str, detail: str, auth_context: dict[str, str]) -> None:
        self._manifest.setdefault("audit_log", []).append(
            {
                "event_type": event_type,
                "subject_id": subject_id,
                "actor": auth_context["user_id"],
                "session_id": auth_context["session_id"],
                "organization_id": auth_context["organization_id"],
                "engagement_id": auth_context["engagement_id"],
                "detail": detail,
            }
        )

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
        self._audit("SOURCE_REGISTERED", source_id, f"hash={record['content_hash']}", auth_context)
        return record

    def add_proposition(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        proposition_id = str(payload["proposition_id"])
        source_ids = [str(value) for value in payload.get("source_ids", [])]
        if not source_ids:
            raise ValueError("A proposition must cite at least one source")
        missing = [source_id for source_id in source_ids if source_id not in self._manifest["sources"]]
        if missing:
            raise KeyError(f"Unknown source IDs: {', '.join(missing)}")
        if proposition_id in self._manifest["propositions"]:
            raise ValueError("Duplicate proposition ID")
        record = {
            "proposition_id": proposition_id,
            "text": str(payload["text"]),
            "source_ids": source_ids,
        }
        self._manifest["propositions"][proposition_id] = record
        self._audit("PROPOSITION_ADDED", proposition_id, f"sources={','.join(source_ids)}", auth_context)
        return record

    def record_contradiction(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        contradiction_id = str(payload["contradiction_id"])
        proposition_a = str(payload["proposition_a"])
        proposition_b = str(payload["proposition_b"])
        if proposition_a == proposition_b:
            raise ValueError("A contradiction requires two distinct propositions")
        for proposition_id in (proposition_a, proposition_b):
            if proposition_id not in self._manifest["propositions"]:
                raise KeyError(f"Unknown proposition ID: {proposition_id}")
        if contradiction_id in self._manifest["contradictions"]:
            raise ValueError("Duplicate contradiction ID")
        record = {
            "contradiction_id": contradiction_id,
            "proposition_a": proposition_a,
            "proposition_b": proposition_b,
            "reason": str(payload["reason"]),
        }
        self._manifest["contradictions"][contradiction_id] = record
        self._audit("CONTRADICTION_RECORDED", contradiction_id, record["reason"], auth_context)
        return record

    def record_reconciliation(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        reconciliation_id = str(payload["reconciliation_id"])
        proposition_ids = [str(value) for value in payload.get("proposition_ids", [])]
        contradiction_ids = [str(value) for value in payload.get("contradiction_ids", [])]
        if not proposition_ids:
            raise ValueError("Reconciliation must reference at least one proposition")
        missing_props = [pid for pid in proposition_ids if pid not in self._manifest["propositions"]]
        if missing_props:
            raise KeyError(f"Unknown proposition IDs: {', '.join(missing_props)}")
        missing_cons = [cid for cid in contradiction_ids if cid not in self._manifest["contradictions"]]
        if missing_cons:
            raise KeyError(f"Unknown contradiction IDs: {', '.join(missing_cons)}")
        if reconciliation_id in self._manifest["reconciliations"]:
            raise ValueError("Duplicate reconciliation ID")
        outcome = str(payload.get("outcome") or "").strip()
        rationale = str(payload.get("rationale") or "").strip()
        if not outcome or not rationale:
            raise ValueError("Reconciliation outcome and rationale are required")
        record = {
            "reconciliation_id": reconciliation_id,
            "proposition_ids": proposition_ids,
            "contradiction_ids": contradiction_ids,
            "outcome": outcome,
            "actor": auth_context["user_id"],
            "rationale": rationale,
        }
        self._manifest["reconciliations"][reconciliation_id] = record
        self._audit("RECONCILIATION_RECORDED", reconciliation_id, rationale, auth_context)
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

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def register_source(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        return self._post("/v1/sources", {"source": payload, "auth_context": auth_context})

    def add_proposition(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        return self._post("/v1/propositions", {**payload, "auth_context": auth_context})

    def record_contradiction(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        return self._post("/v1/contradictions", {**payload, "auth_context": auth_context})

    def record_reconciliation(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        return self._post("/v1/reconciliations", {**payload, "auth_context": auth_context})

    def manifest(self, engagement_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/v1/engagements/{engagement_id}/manifest",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
