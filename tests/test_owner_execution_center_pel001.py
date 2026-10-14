from __future__ import annotations

from types import SimpleNamespace

from coletti_advisory import owner_execution_center as center
from coletti_advisory.models import Role


def test_safe_rows_limits_display_columns():
    data = [
        {"title": "First task", "lifecycle_state": "SCOPED", "extra": "unused"},
        {"title": "Second task", "lifecycle_state": "BLOCKED", "extra": "unused"},
    ]
    result = center._safe_rows(data, keys=("title", "lifecycle_state"))
    assert result == [
        {"title": "First task", "lifecycle_state": "SCOPED"},
        {"title": "Second task", "lifecycle_state": "BLOCKED"},
    ]


def test_safe_rows_rejects_unknown_data_shapes():
    assert center._safe_rows(None, keys=("title",)) == []
    assert center._safe_rows({"title": "wrong shape"}, keys=("title",)) == []


def test_non_owner_cannot_read_execution_center(monkeypatch):
    messages = []
    monkeypatch.setattr(center.st, "error", lambda message: messages.append(message))
    center.render_execution_center(
        principal=SimpleNamespace(role=Role.ANALYST, authenticated=True),
        engagement_id="synthetic",
        core=None,
    )
    assert messages and "Owner" in messages[0]


def test_patch_preserves_original_other_pages(monkeypatch):
    runtime = SimpleNamespace(
        _owner_sidebar=lambda shell, principal, engagement_id: "My Workspace",
        _render_owner_page=lambda shell, page, **kwargs: "Original",
    )
    monkeypatch.setattr(center.st.sidebar, "divider", lambda: None)
    monkeypatch.setattr(center.st.sidebar, "caption", lambda label: None)
    monkeypatch.setattr(center.st.sidebar, "button", lambda *args, **kwargs: False)
    center.patch_execution_center(runtime)
    sidebar = runtime._owner_sidebar
    center.patch_execution_center(runtime)
    assert runtime._owner_sidebar is sidebar
    assert runtime._render_owner_page(None, "Cases") == "Original"
    principal = SimpleNamespace(role=Role.OWNER, user_id="owner-1")
    assert runtime._owner_sidebar(None, principal, "synthetic") == "My Workspace"
