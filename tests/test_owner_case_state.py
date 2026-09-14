from __future__ import annotations

from coletti_advisory import owner_console_ui
from coletti_advisory.experience_shell import CLIENT_PAGES
from coletti_advisory.owner_console_live import OwnerControlPlaneClient
import coletti_advisory.owner_console_runtime  # noqa: F401 - applies owner navigation wiring


class FakePrincipal:
    authenticated = True

    def auth_context(self, engagement_id: str) -> dict[str, str]:
        return {
            "user_id": "owner-1",
            "organization_id": "org-1",
            "engagement_id": engagement_id,
            "role": "owner",
            "session_id": "session-1",
            "authenticated_at": "2026-09-13T21:00:00Z",
        }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_owner_control_plane_reads_case_state_through_private_service(monkeypatch):
    calls = []

    def fake_post(url, *, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        if url.endswith("/v1/owner/case-state/catalog"):
            return FakeResponse(
                {
                    "cases": [
                        {
                            "case_id": "REC-260913-01",
                            "track_type": "HISTORICAL_REFERENCE",
                            "governance_writeback": False,
                            "training_authority": False,
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "case": {"case_id": "REC-260913-01"},
                "counts": {"issues": 0},
                "output_types": [],
            }
        )

    monkeypatch.setattr("coletti_advisory.owner_console_live.requests.post", fake_post)
    core = type(
        "Core",
        (),
        {
            "base_url": "https://core.example.test",
            "headers": {"Authorization": "Bearer test-token"},
            "timeout": 20.0,
        },
    )()
    principal = FakePrincipal()
    client = OwnerControlPlaneClient(core)

    catalog = client.case_state_catalog(principal, "SYN-260901-01")
    state = client.case_state(principal, "SYN-260901-01", "REC-260913-01")

    assert catalog[0]["track_type"] == "HISTORICAL_REFERENCE"
    assert catalog[0]["governance_writeback"] is False
    assert state["case"]["case_id"] == "REC-260913-01"
    assert calls[0][0].endswith("/v1/owner/case-state/catalog")
    assert calls[1][0].endswith("/v1/owner/case-state")
    assert calls[1][1]["case_id"] == "REC-260913-01"
    assert "Authorization" in calls[1][2]


def test_case_state_navigation_is_owner_only():
    owner_labels = [label for label, _icon in owner_console_ui.OWNER_MAIN_NAV]

    assert "Case State" in owner_labels
    assert "Case State" not in CLIENT_PAGES
