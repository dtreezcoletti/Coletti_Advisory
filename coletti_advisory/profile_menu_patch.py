from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from .profile_menu import render_profile_menu
from .workspaces import workspace_label


def _context(experience_shell, principal, engagement_id: str | None = None):
    engagement_id = engagement_id or st.session_state.get("_coletti_selected_engagement")
    if not engagement_id and principal.engagement_ids:
        engagement_id = principal.engagement_ids[0]
    if not engagement_id:
        return None, {}, {}

    manifest: Mapping[str, Any] = {}
    records: Mapping[str, Any] = {}
    core = st.session_state.get("_coletti_core")
    if core is not None:
        try:
            manifest = core.manifest(engagement_id)
        except Exception:
            manifest = {}

    publication_store = st.session_state.get("_coletti_publication_store")
    if publication_store is not None:
        try:
            records = experience_shell.app._load_publication_records(
                publication_store,
                principal,
                engagement_id,
            )
        except Exception:
            records = {}
    return engagement_id, manifest, records


def _request_standard_page(principal, target: str) -> None:
    st.session_state[f"_coletti_profile_requested_page:{principal.user_id}"] = target
    st.rerun()


def _request_owner_page(principal, target: str) -> None:
    st.session_state[f"_owner_reference_page:{principal.user_id}"] = target
    st.rerun()


def patch_profile_menus(experience_shell, owner_ui, owner_notifications, owner_runtime) -> None:
    """Replace static identity pills with current-principal profile menus.

    The menu is personal to the principal whose interface is currently rendered.
    It does not provide cross-employee access to payroll/leave information and it
    does not invent HR/payroll records where no authoritative service exists.
    Every actionable card routes through existing application pages rather than
    introducing a parallel workflow.
    """
    if getattr(experience_shell, "_profile_menus_patched", False):
        return

    def standard_topbar(principal, experience: str) -> None:
        title = {
            "client": "Client Portal",
            "employee": "Team Workspace",
            "owner": "Owner Console",
        }[experience]
        engagement_id, manifest, records = _context(experience_shell, principal)
        left, profile = st.columns([3.1, 1.35], gap="small", vertical_alignment="center")
        with left:
            st.markdown(
                f"<div class='cc-topline-title'>{experience_shell._esc(title)}</div>",
                unsafe_allow_html=True,
            )
        with profile:
            if engagement_id:
                render_profile_menu(
                    principal,
                    engagement_id=engagement_id,
                    manifest=manifest,
                    records=records,
                    key_prefix=f"profile:{principal.user_id}:{experience}",
                    navigate=lambda target: _request_standard_page(principal, target),
                )
            else:
                st.caption(principal.display_name)

    def fallback_owner_topbar(principal, manifest: Mapping[str, Any], engagement_ids) -> None:
        engagement_id = st.session_state.get("_coletti_selected_engagement")
        if not engagement_id and engagement_ids:
            engagement_id = engagement_ids[0]
        records: Mapping[str, Any] = {}
        publication_store = st.session_state.get("_coletti_publication_store")
        if engagement_id and publication_store is not None:
            try:
                records = experience_shell.app._load_publication_records(
                    publication_store,
                    principal,
                    engagement_id,
                )
            except Exception:
                records = {}

        left, search_col, profile = st.columns(
            [1.25, 2.2, 1.45],
            gap="small",
            vertical_alignment="center",
        )
        with left:
            st.markdown(
                "<div class='oc-topbrand'><strong>ColettiOS</strong><span>Owner Console</span></div>",
                unsafe_allow_html=True,
            )
        with search_col:
            st.markdown("<div class='oc-search-shell'>", unsafe_allow_html=True)
            query = st.text_input(
                "Search",
                placeholder="Search cases, clients, documents, team members, or help…",
                label_visibility="collapsed",
                key="owner_reference_search",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with profile:
            if engagement_id:
                render_profile_menu(
                    principal,
                    engagement_id=engagement_id,
                    manifest=manifest,
                    records=records,
                    key_prefix=f"owner-profile:{principal.user_id}",
                    navigate=lambda target: _request_owner_page(principal, target),
                )

        query = query.strip().lower()
        if not query:
            return
        matches: list[str] = []
        for eid in engagement_ids:
            label = workspace_label(eid)
            if query in str(eid).lower() or query in label.lower():
                matches.append(f"Case · {label} · {eid}")
        for source in (manifest.get("sources") or {}).values():
            meta = source.get("metadata") or {}
            filename = str(meta.get("filename") or source.get("source_id") or "")
            classification = str(meta.get("classification") or "")
            if query in filename.lower() or query in classification.lower():
                matches.append(f"Document · {filename}")
            if len(matches) >= 8:
                break
        if matches:
            with st.expander(f"Search results · {len(matches)}", expanded=True):
                for match in matches[:8]:
                    st.write(match)
        else:
            st.caption("No match in the currently authorized Streamlit workspace data.")

    def live_owner_topbar(principal, manifest: Mapping[str, Any], engagement_ids, *, core, engagement_id: str) -> None:
        snapshot = owner_notifications._snapshot(core, principal, engagement_id)
        if not snapshot:
            fallback_owner_topbar(principal, manifest, engagement_ids)
            return

        notifications = owner_notifications.build_owner_notifications(snapshot)
        publication_store = st.session_state.get("_coletti_publication_store")
        records: Mapping[str, Any] = {}
        if publication_store is not None:
            try:
                records = experience_shell.app._load_publication_records(
                    publication_store,
                    principal,
                    engagement_id,
                )
            except Exception:
                records = {}

        left, search_col, bell_col, profile = st.columns(
            [1.2, 2.25, .42, 1.45],
            gap="small",
            vertical_alignment="center",
        )
        with left:
            st.markdown(
                "<div class='oc-topbrand'><strong>ColettiOS</strong><span>Owner Console</span></div>",
                unsafe_allow_html=True,
            )
        with search_col:
            st.markdown("<div class='oc-search-shell'>", unsafe_allow_html=True)
            owner_notifications._render_search(principal, manifest, engagement_ids, snapshot)
            st.markdown("</div>", unsafe_allow_html=True)
        with bell_col:
            label = f"🔔 {len(notifications)}" if notifications else "🔔"
            with st.popover(label, use_container_width=True):
                st.markdown("### Notifications")
                st.caption("Current in-app signals from Dispatcher and Registry. External delivery is a separate protected activation.")
                if not notifications:
                    st.success("No current owner notification requires attention.")
                else:
                    for idx, item in enumerate(notifications[:12]):
                        st.markdown(
                            f"**{owner_ui._esc(item['kind'])} · {owner_ui._esc(item['title'])}**",
                            unsafe_allow_html=True,
                        )
                        st.caption(item["detail"])
                        if st.button(
                            "Open",
                            key=f"owner-notification-open-{idx}",
                            use_container_width=True,
                        ):
                            owner_notifications._route(principal, item["target"])
                        if idx < min(len(notifications), 12) - 1:
                            st.divider()
        with profile:
            render_profile_menu(
                principal,
                engagement_id=engagement_id,
                manifest=manifest,
                records=records,
                key_prefix=f"owner-live-profile:{principal.user_id}",
                navigate=lambda target: _request_owner_page(principal, target),
            )

    experience_shell._topbar = standard_topbar
    owner_ui._owner_topbar = fallback_owner_topbar
    owner_notifications.render_live_owner_topbar = live_owner_topbar
    owner_runtime.render_live_owner_topbar = live_owner_topbar
    experience_shell._profile_menus_patched = True
