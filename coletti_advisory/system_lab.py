from __future__ import annotations

import importlib.metadata
import os
import platform
import tempfile

import requests
import streamlit as st

from .core_adapter import SyntheticCoreAdapter
from .intake import ingest_file
from .models import Permission
from .security import SECURITY_CONTROLS
from .storage import EncryptedLocalDemoStorage


SYSTEM_LAB_SECTIONS = (
    "Core Test Lab",
    "Clean Room",
    "CI & Releases",
    "Security Gate",
    "Production Readiness",
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

PRODUCTION_READINESS_CAVEAT = (
    "There is still no verified basis to declare production storage complete, private deployment fully passed, "
    "production auth fully passed, production mode activated, finished production report flow validated, or "
    "complete production E2E acceptance passed unless the corresponding live production verification has PASS evidence."
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


def _diagnostic_intake_runtime():
    """Return a session-isolated synthetic Core and encrypted ephemeral store for System Lab probes."""
    if "_system_lab_probe_core" not in st.session_state:
        st.session_state["_system_lab_probe_core"] = SyntheticCoreAdapter()
    if "_system_lab_probe_storage" not in st.session_state:
        root = os.path.join(tempfile.gettempdir(), "coletti_system_lab_secure_store")
        st.session_state["_system_lab_probe_storage"] = EncryptedLocalDemoStorage(root, os.urandom(32))
    return st.session_state["_system_lab_probe_core"], st.session_state["_system_lab_probe_storage"]


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


def _render_clean_room(
    manifest: dict,
    *,
    app_mode: str,
    principal,
    engagement_id: str,
) -> None:
    st.subheader("Sandbox / Clean Room")
    st.caption(
        "Synthetic-only inspection area. Clean Room probes use separate diagnostic state and do not mutate the active engagement, reviewer conclusions, or report drafts."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active workspace sources", len(manifest.get("sources") or {}))
    c2.metric("Propositions", len(manifest.get("propositions") or {}))
    c3.metric("Contradictions", len(manifest.get("contradictions") or {}))
    c4.metric("Escalations", len(manifest.get("escalations") or {}))

    st.markdown("**Synthetic intake path probe**")
    st.caption(
        "This bypasses the browser file-picker widget but exercises the same server-side intake classes: "
        "authorization → AES-GCM encrypted local demo storage → SHA-256 integrity hash → Core source registration → authenticated audit event. "
        "It runs against a separate diagnostic Core and separate ephemeral encrypted store."
    )
    if app_mode != "demo":
        st.warning("The one-click probe is disabled outside demo mode. Production-path E2E requires its own controlled synthetic acceptance procedure.")
    else:
        diagnostic_core, diagnostic_storage = _diagnostic_intake_runtime()
        if st.button("Run isolated synthetic intake probe", type="primary", key="system-lab-intake-probe"):
            before_active_source_count = len(manifest.get("sources") or {})
            result = ingest_file(
                principal=principal,
                engagement_id=engagement_id,
                filename="SYNTHETIC_SYSTEM_LAB_INTAKE_PROBE.txt",
                data=(
                    b"COLETTI & CO. SYNTHETIC INTAKE PROBE\n"
                    b"No real client, legal, medical, financial, or identifying information.\n"
                ),
                classification="Synthetic Diagnostic Record",
                storage=diagnostic_storage,
                core=diagnostic_core,
            )
            diagnostic_manifest = diagnostic_core.manifest(engagement_id)
            source_id = result["source"]["source_id"]
            matching_events = [
                event
                for event in diagnostic_manifest.get("audit_log", [])
                if event.get("event_type") == "SOURCE_REGISTERED" and event.get("subject_id") == source_id
            ]
            st.session_state["_last_system_lab_intake_probe"] = {
                "source_id": source_id,
                "content_hash": result["storage"]["content_hash"],
                "storage_uri": result["storage"]["storage_uri"],
                "encrypted": result["storage"]["encrypted"],
                "evidence_state": (diagnostic_manifest.get("source_states") or {}).get(source_id),
                "audit_actor": matching_events[-1].get("actor") if matching_events else None,
                "audit_event": bool(matching_events),
                "active_source_count_before": before_active_source_count,
            }
            st.rerun()

        probe = st.session_state.get("_last_system_lab_intake_probe")
        if probe:
            active_source_count_now = len(manifest.get("sources") or {})
            isolation_ok = active_source_count_now == probe["active_source_count_before"]
            passed = (
                probe["encrypted"] is True
                and probe["evidence_state"] == "INGESTED"
                and probe["audit_event"] is True
                and isolation_ok
            )
            if passed:
                st.success(f"Isolated synthetic intake probe: PASS · {probe['source_id']}")
            else:
                st.error("Isolated synthetic intake probe did not satisfy every diagnostic invariant.")
            st.write(
                {
                    "encrypted": probe["encrypted"],
                    "sha256": probe["content_hash"],
                    "storage_uri": probe["storage_uri"],
                    "evidence_state": probe["evidence_state"],
                    "authenticated_audit_actor": probe["audit_actor"],
                    "audit_event_recorded": probe["audit_event"],
                    "active_engagement_unchanged": isolation_ok,
                }
            )

    states = manifest.get("source_states") or {}
    if states:
        st.write("Active workspace evidence states")
        st.dataframe(
            [{"Source": source_id, "State": state} for source_id, state in states.items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No synthetic evidence-state data is currently loaded in this workspace.")

    with st.expander("Active synthetic manifest inspector"):
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


def _production_readiness_rows(
    *,
    app_mode: str,
    storage_backend: str,
    core_backend: str,
    storage_probe: dict | None,
) -> list[dict[str, str]]:
    storage_status = "NOT VERIFIED"
    storage_basis = "Requires live production GCS roundtrip evidence."
    if storage_probe:
        storage_status = str(storage_probe.get("status") or "FAIL")
        storage_basis = "Live synthetic GCS write/read/decrypt/hash/metadata/cleanup probe."

    production_mode_status = "PASS" if app_mode == "production" else "NOT VERIFIED"
    production_mode_basis = (
        "This running process reports APP_MODE=production."
        if production_mode_status == "PASS"
        else "Current runtime is not production mode."
    )

    return [
        {
            "Control": "Production storage",
            "Status": storage_status,
            "Verification basis": storage_basis,
        },
        {
            "Control": "Private deployment",
            "Status": "NOT VERIFIED",
            "Verification basis": "Requires live private deployment and protected Core service acceptance evidence.",
        },
        {
            "Control": "Production authentication",
            "Status": "NOT VERIFIED",
            "Verification basis": "Requires login, expiration, re-authentication, logout/revocation, RBAC and engagement-isolation acceptance.",
        },
        {
            "Control": "Production mode",
            "Status": production_mode_status,
            "Verification basis": production_mode_basis,
        },
        {
            "Control": "Finished production report flow",
            "Status": "NOT VERIFIED",
            "Verification basis": "Requires production-path intake through approved frozen client publication.",
        },
        {
            "Control": "Complete production E2E",
            "Status": "NOT VERIFIED",
            "Verification basis": "Requires one unrelated synthetic engagement through the complete real production stack without developer intervention.",
        },
    ]


def _overall_production_readiness(rows: list[dict[str, str]]) -> str:
    return "PRODUCTION READY" if rows and all(row.get("Status") == "PASS" for row in rows) else "NOT PRODUCTION READY"


def _render_production_readiness(
    *,
    app_mode: str,
    storage_backend: str,
    core_backend: str,
    storage,
    principal,
    engagement_id: str,
) -> None:
    if storage is None:
        storage = st.session_state.get("_coletti_storage")

    st.subheader("Production Readiness")
    st.caption("Temporary pre-launch operational verification. No readiness percentage is used.")
    st.warning(PRODUCTION_READINESS_CAVEAT)

    probe = st.session_state.get("_production_storage_probe")
    if probe and (
        probe.get("app_mode") != app_mode
        or probe.get("storage_backend") != storage_backend
        or probe.get("engagement_id") != engagement_id
    ):
        probe = None

    can_probe_storage = (
        app_mode == "production"
        and storage_backend == "gcs"
        and hasattr(storage, "verify_operational")
    )
    if can_probe_storage:
        st.markdown("**LR-04 / PI-006–007 · Live production storage verification**")
        st.caption(
            "Uses synthetic bytes only. The probe writes one client-side AES-GCM encrypted sentinel to the configured production bucket, reads it back, verifies metadata and plaintext SHA-256 after authenticated decryption, then deletes the exact probe generation."
        )
        if st.button("Run live production storage verification", type="primary", key="production-storage-probe"):
            result = storage.verify_operational(
                organization_id=principal.organization_id,
                engagement_id=engagement_id,
            )
            st.session_state["_production_storage_probe"] = {
                "app_mode": app_mode,
                "storage_backend": storage_backend,
                "engagement_id": engagement_id,
                **result.as_dict(),
            }
            st.rerun()
    else:
        st.info(
            "Live production storage verification is unavailable in this runtime. It becomes runnable only when APP_MODE=production and STORAGE_BACKEND=gcs are active with the production storage adapter."
        )

    storage_probe = probe if probe else None
    rows = _production_readiness_rows(
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        storage_probe=storage_probe,
    )
    overall = _overall_production_readiness(rows)
    if overall == "PRODUCTION READY":
        st.success(overall)
    else:
        st.error(overall)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if storage_probe:
        if storage_probe.get("status") == "PASS":
            st.success("Production storage verification: PASS")
        else:
            st.error("Production storage verification: FAIL")
        st.write(storage_probe.get("checks") or {})
        with st.expander("Production storage verification evidence"):
            st.json(storage_probe.get("evidence") or {})
        st.caption(
            "A storage PASS proves only the live storage control. It does not imply that authentication, private Core deployment, report flow, recovery, or complete production E2E acceptance has passed."
        )


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


def render_system_lab(
    *,
    principal,
    manifest: dict,
    app_mode: str,
    storage_backend: str,
    core_backend: str,
    engagement_id: str,
    storage=None,
) -> None:
    if not can_access_system_lab(principal):
        st.error("Your role does not permit access to the System Lab.")
        st.stop()

    st.title("System Lab")
    st.caption("Owner / Admin only · synthetic testing · release diagnostics · security visibility")

    core_run = _latest_actions_run(CORE_REPOSITORY)
    commercial_run = _latest_actions_run(COMMERCIAL_REPOSITORY)

    core_tab, clean_tab, ci_tab, security_tab, readiness_tab, audit_tab = st.tabs(SYSTEM_LAB_SECTIONS)
    with core_tab:
        _render_core_test_lab(core_run)
    with clean_tab:
        _render_clean_room(
            manifest,
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
        )
    with ci_tab:
        _render_ci_releases(core_run, commercial_run)
    with security_tab:
        _render_security_gate(app_mode, storage_backend, core_backend)
    with readiness_tab:
        _render_production_readiness(
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
            storage=storage,
            principal=principal,
            engagement_id=engagement_id,
        )
    with audit_tab:
        _render_audit(manifest, commercial_run)
