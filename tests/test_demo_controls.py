from types import SimpleNamespace

import pytest

from coletti_advisory.core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from coletti_advisory.demo_controls import _clear_demo_data, _reset_demo_data, demo_data_available
from coletti_advisory.synthetic import SYNTHETIC_ENGAGEMENT
from coletti_advisory.workspaces import LIVE_WORKSPACE_ID


class _PublicationStore:
    def __init__(self):
        self.saved = None

    def save(self, *, organization_id, engagement_id, records):
        self.saved = {
            "organization_id": organization_id,
            "engagement_id": engagement_id,
            "records": records,
        }


def test_demo_data_control_is_available_only_for_synthetic_demo_path():
    core = SyntheticCoreAdapter()
    assert demo_data_available(
        app_mode="demo",
        engagement_id=SYNTHETIC_ENGAGEMENT["engagement_id"],
        core=core,
    )


def test_demo_data_control_is_not_available_for_live_workspace():
    assert not demo_data_available(
        app_mode="production",
        engagement_id=LIVE_WORKSPACE_ID,
        core=SyntheticCoreAdapter(),
    )


def test_demo_data_control_is_not_available_for_http_core():
    core = HttpColettiOSAdapter("https://core.example.invalid", "synthetic-test-token")
    assert not demo_data_available(
        app_mode="demo",
        engagement_id=SYNTHETIC_ENGAGEMENT["engagement_id"],
        core=core,
    )


def test_demo_reset_restores_manifest_without_forcing_partial_rerun():
    core = SyntheticCoreAdapter()
    auth = {
        "user_id": "usr-demo",
        "organization_id": "org-demo",
        "engagement_id": SYNTHETIC_ENGAGEMENT["engagement_id"],
        "role": "owner",
        "session_id": "sess-demo",
        "authenticated_at": "now",
    }
    core.register_source(
        {"source_id": "SRC-TEMP", "content_hash": "temp", "metadata": {}},
        auth,
    )
    assert "SRC-TEMP" in core.manifest(SYNTHETIC_ENGAGEMENT["engagement_id"])["sources"]

    fake_shell = SimpleNamespace(st=SimpleNamespace(session_state={}))
    principal = SimpleNamespace(organization_id="org-demo")

    _reset_demo_data(
        fake_shell,
        principal=principal,
        engagement_id=SYNTHETIC_ENGAGEMENT["engagement_id"],
        core=core,
    )

    assert "SRC-TEMP" not in core.manifest(SYNTHETIC_ENGAGEMENT["engagement_id"])["sources"]
    assert fake_shell.st.session_state["_demo_data_loaded_notice"] is True
    assert fake_shell.st.session_state["_document_processing_queue"] == {}


def test_clear_demo_data_removes_case_processing_and_publication_state():
    core = SyntheticCoreAdapter()
    publication_store = _PublicationStore()
    fake_shell = SimpleNamespace(
        st=SimpleNamespace(
            session_state={
                "_coletti_publication_store": publication_store,
                "_document_processing_queue": {"SRC-PENDING": {"candidates": [{"text": "pending"}]}},
                "_last_intake_result": {"source_id": "SRC-PENDING"},
                "_demo_data_loaded_notice": True,
            }
        )
    )
    principal = SimpleNamespace(organization_id="org-synthetic")

    _clear_demo_data(
        fake_shell,
        principal=principal,
        engagement_id=SYNTHETIC_ENGAGEMENT["engagement_id"],
        core=core,
    )

    manifest = core.manifest(SYNTHETIC_ENGAGEMENT["engagement_id"])
    assert manifest["sources"] == {}
    assert manifest["propositions"] == {}
    assert manifest["contradictions"] == {}
    assert fake_shell.st.session_state["_document_processing_queue"] == {}
    assert "_last_intake_result" not in fake_shell.st.session_state
    assert "_demo_data_loaded_notice" not in fake_shell.st.session_state
    assert fake_shell.st.session_state["_demo_data_cleared_notice"] is True
    assert publication_store.saved == {
        "organization_id": "org-synthetic",
        "engagement_id": SYNTHETIC_ENGAGEMENT["engagement_id"],
        "records": {},
    }


def test_clear_demo_data_fails_closed_for_non_synthetic_core():
    fake_shell = SimpleNamespace(st=SimpleNamespace(session_state={}))
    principal = SimpleNamespace(organization_id="org-synthetic")
    http_core = HttpColettiOSAdapter("https://core.example.invalid", "synthetic-test-token")

    with pytest.raises(PermissionError):
        _clear_demo_data(
            fake_shell,
            principal=principal,
            engagement_id=SYNTHETIC_ENGAGEMENT["engagement_id"],
            core=http_core,
        )
