from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from . import supabase_auth
from .models import Role


_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "WORKING_DRAFT": ("DRAFT",),
    "DRAFT": ("MASTER", "RETIRED"),
    "MASTER": ("SUPERSEDED", "RETIRED"),
}


def _allowed_targets(state: str) -> tuple[str, ...]:
    return _ALLOWED_TRANSITIONS.get(str(state or "").strip().upper(), ())


def _documents(snapshot: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, Mapping):
        return []
    raw = snapshot.get("documents")
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _load_snapshot() -> dict[str, Any]:
    token = supabase_auth.current_access_token()
    if not token:
        raise PermissionError("An authenticated Owner session is required for the Docket.")
    payload = supabase_auth._rpc("owner_docket_snapshot", access_token=token, payload={})
    if not isinstance(payload, dict):
        raise PermissionError("Supabase returned an invalid Docket snapshot.")
    return dict(payload)


def _transition(document_key: str, target_state: str, reason: str) -> dict[str, Any]:
    token = supabase_auth.current_access_token()
    if not token:
        raise PermissionError("An authenticated Owner session is required for Docket transitions.")
    payload = supabase_auth._rpc(
        "owner_docket_transition",
        access_token=token,
        payload={
            "p_document_key": document_key,
            "p_target_state": target_state,
            "p_reason": reason,
        },
    )
    if not isinstance(payload, dict):
        raise PermissionError("Supabase returned an invalid Docket transition result.")
    return dict(payload)


def render_owner_docket(principal) -> None:
    st.title("Docket")
    st.caption("Controlled governance documents · Owner review and state transitions")

    if getattr(principal, "role", None) != Role.OWNER:
        st.error("The Docket is Owner-only.")
        st.stop()

    try:
        snapshot = _load_snapshot()
    except Exception as exc:
        st.error("The authoritative Docket could not be loaded from Supabase.")
        st.caption(str(exc))
        return

    documents = _documents(snapshot)
    state_counts = snapshot.get("state_counts") if isinstance(snapshot.get("state_counts"), Mapping) else {}
    cols = st.columns(4)
    for index, state in enumerate(("WORKING_DRAFT", "DRAFT", "MASTER", "RETIRED")):
        cols[index].metric(state.replace("_", " ").title(), int(state_counts.get(state, 0) or 0))

    st.info(
        "Docket state changes are human decisions. ColettiOS may display the available transition, "
        "but it does not promote governance documents on its own."
    )

    if not documents:
        st.caption("No Docket documents are currently recorded.")
        return

    for document in documents:
        key = str(document.get("document_key") or "").strip()
        title = str(document.get("title") or key or "Untitled document")
        state = str(document.get("document_state") or "UNKNOWN").upper()
        version = str(document.get("version") or "—")
        authority = str(document.get("authority") or "—")
        updated_at = str(document.get("updated_at") or "—")

        with st.expander(f"{title} · {state}", expanded=state in {"WORKING_DRAFT", "DRAFT"}):
            left, right = st.columns([2, 1])
            with left:
                st.write(f"**Document key:** `{key}`")
                st.write(f"**Authority:** {authority}")
            with right:
                st.write(f"**Version:** {version}")
                st.write(f"**Updated:** {updated_at}")

            targets = _allowed_targets(state)
            if not targets or not key:
                st.caption("No Owner transition is available from the current state.")
                continue

            target = st.selectbox(
                "Target state",
                targets,
                key=f"docket-target:{key}",
            )
            reason = st.text_input(
                "Reason for transition",
                key=f"docket-reason:{key}",
                placeholder="Required human reason",
            )
            if st.button(
                f"Move to {target}",
                key=f"docket-transition:{key}:{target}",
                type="primary",
                disabled=not reason.strip(),
            ):
                try:
                    result = _transition(key, target, reason.strip())
                except Exception as exc:
                    st.error("The Docket transition was rejected. No state was changed through this screen.")
                    st.caption(str(exc))
                else:
                    st.success(
                        f"{result.get('document_key', key)} is now {result.get('document_state', target)}."
                    )
                    st.rerun()
