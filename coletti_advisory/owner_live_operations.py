"""Owner-only live operating screens backed by authenticated Supabase RPCs.

This module is a single integration point for the existing institutional records.
It does not create fabricated financial, contract, worker or integration status.
Protected mutations continue to use the existing owner-scoped RPCs.
"""
from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID

import streamlit as st

from . import supabase_auth
from .models import Role

DEPARTMENTS = (
    ("FABER", "Engineering & Infrastructure"),
    ("VOX", "Marketing & Brand Communications"),
    ("QUAERO", "Research & Business Intelligence"),
    ("MONETA", "Financial Operations"),
    ("SCRIBA", "Documentation & Records"),
    ("CURA", "Client Relations & Communications"),
    ("CIVIS", "Human Resources & Employee Operations"),
    ("AUGEO", "Business Development & New Ventures"),
    ("ACQUIRO", "Client Acquisition & Sales"),
)

PAGE_SOURCE = {
    "Billing": ("invoices", "Registered invoices and provider references"),
    "Contracts": ("contracts", "Contract register and execution status"),
    "Pricing": ("pricing", "Service pricing configuration"),
    "Assignments": ("assignments", "Authorized case assignments"),
    "Integrations": ("integrations", "Provider and connection records"),
    "Procedures": ("sops", "Governed standard operating procedures"),
    "Documents": ("contracts", "Contracts and institutional document records"),
    "Capacity": ("assignments", "Assigned personnel; not a verified capacity forecast"),
}

def _is_owner(principal: Any) -> bool:
    return (
        getattr(principal, "role", None) == Role.OWNER
        and bool(getattr(principal, "authenticated", False))
    )

def _rpc(name: str) -> dict[str, Any]:
    token = supabase_auth.current_access_token()
    if not token:
        raise PermissionError("Authenticated Owner session required.")
    result = supabase_auth._rpc(name, access_token=token, payload={})
    if not isinstance(result, dict):
        raise ValueError("The authoritative service returned an unexpected response.")
    return result

def _money(cents: Any) -> str:
    if cents is None:
        return "—"
    try:
        return f"${int(cents) / 100:,.2f}"
    except (ValueError, TypeError):
        return "Unverified"

