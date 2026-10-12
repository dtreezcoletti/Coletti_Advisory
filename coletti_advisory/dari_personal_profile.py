from __future__ import annotations

"""Owner-controlled DOMUS profile editor. No institutional or employee memory writes."""

import re
from typing import Any

import requests
import streamlit as st

from . import supabase_auth
from .models import Role

CATEGORIES = {
    "How I work": "WORK_RHYTHM",
    "Communication preferences": "COMMUNICATION",
    "Decision support": "DECISION_SUPPORT",
    "Boundaries and permissions": "BOUNDARIES",
    "Personal goals": "PERSONAL_GOALS",
}


def profile_key_from_title(title: str) -> str:
    """Deterministic key: proposing the same title requests a replacement review."""
    slug = re.sub(r"[^a-z0-9]+", ".", title.strip().lower()).strip(".")
    if not slug:
        raise ValueError("Give this preference a short descriptive title")
    return "user." + slug[:90]


def _owner_token(principal: Any) -> str:
    if principal.role != Role.OWNER or not principal.authenticated:
        raise PermissionError("Only the signed-in Owner can manage this profile")
    token = supabase_auth.current_access_token()
    user = st.session_state.get("_coletti_supabase_user") or {}
    if not token or str(user.get("id") or "") != str(principal.user_id):
        raise PermissionError("The Owner Supabase session must match this workspace")
    return token


def _rpc(principal: Any, name: str, values: dict[str, Any]) -> Any:
    return supabase_auth._rpc(name, access_token=_owner_token(principal), payload=values)


def render_owner_learning(principal: Any, *, key_prefix: str) -> None:
    """Review private DARI working preferences in the existing Owner profile menu.

    Candidates are not reasoning context until the Owner clicks Confirm.
    Personal text is never sent to the institutional registry or Dispatcher.
    """
    if principal.role != Role.OWNER:
        return

    with st.expander("DARI · Getting to Know Me", expanded=False):
        st.caption(
            "Personal DARI (DOMUS). DARI may suggest ways to collaborate, "
            "but you control which preferences it remembers. "
            "These entries do not authorize business actions or policy changes."
        )
        if not principal.authenticated:
            st.info("Sign in to your Owner account to manage DARI's private profile.")
            return
        try:
            items = _rpc(principal, "dari_personal_profile_list_v1", {})
            if not isinstance(items, list):
                raise ValueError("Unexpected personal-profile response")
        except (PermissionError, requests.RequestException, ValueError):
            st.warning("DARI's private profile is unavailable in this session.")
            return

        with st.form(f"{key_prefix}:dari-new", clear_on_submit=True):
            title = st.text_input(
                "Preference title",
                placeholder="How to challenge my business decisions",
                max_chars=90,
            )
            category_label = st.selectbox(
                "Category",
                list(CATEGORIES),
                index=2,
            )
            statement = st.text_area(
                "What should DARI know about how to work with you?",
                placeholder="Present alternatives, costs, and uncertainties; leave the final choice to me.",
                max_chars=1800,
            )
            propose = st.form_submit_button("Propose for my review", type="primary")

        if propose:
            try:
                key = profile_key_from_title(title)
                if not statement.strip():
                    raise ValueError("A preference statement is required")
                _rpc(
                    principal,
                    "dari_personal_profile_propose_v1",
                    {
                        "p_key": key,
                        "p_statement": statement.strip(),
                        "p_category": CATEGORIES[category_label],
                        "p_basis": "USER_DIRECT",
                        "p_provenance_ref": None,
                    },
                )
            except ValueError as exc:
                st.error(str(exc))
            except (PermissionError, requests.RequestException):
                st.error("The proposal could not be saved.")
            else:
                st.success("Saved as a candidate. Confirm it before DARI can use it.")
                st.rerun()

        if not items:
            st.caption("No stored DARI preferences yet.")
            return

        st.markdown("**Review what DARI has learned**")
        for entry in items:
            learning_id = str(entry.get("learning_id") or "")
            state = str(entry.get("status") or "")
            if not learning_id:
                continue
            st.markdown(f"**{entry.get('profile_key', 'Preference')}** · {state.title()}")
            st.write(str(entry.get("statement") or ""))
            st.caption(
                f"{str(entry.get('category') or '').replace('_', ' ').title()} · "
                f"{str(entry.get('basis') or '').replace('_', ' ').title()}"
            )
            action: str | None = None
            if state == "CANDIDATE":
                yes, no = st.columns(2)
                if yes.button("Confirm", key=f"{key_prefix}:{learning_id}:confirm"):
                    action = "CONFIRM"
                if no.button("Reject", key=f"{key_prefix}:{learning_id}:reject"):
                    action = "REJECT"
            elif state == "CONFIRMED":
                if st.button("Retire", key=f"{key_prefix}:{learning_id}:retire"):
                    action = "RETIRE"
            if action:
                try:
                    _rpc(principal, "dari_personal_profile_review_v1", {
                        "p_learning_id": learning_id, "p_action": action
                    })
                except (PermissionError, requests.RequestException):
                    st.error("Review could not be saved.")
                else:
                    st.rerun()

            delete_key = f"{key_prefix}:{learning_id}:delete-requested"
            if st.button("Delete this entry", key=f"{key_prefix}:{learning_id}:delete"):
                st.session_state[delete_key] = True
            if st.session_state.get(delete_key):
                st.caption("Deleting removes the preference text; minimal action metadata remains.")
                if st.button(
                    "Confirm permanent deletion",
                    key=f"{key_prefix}:{learning_id}:delete-confirm",
                ):
                    try:
                        _rpc(principal, "dari_personal_profile_review_v1", {
                            "p_learning_id": learning_id, "p_action": "DELETE"
                        })
                    except (PermissionError, requests.RequestException):
                        st.error("Deletion could not be completed.")
                    else:
                        st.session_state.pop(delete_key, None)
                        st.rerun()
            st.divider()

        st.caption(
            "Only confirmed entries are eligible for the future DARI reasoning context. "
            "Highly sensitive personal details should not be entered until separate "
            "encrypted-vault controls are verified."
        )
