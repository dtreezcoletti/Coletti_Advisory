from __future__ import annotations

import streamlit as st

from .analysis import build_analytical_issues, build_summary
from .publication import published_reports
from .reporting import build_publication_gate
from .workspaces import workspace_label


def _nav_key(principal, experience: str) -> str:
    return f"_coletti_navigation:{principal.user_id}:{experience}"


def _drill_context_key(principal) -> str:
    return f"_drill_through_context:{principal.user_id}"


def _goto(principal, experience: str, page: str, *, object_type: str, label: str) -> None:
    st.session_state[_drill_context_key(principal)] = {
        "object_type": object_type,
        "page": page,
        "filters": {"source": f"{experience}_dashboard", "label": label},
    }
    st.session_state[_nav_key(principal, experience)] = page
    st.rerun()


def _connected_metric(principal, experience: str, *, value: str, label: str, object_type: str, page: str, key: str) -> None:
    with st.container(border=True):
        st.metric(label, value)
        if st.button("Open →", key=key, use_container_width=True):
            _goto(principal, experience, page, object_type=object_type, label=label)


def _client_dashboard(shell, principal, engagement_id: str, manifest: dict, records: dict) -> None:
    first_name = (principal.display_name or "there").strip().split()[0]
    if first_name.lower() == "synthetic":
        first_name = "Client"
    shell._hero(
        kicker="Client Portal",
        title=f"Welcome, {first_name}.",
        subtitle="Thank you for trusting Coletti & Co.",
        body="Your case, records, requests, progress, reports, and communications all resolve to the same authorized case workspace.",
    )
    current, _ = shell._client_stage(records, manifest)
    cols = st.columns(4)
    with cols[0]:
        _connected_metric(principal, "client", value=workspace_label(engagement_id), label="Your Case", object_type="case", page="My Case", key="client-kpi-case")
    with cols[1]:
        _connected_metric(principal, "client", value=f"{min(current + 1, 6)} of 6", label="Stages Reached", object_type="case", page="Progress", key="client-kpi-progress")
    with cols[2]:
        _connected_metric(principal, "client", value=str(len(manifest.get("sources") or {})), label="Documents Submitted", object_type="source", page="Upload Documents", key="client-kpi-documents")
    with cols[3]:
        _connected_metric(principal, "client", value="0", label="Open Requests", object_type="notification", page="Requests & To-Do", key="client-kpi-requests")

    shell._progress_panel(records, manifest)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown("### Recent Activity")
        with st.container(border=True):
            st.markdown("**Your workspace is active**")
            st.caption("Secure records processing and review are available.")
            if st.button("Open case →", key="client-activity-case", use_container_width=True):
                _goto(principal, "client", "My Case", object_type="case", label="Workspace active")
    with right:
        st.markdown("### Your Documents")
        st.markdown(f"<div class='cc-panel'>{shell._source_rows(manifest)}</div>", unsafe_allow_html=True)
        if st.button("Open document intake →", key="client-documents-open", use_container_width=True):
            _goto(principal, "client", "Upload Documents", object_type="source", label="Your Documents")


def _employee_dashboard(shell, principal, engagement_id: str, manifest: dict, records: dict, reports: dict) -> None:
    summary = build_summary(manifest)
    gate = build_publication_gate(manifest)
    shell._hero(
        kicker="Coletti & Co. Team",
        title="Review with clarity.",
        subtitle=workspace_label(engagement_id),
        body="The dashboard summarizes the same case, records, review, analysis, and report workspaces used to perform the work.",
    )
    cols = st.columns(4)
    with cols[0]:
        _connected_metric(principal, "employee", value=str(summary["sources"]), label="Sources", object_type="source", page="Evidence", key="employee-kpi-sources")
    with cols[1]:
        _connected_metric(principal, "employee", value=str(summary["propositions"]), label="Source-linked Propositions", object_type="record", page="Evidence", key="employee-kpi-propositions")
    with cols[2]:
        target = "Review Center" if "Review Center" in shell._visible_pages(principal) else "Analysis"
        _connected_metric(principal, "employee", value=str(summary["inconsistencies"]), label="Inconsistencies", object_type="blocker", page=target, key="employee-kpi-inconsistencies")
    with cols[3]:
        target = "Review Center" if "Review Center" in shell._visible_pages(principal) else "Analysis"
        _connected_metric(principal, "employee", value=str(gate["review_required_count"]), label="Items Requiring Review", object_type="decision", page=target, key="employee-kpi-review")

    c1, c2 = st.columns([1.05, .95], gap="large")
    with c1:
        st.markdown("### Review Queue")
        issues = build_analytical_issues(manifest)
        if issues:
            st.dataframe(issues, use_container_width=True, hide_index=True)
        else:
            st.info("No analytical issues are currently awaiting review.")
        target = "Review Center" if "Review Center" in shell._visible_pages(principal) else "Analysis"
        if st.button("Open canonical review workspace →", key="employee-review-open", use_container_width=True):
            _goto(principal, "employee", target, object_type="decision", label="Review Queue")
    with c2:
        st.markdown("### Publication Status")
        st.metric("Draft reports", len(reports))
        st.metric("Published reports", len(published_reports(records)))
        if st.button("Open reports →", key="employee-reports-open", use_container_width=True):
            _goto(principal, "employee", "Reports", object_type="report", label="Publication Status")
        st.caption("Client publication remains gated by explicit human review and approval.")


def patch_cross_interface_dashboards(experience_shell) -> None:
    if getattr(experience_shell, "_cross_interface_dashboard_connections_patched", False):
        return
    experience_shell._client_dashboard = lambda principal, engagement_id, manifest, records: _client_dashboard(
        experience_shell, principal, engagement_id, manifest, records
    )
    experience_shell._employee_dashboard = lambda principal, engagement_id, manifest, records, reports: _employee_dashboard(
        experience_shell, principal, engagement_id, manifest, records, reports
    )
    experience_shell._cross_interface_dashboard_connections_patched = True
