from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PublicationStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REVOKED = "REVOKED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def report_fingerprint(report: dict[str, Any]) -> str:
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(canonical).hexdigest()


@dataclass
class ReportPublicationRecord:
    report_type: str
    status: PublicationStatus = PublicationStatus.DRAFT
    revision: int = 1
    draft_hash: str = ""
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    published_by: str | None = None
    published_at: str | None = None
    revoked_by: str | None = None
    revoked_at: str | None = None
    review_note: str | None = None
    published_snapshot: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "status": self.status.value,
            "revision": self.revision,
            "draft_hash": self.draft_hash,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "published_by": self.published_by,
            "published_at": self.published_at,
            "revoked_by": self.revoked_by,
            "revoked_at": self.revoked_at,
            "review_note": self.review_note,
            "published_snapshot": self.published_snapshot,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReportPublicationRecord":
        return cls(
            report_type=str(value["report_type"]),
            status=PublicationStatus(str(value.get("status", "DRAFT"))),
            revision=int(value.get("revision", 1)),
            draft_hash=str(value.get("draft_hash", "")),
            reviewed_by=value.get("reviewed_by"),
            reviewed_at=value.get("reviewed_at"),
            approved_by=value.get("approved_by"),
            approved_at=value.get("approved_at"),
            published_by=value.get("published_by"),
            published_at=value.get("published_at"),
            revoked_by=value.get("revoked_by"),
            revoked_at=value.get("revoked_at"),
            review_note=value.get("review_note"),
            published_snapshot=value.get("published_snapshot"),
        )


class PublicationStore(Protocol):
    def load(self, *, organization_id: str, engagement_id: str) -> dict[str, ReportPublicationRecord]: ...
    def save(self, *, organization_id: str, engagement_id: str, records: dict[str, ReportPublicationRecord]) -> None: ...


def _aad(organization_id: str, engagement_id: str) -> bytes:
    return f"publication-state|{organization_id}|{engagement_id}".encode()