def _display_rows(page: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in rows:
        record = dict(raw)
        if page == "Billing":
            record["Amount"] = _money(record.pop("amount_cents", None))
        elif page == "Pricing":
            record["Minimum"] = _money(record.pop("amount_min_cents", None))
            record["Maximum"] = _money(record.pop("amount_max_cents", None))
        result.append(record)
    return result

def _navigate(principal: Any, page: str) -> None:
    st.session_state[f"_owner_reference_page:{principal.user_id}"] = page
    st.rerun()

def _data_table(title: str, rows: Any, *, page: str) -> None:
    st.subheader(title)
    if not isinstance(rows, list):
        st.error("Invalid source response. This data is not verified.")
        return
    st.caption(f"{len(rows)} record(s) returned by the authenticated source.")
    if rows:
        st.dataframe(_display_rows(page, [dict(item) for item in rows if isinstance(item, Mapping)]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("The authoritative source returned no records. Nothing has been fabricated.")

def _render_assign_action(principal: Any) -> None:
    with st.expander("Change a case assignment (Owner approval required)"):
        st.caption(
            "This submits to the existing authenticated Owner override RPC. "
            "Its database rules validate the case, staff role and authority; "
            "no direct table writes occur."
        )
        with st.form("live-owner-assignment"):
            case_id = st.text_input("Case identifier")
            staff_id = st.text_input("Staff account UUID")
            role = st.selectbox(
                "Case role",
                ("Case Manager", "Analyst", "Human Reviewer", "Fresh Eyes",
                 "QA", "Publication Preparer", "Delivery Coordinator"),
            )
            reason = st.text_area("Reason", max_chars=2000)
            confirm = st.checkbox("I authorize this case-role change.")
            submit = st.form_submit_button("Request authorized assignment", type="primary")
        if submit:
            if not confirm or not case_id.strip() or len(reason.strip()) < 8:
                st.error("A case ID, explicit confirmation, and a substantive reason are required.")
                return
            try:
                parsed = str(UUID(staff_id.strip()))
            except ValueError:
                st.error("Enter a valid staff-account UUID.")
                return
            token = supabase_auth.current_access_token()
            if not token:
                st.error("An authenticated Owner session is required.")
                return
            try:
                response = supabase_auth._rpc(
                    "owner_override_assignment_v1",
                    access_token=token,
                    payload={
                        "p_case_id": case_id.strip(),
                        "p_staff_user_id": parsed,
                        "p_assignment_role": role,
                        "p_reason": reason.strip(),
                        "p_deactivate_existing_role_matches": False,
                    },
                )
            except Exception:
                st.error("The authoritative assignment service rejected or could not verify the request.")
            else:
                st.success("Assignment service accepted the request. Reload to verify the resulting record.")
                st.write(response)

def _render_implementation(data: Mapping[str, Any]) -> None:
    implementation = data.get("implementation") or {}
    items = implementation.get("items") or []
    states = implementation.get("state_counts") or {}
    st.caption("Authenticated Registry implementation matrix; self-reported statuses are not independent acceptance.")
    if states:
        st.dataframe([{"State": key, "Records": value} for key, value in states.items()],
                     hide_index=True, use_container_width=True)
    _data_table("Implementation records", items, page="Implementation")
    release = data.get("release") or {}
    st.subheader("Current release record")
    st.json(release, expanded=False)

def _render_department(principal: Any, dept: str, data: Mapping[str, Any]) -> None:
    details = dict(DEPARTMENTS).get(dept, "Department")
    st.title(f"{dept} · {details}")
    st.caption(
        "Owner-approved departmental charter. Technical commissioning, verified tools, "
        "financial control and autonomous execution remain separate states."
    )
    st.subheader("Governed procedures")
    sops = [r for r in data.get("sops", []) if str(r.get("owning_domain", "")).upper() == dept]
    _data_table("Registered procedures", sops, page="Procedures")
    if dept == "MONETA":
        _data_table("Current pricing", data.get("pricing", []), page="Pricing")
        _data_table("Recorded invoices", data.get("invoices", []), page="Billing")
    elif dept == "CIVIS":
        _data_table("Case-assignment records", data.get("assignments", []), page="Assignments")
    elif dept in {"AUGEO", "ACQUIRO"}:
        _data_table("Approved service configurations", data.get("services", []), page="Services")
    elif dept == "SCRIBA":
        _data_table("Contract records", data.get("contracts", []), page="Contracts")
    elif dept in {"FABER", "CURA", "VOX"}:
        _data_table("Integration records", data.get("integrations", []), page="Integrations")
    st.warning("A complete departmental Operator/Executive commissioning test has not been proven by this view.")

def render_live_owner_operations(principal: Any, page: str) -> bool:
    """Render an explicitly requested live Owner surface.

    Returns True if this module owns the requested page.
    """
    dept = page.split(" · ", 1)[1] if page.startswith("Collegium · ") else None
    handled = page in PAGE_SOURCE or page in {"Implementation", "Service Catalog"} or dept in dict(DEPARTMENTS)
    if not handled:
        return False
    if not _is_owner(principal):
        st.error("An authenticated Owner role is required.")
        return True

    st.caption("LIVE SOURCE · Supabase Owner-authenticated Registry view · No sample data")
    try:
        data = _rpc("owner_portal_operations_snapshot_v1")
    except Exception:
        st.error(
            "The authenticated Owner operations API is unavailable or rejected access. "
            "No local demo or invented records are shown."
        )
        return True

    st.caption(f"Source observation: {data.get('observed_at') or 'not provided'}")
    if dept:
        _render_department(principal, dept, data)
        return True
    if page == "Implementation":
        st.title("Implementation")
        try:
            _render_implementation(_rpc("owner_implementation_snapshot"))
        except Exception:
            st.error("Authoritative implementation details are unavailable.")
        return True
    if page == "Service Catalog":
        st.title("Service Catalog")
        _data_table("Services", data.get("services"), page="Services")
        _data_table("Pricing", data.get("pricing"), page="Pricing")
        return True

    key, description = PAGE_SOURCE[page]
    st.title(page)
    st.caption(description)
    _data_table("Source records", data.get(key), page=page)
    if page == "Assignments":
        _render_assign_action(principal)
    if page == "Contracts":
        if st.button("Open authoritative governance Docket"):
            _navigate(principal, "Docket")
    if page == "Pricing":
        if st.button("Open service definitions"):
            _navigate(principal, "Service Catalog")
    if page == "Documents":
        if st.button("Open Docket"):
            _navigate(principal, "Docket")
    if page == "Capacity":
        st.warning("Assignments do not prove capacity. Capacity planning remains unverified.")
    return True
