from coletti_advisory.models import Principal, Role
from coletti_advisory.multicase_demo import (
    PortfolioSyntheticCoreAdapter,
    portfolio_demo_principal,
    portfolio_principal_for_experience,
)
from coletti_advisory.synthetic_portfolio import (
    DEMO_ALL_ENGAGEMENT_IDS,
    DEMO_CLIENT_ENGAGEMENT_ID,
    DEMO_EMPLOYEE_ENGAGEMENT_IDS,
    portfolio_case,
)
from coletti_advisory.workspaces import workspace_environment, workspace_label


def test_portfolio_contains_distinct_synthetic_cases():
    assert len(DEMO_ALL_ENGAGEMENT_IDS) == 6
    assert len(set(DEMO_ALL_ENGAGEMENT_IDS)) == 6
    assert all(portfolio_case(eid) for eid in DEMO_ALL_ENGAGEMENT_IDS)
    assert all(workspace_environment(eid) == "DEMO" for eid in DEMO_ALL_ENGAGEMENT_IDS)
    assert workspace_label(DEMO_CLIENT_ENGAGEMENT_ID).startswith("JRC-1145-01")


def test_employee_client_and_owner_receive_different_demo_case_scopes():
    base = portfolio_demo_principal()

    employee = portfolio_principal_for_experience(base, "Employee Workspace")
    assert employee.role == Role.ANALYST
    assert employee.engagement_ids == DEMO_EMPLOYEE_ENGAGEMENT_IDS
    assert len(employee.engagement_ids) == 4

    client = portfolio_principal_for_experience(base, "Client Portal")
    assert client.role == Role.CLIENT
    assert client.engagement_ids == (DEMO_CLIENT_ENGAGEMENT_ID,)

    owner = portfolio_principal_for_experience(base, "Owner Console")
    assert owner.role == Role.OWNER
    assert owner.engagement_ids == DEMO_ALL_ENGAGEMENT_IDS

    admin = portfolio_principal_for_experience(base, "Admin Workspace")
    assert admin.role == Role.ADMIN
    assert admin.engagement_ids == DEMO_ALL_ENGAGEMENT_IDS


def test_synthetic_case_manifests_are_isolated_by_engagement():
    core = PortfolioSyntheticCoreAdapter()
    first, second = DEMO_ALL_ENGAGEMENT_IDS[:2]
    before_second = core.manifest(second)

    principal = portfolio_principal_for_experience(portfolio_demo_principal(), "Owner Console")
    core.register_source(
        {
            "source_id": "SRC-ISOLATION-001",
            "content_hash": "isolation-hash",
            "metadata": {"filename": "isolation.pdf", "synthetic": True},
        },
        principal.auth_context(first),
    )

    assert "SRC-ISOLATION-001" in core.manifest(first)["sources"]
    assert "SRC-ISOLATION-001" not in core.manifest(second)["sources"]
    assert core.manifest(second)["sources"] == before_second["sources"]


def test_case_metadata_supports_assignment_and_workload_preview():
    for engagement_id in DEMO_EMPLOYEE_ENGAGEMENT_IDS:
        item = portfolio_case(engagement_id)
        assert item is not None
        assert item["case_id"].startswith("JRC-1145-")
        assert item["assignment"]
        assert item["priority"] in {"High", "Normal", "Low"}
        assert item["stage"]
        assert item["due_date"]
        assert item["next_action"]
        assert item["workload_points"] > 0
