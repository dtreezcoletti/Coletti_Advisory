from __future__ import annotations

import base64
import json
import os
from uuid import uuid4

import streamlit as st

from .auth import demo_principal, require_authenticated_principal
from .core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from .intake import ingest_file
from .models import Permission
from .security import SECURITY_CONTROLS, validate_runtime
from .storage import EncryptedLocalDemoStorage, GoogleCloudEncryptedStorage, decode_master_key
from .synthetic import SYNTHETIC_ENGAGEMENT


def _secret(name: str, default: str = "") -> str:
    return str(st.secrets.get(name, os.environ.get(name, default)))


def _runtime():
    app_mode = _secret("APP_MODE", "demo").lower()
    storage_backend = _secret("STORAGE_BACKEND", "local_demo").lower()
    core_backend = _secret("COLETTIOS_BACKEND", "synthetic").lower()
    session_ttl = int(_secret("SESSION_TTL_MINUTES", "480"))
    principal = require_authenticated_principal(app_mode=app_mode, session_ttl_minutes=session_ttl)
    if principal is None:
        principal = demo_principal()

    if "_coletti_core" not in st.session_state:
        if core_backend == "http":
            st.session_state["_coletti_core"] = HttpColettiOSAdapter(
                _secret("COLETTIOS_API_URL"), _secret("COLETTIOS_API_TOKEN")
            )
        else:
            st.session_state["_coletti_core"] = SyntheticCoreAdapter()

    if "_coletti_storage" not in st.session_state:
        key_value = _secret("STORAGE_MASTER_KEY")
        if not key_value and app_mode == "demo":
            key_value = base64.urlsafe_b64encode(os.urandom(32)).decode()
            st.session_state["_demo_storage_key"] = key_value
        key = decode_master_key(key_value)
        if storage_backend == "gcs":
            st.session_state["_coletti_storage"] = GoogleCloudEncryptedStorage(
                bucket_name=_secret("GCS_BUCKET"),
                service_account_json=_secret("GCP_SERVICE_ACCOUNT_JSON"),
                master_key=key,
            )
        else:
            st.session_state["_coletti_storage"] = EncryptedLocalDemoStorage(".secure_store", key)

    errors = validate_runtime(
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if errors:
        st.error("Production security gate is closed.")
        for error in errors:
            st.write(f"• {error}")
        st.stop()
    return app_mode, storage_backend, core_backend, principal, st.session_state["_coletti_core"], st.session_state["_coletti_storage"]


def _identity_panel(principal, engagement_id: str):
    if principal.authenticated:
        st.sidebar.success(f"Authenticated as: {principal.display_name}")
        st.sidebar.caption(f"Role: {principal.role.value.replace('_', ' ').title()}")
    else:
        st.sidebar.info("Synthetic demo session — no client identity or client data")
    st.sidebar.caption(f"Authorized workspace: {engagement_id}")
    if principal.authenticated and st.sidebar.button("Log out"):
        st.logout()


def run() -> None:
    st.set_page_config(page_title="Coletti & Co. | ColettiOS", page_icon="◈", layout="wide")
    app_mode, storage_backend, core_backend, principal, core, storage = _runtime()

    engagement_id = principal.engagement_ids[0]
    engagement_name = SYNTHETIC_ENGAGEMENT["name"] if engagement_id == "eng-synthetic-demo" else engagement_id
    _identity_panel(principal, engagement_name)

    page = st.sidebar.radio(
        "Workspace",
        ["Command Center", "Engagements", "Intake", "Evidence", "Review Center", "Analysis", "Reports", "Administration"],
    )
    manifest = core.manifest(engagement_id)

    if page == "Command Center":
        st.title("Coletti & Co.")
        st.caption("Commercial interface powered by ColettiOS contracts")
        if app_mode == "demo":
            st.warning("SYNTHETIC DEMO ONLY — do not upload real client, legal, medical, financial, or identifying records.")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sources", len(manifest.get("sources", {})))
        c2.metric("Propositions", len(manifest.get("propositions", {})))
        c3.metric("Contradictions", len(manifest.get("contradictions", {})))
        c4.metric("Open escalations", len(manifest.get("escalations", {})))
        st.subheader("Current operating boundary")
        st.write("Records → traceable propositions → conflicts/gaps → human review → auditable output.")

    elif page == "Engagements":
        st.title("Engagements")
        st.dataframe([{"Workspace": engagement_name, "ID": engagement_id, "Status": "ACTIVE"}], use_container_width=True)

    elif page == "Intake":
        st.title("Secure Intake")
        if app_mode == "demo":
            st.info("Demo uploads are AES-256-GCM encrypted on ephemeral local storage and may disappear on restart.")
        classification = st.selectbox("Document classification", ["Operational Audit", "Business Record", "Financial Record", "Correspondence", "Other"])
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
        st.title("Evidence Workspace")
        sources = list(manifest.get("sources", {}).values())
        st.subheader("Sources")
        st.dataframe(sources, use_container_width=True)
        st.subheader("Propositions")
        st.dataframe(list(manifest.get("propositions", {}).values()), use_container_width=True)
        st.subheader("Contradictions")
        st.dataframe(list(manifest.get("contradictions", {}).values()), use_container_width=True)

    elif page == "Review Center":
        st.title("Review Center")
        st.subheader("Open escalations")
        st.dataframe(list(manifest.get("escalations", {}).values()), use_container_width=True)
        st.caption("ColettiOS preserves conflicts until a documented human resolution occurs.")

    elif page == "Analysis":
        st.title("Analysis")
        st.write("Financial reconstruction, timelines, relationship analysis, and record comparisons attach here through released ColettiOS interfaces.")
        st.json({"source_states": manifest.get("source_states", {})})

    elif page == "Reports":
        st.title("Reports")
        export = json.dumps(manifest, indent=2, default=str)
        st.download_button("Download evidence manifest", export, file_name="colettios_synthetic_manifest.json", mime="application/json")
        st.caption("Reports distinguish record-derived observations from professional determinations.")

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
