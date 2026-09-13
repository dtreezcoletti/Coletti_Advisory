from __future__ import annotations

import hashlib
import io
import json
import posixpath
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
SUPPORTED_EXPORT_NAMES = {"conversations.json", "chatgpt_conversations.json"}


class ContinuityDomain(str, Enum):
    INSTITUTIONAL = "institutional"
    OWNER_PRIVATE = "owner_private"
    LEGAL_PRIVATE = "legal_private"
    ARCHIVE_ONLY = "archive_only"
    AMBIGUOUS = "ambiguous"


class CandidateKind(str, Enum):
    DECISION = "decision"
    RULE = "rule"
    OPEN_ISSUE = "open_issue"
    FACT = "fact"
    WORKING_NOTE = "working_note"


@dataclass(frozen=True)
class ParsedMessage:
    conversation_id: str
    conversation_title: str
    message_id: str
    role: str
    created_at: str | None
    text: str
    content_hash: str
    domain: ContinuityDomain
    confidence: float
    candidate_kind: CandidateKind
    sensitivity: str
    needs_review: bool
    source_system: str = "chatgpt"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["domain"] = self.domain.value
        data["candidate_kind"] = self.candidate_kind.value
        return data


@dataclass(frozen=True)
class ImportBundle:
    source_system: str
    source_filename: str
    archive_sha256: str
    conversations_discovered: int
    messages_discovered: int
    messages: tuple[ParsedMessage, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def review_count(self) -> int:
        return sum(1 for item in self.messages if item.needs_review)

    def domain_counts(self) -> dict[str, int]:
        counts = {domain.value: 0 for domain in ContinuityDomain}
        for item in self.messages:
            counts[item.domain.value] += 1
        return counts

    def candidate_counts(self) -> dict[str, int]:
        counts = {kind.value: 0 for kind in CandidateKind}
        for item in self.messages:
            counts[item.candidate_kind.value] += 1
        return counts

    def staging_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "owner-continuity-v0.1",
            "mode": "shadow",
            "source_system": self.source_system,
            "source_filename": self.source_filename,
            "archive_sha256": self.archive_sha256,
            "conversations_discovered": self.conversations_discovered,
            "messages_discovered": self.messages_discovered,
            "review_count": self.review_count,
            "domain_counts": self.domain_counts(),
            "candidate_counts": self.candidate_counts(),
            "warnings": list(self.warnings),
            "messages": [item.to_dict() for item in self.messages],
        }


LEGAL_TERMS = {
    "divorce",
    "dissolution",
    "mda",
    "marital dissolution",
    "court",
    "judge",
    "docket",
    "hearing",
    "alimony",
    "qdro",
    "settlement",
    "opposing counsel",
    "petitioner",
    "respondent",
    "decree",
    "subpoena",
    "discovery",
    "attorney",
    "lawyer",
}

OWNER_PRIVATE_TERMS = {
    "job search",
    "employment",
    "employer",
    "resume",
    "recruiter",
    "interview",
    "salary",
    "career",
    "rent",
    "housing",
    "landlord",
    "apartment",
    "personal finance",
    "checking account",
    "credit card",
    "personal budget",
    "chapter 2",
    "family",
}

INSTITUTIONAL_TERMS = {
    "colettios",
    "coletti & co",
    "coletti and co",
    "dispatcher",
    "dari",
    "supabase",
    "github",
    "client portal",
    "owner portal",
    "employee portal",
    "record state",
    "records reconstruction",
    "production authorization",
    "golden path",
    "governance",
    "implementation matrix",
    "institutional registry",
    "website",
    "client intake",
}

