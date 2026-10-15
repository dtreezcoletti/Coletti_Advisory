"""COW-004 Owner Portal execution lease controls security regression."""
from __future__ import annotations

import pytest

from types import SimpleNamespace

from coletti_advisory.owner_execution_lease_controls import _owner_principal, OwnerLeaseControlUnavailable, _rpc


def test_only_authenticated_owner_can_render_controls():
    assert _owner_principal(SimpleNamespace(authenticated=True, role="owner"))
    assert not _owner_principal(SimpleNamespace(authenticated=False, role="owner"))
    assert not _owner_principal(SimpleNamespace(authenticated=True, role="admin"))
    assert not _owner_principal(SimpleNamespace(authenticated=True, role="client"))

def test_missing_session_prevents_rpc(monkeypatch):
    from coletti_advisory import owner_execution_lease_controls as worker
    monkeypatch.setattr(worker.supabase_auth, "current_access_token", lambda: None)
    monkeypatch.setattr(worker.supabase_auth, "_secret", lambda key, default="": default)
    with pytest.raises(OwnerLeaseControlUnavailable):
        worker._rpc("cow_owner_execution_start_v1", {})

def test_rejected_request_is_not_reported_as_success(monkeypatch):
    from coletti_advisory import owner_execution_lease_controls as worker
    monkeypatch.setattr(worker.supabase_auth, "current_access_token", lambda: "dummy_bearer_token")
    monkeypatch.setattr(worker.supabase_auth, "_secret",
        lambda name, default="": ("https://example.supabase.co" if name=="SUPABASE_URL" else "anon_pub_key"))
    class Denied:
        status_code=403
        ok=False
    monkeypatch.setattr(worker.requests, "post", lambda *a, **k: Denied())
    with pytest.raises(OwnerLeaseControlUnavailable, match="denied"):
        worker._rpc("cow_owner_execution_start_v1", {})

def test_no_unconfirmed_automatic_start():
    from pathlib import Path
    source=Path(__file__).resolve().parents[1].joinpath("coletti_advisory", "owner_execution_lease_controls.py").read_text()
    assert 'confirm != "AUTHORIZE COW EXECUTION"' in source
    assert 'stop != "REVOKE COW EXECUTION"' in source
    assert 'p_confirmation": confirm' in source
