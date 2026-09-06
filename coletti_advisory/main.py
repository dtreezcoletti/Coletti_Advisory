from __future__ import annotations

import base64
import json
import os

import streamlit as st

from .analysis import (
    build_analytical_issues,
    build_cross_record_comparison,
    build_operations_reconstruction,
    build_records_reconstruction,
    build_state_counts,
    build_summary,
)
from .auth import demo_principal, require_authenticated_principal
from .commercial_config import DEFAULT_COMMERCIAL_CONFIG
from .core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from .intake import ingest_file
from .models import Permission
from .publication import (
    EncryptedLocalPublicationStore,
    GoogleCloudPublicationStore,
    PublicationStatus,
    approve_report,
    publish_report,
    published_reports,
    revoke_report,
    send_to_review,
    sync_drafts,
)
from .reporting import build_publication_gate, build_report_bundle
from .security import SECURITY_CONTROLS, validate_production_configuration, validate_runtime
from .storage import EncryptedLocalDemoStorage, GoogleCloudEncryptedStorage, decode_master_key
from .synthetic import SYNTHETIC_ENGAGEMENT


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        value = os.environ.get(name, default)
    return str(value)


def _show_gate_errors(errors: list[str]) -> None:
    st.error("Production security gate is closed.")
    for error in errors:
        st.write(f"• {error}")
    st.stop()


def _master_key(app_mode: str, configured_value: str) -> bytes:
    key_value = configured_value
    if not key_value and app_mode == "demo":
        key_value = str(st.session_state.get("_demo_storage_key") or "")
        if not key_value:
            key_value = base64.urlsafe_b64encode(os.urandom(32)).decode()
            st.session_state["_demo_storage_key"] = key_value
    return decode_master_key(key_value)