def _encrypt_json(value: dict[str, Any], key: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    payload = json.dumps(value, sort_keys=True, default=str).encode()
    return nonce + AESGCM(key).encrypt(nonce, payload, aad)


def _decrypt_json(value: bytes, key: bytes, aad: bytes) -> dict[str, Any]:
    if len(value) < 13:
        raise ValueError("Invalid encrypted publication state")
    nonce, ciphertext = value[:12], value[12:]
    payload = AESGCM(key).decrypt(nonce, ciphertext, aad)
    decoded = json.loads(payload.decode())
    if not isinstance(decoded, dict):
        raise ValueError("Invalid publication state payload")
    return decoded


def _serialize(records: dict[str, ReportPublicationRecord]) -> dict[str, Any]:
    return {key: value.as_dict() for key, value in records.items()}


def _deserialize(value: dict[str, Any]) -> dict[str, ReportPublicationRecord]:
    return {
        str(key): ReportPublicationRecord.from_dict(record)
        for key, record in value.items()
        if isinstance(record, dict)
    }


class EncryptedLocalPublicationStore:
    def __init__(self, root: str | Path, master_key: bytes) -> None:
        self.root = Path(root)
        self.master_key = master_key

    def _path(self, organization_id: str, engagement_id: str) -> Path:
        safe = lambda value: "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
        return self.root / safe(organization_id) / safe(engagement_id) / "publication-state.enc"

    def load(self, *, organization_id: str, engagement_id: str) -> dict[str, ReportPublicationRecord]:
        path = self._path(organization_id, engagement_id)
        if not path.exists():
            return {}
        return _deserialize(_decrypt_json(path.read_bytes(), self.master_key, _aad(organization_id, engagement_id)))

    def save(self, *, organization_id: str, engagement_id: str, records: dict[str, ReportPublicationRecord]) -> None:
        path = self._path(organization_id, engagement_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_encrypt_json(_serialize(records), self.master_key, _aad(organization_id, engagement_id)))


class GoogleCloudPublicationStore:
    def __init__(self, *, bucket_name: str, service_account_json: str, master_key: bytes) -> None:
        from google.cloud import storage
        from google.oauth2 import service_account

        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        self.client = storage.Client(project=info.get("project_id"), credentials=credentials)
        self.bucket = self.client.bucket(bucket_name)
        self.master_key = master_key

    def _blob(self, organization_id: str, engagement_id: str):
        safe = lambda value: "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
        return self.bucket.blob(f"{safe(organization_id)}/{safe(engagement_id)}/_state/publication-state.enc")

    def load(self, *, organization_id: str, engagement_id: str) -> dict[str, ReportPublicationRecord]:
        blob = self._blob(organization_id, engagement_id)
        if not blob.exists(client=self.client):
            return {}
        payload = blob.download_as_bytes()
        return _deserialize(_decrypt_json(payload, self.master_key, _aad(organization_id, engagement_id)))

    def save(self, *, organization_id: str, engagement_id: str, records: dict[str, ReportPublicationRecord]) -> None:
        blob = self._blob(organization_id, engagement_id)
        payload = _encrypt_json(_serialize(records), self.master_key, _aad(organization_id, engagement_id))
        blob.metadata = {
            "organization_id": organization_id,
            "engagement_id": engagement_id,
            "state_type": "report-publication",
            "encryption": "AES-256-GCM-client-side",
        }
        blob.upload_from_string(payload, content_type="application/octet-stream")


def sync_drafts(
    records: dict[str, ReportPublicationRecord],
    report_bundle: dict[str, dict[str, Any]],
) -> dict[str, ReportPublicationRecord]:
    updated = dict(records)
    for report_type, report in report_bundle.items():
        fingerprint = report_fingerprint(report)
        record = updated.get(report_type)
        if record is None:
            updated[report_type] = ReportPublicationRecord(report_type=report_type, draft_hash=fingerprint)
            continue
        if record.draft_hash != fingerprint and record.status != PublicationStatus.PUBLISHED:
            record.revision += 1
            record.draft_hash = fingerprint
            record.status = PublicationStatus.DRAFT
            record.reviewed_by = None
            record.reviewed_at = None
            record.approved_by = None
            record.approved_at = None
            record.review_note = None
    return updated


def send_to_review(record: ReportPublicationRecord, *, actor: str, note: str | None = None) -> None:
    if record.status not in {PublicationStatus.DRAFT, PublicationStatus.REVOKED}:
        raise ValueError("Only draft or revoked reports can enter review")
    record.status = PublicationStatus.IN_REVIEW
    record.reviewed_by = actor
    record.reviewed_at = utc_now_iso()
    record.review_note = note or None


def approve_report(record: ReportPublicationRecord, *, actor: str) -> None:
    if record.status != PublicationStatus.IN_REVIEW:
        raise ValueError("Report must be in review before approval")
    record.status = PublicationStatus.APPROVED
    record.approved_by = actor
    record.approved_at = utc_now_iso()


def publish_report(record: ReportPublicationRecord, *, actor: str, report: dict[str, Any]) -> None:
    if record.status != PublicationStatus.APPROVED:
        raise ValueError("Report must be approved before publication")
    if record.draft_hash != report_fingerprint(report):
        raise ValueError("Approved draft changed; return report to review")
    snapshot = json.loads(json.dumps(report, default=str))
    snapshot["document_status"] = "PUBLISHED"
    record.published_snapshot = snapshot
    record.status = PublicationStatus.PUBLISHED
    record.published_by = actor
    record.published_at = utc_now_iso()
    record.revoked_by = None
    record.revoked_at = None


def revoke_report(record: ReportPublicationRecord, *, actor: str) -> None:
    if record.status != PublicationStatus.PUBLISHED:
        raise ValueError("Only published reports can be revoked")
    record.status = PublicationStatus.REVOKED
    record.revoked_by = actor
    record.revoked_at = utc_now_iso()


def published_reports(records: dict[str, ReportPublicationRecord]) -> dict[str, dict[str, Any]]:
    return {
        report_type: record.published_snapshot
        for report_type, record in records.items()
        if record.status == PublicationStatus.PUBLISHED and record.published_snapshot is not None
    }
