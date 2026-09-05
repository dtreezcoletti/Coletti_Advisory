from __future__ import annotations

import importlib.metadata
import platform

import requests
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

CORE_REPOSITORY = "dtreezcoletti/ColettiOS"
COMMERCIAL_REPOSITORY = "dtreezcoletti/Coletti_Advisory"

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


@st.cache_data(ttl=180, show_spinner=False)
def _latest_actions_run(repository: str, branch: str = "main") -> dict | None:
    """Read the latest public GitHub Actions run without granting the app write access."""
    url = f"https://api.github.com/repos/{repository}/actions/runs"
    try:
        response = requests.get(
            url,
            params={"branch": branch, "per_page": 1},
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "coletti-system-lab",
            },
            timeout=5,
        )
        response.raise_for_status()
        runs = response.json().get("workflow_runs") or []
    except (requests.RequestException, ValueError) as exc:
        return {"error": exc.__class__.__name__}

    if not runs:
        return None

    run = runs[0]
    return {
        "name": run.get("name") or "GitHub Actions",
        "status": run.get("status") or "unknown",
        "conclusion": run.get("conclusion"),
        "sha": run.get("head_sha") or "",
        "updated_at": run.get("updated_at") or "",
        "url": run.get("html_url") or "",
        "event": run.get("event") or "",
    }


def _live_gate_label(run: dict | None) -> str:
    if not run or run.get("error"):
        return "UNAVAILABLE"
    if run.get("status") != "completed":
        return str(run.get("status") or "unknown").upper()
    if run.get("conclusion") == "success":
        return "PASS"
    conclusion = str(run.get("conclusion") or "unknown").upper()
    return f"FAIL · {conclusion}"


def _short_sha(run: dict | None) -> str:
    if not run:
        return "—"
    sha = str(run.get("sha") or "")
    return sha[:10] if sha else "—"


def _render_core_test_lab(core_run: dict | None) -> None:
    st.subheader("Core Test Lab")
    st.caption(
        "Owner/admin diagnostic surface for the controlled ColettiOS Core acceptance gate. "
        "The live column reflects the latest full Core main-branch CI gate, which compiles Core, runs the complete pytest suite, and builds the container."
    )
    live_gate = _live_gate_label(core_run)
    rows = [
        {
            "Acceptance test": test_id,
            "Invariant": invariant,
            "Controlled baseline": "PASS",
            "Latest Core gate": live_gate,
        }
        for test_id, invariant in CORE_ACCEPTANCE_MATRIX
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if live_gate == "PASS":
        st.success(f"Latest ColettiOS Core main gate: PASS · {_short_sha(core_run)}")
    elif live_gate in {"QUEUED", "IN_PROGRESS", "REQUESTED", "WAITING", "PENDING"}:
        st.info(f"Latest ColettiOS Core main gate: {live_gate} · {_short_sha(core_run)}")
    else:
        st.warning(
            f"Latest ColettiOS Core main gate: {live_gate}. The controlled v1.0 baseline remains preserved; investigate before treating newer code as accepted."
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


def _render_run_card(label: str, repository: str, run: dict | None) -> None:
    gate = _live_gate_label(run)
    with st.container(border=True):
        st.markdown(f"**{label}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gate", gate)
        c2.metric("Main SHA", _short_sha(run))
        c3.metric("Workflow", str((run or {}).get("name") or "—"))
        if run and run.get("updated_at"):
            st.caption(f"Updated: {run['updated_at']} · Event: {run.get('event') or '—'}")
        if run and run.get("url"):
            st.link_button(f"Open {label} workflow", run["url"])
        if run and run.get("error"):
            st.warning(f"Live CI lookup unavailable ({run['error']}). Controlled baselines are unchanged.")
        st.caption(repository)


def _render_ci_releases(core_run: dict | None, commercial_run: dict | None) -> None:
    st.subheader("CI & Releases")
    st.caption(
        "Read-only live release/test visibility. The hosted app reads public GitHub Actions metadata and has no permission to execute shell commands or mutate either repository."
    )
    _render_run_card("ColettiOS Core", CORE_REPOSITORY, core_run)
    _render_run_card("Coletti & Co. Commercial", COMMERCIAL_REPOSITORY, commercial_run)
    st.info("CI data is cached for three minutes to avoid unnecessary GitHub API traffic.")


def _render_security_gate(app_mode: str, storage_backend: str, core_backend: str) -> None:
    st.subheader("Security Gate")
    st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
    for label, implemented in SECURITY_CONTROLS:
        st.write(f"{'✅' if implemented else '🔨'} {label}")


def _render_audit(manifest: dict, commercial_run: dict | None) -> None:
    st.subheader("Audit & Diagnostics")
    audit_log = manifest.get("audit_log") or []
    if audit_log:
        st.dataframe(audit_log, use_container_width=True, hide_index=True)
    else:
        st.info("No audit events are currently available for this workspace.")

    try:
        streamlit_version = importlib.metadata.version("streamlit")
    except importlib.metadata.PackageNotFoundError:
        streamlit_version = "unknown"

    with st.expander("Runtime diagnostics", expanded=True):
        st.write(
            {
                "streamlit_version": streamlit_version,
                "python_version": platform.python_version(),
                "latest_commercial_main_sha": _short_sha(commercial_run),
                "latest_commercial_ci_gate": _live_gate_label(commercial_run),
                "sources": len(manifest.get("sources") or {}),
                "propositions": len(manifest.get("propositions") or {}),
                "reviewer_conclusions": len(manifest.get("reviewer_conclusions") or {}),
                "contradictions": len(manifest.get("contradictions") or {}),
                "reconciliations": len(manifest.get("reconciliations") or {}),
                "escalations": len(manifest.get("escalations") or {}),
                "audit_events": len(audit_log),
            }
        )
        st.caption(
            "Latest commercial main SHA is repository state, not a cryptographic claim that Community Cloud has already activated that exact revision. Runtime Streamlit/Python versions are reported by this running process."
        )


def render_system_lab(*, principal, manifest: dict, app_mode: str, storage_backend: str, core_backend: str) -> None:
    if not can_access_system_lab(principal):
        st.error("Your role does not permit access to the System Lab.")
        st.stop()

    st.title("System Lab")
    st.caption("Owner / Admin only · synthetic testing · release diagnostics · security visibility")

    core_run = _latest_actions_run(CORE_REPOSITORY)
    commercial_run = _latest_actions_run(COMMERCIAL_REPOSITORY)

    core_tab, clean_tab, ci_tab, security_tab, audit_tab = st.tabs(SYSTEM_LAB_SECTIONS)
    with core_tab:
        _render_core_test_lab(core_run)
    with clean_tab:
        _render_clean_room(manifest)
    with ci_tab:
        _render_ci_releases(core_run, commercial_run)
    with security_tab:
        _render_security_gate(app_mode, storage_backend, core_backend)
    with audit_tab:
        _render_audit(manifest, commercial_run)
