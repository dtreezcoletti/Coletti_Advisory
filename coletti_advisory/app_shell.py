from __future__ import annotations

from uuid import uuid4

import streamlit as st

from . import main as app
from .document_processing import extract_candidate_statements
from .models import Permission
from .system_lab import render_system_lab
from .workspaces import live_workspace_gate_errors, workspace_environment, workspace_label


def _workspace_pages(principal) -> list[str]:
    pages = app._workspace_pages(principal)
    if principal.can(Permission.MANAGE_USERS) and "System Lab" not in pages:
        try:
            admin_index = pages.index("Administration")
        except ValueError:
            admin_index = len(pages)
        pages.insert(admin_index, "System Lab")
    return pages


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
        format_func=workspace_label,
    )
    if not principal.can_access(selected):
        st.error("Workspace authorization failed.")
        st.stop()

    environment = workspace_environment(selected)
    if environment == "LIVE":
        st.sidebar.warning("LIVE workspace · real operational data")
    elif environment == "DEMO":
        st.sidebar.caption("DEMO workspace · synthetic data only")
    else:
        st.sidebar.caption("Authorized engagement workspace")

    if principal.authenticated and st.sidebar.button("Log out"):
        st.logout()
    return selected


def _intake_upload_key(generation: int) -> str:
    return f"secure-intake-upload-{generation}"


def _processing_queue() -> dict[str, dict]:
    return st.session_state.setdefault("_document_processing_queue", {})


def _render_secure_intake(*, app_mode, principal, engagement_id, storage, core) -> None:
    if not principal.can(Permission.UPLOAD):
        st.error("Your role does not permit source uploads.")
        st.stop()

    st.title("Secure Intake")
    if app_mode == "demo":
        st.info(
            "Demo uploads are AES-256-GCM encrypted on ephemeral local storage and may disappear on restart. "
            "Use synthetic files only."
        )
        st.warning(
            "Android/Chrome currently has a confirmed Streamlit file-picker timeout bug. For this synthetic test, "
            "choose the file promptly after opening the picker. If the tile turns red, use Reset upload control. "
            "System Lab → Clean Room can test the server-side intake path without the mobile picker."
        )

    last_intake = st.session_state.pop("_last_intake_result", None)
    if last_intake:
        st.success(f"Source intake completed · {last_intake['source_id']}")
        st.caption(
            f"Extraction: {last_intake['candidate_count']} candidate statement(s) queued for human review · "
            f"method: {last_intake['extraction_method']}"
        )
        for warning in last_intake.get("warnings", []):
            st.warning(warning)

    classification = st.selectbox(
        "Document classification",
        ["Operational Audit", "Business Record", "Financial Record", "Correspondence", "Other"],
    )

    generation = int(st.session_state.get("_intake_upload_generation", 0))
    upload_key = _intake_upload_key(generation)
    uploaded = st.file_uploader(
        "Upload a source record",
        key=upload_key,
        max_upload_size=200,
        help=(
            "If a mobile upload shows a red ! or stalls after returning from the Android file picker, "
            "tap Reset upload control and choose the file again."
        ),
    )

    reset_col, status_col = st.columns([1, 2])
    if reset_col.button("Reset upload control", key=f"reset-{upload_key}"):
        st.session_state["_intake_upload_generation"] = generation + 1
        st.rerun()

    if uploaded is None:
        status_col.caption(
            "Mobile recovery: if the file tile turns red, reset the upload control rather than refreshing the whole app."
        )
    else:
        status_col.success(f"Ready to register: {uploaded.name} · {uploaded.size / 1024:.1f} KB")

    if st.button("Register source", type="primary", disabled=uploaded is None):
        data = uploaded.getvalue()
        result = app.ingest_file(
            principal=principal,
            engagement_id=engagement_id,
            filename=uploaded.name,
            data=data,
            classification=classification,
            storage=storage,
            core=core,
        )
        extraction = extract_candidate_statements(uploaded.name, data)
        source_id = result["source"]["source_id"]
        _processing_queue()[source_id] = {
            "source_id": source_id,
            "filename": uploaded.name,
            **extraction.to_dict(),
        }
        st.session_state["_last_intake_result"] = {
            "source_id": source_id,
            "candidate_count": len(extraction.candidates),
            "extraction_method": extraction.extraction_method,
            "warnings": list(extraction.warnings),
        }
        st.session_state["_intake_upload_generation"] = generation + 1
        st.rerun()


