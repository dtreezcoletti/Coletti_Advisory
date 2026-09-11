from __future__ import annotations

import re
from datetime import date
from typing import Any

import streamlit as st


CLIENT_CONTEXT_KEY = "_owner_dari_client_context"
_CLIENT_ID_RE = re.compile(r"\bC\d{2}-\d{2}\b", re.IGNORECASE)


def _set_client_context(client_operations, client_id: str) -> None:
    try:
        detail = client_operations.client_detail(client_id)
        client = detail.get("client") or {}
    except Exception:
        client = {}
    st.session_state[CLIENT_CONTEXT_KEY] = {
        "client_id": client_id,
        "display_name": client.get("display_name") or client_id,
    }


def _context() -> dict[str, str]:
    raw = st.session_state.get(CLIENT_CONTEXT_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _query_text(prompt: str) -> str:
    text = prompt.strip()
    match = _CLIENT_ID_RE.search(text)
    if match:
        return match.group(0).upper()
    text = re.sub(
        r"\b(find|open|show|me|client|relationship|please|look up|lookup|search for|search)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return " ".join(text.split()).strip(" ?.,")


def _brief(client_operations, client_id: str) -> str | None:
    detail = client_operations.client_detail(client_id)
    client = detail.get("client") or {}
    if not client:
        return None
    cases = detail.get("cases") or []
    reports = detail.get("reports") or []
    active = [row for row in cases if str(row.get("status") or "").upper() not in {"CLOSED", "ARCHIVED"}]
    next_action = client.get("next_action") or "No relationship-level next action is recorded."
    return (
        f"{client.get('display_name') or client_id} · {client_id} · {client.get('status') or 'UNKNOWN'}. "
        f"Accessible cases: {len(cases)} ({len(active)} active). Accessible reports: {len(reports)}. "
        f"Next action: {next_action}"
    )


def _client_answer(client_operations, prompt: str) -> str | None:
    q = prompt.strip().lower()
    if not q:
        return None
    context = _context()
    context_id = str(context.get("client_id") or "")

    try:
        if context_id and any(
            phrase in q
            for phrase in (
                "this client",
                "this relationship",
                "their cases",
                "client's cases",
                "clients cases",
                "relationship brief",
                "who referred",
                "referral source",
            )
        ):
            detail = client_operations.client_detail(context_id)
            client = detail.get("client") or {}
            if "who referred" in q or "referral source" in q:
                return f"{client.get('display_name') or context_id} · {context_id} was referred by {client.get('referral_source') or 'no referral source currently recorded'}."
            if "case" in q:
                cases = detail.get("cases") or []
                if not cases:
                    return f"{client.get('display_name') or context_id} · {context_id} has no Case visible to your current role."
                summary = "; ".join(
                    f"{row.get('case_id')} ({row.get('status') or 'UNKNOWN'})"
                    for row in cases[:8]
                )
                return f"Accessible Cases for {client.get('display_name') or context_id} · {context_id}: {summary}."
            return _brief(client_operations, context_id)

        if "active client" in q and ("no open case" in q or "without" in q and "case" in q):
            rows = client_operations.list_clients(status="ACTIVE", limit=500)
            matches = [row for row in rows if int(row.get("active_case_count") or 0) == 0]
            if not matches:
                return "No accessible ACTIVE Client relationship currently has zero active Cases."
            labels = "; ".join(
                f"{row.get('display_name') or row.get('client_id')} · {row.get('client_id')}"
                for row in matches[:10]
            )
            return f"{len(matches)} accessible ACTIVE Client relationship(s) have no active Case: {labels}."

        if "client" in q and ("need attention" in q or "needs attention" in q or "overdue" in q):
            rows = client_operations.list_clients(limit=500)
            today = date.today().isoformat()
            matches = [
                row for row in rows
                if row.get("next_action_date") and str(row.get("next_action_date")) <= today
            ]
            if not matches:
                return "No accessible Client relationship currently has a due or overdue relationship-level next action."
            labels = "; ".join(
                f"{row.get('display_name') or row.get('client_id')} · {row.get('client_id')}: {row.get('next_action') or 'action due'}"
                for row in matches[:10]
            )
            return f"{len(matches)} Client relationship(s) need attention: {labels}."

        identifier = _CLIENT_ID_RE.search(prompt)
        if identifier:
            client_id = identifier.group(0).upper()
            rows = client_operations.list_clients(query=client_id, limit=10)
            if not rows:
                return f"No Client relationship matching {client_id} is visible to your current role."
            _set_client_context(client_operations, client_id)
            return _brief(client_operations, client_id)

        if any(word in q for word in ("find", "lookup", "look up", "search", "open client")):
            query = _query_text(prompt)
            if not query:
                return None
            rows = client_operations.list_clients(query=query, limit=10)
            if not rows:
                return f"No Client relationship matching “{query}” is visible to your current role."
            if len(rows) == 1:
                client_id = str(rows[0]["client_id"])
                _set_client_context(client_operations, client_id)
                return _brief(client_operations, client_id)
            labels = "; ".join(
                f"{row.get('display_name') or row.get('client_id')} · {row.get('client_id')}"
                for row in rows[:10]
            )
            return f"I found {len(rows)} accessible Client relationships matching “{query}”: {labels}."
    except Exception:
        # DARI must fail closed to the existing command router rather than bypass
        # the Clients RPC boundary when the relationship service is unavailable.
        return None
    return None


class _ClientContextProxy:
    def __init__(self, base):
        self._base = base

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def route_command(self, principal, engagement_id: str, command_text: str, **kwargs):
        context = dict(kwargs.get("context") or {})
        current = _context()
        if context.get("requested_capability") == "owner_console_dari" and current.get("client_id"):
            context.update(
                {
                    "selected_client_id": current["client_id"],
                    "selected_client_name": current.get("display_name") or current["client_id"],
                    "source_surface": "Clients",
                }
            )
        kwargs["context"] = context
        return self._base.route_command(principal, engagement_id, command_text, **kwargs)


def patch_clients_dari_context(client_operations, owner_live_ui) -> None:
    """Carry a selected Client into DARI without enlarging the user's permissions."""
    if getattr(owner_live_ui, "_clients_dari_context_v1_patched", False):
        return

    original_go = client_operations._go

    def go(principal, page: str, *, case_id: str | None = None):
        if page == "DARI":
            client_id = st.session_state.get("_clients_v1_selected")
            if client_id:
                _set_client_context(client_operations, str(client_id))
        return original_go(principal, page, case_id=case_id)

    client_operations._go = go

    original_answer = owner_live_ui._deterministic_dari_answer

    def deterministic_answer(prompt: str, snapshot):
        client_answer = _client_answer(client_operations, prompt)
        if client_answer is not None:
            return client_answer
        return original_answer(prompt, snapshot)

    owner_live_ui._deterministic_dari_answer = deterministic_answer

    original_client = owner_live_ui._client

    def client(core):
        base = original_client(core)
        return _ClientContextProxy(base) if base is not None else None

    owner_live_ui._client = client

    original_render = owner_live_ui._render_dari_live

    def render(core, principal, engagement_id: str, snapshot):
        current = _context()
        if current.get("client_id"):
            st.caption(
                f"Client context: {current.get('display_name') or current['client_id']} · {current['client_id']} · DARI remains constrained by your existing case/client permissions."
            )
        return original_render(core, principal, engagement_id, snapshot)

    owner_live_ui._render_dari_live = render
    owner_live_ui._clients_dari_context_v1_patched = True
