from __future__ import annotations

import streamlit as st

from .models import Permission
from .security import SECURITY_CONTROLS


SYSTEM_LAB_SECTIONS = (
    "Core Test Lab",
    "Clean Room",
    "CI & Releases",
    "Security Gate",
    "Audit & Diagnostics",
)


CORE_ACCEPTANCE_MATRIX = (
    ("AC-01", "Source required for propositions"),
    ("AC-02", "Provenance preservation"),
    ("AC-03", "Evidence-state transitions"),
    ("AC-04", "Contradiction preservation"),
    ("AC-05", "Reconciliation without silent promotion"),
    ("AC-06", "Reviewer / evidence separation"),
    ("AC-07", "Audit-history integrity"),
    ("AC-08", "Generalized schema behavior"),
    ("AC-09", "Unrelated synthetic engagement"),
    ("AC-10", "Zero historical-case dependency"),
)


def can_access_system_lab(principal) -> bool:
    """The lab is restricted to principals with administrative authority."""
    return principal.can(Permission.MANAGE_USERS)


def _render_core_test_lab() -> None:
    st.subheader("Core Test Lab")
    st.caption(
        "Owner/admin diagnostic surface for the controlled ColettiOS Core acceptance gate. "
        "This view does not expose test controls to client or ordinary analyst workspaces."
    )
    rows = [
        {
            "Acceptance test": test_id,
            "Invariant": invariant,
            "Controlled baseline": "PASS",
            "Live run": "Not connected",
        }
        for test_id, invariant in CORE_ACCEPTANCE_MATRIX
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.info(
        "Controlled Core v1.0 baseline is accepted. The next wiring step is to feed current GitHub Actions "
        "or a signed clean-room result artifact into the Live run column."
    )


def _render_clean_room(manifest: dict) -> None:
    st.subheader("Sandbox / Clean Room")
    st.caption(
        "Synthetic-only inspection area. Nothing shown here changes client evidence, reviewer conclusions, "
        "or published reports."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources", len(manifest.get("sources") or {}))
    c2.metric("Propositions", len(manifest.get("propositions") or {}))
    c3.metric("Contradictions", len(manifest.get("contradictions") or {}))
    c4.metric("Escalations", len(manifest.get("escalations") or {}))

    states = manifest.get("source_states") or {}
    if states:
        st.write("Evidence states")
        st.dataframe(
            [{"Source": source_id, "State": state} for source_id, state in states.items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No synthetic evidence-state data is currently loaded in this workspace.")

    with st.expander("Synthetic manifest inspector"):
        st.json(manifest)


def _render_ci_releases() -> None:
    st.subheader("CI & Releases")
    st.caption("Release and test-gate visibility without giving the Streamlit server arbitrary shell execution.")
    st.write("**Core acceptance gate:** Controlled")
    st.write("**Live GitHub Actions feed:** Not connected to this UI yet")
    st.write("**Recommended production behavior:** Read signed/authorized CI results; do not execute arbitrary test commands from the hosted app.")
    st.info("This section is intentionally read-only until the CI result feed is wired.")


def _render_security_gate(app_mode: str, storage_backend: str, core_backend: str) -> None:
    st.subheader("Security Gate")
    st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
    for label, implemented in SECURITY_CONTROLS:
        st.write(f"{'✅' if implemented else '🔨'} {label}")


def _render_audit(manifest: dict) -> None:
    st.subheader("Audit & Diagnostics")
    audit_log = manifest.get("audit_log") or []
    if audit_log:
        st.dataframe(audit_log, use_container_width=True, hide_index=True)
    else:
        st.info("No audit events are currently available for this workspace.")

    with st.expander("Runtime manifest diagnostics"):
        st.write(
            {
                "sources": len(manifest.get("sources") or {}),
                "propositions": len(manifest.get("propositions") or {}),
                "reviewer_conclusions": len(manifest.get("reviewer_conclusions") or {}),
                "contradictions": len(manifest.get("contradictions") or {}),
                "reconciliations": len(manifest.get("reconciliations") or {}),
                "escalations": len(manifest.get("escalations") or {}),
                "audit_events": len(audit_log),
            }
        )


def render_system_lab(*, principal, manifest: dict, app_mode: str, storage_backend: str, core_backend: str) -> None:
    if not can_access_system_lab(principal):
        st.error("Your role does not permit access to the System Lab.")
        st.stop()

    st.title("System Lab")
    st.caption("Owner / Admin only · synthetic testing · release diagnostics · security visibility")

    core_tab, clean_tab, ci_tab, security_tab, audit_tab = st.tabs(SYSTEM_LAB_SECTIONS)
    with core_tab:
        _render_core_test_lab()
    with clean_tab:
        _render_clean_room(manifest)
    with ci_tab:
        _render_ci_releases()
    with security_tab:
        _render_security_gate(app_mode, storage_backend, core_backend)
    with audit_tab:
        _render_audit(manifest)
