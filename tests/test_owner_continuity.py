from __future__ import annotations

import io
import json
import zipfile

import pytest

from coletti_advisory.owner_continuity import (
    CandidateKind,
    ContinuityDomain,
    classify_text,
    parse_ai_export,
)


def _sample_export() -> list[dict]:
    return [
        {
            "id": "conv-1",
            "title": "Mixed owner conversation",
            "mapping": {
                "node-1": {
                    "message": {
                        "id": "m1",
                        "create_time": 1,
                        "author": {"role": "user"},
                        "content": {"parts": ["ColettiOS production authorization remains false until Golden Path testing is complete."]},
                    }
                },
                "node-2": {
                    "message": {
                        "id": "m2",
                        "create_time": 2,
                        "author": {"role": "user"},
                        "content": {"parts": ["My job search and recruiter follow-ups belong in my employment plan."]},
                    }
                },
                "node-3": {
                    "message": {
                        "id": "m3",
                        "create_time": 3,
                        "author": {"role": "user"},
                        "content": {"parts": ["The divorce settlement draft discusses alimony and the dissolution order."]},
                    }
                },
            },
        }
    ]


def test_parse_json_mixed_conversation_by_message() -> None:
    data = json.dumps(_sample_export()).encode("utf-8")
    bundle = parse_ai_export("conversations.json", data)
    assert bundle.conversations_discovered == 1
    assert bundle.messages_discovered == 3
    assert [item.domain for item in bundle.messages] == [
        ContinuityDomain.INSTITUTIONAL,
        ContinuityDomain.OWNER_PRIVATE,
        ContinuityDomain.LEGAL_PRIVATE,
    ]


def test_parse_chatgpt_zip_directly() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("export/conversations.json", json.dumps(_sample_export()))
    bundle = parse_ai_export("chatgpt-export.zip", buf.getvalue())
    assert bundle.messages_discovered == 3
    assert bundle.source_system == "chatgpt"
    assert len(bundle.archive_sha256) == 64


def test_archive_rejects_unsafe_path() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("../conversations.json", json.dumps(_sample_export()))
    with pytest.raises(ValueError, match="unsafe path"):
        parse_ai_export("bad.zip", buf.getvalue())


def test_unknown_text_is_archive_only_not_institutional() -> None:
    domain, confidence, sensitivity, needs_review = classify_text("We should revisit this sometime next week because I am not sure yet.")
    assert domain == ContinuityDomain.ARCHIVE_ONLY
    assert sensitivity == "private"
    assert confidence > 0
    assert needs_review is False


def test_mixed_private_and_institutional_text_requires_review() -> None:
    domain, _confidence, _sensitivity, needs_review = classify_text(
        "My job search schedule needs to change because the ColettiOS Golden Path work moved."
    )
    assert domain == ContinuityDomain.AMBIGUOUS
    assert needs_review is True


def test_candidate_kind_prefers_control_markers() -> None:
    bundle = parse_ai_export("conversations.json", json.dumps(_sample_export()).encode("utf-8"))
    assert bundle.messages[0].candidate_kind in {CandidateKind.DECISION, CandidateKind.RULE, CandidateKind.OPEN_ISSUE}


def test_staging_manifest_is_shadow_mode() -> None:
    bundle = parse_ai_export("conversations.json", json.dumps(_sample_export()).encode("utf-8"))
    manifest = bundle.staging_manifest()
    assert manifest["mode"] == "shadow"
    assert manifest["schema_version"] == "owner-continuity-v0.1"
    assert len(manifest["messages"]) == 3
