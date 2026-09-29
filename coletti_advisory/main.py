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
from .supabase_auth import current_access_token
from .commercial_config import DEFAULT_COMMERCIAL_CONFIG
from .core_adapter import HttpColettiOSAdapter, SyntheticCoreAdapter
from .intake import ingest_file
from .models import Permission
from .publication import (
    EncryptedLocalPublicationStore,
    SupabasePublicationStore,
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
from .storage import EncryptedLocalDemoStorage, SupabaseEncryptedStorage, decode_master_key
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
    app_mode = _secret("APP_MODE", "production").lower()
    storage_backend = _secret("STORAGE_BACKEND", "supabase").lower()
    core_backend = _secret("COLETTIOS_BACKEND", "http").lower()
    session_ttl_raw = _secret("SESSION_TTL_MINUTES", "480")

    production_config = {
        "SUPABASE_URL": _secret("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": _secret("SUPABASE_ANON_KEY"),
        "SUPABASE_STORAGE_BUCKET": _secret("SUPABASE_STORAGE_BUCKET", "client-documents"),
        "STORAGE_MASTER_KEY": _secret("STORAGE_MASTER_KEY"),
        "COLETTIOS_API_URL": _secret("COLETTIOS_API_URL"),
        "COLETTIOS_API_TOKEN": _secret("COLETTIOS_API_TOKEN"),
        "SESSION_TTL_MINUTES": session_ttl_raw,
    }
    preflight_errors = validate_production_configuration(app_mode=app_mode, config=production_config)
    if preflight_errors:
        _show_gate_errors(preflight_errors)

    try:
        session_ttl = int(session_ttl_raw)
    except ValueError:
        _show_gate_errors(["SESSION_TTL_MINUTES must be an integer"])

    principal = require_authenticated_principal(
        app_mode=app_mode,
        session_ttl_minutes=session_ttl,
    )
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
    access_token = current_access_token()
    if app_mode == "production" and not access_token:
        _show_gate_errors(["Supabase Auth access token is required for production storage"])

    if "_coletti_core" not in st.session_state:
        if core_backend == "http":
            st.session_state["_coletti_core"] = HttpColettiOSAdapter(
                production_config["COLETTIOS_API_URL"], production_config["COLETTIOS_API_TOKEN"]
            )
        else:
            st.session_state["_coletti_core"] = SyntheticCoreAdapter()

    if "_coletti_storage" not in st.session_state:
        if storage_backend == "supabase":
            storage = SupabaseEncryptedStorage(
                supabase_url=production_config["SUPABASE_URL"],
                access_token=access_token or "",
                bucket_name=production_config["SUPABASE_STORAGE_BUCKET"],
                master_key=key,
            )
            storage.set_anon_key(production_config["SUPABASE_ANON_KEY"])
            st.session_state["_coletti_storage"] = storage
        else:
            st.session_state["_coletti_storage"] = EncryptedLocalDemoStorage(".secure_store", key)

    if "_coletti_publication_store" not in st.session_state:
        if storage_backend == "supabase":
            st.session_state["_coletti_publication_store"] = SupabasePublicationStore(
                supabase_url=production_config["SUPABASE_URL"],
                anon_key=production_config["SUPABASE_ANON_KEY"],
                access_token=access_token or "",
                bucket_name="published-reports",
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

