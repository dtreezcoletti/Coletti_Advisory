from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

import streamlit as st

from .mobile_mvp import prepare_dari_command
from .owner_console_ui import _dari_queue, _esc, _first_name, _greeting


def render_owner_dari(principal, engagement_id: str, decisions: list[dict[str, str]], manifest: Mapping[str, Any]) -> None:
    """Render the owner DARI rail without pretending demo commands reach production.

    Authenticated owner sessions stage through the existing permission-scoped DARI
    command envelope. The unauthenticated synthetic demo keeps commands local to
    Streamlit session state so the reference UI remains testable without weakening
    the production authentication boundary.
    """
    contradictions = len(manifest.get("contradictions") or {})
    st.markdown(
        "<section class='oc-card'><div class='oc-dari-header'><div class='oc-dari-orb'></div>"
        "<div><span class='oc-dari-title'>DARI</span><span class='oc-dari-sub'>Your AI Assistant</span></div></div>"
        f"<div class='oc-dari-copy'><strong>{_esc(_greeting())}, {_esc(_first_name(principal))}.</strong>"
        "<span>Here are a few things that need your attention.</span></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>!</div><div>{len(decisions)} decision item(s) surfaced</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>⌁</div><div>{contradictions} recorded contradiction(s)</div></div>"
        f"<div class='oc-alert-line'><div class='oc-alert-dot'>▣</div><div>{len(principal.engagement_ids)} authorized case workspace(s)</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )

    command = st.text_input(
        "Ask DARI",
        placeholder="Ask DARI a question…",
        label_visibility="collapsed",
        key="owner_dari_command",
    )
    submitted = st.button(
        "Ask DARI →",
        type="primary",
        use_container_width=True,
        disabled=not command.strip(),
        key="owner_dari_submit",
    )
    if not submitted:
        return

    queue = _dari_queue(principal, engagement_id)
    if principal.authenticated:
        envelope = prepare_dari_command(
            principal,
            engagement_id,
            command,
            case_id=engagement_id,
            protected_action=False,
        )
        queue.append(asdict(envelope))
        st.success("DARI command staged for the authorized backend.")
        return

    queue.append(
        {
            "state": "DEMO_PREVIEW",
            "engagement_id": engagement_id,
            "text": command.strip(),
        }
    )
    st.info("Synthetic demo only · DARI command staged locally and not sent to a live backend.")