def _render_extraction_review(*, principal, engagement_id: str, core) -> None:
    st.subheader("Extracted Statement Review")
    st.caption(
        "Extraction never becomes evidence automatically. An authorized analyst must explicitly promote a candidate "
        "before ColettiOS treats it as a source-linked proposition."
    )
    queue = _processing_queue()
    if not queue:
        st.info("No extracted statements are waiting for review in this session.")
        return

    source_id = st.selectbox(
        "Source awaiting review",
        list(queue.keys()),
        format_func=lambda value: f"{value} · {queue[value].get('filename', value)}",
        key="processing-source",
    )
    entry = queue[source_id]
    for warning in entry.get("warnings", []):
        st.warning(warning)

    candidates = entry.get("candidates") or []
    if not candidates:
        st.info("This source has no deterministic text candidates. Keep the source registered and route it for manual review/OCR as needed.")
        if st.button("Dismiss empty extraction queue", key=f"dismiss-{source_id}"):
            queue.pop(source_id, None)
            st.rerun()
        return

    st.dataframe(
        [
            {
                "Candidate": item["candidate_id"],
                "Locator": item["locator"],
                "Record-derived text": item["text"],
                "Method": item["extraction_method"],
            }
            for item in candidates
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not principal.can(Permission.ANALYZE):
        st.info("Your role may inspect extracted statements but cannot promote them to propositions.")
        return

    by_id = {item["candidate_id"]: item for item in candidates}
    selected = st.multiselect(
        "Promote selected candidates",
        list(by_id.keys()),
        format_func=lambda value: f"{by_id[value]['locator']} · {by_id[value]['text'][:100]}",
        key=f"promote-{source_id}",
    )
    acknowledged = st.checkbox(
        "I verified that the selected statements accurately reflect this source. Promotion creates source-linked Core propositions; it does not declare them independently true.",
        key=f"promote-ack-{source_id}",
    )
    if st.button(
        "Promote to propositions",
        type="primary",
        disabled=not selected or not acknowledged,
        key=f"promote-button-{source_id}",
    ):
        auth_context = principal.auth_context(engagement_id)
        for candidate_id in selected:
            candidate = by_id[candidate_id]
            proposition_id = f"PROP-{uuid4().hex[:12].upper()}"
            core.add_proposition(
                {
                    "proposition_id": proposition_id,
                    "text": f"[{candidate['locator']}] {candidate['text']}",
                    "source_ids": [source_id],
                },
                auth_context,
            )
        selected_set = set(selected)
        entry["candidates"] = [item for item in candidates if item["candidate_id"] not in selected_set]
        if not entry["candidates"]:
            queue.pop(source_id, None)
        st.rerun()


def _render_contradiction_reconciliation(*, principal, engagement_id: str, core, manifest: dict) -> None:
    st.subheader("Cross-Record Review")
    propositions = manifest.get("propositions") or {}
    contradictions = manifest.get("contradictions") or {}
    reconciliations = manifest.get("reconciliations") or {}

    if len(propositions) >= 2 and principal.can(Permission.REVIEW):
        proposition_ids = list(propositions.keys())
        left = st.selectbox("Proposition A", proposition_ids, key="contradiction-left")
        right_options = [value for value in proposition_ids if value != left]
        right = st.selectbox("Proposition B", right_options, key="contradiction-right")
        reason = st.text_area(
            "Why these record-derived propositions conflict",
            key="contradiction-reason",
            placeholder="Describe the specific inconsistency shown by the records.",
        )
        if st.button("Record contradiction", disabled=not reason.strip(), key="record-contradiction"):
            core.record_contradiction(
                {
                    "contradiction_id": f"CON-{uuid4().hex[:12].upper()}",
                    "proposition_a": left,
                    "proposition_b": right,
                    "reason": reason.strip(),
                },
                principal.auth_context(engagement_id),
            )
            st.rerun()
    else:
        st.caption("At least two propositions and review permission are required to record a contradiction.")

    st.markdown("**Recorded contradictions**")
    if contradictions:
        st.dataframe(list(contradictions.values()), use_container_width=True, hide_index=True)
    else:
        st.info("No contradictions are currently recorded.")

    if contradictions and principal.can(Permission.REVIEW):
        contradiction_id = st.selectbox("Contradiction to reconcile", list(contradictions.keys()), key="reconcile-contradiction")
        contradiction = contradictions[contradiction_id]
        related_props = [contradiction["proposition_a"], contradiction["proposition_b"]]
        outcome = st.text_input(
            "Reconciliation outcome",
            key="reconciliation-outcome",
            placeholder="Example: variance remains unresolved pending third-party confirmation",
        )
        rationale = st.text_area(
            "Reviewer rationale",
            key="reconciliation-rationale",
            placeholder="State what the record supports and what remains unresolved. Do not silently promote one source over another.",
        )
        acknowledged = st.checkbox(
            "I understand this is a reviewer reconciliation record, separate from the underlying source evidence.",
            key="reconciliation-ack",
        )
        if st.button(
            "Record reconciliation",
            disabled=not outcome.strip() or not rationale.strip() or not acknowledged,
            key="record-reconciliation",
        ):
            core.record_reconciliation(
                {
                    "reconciliation_id": f"REC-{uuid4().hex[:12].upper()}",
                    "proposition_ids": related_props,
                    "contradiction_ids": [contradiction_id],
                    "outcome": outcome.strip(),
                    "rationale": rationale.strip(),
                },
                principal.auth_context(engagement_id),
            )
            st.rerun()

    st.markdown("**Reviewer reconciliations**")
    if reconciliations:
        st.dataframe(list(reconciliations.values()), use_container_width=True, hide_index=True)
    else:
        st.caption("No reviewer reconciliation has been recorded yet.")


def _render_evidence_workspace(*, principal, engagement_id: str, core, manifest: dict) -> None:
    if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)):
        st.error("Your role does not permit access to the internal evidence workspace.")
        st.stop()

    st.title("Evidence Workspace")
    st.subheader("Sources")
    st.dataframe(list(manifest.get("sources", {}).values()), use_container_width=True)

    _render_extraction_review(principal=principal, engagement_id=engagement_id, core=core)

    st.subheader("Propositions")
    propositions = list((manifest.get("propositions") or {}).values())
    if propositions:
        st.dataframe(propositions, use_container_width=True, hide_index=True)
    else:
        st.info("No propositions have been promoted from source records yet.")

    _render_contradiction_reconciliation(
        principal=principal,
        engagement_id=engagement_id,
        core=core,
        manifest=manifest,
    )


