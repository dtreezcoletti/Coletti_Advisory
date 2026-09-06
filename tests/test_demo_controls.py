from types import SimpleNamespace

from coletti_advisory.core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from coletti_advisory.demo_controls import _reset_demo_data, demo_data_available
from coletti_advisory.synthetic import SYNTHETIC_ENGAGEMENT
from coletti_advisory.workspaces import LIVE_WORKSPACE_ID


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

    # Deliberately provide only session_state. If the reset path tries to call
    # st.rerun(), this fake Streamlit object has no such attribute and the test fails.
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