def _runtime():
    app_mode = _secret("APP_MODE", "demo").lower()
    storage_backend = _secret("STORAGE_BACKEND", "local_demo").lower()
    core_backend = _secret("COLETTIOS_BACKEND", "synthetic").lower()
    session_ttl_raw = _secret("SESSION_TTL_MINUTES", "480")

    production_config = {
        "GCS_BUCKET": _secret("GCS_BUCKET"),
        "GCP_SERVICE_ACCOUNT_JSON": _secret("GCP_SERVICE_ACCOUNT_JSON"),
        "STORAGE_MASTER_KEY": _secret("STORAGE_MASTER_KEY"),
        "COLETTIOS_API_URL": _secret("COLETTIOS_API_URL"),
        "COLETTIOS_API_TOKEN": _secret("COLETTIOS_API_TOKEN"),
        "AUTHZ_REGISTRY_JSON": _secret("AUTHZ_REGISTRY_JSON"),
        "SESSION_TTL_MINUTES": session_ttl_raw,
    }
    preflight_errors = validate_production_configuration(app_mode=app_mode, config=production_config)
    if preflight_errors:
        _show_gate_errors(preflight_errors)

    try:
        session_ttl = int(session_ttl_raw)
    except ValueError:
        if app_mode == "production":
            _show_gate_errors(["SESSION_TTL_MINUTES must be an integer"])
        session_ttl = 480

    principal = require_authenticated_principal(app_mode=app_mode, session_ttl_minutes=session_ttl)
    if principal is None:
        principal = demo_principal()

    runtime_errors = validate_runtime(
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if runtime_errors:
        _show_gate_errors(runtime_errors)

    key = _master_key(app_mode, production_config["STORAGE_MASTER_KEY"])

    if "_coletti_core" not in st.session_state:
        if core_backend == "http":
            st.session_state["_coletti_core"] = HttpColettiOSAdapter(
                production_config["COLETTIOS_API_URL"], production_config["COLETTIOS_API_TOKEN"]
            )
        else:
            st.session_state["_coletti_core"] = SyntheticCoreAdapter()

    if "_coletti_storage" not in st.session_state:
        if storage_backend == "gcs":
            st.session_state["_coletti_storage"] = GoogleCloudEncryptedStorage(
                bucket_name=production_config["GCS_BUCKET"],
                service_account_json=production_config["GCP_SERVICE_ACCOUNT_JSON"],
                master_key=key,
            )
        else:
            st.session_state["_coletti_storage"] = EncryptedLocalDemoStorage(".secure_store", key)

    if "_coletti_publication_store" not in st.session_state:
        if storage_backend == "gcs":
            st.session_state["_coletti_publication_store"] = GoogleCloudPublicationStore(
                bucket_name=production_config["GCS_BUCKET"],
                service_account_json=production_config["GCP_SERVICE_ACCOUNT_JSON"],
                master_key=key,
            )
        else:
            st.session_state["_coletti_publication_store"] = EncryptedLocalPublicationStore(
                ".secure_store", key
            )

    return (
        app_mode,
        storage_backend,
        core_backend,
        principal,
        st.session_state["_coletti_core"],
        st.session_state["_coletti_storage"],
        st.session_state["_coletti_publication_store"],
    )


def _workspace_label(engagement_id: str) -> str:
    if engagement_id == SYNTHETIC_ENGAGEMENT["engagement_id"]:
        return SYNTHETIC_ENGAGEMENT["name"]
    return engagement_id


def _identity_panel(principal) -> str:
    if principal.authenticated:
        st.sidebar.success(f"Authenticated as: {principal.display_name}")
        st.sidebar.caption(f"Role: {principal.role.value.replace('_', ' ').title()}")
    else:
        st.sidebar.info("Synthetic demo session — no client identity or client data")

    options = list(principal.engagement_ids)
    selected = st.sidebar.selectbox(
        "Authorized workspace",
        options,
        format_func=_workspace_label,
    )
    if not principal.can_access(selected):
        st.error("Workspace authorization failed.")
        st.stop()

    if principal.authenticated and st.sidebar.button("Log out"):
        st.logout()
    return selected


def _workspace_pages(principal) -> list[str]:
    pages = ["Command Center", "Engagements"]
    if principal.can(Permission.UPLOAD):
        pages.append("Intake")
    if principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW):
        pages.append("Evidence")
    if principal.can(Permission.REVIEW):
        pages.append("Review Center")
    if principal.can(Permission.ANALYZE):
        pages.append("Analysis")
    pages.append("Reports")
    if principal.can(Permission.MANAGE_USERS):
        pages.append("Administration")
    return pages


def _show_table(rows: list[dict], *, empty_message: str) -> None:
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)


def _save_publication_records(store, principal, engagement_id: str, records) -> None:
    store.save(
        organization_id=principal.organization_id,
        engagement_id=engagement_id,
        records=records,
    )


def _load_publication_records(store, principal, engagement_id: str):
    return store.load(
        organization_id=principal.organization_id,
        engagement_id=engagement_id,
    )


def _render_analysis(manifest: dict) -> None:
    st.title("Analysis")
    st.caption("Internal reconstruction workspace · source-linked · human-reviewed · not a licensed professional determination")

    summary = build_summary(manifest)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources reviewed", summary["sources"])
    c2.metric("Record propositions", summary["propositions"])
    c3.metric("Inconsistencies", summary["inconsistencies"])
    c4.metric("Open issues", summary["open_issues"])

    st.subheader("Reconstruction Overview")
    _show_table(
        build_state_counts(manifest),
        empty_message="No evidence-state data is available for this engagement yet.",
    )

    records_tab, operations_tab, comparison_tab, issues_tab = st.tabs(
        ["Records Reconstruction", "Operations Reconstruction", "Cross-Record Comparison", "Analytical Issues"]
    )

    with records_tab:
        st.caption("Record-derived propositions with their supporting source IDs, filenames, evidence states, and review status.")
        _show_table(
            build_records_reconstruction(manifest),
            empty_message="No record-derived propositions have been created yet.",
        )

    with operations_tab:
        st.caption(
            "Operational record inputs and unresolved follow-ups. This view does not infer process deviations unless the records support them."
        )
        _show_table(
            build_operations_reconstruction(manifest),
            empty_message="No operational record inputs are available yet.",
        )

    with comparison_tab:
        st.caption("Side-by-side record statements where the current evidence set identifies a conflict requiring review.")
        _show_table(
            build_cross_record_comparison(manifest),
            empty_message="No cross-record inconsistencies are currently recorded.",
        )

    with issues_tab:
        st.caption("Issues are classified without converting them into legal, accounting, investigative, or other licensed conclusions.")
        _show_table(
            build_analytical_issues(manifest),
            empty_message="No analytical issues are currently open.",
        )