def run() -> None:
    st.set_page_config(page_title="Coletti & Co. | ColettiOS", page_icon="◈", layout="wide")
    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = app._runtime()

    engagement_id = _identity_panel(principal)
    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if gate_errors:
        st.error("Coletti & Co. Live is configured but locked until the production gate is open.")
        for error in gate_errors:
            st.write(f"• {error}")
        st.stop()

    page = st.sidebar.radio("Workspace", _workspace_pages(principal))
    manifest = core.manifest(engagement_id)

    internal_user = principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)
    reports = app.build_report_bundle(manifest) if internal_user else {}
    records = app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = app.sync_drafts(records, reports)
        app._save_publication_records(publication_store, principal, engagement_id, records)

    if page == "Command Center":
        st.title("Coletti & Co.")
        st.caption("Commercial interface powered by ColettiOS contracts")
        environment = workspace_environment(engagement_id)
        if environment == "DEMO":
            st.warning("SYNTHETIC DEMO ONLY — do not upload real client, legal, medical, financial, or identifying records.")
        elif environment == "LIVE":
            st.success("LIVE WORKSPACE — authenticated production Core and durable encrypted storage are active.")
        if internal_user:
            app._render_internal_command_center(manifest, reports, records)
        else:
            app._render_client_command_center(manifest, records)

    elif page == "Engagements":
        st.title("Engagements")
        rows = [
            {
                "Workspace": workspace_label(eid),
                "Environment": workspace_environment(eid),
                "ID": eid,
                "Status": "ACTIVE",
            }
            for eid in principal.engagement_ids
        ]
        st.dataframe(rows, use_container_width=True)

    elif page == "Intake":
        _render_secure_intake(
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )

    elif page == "Evidence":
        _render_evidence_workspace(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
            manifest=manifest,
        )

    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)

    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        app._render_analysis(manifest)

    elif page == "Reports":
        if internal_user:
            app._render_internal_reports(manifest, reports, records)
        else:
            app._render_client_reports(records)

    elif page == "System Lab":
        render_system_lab(
            principal=principal,
            manifest=manifest,
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
            engagement_id=engagement_id,
        )

    elif page == "Administration":
        st.title("Administration & Security")
        if not principal.can(Permission.MANAGE_USERS):
            st.error("Your role does not permit administration.")
            st.stop()
        st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
        st.subheader("Authentication & Security Release Gate")
        for label, implemented in app.SECURITY_CONTROLS:
            st.write(f"{'✅' if implemented else '🔨'} {label}")
        st.subheader("Audit log")
        st.dataframe(manifest.get("audit_log", []), use_container_width=True)
