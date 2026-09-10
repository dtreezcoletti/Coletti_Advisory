from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .analysis import build_summary
from .demo_controls import DEMO_EXPERIENCES, demo_experience_switching_available
from .workspaces import workspace_environment, workspace_label


CASE_FLOW = (
    "Case Queue",
    "Record Ingestion",
    "Evidence",
    "Analysis",
    "Human Review",
    "Reports",
)

PAGE_INTEGRATION_STATUS = (
    ("My Workspace", "CONNECTED", "Live owner/Dispatcher snapshot with DARI and owner actions"),
    ("Case Queue", "CONNECTED", "Shared case selector and workflow routing"),
    ("Record Ingestion", "CONNECTED", "Secure upload + Google Drive import into the same source pipeline"),
    ("Evidence", "CONNECTED", "Registered sources, ingested-material staging, extraction review, propositions, cross-record review"),
    ("Analysis", "CONNECTED", "Reads the selected case manifest"),
    ("Human Review", "CONNECTED", "Selected-case review and publication preparation"),
    ("Reports", "CONNECTED", "Selected-case draft/report state and publication flow"),
    ("Clients", "CONNECTED", "Authorized client/case workspaces route into the shared selected-case context"),
    ("Approvals", "CONNECTED", "Authoritative owner decision queue"),
    ("Dispatcher", "CONNECTED", "Authoritative task/project/calendar/reconciliation control plane"),
    ("Team", "CONNECTED", "Administration and permission controls"),
    ("Firm Overview", "CONNECTED", "Aggregates authorized case manifests and integration health"),
    ("Settings", "CONNECTED", "Administration/security controls and System Lab handoff"),
    ("Messages", "BACKEND REQUIRED", "No durable communications store/service is implemented yet"),
    ("Financials", "BACKEND REQUIRED", "No authoritative firm financial ledger feed is implemented yet"),
    ("Knowledge Base", "REFERENCE ONLY", "Current page is static operating-method guidance; authoritative Docket/knowledge service is not implemented"),
)


def _page_key(principal) -> str:
    return f"_owner_reference_page:{principal.user_id}"


def _engagement_key(principal) -> str:
    return f"_coletti_active_engagement:{principal.user_id}"


def _requested_engagement_key(principal) -> str:
    return f"_coletti_requested_engagement:{principal.user_id}"


def _go(principal, page: str, *, engagement_id: str | None = None) -> None:
    if engagement_id:
        st.session_state[_requested_engagement_key(principal)] = engagement_id
    st.session_state[_page_key(principal)] = page
    st.rerun()


def patch_shared_engagement_selector(experience_shell) -> None:
    """Use one explicit selected-case state across sidebar, case queue, and owner pages.

    In the anonymous synthetic tenant, the Authorized workspace control doubles as
    the interface switcher so Client / Employee / Admin / Owner are always
    reachable from the same visible place. Live/authenticated workspaces retain
    the normal case-only selector.
    """
    if getattr(experience_shell, "_shared_engagement_selector_patched", False):
        return

    def _select_engagement(principal) -> str:
        options = list(principal.engagement_ids)
        if not options:
            st.error("No authorized workspace is available for this account.")
            st.stop()

        key = _engagement_key(principal)
        requested = st.session_state.pop(_requested_engagement_key(principal), None)
        current = st.session_state.get(key)
        if requested in options:
            st.session_state[key] = requested
        elif current not in options:
            st.session_state[key] = options[0]

        app_mode = experience_shell.app._secret("APP_MODE", "demo").lower()
        core = st.session_state.get("_coletti_core")
        if demo_experience_switching_available(
            app_mode=app_mode,
            principal=principal,
            core=core,
        ):
            labels = [label for label, _role, _description in DEMO_EXPERIENCES]
            current_interface = st.session_state.get("_coletti_demo_experience", labels[0])
            if current_interface not in labels:
                current_interface = labels[0]
                st.session_state["_coletti_demo_experience"] = current_interface

            selected = st.session_state[key]
            selected_interface = st.sidebar.selectbox(
                "Authorized workspace",
                labels,
                index=labels.index(current_interface),
                key="_coletti_demo_experience",
                format_func=lambda label: f"{label} · {workspace_label(selected)}",
                help=(
                    "Synthetic demo only. Switch between the Client, Employee, Admin, and Owner interfaces "
                    "while keeping the same synthetic case and data."
                ),
            )
            description = next(
                description
                for label, _role, description in DEMO_EXPERIENCES
                if label == selected_interface
            )
            st.sidebar.caption(f"{description} · same synthetic case across views")
        else:
            selected = st.sidebar.selectbox(
                "Authorized workspace",
                options,
                format_func=workspace_label,
                key=key,
            )
            st.sidebar.caption(f"{workspace_environment(selected)} workspace")

        if not principal.can_access(selected):
            st.error("Workspace authorization failed.")
            st.stop()

        st.sidebar.divider()
        # Preserve the demo-control/topbar compatibility contract while making
        # the selected engagement explicit and reusable by page integrations.
        st.session_state["_coletti_selected_engagement"] = selected
        return selected

    experience_shell._select_engagement = _select_engagement
    experience_shell._shared_engagement_selector_patched = True


def _manifest_stage(manifest: Mapping[str, Any]) -> str:
    if manifest.get("contradictions"):
        return "Human Review"
    if manifest.get("propositions"):
        return "Analysis"
    if manifest.get("sources"):
        return "Evidence"
    return "Record Ingestion"