def _render_review_center(manifest: dict, reports: dict, records: dict, store, principal, engagement_id: str) -> None:
    st.title("Review Center")
    st.caption("Human review sits between internal analysis and any client-facing report publication.")

    issues = build_analytical_issues(manifest)
    gate = build_publication_gate(manifest)

    c1, c2, c3 = st.columns(3)
    c1.metric("Analytical issues", len(issues))
    c2.metric("Verification routes", gate["verification_recommendation_count"])
    c3.metric("Reports published", len(published_reports(records)))

    st.subheader("Analytical Review Queue")
    _show_table(issues, empty_message="No analytical issues are currently awaiting review.")

    st.subheader("Open ColettiOS Escalations")
    _show_table(
        list((manifest.get("escalations") or {}).values()),
        empty_message="No ColettiOS escalations are currently open.",
    )

    st.subheader("Report Approval & Publishing")
    st.caption(
        "Open issues may remain documented in a report. Publication requires an explicit reviewer decision that those issues, boundaries, and verification routes are accurately presented."
    )

    for report_name, report in reports.items():
        record = records[report_name]
        with st.expander(f"{report_name} · {record.status.value} · Revision {record.revision}", expanded=True):
            st.write(f"Current draft fingerprint: `{record.draft_hash[:16]}…`")
            if record.published_snapshot is not None:
                st.success(
                    f"A prior client snapshot exists from {record.published_at or 'an earlier publication'}. "
                    "It remains frozen unless explicitly revoked or replaced by a newly approved publication."
                )

            if record.status in {PublicationStatus.DRAFT, PublicationStatus.REVOKED}:
                note = st.text_input(
                    "Review note",
                    value=record.review_note or "",
                    key=f"review-note-{report_name}",
                    placeholder="Optional note for the review record",
                )
                if st.button("Send to Review", key=f"send-review-{report_name}"):
                    send_to_review(record, actor=principal.user_id, note=note)
                    _save_publication_records(store, principal, engagement_id, records)
                    st.rerun()

            elif record.status == PublicationStatus.IN_REVIEW:
                if record.reviewed_at:
                    st.caption(f"Review opened by {record.reviewed_by} at {record.reviewed_at}")
                acknowledged = st.checkbox(
                    "I reviewed the source-linked analysis, unresolved issues, service boundaries, and verification/referral guidance for this report.",
                    key=f"ack-{report_name}",
                )
                if st.button("Approve Report", disabled=not acknowledged, key=f"approve-{report_name}"):
                    approve_report(record, actor=principal.user_id)
                    _save_publication_records(store, principal, engagement_id, records)
                    st.rerun()

            elif record.status == PublicationStatus.APPROVED:
                st.success(f"Approved by {record.approved_by} at {record.approved_at}")
                st.warning("Publishing creates a frozen client-visible snapshot. Later evidence will create a new draft revision rather than mutate this release.")
                if st.button("Publish to Client", type="primary", key=f"publish-{report_name}"):
                    publish_report(record, actor=principal.user_id, report=report)
                    _save_publication_records(store, principal, engagement_id, records)
                    st.rerun()

            elif record.status == PublicationStatus.PUBLISHED:
                st.success(f"Published by {record.published_by} at {record.published_at}")
                if st.button("Revoke Client Publication", key=f"revoke-{report_name}"):
                    revoke_report(record, actor=principal.user_id)
                    _save_publication_records(store, principal, engagement_id, records)
                    st.rerun()

    st.caption(gate["rule"])


