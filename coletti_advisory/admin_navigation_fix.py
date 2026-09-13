from __future__ import annotations

import streamlit as st

from .models import Role


ADMIN_PAGES = {
    "Dashboard",
    "Clients",
    "Cases",
    "Secure Intake",
    "Records",
    "Review Center",
    "Analysis",
    "Reports",
    "Requests & To-Do",
    "Messages",
    "Administration",
}


def patch_admin_client_navigation(client_operations) -> None:
    """Keep Client-originated drill-through inside the Admin experience."""
    if getattr(client_operations, "_admin_navigation_fix_applied", False):
        return

    original_go = client_operations._go

    def go(principal, page: str, *, case_id: str | None = None) -> None:
        if principal.role == Role.ADMIN:
            if case_id:
                st.session_state[client_operations._requested_engagement_key(principal)] = case_id
            st.session_state["_portal_requested_page"] = page if page in ADMIN_PAGES else "Dashboard"
            st.rerun()
        original_go(principal, page, case_id=case_id)

    client_operations._go = go
    client_operations._admin_navigation_fix_applied = True
