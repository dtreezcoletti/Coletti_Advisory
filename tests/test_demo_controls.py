from coletti_advisory.core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from coletti_advisory.demo_controls import demo_data_available
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