def _case_rows(core, principal, active_engagement: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for eid in principal.engagement_ids:
        try:
            manifest = core.manifest(eid)
        except Exception:
            manifest = {}
        summary = build_summary(dict(manifest))
        rows.append(
            {
                "Case": workspace_label(eid),
                "ID": eid,
                "Environment": workspace_environment(eid),
                "Stage": _manifest_stage(manifest),
                "Sources": summary.get("sources", 0),
                "Propositions": summary.get("propositions", 0),
                "Inconsistencies": summary.get("inconsistencies", 0),
                "Selected": "Yes" if eid == active_engagement else "",
            }
        )
    return rows


def _case_launcher(principal, *, active_engagement: str, key_prefix: str) -> None:
    options = list(principal.engagement_ids)
    if not options:
        return
    default_index = options.index(active_engagement) if active_engagement in options else 0
    chosen = st.selectbox(
        "Case to open",
        options,
        index=default_index,
        format_func=lambda eid: f"{workspace_label(eid)} · {eid}",
        key=f"{key_prefix}:case",
    )
    st.caption("Choose the case once, then open the exact stage you need. The same case remains selected across the connected workflow.")
    cols = st.columns(5)
    destinations = ("Record Ingestion", "Evidence", "Analysis", "Human Review", "Reports")
    for idx, destination in enumerate(destinations):
        if cols[idx].button(destination, use_container_width=True, key=f"{key_prefix}:{destination}"):
            _go(principal, destination, engagement_id=chosen)


def render_integrated_case_queue(shell, **kwargs) -> None:
    principal = kwargs["principal"]
    active = kwargs["engagement_id"]
    core = kwargs["core"]
    st.title("Case Queue")
    st.caption("One authenticated case context across intake, records intelligence, analysis, review, and reporting.")
    rows = _case_rows(core, principal, active)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No authorized case workspace is available.")
        return
    st.divider()
    _case_launcher(principal, active_engagement=active, key_prefix="owner-case-queue")


def render_integrated_clients(shell, **kwargs) -> None:
    principal = kwargs["principal"]
    active = kwargs["engagement_id"]
    core = kwargs["core"]
    st.title("Clients")
    st.caption("Authorized client/case workspaces connected to the same active-case context used throughout ColettiOS.")
    rows = _case_rows(core, principal, active)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.divider()
        _case_launcher(principal, active_engagement=active, key_prefix="owner-client-launcher")
    else:
        st.info("No authorized client/case workspace is available.")


def _flow_footer(principal, page: str, engagement_id: str, manifest: Mapping[str, Any]) -> None:
    if page not in CASE_FLOW or page == "Case Queue":
        return
    current = CASE_FLOW.index(page)
    previous_page = CASE_FLOW[current - 1] if current > 0 else "Case Queue"
    next_page = CASE_FLOW[current + 1] if current + 1 < len(CASE_FLOW) else None
    summary = build_summary(dict(manifest))

    st.divider()
    with st.container(border=True):
        st.caption(
            f"CONNECTED CASE WORKFLOW · {workspace_label(engagement_id)} · {engagement_id} · "
            f"{summary.get('sources', 0)} source(s) · {summary.get('propositions', 0)} proposition(s) · "
            f"{summary.get('inconsistencies', 0)} inconsistency item(s)"
        )
        left, middle, right = st.columns([1, 1, 1])
        if left.button(f"← {previous_page}", key=f"flow-prev:{page}", use_container_width=True):
            _go(principal, previous_page, engagement_id=engagement_id)
        if middle.button("Case Queue", key=f"flow-queue:{page}", use_container_width=True):
            _go(principal, "Case Queue", engagement_id=engagement_id)
        if next_page:
            if right.button(f"{next_page} →", key=f"flow-next:{page}", type="primary", use_container_width=True):
                _go(principal, next_page, engagement_id=engagement_id)
        else:
            right.caption("End of internal case-production chain")


def _integration_health() -> None:
    st.divider()
    st.subheader("Page Integration Health")
    st.caption("CONNECTED means the page is wired to an existing authoritative ColettiOS path. BACKEND REQUIRED means the missing service itself still has to be built; the UI is not treated as operational merely because a page exists.")
    st.dataframe(
        [
            {"Page": page, "Integration": status, "Current contract": contract}
            for page, status, contract in PAGE_INTEGRATION_STATUS
        ],
        use_container_width=True,
        hide_index=True,
    )


def patch_owner_page_integration(owner_runtime) -> None:
    """Connect owner pages through one case context and expose integration truth."""
    if getattr(owner_runtime, "_owner_page_integration_patched", False):
        return

    original_render = owner_runtime._render_owner_page

    def _render(shell, page: str, **kwargs):
        if page == "Case Queue":
            return render_integrated_case_queue(shell, **kwargs)
        if page == "Clients":
            return render_integrated_clients(shell, **kwargs)

        result = original_render(shell, page, **kwargs)

        if page in CASE_FLOW:
            _flow_footer(
                kwargs["principal"],
                page,
                kwargs["engagement_id"],
                kwargs["manifest"],
            )
        if page == "Firm Overview":
            _integration_health()
        return result

    owner_runtime._render_owner_page = _render
    owner_runtime._owner_page_integration_patched = True
