from __future__ import annotations

from collections.abc import Callable, Mapping
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


def profile_work_stats(
    principal,
    manifest: Mapping[str, Any] | None = None,
    records: Mapping[str, Any] | None = None,
) -> dict[str, str]:
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


def profile_stat_targets(principal) -> dict[str, str]:
    """Map every visible profile statistic to a real application destination."""
    if principal.role in {Role.CLIENT, Role.READ_ONLY}:
        return {
            "Assigned cases": "My Case",
            "Documents submitted": "My Case",
            "Reports available": "Reports",
        }
    if principal.role == Role.OWNER:
        return {
            "Assigned cases": "Case Queue",
            "Current-case sources": "Evidence",
            "Current-case record statements": "Analysis",
            "Current-case inconsistencies": "Analysis",
            "Current-case open issues": "Human Review",
        }
    return {
        "Assigned cases": "Engagements",
        "Current-case sources": "Evidence",
        "Current-case record statements": "Analysis",
        "Current-case inconsistencies": "Analysis",
        "Current-case open issues": "Review Center",
    }


def _open_or_explain(
    target: str,
    *,
    navigate: Callable[[str], None] | None,
    state_key: str,
) -> None:
    if navigate is not None:
        navigate(target)
    else:
        st.session_state[state_key] = target


def _render_action_stats(
    stats: Mapping[str, str],
    *,
    targets: Mapping[str, str],
    navigate: Callable[[str], None] | None,
    key_prefix: str,
) -> None:
    """Render every profile statistic as an actionable card-like button."""
    items = list(stats.items())
    for start in range(0, len(items), 2):
        cols = st.columns(2)
        for col, (label, value) in zip(cols, items[start : start + 2]):
            target = targets.get(label)
            with col:
                if st.button(
                    f"{value} · {label}",
                    key=f"{key_prefix}:stat:{start}:{label}",
                    use_container_width=True,
                    help=f"Open {target}" if target else "Open this profile detail",
                ):
                    _open_or_explain(
                        target or label,
                        navigate=navigate,
                        state_key=f"{key_prefix}:last-opened",
                    )
    opened = st.session_state.get(f"{key_prefix}:last-opened")
    if opened:
        st.caption(f"Connected destination: {opened}")


def _render_connection_action(
    *,
    label: str,
    target: str | None,
    navigate: Callable[[str], None] | None,
    key: str,
    unavailable_message: str,
) -> None:
    if st.button(label, key=key, use_container_width=True):
        if target and navigate is not None:
            navigate(target)
        else:
            st.session_state[f"{key}:status"] = True
    if st.session_state.get(f"{key}:status"):
        st.info(unavailable_message)


def _owner_control_buttons(
    *,
    navigate: Callable[[str], None] | None,
    key_prefix: str,
) -> None:
    destinations = (
        ("My Workspace", "My Workspace"),
        ("Cases", "Case Queue"),
        ("Approvals", "Approvals"),
        ("Dispatcher", "Dispatcher"),
        ("Team", "Team"),
        ("Financials", "Financials"),
        ("Firm Overview", "Firm Overview"),
        ("Settings & System", "Settings"),
    )
    for start in range(0, len(destinations), 2):
        cols = st.columns(2)
        for col, (label, target) in zip(cols, destinations[start : start + 2]):
            with col:
                if st.button(
                    label,
                    key=f"{key_prefix}:owner-control:{target}",
                    use_container_width=True,
                ):
                    _open_or_explain(
                        target,
                        navigate=navigate,
                        state_key=f"{key_prefix}:last-opened",
                    )


