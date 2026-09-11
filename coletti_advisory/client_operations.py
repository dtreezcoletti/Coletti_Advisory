from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests
import streamlit as st

from . import supabase_auth
from .models import Role


CLIENT_STATUSES = ("ONBOARDING", "ACTIVE", "INACTIVE", "ARCHIVED")
CLIENT_TYPES = ("INDIVIDUAL", "ORGANIZATION")
CONTACT_METHODS = ("PORTAL", "EMAIL", "PHONE")
PRICING_CLASSES = ("STANDARD", "REDUCED_FEE", "PROMOTIONAL_PILOT", "PRO_BONO", "CUSTOM")
PORTAL_ROLES = ("primary", "authorized_contact", "billing_contact", "contract_contact", "read_only")


def _rpc(name: str, payload: dict[str, Any]) -> Any:
    token = supabase_auth.current_access_token()
    if not token:
        raise PermissionError("A live Supabase Auth session is required for Clients.")
    return supabase_auth._rpc(name, access_token=token, payload=payload)


def list_clients(*, query: str = "", status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    value = _rpc(
        "client_directory_v1",
        {"p_query": query or None, "p_status": status or None, "p_limit": limit},
    )
    return [dict(row) for row in value] if isinstance(value, list) else []


def client_detail(client_id: str) -> dict[str, Any]:
    value = _rpc("client_detail_v1", {"p_client_id": client_id})
    return dict(value) if isinstance(value, dict) else {}


def intake_queue(limit: int = 100) -> list[dict[str, Any]]:
    value = _rpc("admin_client_intake_queue_v1", {"p_limit": limit})
    return [dict(row) for row in value] if isinstance(value, list) else []


def duplicate_candidates(*, name: str = "", email: str = "", phone: str = "") -> list[dict[str, Any]]:
    value = _rpc(
        "admin_client_duplicate_candidates_v1",
        {"p_name": name or None, "p_email": email or None, "p_phone": phone or None},
    )
    return [dict(row) for row in value] if isinstance(value, list) else []


def accept_intake(intake_id: str, *, client_type: str) -> str:
    value = _rpc("admin_accept_intake_v1", {"p_intake_id": intake_id, "p_client_type": client_type})
    if not isinstance(value, str) or not value:
        raise RuntimeError("Client acceptance did not return a canonical Client ID.")
    return value


def set_client_status(client_id: str, status: str, *, reason: str = "") -> None:
    _rpc(
        "admin_set_client_status_v1",
        {"p_client_id": client_id, "p_status": status, "p_reason": reason or None},
    )


def update_relationship(client_id: str, values: dict[str, Any]) -> None:
    payload = {"p_client_id": client_id}
    payload.update(values)
    _rpc("admin_update_client_relationship_v1", payload)


def set_portal_user(
    client_id: str,
    email: str,
    *,
    role: str,
    active: bool,
    reason: str = "",
) -> None:
    _rpc(
        "admin_set_client_portal_user_v1",
        {
            "p_client_id": client_id,
            "p_email": email,
            "p_relationship_role": role,
            "p_active": active,
            "p_reason": reason or None,
        },
    )


def _page_key(principal) -> str:
    return f"_owner_reference_page:{principal.user_id}"


def _requested_engagement_key(principal) -> str:
    return f"_coletti_requested_engagement:{principal.user_id}"


def _go(principal, page: str, *, case_id: str | None = None) -> None:
    if case_id:
        st.session_state[_requested_engagement_key(principal)] = case_id
    st.session_state[_page_key(principal)] = page
    st.rerun()


def _error_message(exc: Exception) -> str:
    text = str(exc).strip()
    if "duplicate" in text.lower():
        return "A possible duplicate client was found. Review the duplicate candidates before accepting this intake."
    if "not authorized" in text.lower():
        return "Your current role is not authorized to perform that client action."
    return text or "The client operation could not be completed."


def _safe_rows(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{field: row.get(field) for field in fields} for row in rows]


def _status_metrics(rows: list[dict[str, Any]]) -> None:
    today = date.today().isoformat()
    active = sum(1 for row in rows if row.get("client_status") == "ACTIVE")
    onboarding = sum(1 for row in rows if row.get("client_status") == "ONBOARDING")
    attention = sum(
        1
        for row in rows
        if row.get("next_action_date") and str(row.get("next_action_date")) <= today
    )
    inactive = sum(1 for row in rows if row.get("client_status") in {"INACTIVE", "ARCHIVED"})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Clients", active)
    c2.metric("Onboarding", onboarding)
    c3.metric("Needs Attention", attention)
    c4.metric("Inactive / Archived", inactive)


def _directory_tab(principal, rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("No client relationship matches this view.")
        return

    st.dataframe(
        _safe_rows(
            rows,
            (
                "display_name",
                "client_id",
                "client_status",
                "active_case_count",
                "relationship_owner_name",
                "portal_active",
                "next_action",
                "next_action_date",
            ),
        ),
        use_container_width=True,
        hide_index=True,
    )

    options = [str(row["client_id"]) for row in rows]
    labels = {
        str(row["client_id"]): f"{row.get('display_name') or row['client_id']} · {row['client_id']}"
        for row in rows
    }
    current = st.session_state.get("_clients_v1_selected")
    index = options.index(current) if current in options else 0
    selected = st.selectbox(
        "Open client",
        options,
        index=index,
        format_func=lambda value: labels.get(value, value),
        key="_clients_v1_directory_select",
    )
    st.session_state["_clients_v1_selected"] = selected
    left, middle, right = st.columns(3)
    if left.button("Open relationship", type="primary", use_container_width=True, key="clients-open-relationship"):
        st.session_state["_clients_v1_tab"] = "Client Detail"
        st.rerun()
    if middle.button("Open Cases", use_container_width=True, key="clients-open-cases"):
        detail = client_detail(selected)
        cases = detail.get("cases") or []
        case_id = str(cases[0].get("case_id")) if cases else None
        _go(principal, "Cases", case_id=case_id)
    if right.button("Open DARI", use_container_width=True, key="clients-open-dari"):
        _go(principal, "DARI")


def _intake_tab(principal) -> None:
    if principal.role not in {Role.OWNER, Role.ADMIN}:
        st.info("Client acceptance is restricted to Owner/Admin authority.")
        return
    try:
        rows = intake_queue()
    except (PermissionError, requests.RequestException) as exc:
        st.error(_error_message(exc))
        return
    if not rows:
        st.success("No submitted intake is awaiting a client-acceptance decision.")
        return

    st.caption("Acceptance creates or reuses the permanent Client relationship. A Case is not opened automatically.")
    labels = {
        str(row["intake_id"]): f"{row.get('display_name') or 'Prospective client'} · {row.get('service_requested') or 'Service not specified'} · {row.get('status')}"
        for row in rows
    }
    intake_id = st.selectbox("Intake to review", list(labels), format_func=lambda value: labels[value])
    intake = next(row for row in rows if str(row["intake_id"]) == intake_id)

    with st.container(border=True):
        st.markdown(f"### {intake.get('display_name') or 'Prospective client'}")
        st.caption(f"Status: {intake.get('status')} · Referral source: {intake.get('referral_source') or '—'}")
        st.write(intake.get("matter_summary") or "No matter summary was provided.")
        contact = st.columns(2)
        contact[0].write(f"**Email:** {intake.get('email') or '—'}")
        contact[1].write(f"**Phone:** {intake.get('phone') or '—'}")

    candidates = duplicate_candidates(
        name=str(intake.get("display_name") or ""),
        email=str(intake.get("email") or ""),
        phone=str(intake.get("phone") or ""),
    )
    if candidates:
        st.warning("Possible existing Client relationship detected. Review before accepting.")
        st.dataframe(candidates, use_container_width=True, hide_index=True)
        reviewed = st.checkbox("I reviewed the possible duplicate relationship(s).", key=f"dup-reviewed:{intake_id}")
    else:
        reviewed = True

    client_type = st.radio("Client type", CLIENT_TYPES, horizontal=True, key=f"client-type:{intake_id}")
    if st.button(
        "Accept into Client relationship",
        type="primary",
        disabled=not reviewed,
        use_container_width=True,
        key=f"accept-intake:{intake_id}",
    ):
        try:
            new_client_id = accept_intake(intake_id, client_type=client_type)
            st.session_state["_clients_v1_selected"] = new_client_id
            st.session_state["_clients_v1_tab"] = "Client Detail"
            st.success(f"Accepted. Permanent Client ID: {new_client_id}")
            st.rerun()
        except (PermissionError, RuntimeError, requests.RequestException) as exc:
            st.error(_error_message(exc))


def _relationship_editor(client: dict[str, Any]) -> None:
    with st.expander("Edit relationship record", expanded=False):
        contact_default = client.get("preferred_contact_method") or "EMAIL"
        pricing_default = client.get("pricing_classification") or "STANDARD"
        with st.form(f"client-relationship-edit:{client['client_id']}"):
            legal_name = st.text_input("Legal / canonical name", value=str(client.get("legal_name") or ""))
            preferred_name = st.text_input("Display / preferred name", value=str(client.get("display_name") or ""))
            email = st.text_input("Primary email", value=str(client.get("primary_email") or ""))
            phone = st.text_input("Primary phone", value=str(client.get("primary_phone") or ""))
            c1, c2 = st.columns(2)
            method = c1.selectbox("Preferred contact method", CONTACT_METHODS, index=CONTACT_METHODS.index(contact_default) if contact_default in CONTACT_METHODS else 1)
            timezone = c2.text_input("Time zone", value=str(client.get("time_zone") or ""))
            referral = st.text_input("Referral source", value=str(client.get("referral_source") or ""))
            next_action = st.text_input("Next action", value=str(client.get("next_action") or ""))
            raw_date = client.get("next_action_date")
            parsed = date.fromisoformat(str(raw_date)) if raw_date else None
            next_action_date = st.date_input("Next action date", value=parsed)
            pricing = st.selectbox("Pricing classification", PRICING_CLASSES, index=PRICING_CLASSES.index(pricing_default) if pricing_default in PRICING_CLASSES else 0)
            submitted = st.form_submit_button("Save relationship", type="primary")
        if submitted:
            try:
                update_relationship(
                    str(client["client_id"]),
                    {
                        "p_legal_name": legal_name,
                        "p_preferred_name": preferred_name,
                        "p_primary_email": email,
                        "p_primary_phone": phone,
                        "p_preferred_contact_method": method,
                        "p_time_zone": timezone,
                        "p_referral_source": referral,
                        "p_next_action": next_action,
                        "p_next_action_date": next_action_date.isoformat() if next_action_date else None,
                        "p_pricing_classification": pricing,
                    },
                )
                st.success("Client relationship updated and audited.")
                st.rerun()
            except (PermissionError, requests.RequestException) as exc:
                st.error(_error_message(exc))


def _status_control(client: dict[str, Any]) -> None:
    current = str(client.get("status") or "ACTIVE")
    with st.expander("Change Client status", expanded=False):
        with st.form(f"client-status:{client['client_id']}"):
            target = st.selectbox("Status", CLIENT_STATUSES, index=CLIENT_STATUSES.index(current) if current in CLIENT_STATUSES else 1)
            reason = st.text_input("Reason", placeholder="Required when changing relationship state")
            submitted = st.form_submit_button("Apply status change")
        if submitted:
            if target != current and not reason.strip():
                st.error("A reason is required to change Client status.")
            else:
                try:
                    set_client_status(str(client["client_id"]), target, reason=reason)
                    st.success("Client status updated and audited.")
                    st.rerun()
                except (PermissionError, requests.RequestException) as exc:
                    st.error(_error_message(exc))


def _portal_access(client_id: str, users: list[dict[str, Any]]) -> None:
    if users:
        st.dataframe(
            _safe_rows(users, ("display_name", "email", "role", "active", "created_at", "revoked_at", "revoke_reason")),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No portal user is linked to this Client relationship.")

    with st.form(f"portal-access:{client_id}"):
        email = st.text_input("Authenticated user email")
        role = st.selectbox("Relationship role", PORTAL_ROLES, index=1)
        action = st.radio("Access", ("Grant / update", "Revoke"), horizontal=True)
        reason = st.text_input("Reason", placeholder="Required for revocation")
        submitted = st.form_submit_button("Apply portal access")
    if submitted:
        active = action == "Grant / update"
        if not email.strip():
            st.error("Email is required.")
        elif not active and not reason.strip():
            st.error("A reason is required to revoke portal access.")
        else:
            try:
                set_portal_user(client_id, email, role=role, active=active, reason=reason)
                st.success("Portal access relationship updated and audited.")
                st.rerun()
            except (PermissionError, requests.RequestException) as exc:
                st.error(_error_message(exc))


def _detail_tab(principal, directory_rows: list[dict[str, Any]]) -> None:
    if not directory_rows:
        st.info("No accessible Client relationship is available.")
        return
    options = [str(row["client_id"]) for row in directory_rows]
    selected = st.session_state.get("_clients_v1_selected")
    if selected not in options:
        selected = options[0]
        st.session_state["_clients_v1_selected"] = selected
    labels = {str(row["client_id"]): f"{row.get('display_name') or row['client_id']} · {row['client_id']}" for row in directory_rows}
    selected = st.selectbox("Client relationship", options, index=options.index(selected), format_func=lambda value: labels[value], key="_clients_v1_detail_select")
    st.session_state["_clients_v1_selected"] = selected

    try:
        detail = client_detail(selected)
    except (PermissionError, requests.RequestException) as exc:
        st.error(_error_message(exc))
        return
    client = detail.get("client") or {}
    cases = detail.get("cases") or []
    contracts = detail.get("contracts") or []
    reports = detail.get("reports") or []
    invoices = detail.get("invoices") or []
    users = detail.get("authorized_users") or []
    audit = detail.get("audit") or []

    st.markdown(f"## {client.get('display_name') or selected}")
    st.caption(f"{selected} · {client.get('status') or 'UNKNOWN'} · {client.get('client_type') or 'INDIVIDUAL'}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cases", len(cases))
    c2.metric("Contracts", len(contracts))
    c3.metric("Reports", len(reports))
    c4.metric("Open invoices", sum(1 for invoice in invoices if str(invoice.get("status") or "").upper() not in {"PAID", "VOID", "CANCELLED"}))

    if cases:
        case_options = [str(item["case_id"]) for item in cases]
        case_id = st.selectbox("Case to open", case_options, key=f"client-case:{selected}")
        actions = st.columns(4)
        if actions[0].button("Open Case", type="primary", use_container_width=True, key=f"open-case:{selected}"):
            _go(principal, "Cases", case_id=case_id)
        if actions[1].button("Records", use_container_width=True, key=f"client-records:{selected}"):
            _go(principal, "Records", case_id=case_id)
        if actions[2].button("Reports", use_container_width=True, key=f"client-reports:{selected}"):
            _go(principal, "Reports", case_id=case_id)
        if actions[3].button("DARI", use_container_width=True, key=f"client-dari:{selected}"):
            _go(principal, "DARI")

    relationship, case_tab, contract_tab, billing_tab, report_tab, portal_tab, audit_tab = st.tabs(
        ["Relationship", "Cases", "Contracts", "Billing", "Reports", "Portal Access", "Audit"]
    )
    with relationship:
        st.write({
            "Legal name": client.get("legal_name"),
            "Primary email": client.get("primary_email"),
            "Primary phone": client.get("primary_phone"),
            "Preferred contact": client.get("preferred_contact_method"),
            "Time zone": client.get("time_zone"),
            "Referral source": client.get("referral_source"),
            "Relationship owner": client.get("relationship_owner_name"),
            "Pricing classification": client.get("pricing_classification"),
            "Next action": client.get("next_action"),
            "Next action date": client.get("next_action_date"),
        })
        if principal.role in {Role.OWNER, Role.ADMIN}:
            _relationship_editor(client)
            _status_control(client)
    with case_tab:
        st.dataframe(cases, use_container_width=True, hide_index=True) if cases else st.info("No Case is linked to this Client yet.")
    with contract_tab:
        st.dataframe(contracts, use_container_width=True, hide_index=True) if contracts else st.info("No contract is linked to this Client yet.")
    with billing_tab:
        st.dataframe(invoices, use_container_width=True, hide_index=True) if invoices else st.info("No invoice is linked to this Client yet.")
    with report_tab:
        st.dataframe(reports, use_container_width=True, hide_index=True) if reports else st.info("No report is linked to this Client yet.")
    with portal_tab:
        if principal.role in {Role.OWNER, Role.ADMIN}:
            _portal_access(selected, users)
        else:
            st.dataframe(_safe_rows(users, ("display_name", "role", "active")), use_container_width=True, hide_index=True) if users else st.info("No portal access details are available to this role.")
    with audit_tab:
        if principal.role in {Role.OWNER, Role.ADMIN}:
            st.dataframe(audit, use_container_width=True, hide_index=True) if audit else st.info("No Client audit events are available yet.")
        else:
            st.info("Full Client audit history is restricted to Owner/Admin authority.")


def render_clients_operating_surface(shell, **kwargs) -> None:
    principal = kwargs["principal"]
    st.title("Clients")
    st.caption(
        "Authoritative Client relationships · permanent Client IDs · intake acceptance · case-scoped staff access · audited portal access"
    )

    if not supabase_auth.configured() or not supabase_auth.current_access_token():
        st.warning("The live Clients operating surface requires the canonical Supabase Auth session. No Client record is fabricated in fallback/demo mode.")
        authorized_cases = list(principal.engagement_ids)
        if authorized_cases:
            st.caption("Current authorized case workspaces")
            st.dataframe([{"Case": case_id} for case_id in authorized_cases], use_container_width=True, hide_index=True)
        return

    toolbar = st.columns([2, 1, 1])
    query = toolbar[0].text_input("Search", placeholder="Client ID, name, email, phone, or Case ID", label_visibility="collapsed")
    status_choice = toolbar[1].selectbox("Status", ("ALL",) + CLIENT_STATUSES, label_visibility="collapsed")
    if toolbar[2].button("Refresh", use_container_width=True):
        st.rerun()

    try:
        rows = list_clients(query=query, status=None if status_choice == "ALL" else status_choice)
    except (PermissionError, requests.RequestException) as exc:
        st.error(_error_message(exc))
        return

    _status_metrics(rows)
    tabs = ("Directory", "Intake & Acceptance", "Client Detail") if principal.role in {Role.OWNER, Role.ADMIN} else ("Directory", "Client Detail")
    default_tab = st.session_state.pop("_clients_v1_tab", None)
    if default_tab in tabs:
        # Streamlit tabs cannot be programmatically preselected; preserve selected Client and render all tab state deterministically.
        pass
    rendered = st.tabs(tabs)
    with rendered[0]:
        _directory_tab(principal, rows)
    if principal.role in {Role.OWNER, Role.ADMIN}:
        with rendered[1]:
            _intake_tab(principal)
        with rendered[2]:
            _detail_tab(principal, rows)
    else:
        with rendered[1]:
            _detail_tab(principal, rows)


def patch_clients_operating_surface(owner_runtime) -> None:
    """Install Clients Operating Specification v1 over the existing Clients route."""
    if getattr(owner_runtime, "_clients_operating_spec_v1_patched", False):
        return
    original_render = owner_runtime._render_owner_page

    def render(shell, page: str, **kwargs):
        if page == "Clients":
            return render_clients_operating_surface(shell, **kwargs)
        return original_render(shell, page, **kwargs)

    owner_runtime._render_owner_page = render
    owner_runtime._clients_operating_spec_v1_patched = True
