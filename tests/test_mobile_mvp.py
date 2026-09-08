import pytest

from colettios_advisory.mobile_mvp import (
    MobileCalendarItem,
    mobile_navigation,
    mobile_session,
    prepare_dari_command,
    prepare_mobile_upload,
    prepare_review_action,
    protected_notification,
    require_mobile_staff,
    sanitized_calendar_items,
    summarize_manifest,
)
from colettios_advisory.models import Principal, Role, utc_now_iso


def principal(role: Role, *, authenticated: bool = True, engagements=("eng-1",)) -> Principal:
    return Principal(
        user_id=f"u-{role.value}",
        email=f"{role.value}@example.test",
        display_name=role.value.title(),
        organization_id="org-1",
        role=role,
        engagement_ids=tuple(engagements),
        session_id="session-1",
        authenticated_at=utc_now_iso(),
        authenticated=authenticated,
    )


def test_mobile_requires_authenticated_staff():
    with pytest.raises(PermissionError):
        require_mobile_staff(principal(Role.OWNER, authenticated=False))
    with pytest.raises(PermissionError):
        require_mobile_staff(principal(Role.CLIENT))
    require_mobile_staff(principal(Role.ANALYST))


def test_mobile_navigation_is_role_specific():
    assert mobile_navigation(principal(Role.OWNER)) == ("Today", "Cases", "DARI", "Needs Me", "Company")
    assert mobile_navigation(principal(Role.ANALYST)) == ("Today", "Cases", "DARI", "Reviews", "Alerts")


def test_mobile_session_cannot_cross_engagement_scope():
    p = principal(Role.ANALYST, engagements=("eng-1",))
    assert mobile_session(p, "eng-1").engagement_id == "eng-1"
    with pytest.raises(PermissionError):
        mobile_session(p, "eng-2")


def test_dari_mobile_command_preserves_actor_scope_and_human_gate():
    p = principal(Role.REVIEWER)
    command = prepare_dari_command(p, "eng-1", "Prepare this for review", case_id="eng-1")
    assert command.actor_id == p.user_id
    assert command.session_id == p.session_id
    assert command.human_gate_required is False

    protected = prepare_dari_command(p, "eng-1", "Publish the report", protected_action=True)
    assert protected.human_gate_required is True


def test_secure_mobile_upload_hashes_content_and_requires_upload_permission():
    p = principal(Role.ANALYST)
    envelope = prepare_mobile_upload(
        p,
        "eng-1",
        filename="source.pdf",
        data=b"synthetic-source",
        classification="SOURCE_DOCUMENT",
        capture_method="FILE_PICKER",
    )
    assert envelope.byte_length == len(b"synthetic-source")
    assert len(envelope.content_sha256) == 64
    assert envelope.capture_method == "FILE_PICKER"

    with pytest.raises(PermissionError):
        prepare_mobile_upload(
            principal(Role.READ_ONLY),
            "eng-1",
            filename="source.pdf",
            data=b"x",
            classification="SOURCE_DOCUMENT",
            capture_method="FILE_PICKER",
        )


def test_mobile_upload_rejects_empty_and_unknown_capture_method():
    p = principal(Role.ANALYST)
    with pytest.raises(ValueError):
        prepare_mobile_upload(p, "eng-1", filename="x", data=b"", classification="SOURCE", capture_method="FILE_PICKER")
    with pytest.raises(ValueError):
        prepare_mobile_upload(p, "eng-1", filename="x", data=b"x", classification="SOURCE", capture_method="SCREENSHOT")


def test_review_actions_require_review_permission_and_preserve_protected_gate():
    p = principal(Role.REVIEWER)
    action = prepare_review_action(p, "eng-1", subject_id="F-1", action="approve review")
    assert action.state == "STAGED"
    protected = prepare_review_action(p, "eng-1", subject_id="RPT-1", action="publish", protected=True)
    assert protected.state == "AWAITING_HUMAN_CONFIRMATION"

    with pytest.raises(PermissionError):
        prepare_review_action(principal(Role.CLIENT), "eng-1", subject_id="F-1", action="approve")


def test_lock_screen_notification_never_contains_sensitive_detail():
    note = protected_notification(
        category="publication",
        authenticated_title="Smith report ready",
        authenticated_body="REC-260906-01 passed review",
    )
    assert note.lock_screen_title == "ColettiOS"
    assert "Smith" not in note.lock_screen_body
    assert "REC-260906-01" not in note.lock_screen_body
    assert note.requires_authentication is True


def test_calendar_redaction_requires_authenticated_view():
    item = MobileCalendarItem("cal-1", "Client Smith review", "2026-09-08T10:00:00-05:00", case_id="REC-1", protected_detail=True)
    locked = sanitized_calendar_items([item], authenticated=False)[0]
    unlocked = sanitized_calendar_items([item], authenticated=True)[0]
    assert locked["title"] == "Protected ColettiOS item"
    assert locked["case_id"] is None
    assert unlocked["title"] == "Client Smith review"


def test_manifest_summary_is_count_only():
    summary = summarize_manifest(
        {
            "sources": {"S1": {}, "S2": {}},
            "propositions": {"P1": {}},
            "contradictions": {"C1": {}},
            "reconciliations": {},
        }
    )
    assert summary == {"sources": 2, "propositions": 1, "contradictions": 1, "reconciliations": 0}
