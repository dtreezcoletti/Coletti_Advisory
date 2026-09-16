from __future__ import annotations

from dataclasses import replace

import streamlit as st

from . import supabase_auth
from .models import Role
from .owner_private_nav import OWNER_PRIVATE_PAGES
from .owner_private_pages import render_private_page

OWNER_WORKSPACE_ID = "owner-private"


def patch_owner_identity_workspace() -> None:
    """Ensure an authenticated Owner has an owner workspace even with no case assignment."""
    original = supabase_auth._resolve_principal
    if getattr(original, "_owner_workspace_patched", False):
        return

    def wrapped(session):
        principal = original(session)
        if principal.role == Role.OWNER and not principal.engagement_ids:
            principal = replace(principal, engagement_ids=(OWNER_WORKSPACE_ID,))
        return principal

    wrapped._owner_workspace_patched = True
    supabase_auth._resolve_principal = wrapped


def patch_supabase_logout() -> None:
    """Route the legacy Streamlit logout button through Supabase Auth when configured."""
    original_logout = st.logout
    if getattr(original_logout, "_coletti_supabase_logout_patched", False):
        return

    def wrapped_logout(*args, **kwargs):
        if supabase_auth.configured():
            supabase_auth.sign_out()
            st.rerun()
        return original_logout(*args, **kwargs)

    wrapped_logout._coletti_supabase_logout_patched = True
    st.logout = wrapped_logout


def patch_owner_private_workspace(owner_runtime, owner_ui) -> None:
    """Add the owner-private workspace without exposing it to employee/client navigation."""
    if getattr(owner_runtime, "_owner_private_workspace_patched", False):
        return

    original_sidebar = owner_runtime._owner_sidebar
    original_render = owner_runtime._render_owner_page

    def sidebar(shell, principal, engagement_id: str) -> str:
        active = original_sidebar(shell, principal, engagement_id)
        if principal.role != Role.OWNER:
            return active

        page_key = f"_owner_reference_page:{principal.user_id}"
        st.sidebar.divider()
        st.sidebar.caption("OWNER PRIVATE")
        icons = {
            "Private Home": "⌂",
            "Employment / Career": "◇",
            "Housing": "⌂",
            "Personal Finance": "$",
            "Chapter 2": "◌",
            "Private Legal": "§",
            "Continuity": "∞",
        }
        for page in OWNER_PRIVATE_PAGES:
            if st.sidebar.button(
                f"{icons.get(page, '•')}   {page}",
                key=f"owner-private-nav:{page}",
                type="primary" if st.session_state.get(page_key) == page else "secondary",
                use_container_width=True,
            ):
                st.session_state[page_key] = page
                st.rerun()

        selected = st.session_state.get(page_key, active)
        return selected if selected in OWNER_PRIVATE_PAGES else active

    def render(shell, page: str, **kwargs):
        principal = kwargs["principal"]
        app_mode = kwargs.get("app_mode", "")

        if principal.role == Role.OWNER and page in OWNER_PRIVATE_PAGES:
            return render_private_page(page)

        # The mobile owner deployment is intentionally not the client-data
        # production plane. Prevent real source ingestion until that separate
        # production storage gate is explicitly opened.
        if principal.role == Role.OWNER and app_mode == "owner" and page in {"Records", "Record Ingestion"}:
            st.title("Records")
            st.warning("Real record ingestion is locked in the Owner PWA deployment.")
            st.caption("Use this app for owner operations, Dispatcher, DARI, private planning, and continuity testing. Client/source uploads remain behind the separate production storage authorization gate.")
            return None

        return original_render(shell, page, **kwargs)

    owner_ui._owner_sidebar = sidebar
    owner_runtime._owner_sidebar = sidebar
    owner_runtime._render_owner_page = render
    owner_runtime._owner_private_workspace_patched = True


def patch_owner_pwa(owner_runtime, owner_ui) -> None:
    patch_owner_identity_workspace()
    patch_supabase_logout()
    patch_owner_private_workspace(owner_runtime, owner_ui)
