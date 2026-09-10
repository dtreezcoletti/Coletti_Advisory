from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from .analysis import build_summary
from .models import Permission, ROLE_PERMISSIONS, Role
from .publication import published_reports
from .workspaces import workspace_label


_INTERNAL_ROLES = {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER}


def profile_role_label(principal) -> str:
    labels = {
        Role.OWNER: "Owner",
        Role.ADMIN: "Administrator",
        Role.ANALYST: "Employee · Analyst",
        Role.REVIEWER: "Employee · Reviewer",
        Role.CLIENT: "Client",
        Role.READ_ONLY: "Client · Read Only",
    }
    return labels.get(principal.role, str(principal.role.value).replace("_", " ").title())


def profile_permissions(principal) -> list[str]:
    labels = {
        Permission.VIEW: "View assigned workspace",
        Permission.UPLOAD: "Upload records",
        Permission.ANALYZE: "Analyze records",
        Permission.REVIEW: "Human review",
        Permission.MANAGE_USERS: "Manage users",
        Permission.MANAGE_ENGAGEMENTS: "Manage cases",
    }
    return [labels[permission] for permission in Permission if permission in ROLE_PERMISSIONS[principal.role]]


def profile_work_stats(principal, manifest: Mapping[str, Any] | None = None, records: Mapping[str, Any] | None = None) -> dict[str, str]:
    manifest = dict(manifest or {})
    summary = build_summary(manifest)
    assigned_cases = len(tuple(principal.engagement_ids))

    if principal.role in {Role.CLIENT, Role.READ_ONLY}:
        return {
            "Assigned cases": str(assigned_cases),
            "Documents submitted": str(summary.get("sources", 0)),
            "Reports available": str(len(published_reports(records or {}))),
        }

    return {
        "Assigned cases": str(assigned_cases),
        "Current-case sources": str(summary.get("sources", 0)),
        "Current-case record statements": str(summary.get("propositions", 0)),
        "Current-case inconsistencies": str(summary.get("inconsistencies", 0)),
        "Current-case open issues": str(summary.get("open_issues", 0)),
    }


def _render_stats(stats: Mapping[str, str]) -> None:
    items = list(stats.items())
    for start in range(0, len(items), 2):
        cols = st.columns(2)
        for col, (label, value) in zip(cols, items[start : start + 2]):
            col.metric(label, value)


def render_profile_menu(
    principal,
    *,
    engagement_id: str,
    manifest: Mapping[str, Any] | None = None,
    records: Mapping[str, Any] | None = None,
    key_prefix: str = "profile-menu",
) -> None:
    """Render the signed-in person's permission-aware personal profile menu.

    This surface intentionally shows only data belonging to the current principal
    and their assigned workspaces. Payroll and leave remain explicit backend gaps
    until an authoritative HR/payroll service is connected; the UI never invents
    compensation or leave records.
    """
    role_label = profile_role_label(principal)
    trigger_name = principal.display_name or "My Profile"

    with st.popover(f"{trigger_name} · {role_label}  ▾", use_container_width=True):
        st.markdown(f"### {trigger_name}")
        st.caption(f"{role_label} · {workspace_label(engagement_id)}")

        if principal.role in {Role.CLIENT, Role.READ_ONLY}:
            account_tab, access_tab = st.tabs(("My Account", "Access"))
            with account_tab:
                _render_stats(profile_work_stats(principal, manifest, records))
                st.caption("Client-safe account view. Internal analysis, reviewer notes, staff workload, payroll, and administrative controls are not exposed here.")
            with access_tab:
                st.markdown("**Your permissions**")
                for permission in profile_permissions(principal):
                    st.write(f"✓ {permission}")
            return

        work_tab, time_off_tab, payroll_tab, access_tab = st.tabs(("My Work", "Time Off", "Payroll", "Access"))

        with work_tab:
            _render_stats(profile_work_stats(principal, manifest, records))
            st.caption("Personal workload summary from your currently assigned ColettiOS workspace access. Team-wide statistics belong in management views, not another employee's profile.")

        with time_off_tab:
            st.markdown("**My time off**")
            st.info("Authoritative time-off requests are not connected to an HR/leave service yet.")
            st.button(
                "Request time off",
                key=f"{key_prefix}:request-time-off",
                use_container_width=True,
                disabled=True,
                help="This becomes available when the approved HR/time-off backend is connected.",
            )
            st.caption("No synthetic request is fabricated here. Once connected, this area can show request status, available leave, upcoming approved time off, and request history according to position and policy.")

        with payroll_tab:
            st.markdown("**My payroll**")
            st.info("Authoritative payroll data is not connected yet.")
            st.caption("When a payroll source is connected, this area can show the current employee's pay statements, YTD totals, deductions/withholding summary, and payroll documents. Compensation data remains private to the individual and specifically authorized payroll/administrative roles.")

        with access_tab:
            st.markdown("**Position & access**")
            st.write(f"**Position:** {role_label}")
            st.write(f"**Assigned cases:** {len(tuple(principal.engagement_ids))}")
            st.markdown("**Your permissions**")
            for permission in profile_permissions(principal):
                st.write(f"✓ {permission}")
            if principal.role == Role.OWNER:
                st.caption("Owner profile reflects full application permissions. Protected actions still remain subject to their required human/security gates.")
            elif principal.role == Role.ADMIN:
                st.caption("Administrator access includes user/case administration but does not make another employee's private payroll or leave information part of this personal profile.")
