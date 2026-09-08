from __future__ import annotations

import streamlit as st

from coletti_advisory import main as app
from coletti_advisory.commercial_config import DEFAULT_COMMERCIAL_CONFIG
from coletti_advisory.mobile_mvp import render_mobile_companion, require_mobile_staff
from coletti_advisory.workspaces import live_workspace_gate_errors


def run() -> None:
    st.set_page_config(
        page_title="Coletti Mobile | ColettiOS",
        page_icon="◈",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    app_mode, storage_backend, core_backend, principal, core, storage, _publication_store = app._runtime()

    try:
        require_mobile_staff(principal)
    except PermissionError as exc:
        st.error(str(exc))
        st.caption("Coletti Mobile owner/employee MVP is disabled for demo, client, and unauthenticated sessions.")
        st.stop()

    engagement_id = app._identity_panel(principal)
    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if gate_errors:
        st.error("Coletti Mobile is locked until the existing workspace security gate passes.")
        for error in gate_errors:
            st.write(f"• {error}")
        st.stop()

    manifest = core.manifest(engagement_id)
    render_mobile_companion(
        principal=principal,
        engagement_id=engagement_id,
        manifest=manifest,
        classifications=DEFAULT_COMMERCIAL_CONFIG.source_classifications,
        ingest_file=app.ingest_file,
        storage=storage,
        core=core,
    )


if __name__ == "__main__":
    run()