DECISION_MARKERS = (
    "approved",
    "we decided",
    "decision:",
    "adopt",
    "final",
    "authoritative",
    "controlling",
    "lock this",
    "make this",
)
RULE_MARKERS = (
    "must",
    "shall",
    "never",
    "always",
    "rule:",
    "requirement",
    "acceptance criterion",
)
OPEN_ISSUE_MARKERS = (
    "missing",
    "open issue",
    "unresolved",
    "blocker",
    "not built",
    "not implemented",
    "needs migration",
    "needs review",
    "remains false",
    "blocked until",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iso_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        return text or None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content") or {}
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        values: list[str] = []
        for part in parts:
            if isinstance(part, str):
                values.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    values.append(text)
        return "\n".join(value.strip() for value in values if value.strip()).strip()
    text = content.get("text")
    return text.strip() if isinstance(text, str) else ""


def _term_score(text: str, terms: Iterable[str]) -> int:
    lowered = text.casefold()
    return sum(1 for term in terms if term in lowered)


def classify_text(text: str) -> tuple[ContinuityDomain, float, str, bool]:
    clean = " ".join(text.split())
    if len(clean) < 12:
        return ContinuityDomain.ARCHIVE_ONLY, 0.99, "normal", False

    legal = _term_score(clean, LEGAL_TERMS)
    private = _term_score(clean, OWNER_PRIVATE_TERMS)
    institutional = _term_score(clean, INSTITUTIONAL_TERMS)

    if legal:
        confidence = min(0.99, 0.82 + 0.04 * legal)
        mixed = institutional > 0 or private > 0
        return ContinuityDomain.LEGAL_PRIVATE, confidence, "restricted", mixed or confidence < 0.9

    if private and institutional:
        if abs(private - institutional) <= 1:
            return ContinuityDomain.AMBIGUOUS, 0.55, "private", True
        if private > institutional:
            return ContinuityDomain.OWNER_PRIVATE, 0.76, "private", True
        return ContinuityDomain.INSTITUTIONAL, 0.76, "normal", True

    if private:
        return ContinuityDomain.OWNER_PRIVATE, min(0.97, 0.8 + 0.04 * private), "private", private == 1

    if institutional:
        return ContinuityDomain.INSTITUTIONAL, min(0.98, 0.82 + 0.04 * institutional), "normal", institutional == 1

    # Unknown history is preserved but not promoted. This intentionally favors
    # false negatives over leaking private material into the institutional domain.
    return ContinuityDomain.ARCHIVE_ONLY, 0.65, "private", False


def candidate_kind(text: str) -> CandidateKind:
    lowered = text.casefold()
    if any(marker in lowered for marker in DECISION_MARKERS):
        return CandidateKind.DECISION
    if any(marker in lowered for marker in RULE_MARKERS):
        return CandidateKind.RULE
    if any(marker in lowered for marker in OPEN_ISSUE_MARKERS):
        return CandidateKind.OPEN_ISSUE
    if len(text) >= 80:
        return CandidateKind.FACT
    return CandidateKind.WORKING_NOTE


def _parse_openai_conversations(payload: Any) -> tuple[list[ParsedMessage], int]:
    conversations = payload
    if isinstance(payload, dict):
        conversations = payload.get("conversations") or payload.get("items") or []
    if not isinstance(conversations, list):
        raise ValueError("Unsupported conversation export structure")

    parsed: list[ParsedMessage] = []
    conversation_count = 0
    seen_hashes: set[tuple[str, str]] = set()

    for index, conversation in enumerate(conversations):
        if not isinstance(conversation, dict):
            continue
        mapping = conversation.get("mapping")
        if not isinstance(mapping, dict):
            continue
        conversation_count += 1
        conversation_id = str(conversation.get("id") or conversation.get("conversation_id") or f"conversation-{index + 1}")
        title = str(conversation.get("title") or "Untitled conversation")

        nodes: list[tuple[float, str, dict[str, Any]]] = []
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            created_raw = message.get("create_time")
            try:
                sort_time = float(created_raw or 0)
            except (TypeError, ValueError):
                sort_time = 0.0
            nodes.append((sort_time, str(node_id), message))
        nodes.sort(key=lambda item: (item[0], item[1]))

        for _sort_time, node_id, message in nodes:
            text = _message_text(message)
            if not text:
                continue
            author = message.get("author") or {}
            role = str(author.get("role") or "unknown") if isinstance(author, dict) else "unknown"
            message_id = str(message.get("id") or node_id)
            content_hash = _sha256(text.encode("utf-8"))
            dedupe_key = (conversation_id, message_id)
            if dedupe_key in seen_hashes:
                continue
            seen_hashes.add(dedupe_key)
            domain, confidence, sensitivity, needs_review = classify_text(text)
            parsed.append(
                ParsedMessage(
                    conversation_id=conversation_id,
                    conversation_title=title,
                    message_id=message_id,
                    role=role,
                    created_at=_iso_timestamp(message.get("create_time")),
                    text=text,
                    content_hash=content_hash,
                    domain=domain,
                    confidence=confidence,
                    candidate_kind=candidate_kind(text),
                    sensitivity=sensitivity,
                    needs_review=needs_review,
                )
            )

    return parsed, conversation_count


def _safe_zip_json(data: bytes) -> tuple[Any, tuple[str, ...]]:
    warnings: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("Archive contains too many files")
        total = sum(max(0, item.file_size) for item in infos)
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("Archive expands beyond the allowed size")

        candidates: list[zipfile.ZipInfo] = []
        for item in infos:
            normalized = posixpath.normpath(item.filename.replace("\\", "/"))
            if normalized.startswith("../") or normalized.startswith("/"):
                raise ValueError("Archive contains an unsafe path")
            if item.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Archive member is too large: {item.filename}")
            if posixpath.basename(normalized).casefold() in SUPPORTED_EXPORT_NAMES:
                candidates.append(item)

        if not candidates:
            json_members = [item for item in infos if item.filename.casefold().endswith(".json")]
            if len(json_members) == 1:
                candidates = json_members
                warnings.append("Used the only JSON file in the archive because conversations.json was not found.")
            else:
                raise ValueError("No supported conversation JSON file found in archive")

        selected = sorted(candidates, key=lambda item: len(item.filename))[0]
        with archive.open(selected, "r") as handle:
            return json.load(handle), tuple(warnings)


def parse_ai_export(filename: str, data: bytes) -> ImportBundle:
    if not data:
        raise ValueError("The uploaded export is empty")
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("The uploaded export is too large for v0.1")

    suffix = filename.casefold()
    warnings: tuple[str, ...] = ()
    if suffix.endswith(".zip"):
        payload, warnings = _safe_zip_json(data)
    elif suffix.endswith(".json"):
        payload = json.loads(data.decode("utf-8"))
    else:
        raise ValueError("Upload a ChatGPT/AI export as .zip or .json")

    messages, conversation_count = _parse_openai_conversations(payload)
    if not messages:
        raise ValueError("No supported conversation messages were found in this export")

    return ImportBundle(
        source_system="chatgpt",
        source_filename=filename,
        archive_sha256=_sha256(data),
        conversations_discovered=conversation_count,
        messages_discovered=len(messages),
        messages=tuple(messages),
        warnings=warnings,
    )
