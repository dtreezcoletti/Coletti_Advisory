from __future__ import annotations

import streamlit as st

from .owner_workspace import _get_bundle, _render_continuity


def render_private_page(page: str) -> None:
    if page == "Continuity":
        _render_continuity()
        return

    captions = {
        "Private Home": "Personal operating layer outside institutional state",
        "Employment / Career": "Outside employment and career planning",
        "Housing": "Housing and household continuity",
        "Personal Finance": "Personal finances distinct from company finance",
        "Chapter 2": "Private planning and capacity",
        "Private Legal": "Private legal records with stricter source controls",
    }
    st.title(page)
    st.caption(captions.get(page, "Private workspace"))

    if page == "Private Home":
        bundle = _get_bundle()
        left, middle, right = st.columns(3)
        left.metric("Private areas", "5")
        middle.metric("Boundary", "Private")
        right.metric("Continuity", "Shadow staged" if bundle else "Not imported")
        st.write("Employment / Career, Housing, Personal Finance, Chapter 2, and Private Legal are separate from institutional operations.")
    elif page == "Employment / Career":
        st.write("Job search, employers, recruiters, applications, interviews, compensation, resume work, and career planning.")
    elif page == "Housing":
        st.write("Rent, utilities, housing search, landlord matters, and housing planning.")
    elif page == "Personal Finance":
        st.write("Personal balances, cash flow, obligations, budgeting, and planning.")
    elif page == "Chapter 2":
        st.write("Personal planning, capacity signals, life administration, and continuity.")
    elif page == "Private Legal":
        st.write("Private legal history is staged conservatively and requires source authority plus review before promotion.")
