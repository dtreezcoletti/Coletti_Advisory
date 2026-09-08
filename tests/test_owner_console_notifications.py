from coletti_advisory.owner_console_notifications import build_owner_notifications


def test_notifications_project_authoritative_owner_signals_without_new_state():
    snapshot = {
        "approvals": [
            {
                "title": "Release authorization",
                "protected_gate": True,
            }
        ],
        "tasks": [
            {"title": "Overdue task", "project": "ColettiOS", "overdue": True, "due_today": False},
            {"title": "Today task", "project": "Dispatcher", "overdue": False, "due_today": True},
        ],
        "reconciliations": [
            {"status": "ATTENTION_REQUIRED", "mismatch_count": 2},
            {"status": "PASS", "mismatch_count": 0},
        ],
        "calendar_commands": [
            {"title": "Move priority block", "approval_state": "REQUIRED"},
            {"title": "Completed calendar change", "approval_state": "APPROVED"},
        ],
    }

    notifications = build_owner_notifications(snapshot)

    assert [item["kind"] for item in notifications] == [
        "Decision",
        "Overdue",
        "Due today",
        "Reconciliation",
        "Calendar",
    ]
    assert notifications[0]["target"] == "Approvals"
    assert all(item["target"] in {"Approvals", "Dispatcher"} for item in notifications)


def test_notification_center_is_quiet_when_authoritative_state_is_clear():
    snapshot = {
        "approvals": [],
        "tasks": [{"title": "Later", "overdue": False, "due_today": False}],
        "reconciliations": [{"status": "PASS", "mismatch_count": 0}],
        "calendar_commands": [{"title": "Done", "approval_state": "APPROVED"}],
    }

    assert build_owner_notifications(snapshot) == []
