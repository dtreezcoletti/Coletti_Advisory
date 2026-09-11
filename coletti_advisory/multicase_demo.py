from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from .analysis import build_summary
from .core_adapter import SyntheticCoreAdapter
from .models import Principal, Role, utc_now_iso
from .synthetic_portfolio import (
    DEMO_ALL_ENGAGEMENT_IDS,
    DEMO_CLIENT_ENGAGEMENT_ID,
    DEMO_EMPLOYEE_ENGAGEMENT_IDS,
    DEMO_MANIFESTS,
    portfolio_case,
    portfolio_label,
)


class PortfolioSyntheticCoreAdapter(SyntheticCoreAdapter):
    """Demo-only synthetic adapter with isolated state for several fake cases.

    Production Core behavior is unchanged. Every case gets its own manifest and
    mutations are routed by auth_context.engagement_id so selecting a second case
    cannot silently read or mutate the first case's synthetic state.
    """

    def __init__(self) -> None:
        self.reset_demo_data()

    def reset_demo_data(self) -> None:
        self._manifests = copy.deepcopy(DEMO_MANIFESTS)
        self._manifest = self._manifests[DEMO_CLIENT_ENGAGEMENT_ID]

    def clear_demo_data(self) -> None:
        from .synthetic_portfolio import DEMO_CASES, empty_manifest_for_case

        self._manifests = {
            item["engagement_id"]: empty_manifest_for_case(item)
            for item in DEMO_CASES
        }
        self._manifest = self._manifests[DEMO_CLIENT_ENGAGEMENT_ID]

    def _activate(self, engagement_id: str) -> None:
        if engagement_id not in self._manifests:
            raise KeyError(f"Unknown synthetic engagement: {engagement_id}")
        self._manifest = self._manifests[engagement_id]

    def register_source(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        self._activate(auth_context["engagement_id"])
        return super().register_source(payload, auth_context)

    def add_proposition(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        self._activate(auth_context["engagement_id"])
        return super().add_proposition(payload, auth_context)

    def record_contradiction(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        self._activate(auth_context["engagement_id"])
        return super().record_contradiction(payload, auth_context)

    def record_reconciliation(self, payload: dict[str, Any], auth_context: dict[str, str]) -> dict[str, Any]:
        self._activate(auth_context["engagement_id"])
        return super().record_reconciliation(payload, auth_context)

    def manifest(self, engagement_id: str) -> dict[str, Any]:
        if engagement_id not in self._manifests:
            raise KeyError(f"Unknown synthetic engagement: {engagement_id}")
        return copy.deepcopy(self._manifests[engagement_id])


def portfolio_demo_principal() -> Principal:
    return Principal(
        user_id="demo-session",
        email="demo@synthetic.invalid",
        display_name="Synthetic Demo",
        organization_id="org-synthetic",
        role=Role.OWNER,
        engagement_ids=DEMO_ALL_ENGAGEMENT_IDS,
        session_id="demo-session",
        authenticated_at=utc_now_iso(),
        authenticated=False,
    )


def portfolio_principal_for_experience(principal: Principal, selection: str) -> Principal:
    if principal.authenticated or principal.organization_id != "org-synthetic":
        raise PermissionError("Demo experience switching is restricted to the anonymous synthetic tenant")

    role_map = {
        "Owner Console": Role.OWNER,
        "Admin Workspace": Role.ADMIN,
        "Employee Workspace": Role.ANALYST,
        "Client Portal": Role.CLIENT,
    }
    if selection not in role_map:
        raise ValueError("Unknown demo experience")

    role = role_map[selection]
    persona_name = {
        Role.OWNER: "Synthetic Owner",
        Role.ADMIN: "Synthetic Administrator",
        Role.ANALYST: "Synthetic Employee",
        Role.CLIENT: "Synthetic Client",
    }[role]
    if role == Role.CLIENT:
        engagement_ids = (DEMO_CLIENT_ENGAGEMENT_ID,)
    elif role == Role.ANALYST:
        engagement_ids = DEMO_EMPLOYEE_ENGAGEMENT_IDS
    else:
        engagement_ids = DEMO_ALL_ENGAGEMENT_IDS

    return replace(
        principal,
        email=f"demo+{role.value}@synthetic.invalid",
        display_name=persona_name,
        role=role,
        engagement_ids=engagement_ids,
        authenticated=False,
    )


def _employee_portfolio_rows(core, principal: Principal, selected_engagement: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for engagement_id in principal.engagement_ids:
        manifest = core.manifest(engagement_id)
        summary = build_summary(manifest)
        meta = dict(manifest.get("case_meta") or portfolio_case(engagement_id) or {})
        rows.append(
            {
                "Case": meta.get("case_id") or engagement_id,
                "Client": meta.get("client") or "Synthetic Client",
                "Assignment": meta.get("assignment") or "Assigned",
                "Stage": meta.get("stage") or "Unknown",
                "Priority": meta.get("priority") or "Normal",
                "Due": meta.get("due_date") or "—",
                "Sources": summary.get("sources", 0),
                "Conflicts": summary.get("inconsistencies", 0),
                "Next Action": meta.get("next_action") or "Review case",
                "Selected": "●" if engagement_id == selected_engagement else "",
            }
        )
    return rows


def install_multicase_demo(experience_shell, demo_controls_module, demo_selector_fix_module) -> None:
    """Install a synthetic-only portfolio without changing live authorization."""
    if getattr(experience_shell, "_multicase_demo_installed", False):
        return

    # Runtime construction: demo uses the portfolio adapter/principal; production
    # paths still resolve to the configured HTTP Core and authenticated principal.
    experience_shell.app.SyntheticCoreAdapter = PortfolioSyntheticCoreAdapter
    experience_shell.app.demo_principal = portfolio_demo_principal

    # The existing demo experience switcher keeps one visible role selector. Give
    # each persona an intentionally different case-access scope.
    demo_controls_module.principal_for_demo_experience = portfolio_principal_for_experience
    demo_selector_fix_module.principal_for_demo_experience = portfolio_principal_for_experience

    experience_shell._multicase_demo_installed = True


def patch_multicase_case_selector(experience_shell) -> None:
    """Add an assigned-case selector beneath the existing demo persona selector."""
    if getattr(experience_shell, "_multicase_case_selector_patched", False):
        return

    original_select = experience_shell._select_engagement

    def select_with_assigned_cases(principal: Principal) -> str:
        selected = original_select(principal)
        if (
            principal.authenticated
            or principal.organization_id != "org-synthetic"
            or len(principal.engagement_ids) <= 1
        ):
            return selected

        options = list(principal.engagement_ids)
        key = f"_coletti_employee_case:{principal.user_id}:{principal.role.value}"
        current = experience_shell.st.session_state.get(key)
        if current not in options:
            current = selected if selected in options else options[0]
            experience_shell.st.session_state[key] = current

        chosen = experience_shell.st.sidebar.selectbox(
            "Assigned case",
            options,
            index=options.index(current),
            key=key,
            format_func=portfolio_label,
            help="Synthetic portfolio only. Choose one of the cases assigned to this demo persona.",
        )
        meta = portfolio_case(chosen) or {}
        experience_shell.st.sidebar.caption(
            f"{meta.get('assignment', 'Assigned')} · {meta.get('priority', 'Normal')} priority · due {meta.get('due_date', '—')}"
        )
        experience_shell.st.sidebar.divider()
        experience_shell.st.session_state["_coletti_selected_engagement"] = chosen
        return chosen

    experience_shell._select_engagement = select_with_assigned_cases
    experience_shell._multicase_case_selector_patched = True


def patch_employee_portfolio_dashboard(experience_shell) -> None:
    """Replace the one-case demo employee home with a portfolio-first view."""
    if getattr(experience_shell, "_employee_portfolio_dashboard_patched", False):
        return

    original_dashboard = experience_shell._employee_dashboard

    def employee_dashboard(principal, engagement_id: str, manifest: dict, records: dict, reports: dict) -> None:
        if (
            principal.authenticated
            or principal.organization_id != "org-synthetic"
            or principal.role not in {Role.ANALYST, Role.ADMIN, Role.REVIEWER}
            or len(principal.engagement_ids) <= 1
        ):
            return original_dashboard(principal, engagement_id, manifest, records, reports)

        core = experience_shell.st.session_state.get("_coletti_core")
        if not isinstance(core, PortfolioSyntheticCoreAdapter):
            return original_dashboard(principal, engagement_id, manifest, records, reports)

        rows = _employee_portfolio_rows(core, principal, engagement_id)
        selected_meta = dict(manifest.get("case_meta") or portfolio_case(engagement_id) or {})
        total_sources = sum(int(row["Sources"]) for row in rows)
        high_priority = sum(1 for row in rows if row["Priority"] == "High")
        review_cases = sum(1 for row in rows if row["Stage"] in {"Human Review", "Report Preparation"})
        workload = sum(int((portfolio_case(eid) or {}).get("workload_points", 0)) for eid in principal.engagement_ids)

        first_name = (principal.display_name or "Employee").split()[0]
        if first_name.lower() == "synthetic":
            first_name = "Employee"
        experience_shell._hero(
            kicker="ColettiOS Employee Workspace",
            title=f"Good morning, {first_name}.",
            subtitle=f"{len(rows)} assigned cases · one controlled workspace",
            body="Start with the case that has the highest consequence or nearest due date, then move through intake, records review, analysis, human review, and reporting without losing case context.",
        )
        experience_shell._stats(
            [
                ("▦", str(len(rows)), "Assigned Cases"),
                ("!", str(high_priority), "High Priority"),
                ("✓", str(review_cases), "Review / Report Cases"),
                ("▤", str(total_sources), "Sources Across Portfolio"),
            ]
        )

        experience_shell.st.markdown("### My Assigned Cases")
        experience_shell.st.caption(
            f"Workload score: {workload} · synthetic capacity signal only. Select a case in the sidebar to make it the active context across the workflow."
        )
        experience_shell.st.dataframe(rows, use_container_width=True, hide_index=True)

        experience_shell.st.markdown("### Active Case")
        left, middle, right = experience_shell.st.columns([1.15, .85, .9], gap="large")
        with left:
            experience_shell.st.markdown(
                f"**{selected_meta.get('case_id', engagement_id)} · {selected_meta.get('client', 'Synthetic Client')}**"
            )
            experience_shell.st.write(selected_meta.get("name", portfolio_label(engagement_id)))
            experience_shell.st.caption(selected_meta.get("service", "Records Reconstruction"))
        with middle:
            experience_shell.st.metric("Stage", selected_meta.get("stage", "Unknown"))
            experience_shell.st.caption(
                f"{selected_meta.get('priority', 'Normal')} priority · due {selected_meta.get('due_date', '—')}"
            )
        with right:
            summary = build_summary(manifest)
            experience_shell.st.metric("Open conflicts", summary.get("inconsistencies", 0))
            experience_shell.st.caption(selected_meta.get("assignment", "Assigned"))

        with experience_shell.st.container(border=True):
            experience_shell.st.markdown("**Next required action**")
            experience_shell.st.write(selected_meta.get("next_action", "Review the selected case."))
            experience_shell.st.caption(
                "Assignment metadata is demonstrative only; no live client or employee record is created by this sandbox."
            )

    experience_shell._employee_dashboard = employee_dashboard
    experience_shell._employee_portfolio_dashboard_patched = True