def _render_report_section(title: str, value) -> None:
    st.subheader(title)
    if isinstance(value, list):
        _show_table(value, empty_message=f"No {title.lower()} are available in this report.")
    elif isinstance(value, dict):
        if value:
            st.json(value)
        else:
            st.info(f"No {title.lower()} are available in this report.")
    else:
        st.write(value)


def _render_internal_reports(manifest: dict, reports: dict, records: dict) -> None:
    st.title("Reports")
    st.caption("Controlled report drafting · populated from the shared analysis layer · client publication remains gated")

    gate = build_publication_gate(manifest)
    published_count = len(published_reports(records))

    c1, c2, c3 = st.columns(3)
    c1.metric("Report drafts", len(reports))
    c2.metric("Items requiring review", gate["review_required_count"])
    c3.metric("Client-visible reports", published_count)

    tabs = st.tabs(list(reports.keys()))
    for tab, (report_name, report) in zip(tabs, reports.items()):
        record = records[report_name]
        with tab:
            st.subheader(report_name)
            st.caption(f"Current workflow state: {record.status.value} · Revision {record.revision}")
            if record.published_snapshot is not None:
                st.info("The client currently has a frozen published snapshot. This working draft may be newer and will not replace it until reviewed and published.")
            else:
                st.warning("No client-visible version has been published yet.")

            st.write(report["purpose"])
            st.info(report["boundary"])

            for key, value in report.items():
                if key in {"report_type", "document_status", "purpose", "boundary"}:
                    continue
                _render_report_section(key.replace("_", " ").title(), value)

            export = json.dumps(report, indent=2, default=str)
            safe_name = report_name.lower().replace(" ", "_") + f"_rev_{record.revision}_draft.json"
            st.download_button(
                f"Download {report_name} draft",
                export,
                file_name=safe_name,
                mime="application/json",
                key=f"download-{safe_name}",
            )

    with st.expander("Publishing gate details"):
        st.json(gate)


def _render_client_reports(records: dict) -> None:
    st.title("Reports")
    st.caption("Client-facing report delivery · published versions only")
    published = published_reports(records)
    if not published:
        st.info("No reports have been published to this workspace yet.")
        return

    tabs = st.tabs(list(published.keys()))
    for tab, (report_name, report) in zip(tabs, published.items()):
        with tab:
            st.subheader(report_name)
            publication = report.get("publication") or {}
            if publication:
                st.caption(
                    f"Published revision {publication.get('revision', '—')} · {publication.get('published_at', 'publication time unavailable')}"
                )
            st.info(report.get("boundary", "Published report"))
            for key, value in report.items():
                if key in {"report_type", "document_status", "purpose", "boundary", "publication"}:
                    continue
                _render_report_section(key.replace("_", " ").title(), value)
            export = json.dumps(report, indent=2, default=str)
            safe_name = report_name.lower().replace(" ", "_") + "_published.json"
            st.download_button(
                f"Download {report_name}",
                export,
                file_name=safe_name,
                mime="application/json",
                key=f"client-download-{safe_name}",
            )


def _render_internal_command_center(manifest: dict, reports: dict, records: dict) -> None:
    summary = build_summary(manifest)
    gate = build_publication_gate(manifest)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources", summary["sources"])
    c2.metric("Propositions", summary["propositions"])
    c3.metric("Inconsistencies", summary["inconsistencies"])
    c4.metric("Open issues", summary["open_issues"])

    st.subheader("Engagement Workflow")
    w1, w2, w3, w4, w5, w6 = st.columns(6)
    w1.metric("1 · Intake", summary["sources"])
    w2.metric("2 · Evidence", summary["propositions"])
    w3.metric("3 · Analysis", summary["inconsistencies"])
    w4.metric("4 · Review", gate["review_required_count"])
    w5.metric("5 · Drafts", len(reports))
    w6.metric("6 · Published", len(published_reports(records)))
    st.caption("Intake → Evidence → Analysis → Human Review → Report Drafts → Publishing Gate → Client")

    st.subheader("Current operating boundary")
    st.write("Records → traceable propositions → conflicts/gaps → human review → auditable output.")


