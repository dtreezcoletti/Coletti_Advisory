from datetime import date

from coletti_advisory.workspace_v2 import _ack_key, classify_dari_command
from coletti_advisory.models import Principal, Role


def _principal() -> Principal:
    return Principal(
        user_id="usr-owner",
        email="owner@example.com",
        display_name="Demetries Coletti",
        organization_id="org-test",
        role=Role.OWNER,
        engagement_ids=("eng-test",),
        session_id="sess-test",
        authenticated_at="2026-09-08T14:00:00+00:00",
        authenticated=True,
    )


def test_dari_primary_command_classification():
    assert classify_dari_command("What needs my decision?") == "decisions"
    assert classify_dari_command("What should I work on next?") == "next"
    assert classify_dari_command("Find C26-92") == "find"
    assert classify_dari_command("Show production blockers") == "blockers"
    assert classify_dari_command("Continue where I left off") == "continue"


def test_start_my_day_ack_is_user_and_date_scoped():
    principal = _principal()
    key = _ack_key(principal, date(2026, 9, 8))
    assert "usr-owner" in key
    assert key.endswith("2026-09-08")