def render_profile_menu(
    principal,
    *,
    engagement_id: str,
    manifest: Mapping[str, Any] | None = None,
    records: Mapping[str, Any] | None = None,
    key_prefix: str = "profile-menu",
    navigate: Callable[[str], None] | None = None,
) -> None:
    """Render the signed-in person's permission-aware personal profile menu.

    Every visible profile card is actionable. The current principal can open
    their own work/access destinations; the owner additionally gets direct
    navigation to owner control surfaces. Payroll and leave remain explicit
    backend gaps until authoritative services are connected, so the interface
    never fabricates compensation or leave records.
    """
    role_label = profile_role_label(principal)
    trigger_name = principal.display_name or "My Profile"

    with st.popover(f"{trigger_name} · {role_label}  ▾", use_container_width=True):
        st.markdown(f"### {trigger_name}")
        st.caption(f"{role_label} · {workspace_label(engagement_id)}")

        if principal.role in {Role.CLIENT, Role.READ_ONLY}:
            account_tab, access_tab = st.tabs(("My Account", "Access"))
            with account_tab:
                _render_action_stats(
                    profile_work_stats(principal, manifest, records),
                    targets=profile_stat_targets(principal),
                    navigate=navigate,
                    key_prefix=f"{key_prefix}:client",
                )
                st.caption(
                    "Client-safe account view. Internal analysis, reviewer notes, staff workload, payroll, and administrative controls are not exposed here."
                )
            with access_tab:
                st.markdown("**Your permissions**")
                for permission in profile_permissions(principal):
                    st.write(f"✓ {permission}")
                _render_connection_action(
                    label="Open My Account",
                    target="My Account",
                    navigate=navigate,
                    key=f"{key_prefix}:client-account",
                    unavailable_message="Use the My Account page for the currently available client account details.",
                )
            return

        tabs = ["My Work", "Time Off", "Payroll", "Access"]
        if principal.role == Role.OWNER:
            tabs.append("Owner Controls")
        elif principal.role == Role.ADMIN:
            tabs.append("Admin Controls")
        rendered_tabs = st.tabs(tuple(tabs))

        with rendered_tabs[0]:
            _render_action_stats(
                profile_work_stats(principal, manifest, records),
                targets=profile_stat_targets(principal),
                navigate=navigate,
                key_prefix=f"{key_prefix}:work",
            )
            st.caption(
                "Personal workload summary from your currently assigned ColettiOS workspace access. Team-wide statistics belong in management views, not another employee's profile."
            )

        with rendered_tabs[1]:
            st.markdown("**My time off**")
            st.info("Authoritative time-off requests are not connected to an HR/leave service yet.")
            target = "Settings" if principal.role == Role.OWNER else "Administration" if principal.role == Role.ADMIN else None
            label = "Configure time-off integration" if target else "Check time-off connection"
            _render_connection_action(
                label=label,
                target=target,
                navigate=navigate,
                key=f"{key_prefix}:time-off",
                unavailable_message=(
                    "Time-off remains a backend-required capability. Once connected, this area can show request status, available leave, upcoming approved time off, and request history."
                ),
            )

        with rendered_tabs[2]:
            st.markdown("**My payroll**")
            st.info("Authoritative payroll data is not connected yet.")
            target = "Financials" if principal.role == Role.OWNER else "Administration" if principal.role == Role.ADMIN else None
            label = "Open payroll integration controls" if target else "Check payroll connection"
            _render_connection_action(
                label=label,
                target=target,
                navigate=navigate,
                key=f"{key_prefix}:payroll",
                unavailable_message=(
                    "Payroll remains a backend-required capability. Once connected, this area can show the current employee's pay statements, YTD totals, deductions/withholding summary, and payroll documents."
                ),
            )

        with rendered_tabs[3]:
            st.markdown("**Position & access**")
            st.write(f"**Position:** {role_label}")
            st.write(f"**Assigned cases:** {len(tuple(principal.engagement_ids))}")
            st.markdown("**Your permissions**")
            for permission in profile_permissions(principal):
                st.write(f"✓ {permission}")
            if principal.role == Role.OWNER:
                _render_connection_action(
                    label="Open Settings & Security",
                    target="Settings",
                    navigate=navigate,
                    key=f"{key_prefix}:owner-settings",
                    unavailable_message="Owner settings are available from the owner navigation.",
                )
                st.caption(
                    "Owner profile reflects full application permissions. Protected actions still remain subject to their required human/security gates."
                )
            elif principal.role == Role.ADMIN:
                _render_connection_action(
                    label="Open Administration",
                    target="Administration",
                    navigate=navigate,
                    key=f"{key_prefix}:admin-access",
                    unavailable_message="Administration is available from the team workspace navigation.",
                )
                st.caption(
                    "Administrator access includes user/case administration but does not make another employee's private payroll or leave information part of this personal profile."
                )

        if principal.role == Role.OWNER:
            with rendered_tabs[4]:
                st.markdown("**Owner control center**")
                st.caption(
                    "View, correct, and manage your authorized operating surfaces from your account. Protected or material changes continue to use their required approval/security gates."
                )
                _owner_control_buttons(navigate=navigate, key_prefix=key_prefix)
        elif principal.role == Role.ADMIN:
            with rendered_tabs[4]:
                st.markdown("**Administration shortcuts**")
                for label, target in (("Administration", "Administration"), ("Cases", "Engagements"), ("Review", "Review Center")):
                    if st.button(
                        label,
                        key=f"{key_prefix}:admin-control:{target}",
                        use_container_width=True,
                    ):
                        _open_or_explain(
                            target,
                            navigate=navigate,
                            state_key=f"{key_prefix}:last-opened",
                        )