def _render_client_command_center(manifest: dict, records: dict) -> None:
    published_count = len(published_reports(records))
    c1, c2, c3 = st.columns(3)
    c1.metric("Records submitted", len(manifest.get("sources", {})))
    c2.metric("Reports available", published_count)
    c3.metric("Workspace", "Active")
    st.subheader("Engagement Status")
    st.write("Upload records → Coletti & Co. processing/review → published reports")
    st.caption("Internal propositions, analytical issues, reviewer notes, and draft reports are not exposed in the client workspace.")


def run() -> None:
    st.set_page_config(page_title="Coletti & Co. | ColettiOS", page_icon="◈", layout="wide")
    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = _runtime()

    engagement_id = _identity_panel(principal)
    page = st.sidebar.radio("Workspace", _workspace_pages(principal))
    manifest = core.manifest(engagement_id)

    internal_user = principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)
    reports = build_report_bundle(manifest) if internal_user else {}
    records = _load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = sync_drafts(records, reports)
        _save_publication_records(publication_store, principal, engagement_id, records)

    if page == "Command Center":
        st.title("Coletti & Co.")
        st.caption("Commercial interface powered by ColettiOS contracts")
        if app_mode == "demo":
            st.warning("SYNTHETIC DEMO ONLY — do not upload real client, legal, medical, financial, or identifying records.")
        if internal_user:
            _render_internal_command_center(manifest, reports, records)
        else:
            _render_client_command_center(manifest, records)

    elif page == "Engagements":
        st.title("Engagements")
        rows = [{"Workspace": _workspace_label(eid), "ID": eid, "Status": "ACTIVE"} for eid in principal.engagement_ids]
        st.dataframe(rows, use_container_width=True)

    elif page == "Intake":
        if not principal.can(Permission.UPLOAD):
            st.error("Your role does not permit source uploads.")
            st.stop()
        st.title("Secure Intake")
        if app_mode == "demo":
            st.info("Demo uploads are AES-256-GCM encrypted on ephemeral local storage and may disappear on restart. Use synthetic files only.")
        classification = st.selectbox(
            "Source classification",
            list(DEFAULT_COMMERCIAL_CONFIG.source_classifications),
        )
        uploaded = st.file_uploader("Upload a source record")
        if st.button("Register source", type="primary", disabled=uploaded is None):
            result = ingest_file(
                principal=principal,
                engagement_id=engagement_id,
                filename=uploaded.name,
                data=uploaded.getvalue(),
                classification=classification,
                storage=storage,
                core=core,
            )
            st.success("Source intake completed")
            st.write("✓ Engagement authorization verified")
            st.write("✓ File encrypted before storage")
            st.write("✓ SHA-256 content hash generated")
            st.write(f"✓ Source {result['source']['source_id']} registered")
            st.write("✓ Audit actor recorded")
            st.rerun()

    elif page == "Evidence":
        if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)):
            st.error("Your role does not permit access to the internal evidence workspace.")
            st.stop()
        st.title("Evidence Workspace")
        st.subheader("Sources")
        st.dataframe(list(manifest.get("sources", {}).values()), use_container_width=True)
        st.subheader("Propositions")
        st.dataframe(list(manifest.get("propositions", {}).values()), use_container_width=True)
        st.subheader("Contradictions")
        st.dataframe(list(manifest.get("contradictions", {}).values()), use_container_width=True)

    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        _render_review_center(manifest, reports, records, publication_store, principal, engagement_id)

    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        _render_analysis(manifest)

    elif page == "Reports":
        if internal_user:
            _render_internal_reports(manifest, reports, records)
        else:
            _render_client_reports(records)

    elif page == "Administration":
        st.title("Administration & Security")
        if not principal.can(Permission.MANAGE_USERS):
            st.error("Your role does not permit administration.")
            st.stop()
        st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
        st.subheader("Authentication & Security Release Gate")
        for label, implemented in SECURITY_CONTROLS:
            st.write(f"{'✅' if implemented else '🔨'} {label}")
        st.subheader("Audit log")
        st.dataframe(manifest.get("audit_log", []), use_container_width=True)
