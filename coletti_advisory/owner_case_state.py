from __future__ import annotations

from typing import Any

import streamlit as st

from .owner_console_live import OwnerControlPlaneClient, OwnerControlPlaneUnavailable


def _safe_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _show_table(title: str, rows: list[dict[str, Any]], *, empty: str) -> None:
    st.subheader(title)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption(empty)


def render_owner_case_state(*, principal, engagement_id: str, core) -> None:
    """Render the internal canonical reconstructed-case-state control surface.

    This is intentionally owner-only and read-only. It exposes reconstructed
    control metadata through the private ColettiOS service, not direct Supabase
    credentials and not original source-file bytes.
    """
    st.title("Canonical Case State")
    st.caption(
        "Owner-only reconstructed-state view. Reports are controlled views over this state; "
        "this page does not publish records to clients."
    )

    try:
        client = OwnerControlPlaneClient(core)
        catalog = client.case_state_catalog(principal, engagement_id)
    except OwnerControlPlaneUnavailable as exc:
        st.info(str(exc))
        st.caption("Canonical case-state controls are available when the authenticated private ColettiOS service is active.")
        return

    if not catalog:
        st.info("No canonical registry cases are available to this owner service yet.")
        return

    case_ids = [str(item.get("case_id")) for item in catalog if item.get("case_id")]
    if not case_ids:
        st.info("No canonical case identifiers were returned.")
        return

    selected_case = st.selectbox(
        "Canonical case",
        case_ids,
        key="owner_canonical_case_state_selection",
    )
    catalog_row = next((item for item in catalog if item.get("case_id") == selected_case), {})

    track = str(catalog_row.get("track_type") or "UNCLASSIFIED")
    governance_writeback = bool(catalog_row.get("governance_writeback"))
    training_authority = bool(catalog_row.get("training_authority"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Validation Track", track.replace("_", " ").title())
    c2.metric("Governance Writeback", "ENABLED" if governance_writeback else "BLOCKED")
    c3.metric("Training Authority", "ENABLED" if training_authority else "BLOCKED")
    c4.metric("Reflection Minimum", f"{int(catalog_row.get('minimum_reflection_days') or 5)} days")

    if track == "HISTORICAL_REFERENCE":
        st.warning(
            "Historical Reference control is active. Case-specific facts are non-authoritative: "
            "governance writeback and training authority must remain blocked."
        )
    elif track == "SYNTHETIC_REGRESSION":
        st.success("Synthetic Regression track: suitable for structural testing, subject to the governed promotion path.")

    try:
        snapshot = client.case_state(principal, engagement_id, selected_case)
    except (OwnerControlPlaneUnavailable, ValueError) as exc:
        st.error(str(exc))
        return

    counts = dict(snapshot.get("counts") or {})
    metrics = st.columns(4)
    metrics[0].metric("Issues", counts.get("issues", 0))
    metrics[1].metric("Timeline Events", counts.get("timeline_events", 0))
    metrics[2].metric("Open Record Gaps", counts.get("gaps", 0))
    metrics[3].metric("Professional Questions", counts.get("professional_questions", 0))

    tabs = st.tabs(
        [
            "Issues",
            "Timeline",
            "Procedure",
            "Discovery",
            "Contradictions",
            "Obligations",
            "Missing Records",
            "Professional Matrix",
            "Outputs",
        ]
    )

    with tabs[0]:
        _show_table("Issue / Question Register", _safe_rows(snapshot.get("issues")), empty="No issues recorded.")
    with tabs[1]:
        _show_table("Timeline / Event Register", _safe_rows(snapshot.get("timeline")), empty="No timeline events recorded.")
    with tabs[2]:
        _show_table("Procedural Posture Register", _safe_rows(snapshot.get("procedural_posture")), empty="No procedural items recorded.")
    with tabs[3]:
        _show_table("Discovery Obligation Matrix", _safe_rows(snapshot.get("discovery_obligations")), empty="No discovery obligations recorded.")
        st.caption("Receipt, verification, completeness, supplementation, and closure remain independent dimensions.")
    with tabs[4]:
        _show_table("Contradiction & Reconciliation Ledger", _safe_rows(snapshot.get("contradictions")), empty="No contradictions recorded.")
        st.caption("An apparent conflict is not a true inconsistency until scope, time period, and measurement are evaluated.")
    with tabs[5]:
        _show_table("Obligation & Performance Ledger", _safe_rows(snapshot.get("obligations")), empty="No obligations recorded.")
        st.caption("Authority status and performance status remain separate.")
    with tabs[6]:
        _show_table("Missing Documentation / Gap Register", _safe_rows(snapshot.get("missing_documentation")), empty="No record gaps recorded.")
    with tabs[7]:
        _show_table(
            "Professional Proof/Disproof Matrix",
            _safe_rows(snapshot.get("professional_proof_disproof")),
            empty="No professional proof/disproof questions recorded.",
        )
        st.caption(
            "Proof/disproof describes the condition of the reconstructed record. "
            "The qualified professional determines the protected professional effect."
        )
    with tabs[8]:
        _show_table("Approved Output Types", _safe_rows(snapshot.get("output_types")), empty="No output catalog available.")
        st.caption("All approved outputs derive from the canonical reconstructed case state and require a timeline.")
