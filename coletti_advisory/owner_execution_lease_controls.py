"""COW-004 Owner execution controls, backed by signed Supabase Auth RPCs.

This component cannot create leases by merely displaying. All status, start
and revoke operations are enforced by server-side functions and a verified
Supabase Auth JWT. No DB/admin credentials are present in this app.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests
import streamlit as st

from . import supabase_auth

REPOSITORIES = ("dtreezcoletti/ColettiOS", "dtreezcoletti/Coletti_Advisory")
ACTIONS = ("repo_status", "pytest", "git_fetch", "git_pull_ff")


class OwnerLeaseControlUnavailable(RuntimeError):
    pass


def _owner_principal(principal: Any) -> bool:
    role = getattr(principal, "role", None)
    role_text = str(getattr(role, "value", role) or "").lower()
    return bool(getattr(principal, "authenticated", False) and role_text == "owner")


def _rpc(name: str, payload: dict[str, Any]) -> Any:
    token = supabase_auth.current_access_token()
    url = supabase_auth._secret("SUPABASE_URL", "").rstrip("/")
    key = supabase_auth._secret("SUPABASE_ANON_KEY", "")
    if not token or not url.startswith("https://") or not key:
        raise OwnerLeaseControlUnavailable("Verified Owner authentication is unavailable")
    try:
        res = requests.post(
            f"{url}/rest/v1/rpc/{name}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Cache-Control": "no-store",
            },
            json=payload,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise OwnerLeaseControlUnavailable("Execution control service is unreachable") from exc
    if not res.ok:
        # Do not expose database exceptions or permission internals.
        if res.status_code in (401, 403):
            raise OwnerLeaseControlUnavailable("Verified Owner authorization was denied")
        if res.status_code == 400:
            raise OwnerLeaseControlUnavailable("Lease request rejected by security policy or worker readiness")
        raise OwnerLeaseControlUnavailable("Execution control service did not accept the request")
    try:
        return res.json()
    except ValueError as exc:
        raise OwnerLeaseControlUnavailable("Invalid execution control response") from exc


def render_owner_execution_worker(principal: Any) -> None:
    st.subheader("Execution Worker")
    st.caption("Owner-only time-limited authority. Source changes and releases remain behind separate approval gates.")
    if not _owner_principal(principal):
        st.warning("This control requires the authenticated Owner.")
        return
    try:
        history = _rpc("cow_owner_execution_lease_status_v1", {})
    except OwnerLeaseControlUnavailable as exc:
        st.warning(str(exc))
        return
    if not isinstance(history, list):
        st.error("Execution authority records were unavailable.")
        return
    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.info("No COW-002 engineering leases have been activated.")

    st.markdown("#### Authorize a bounded engineering lease")
    st.caption("Authorization only succeeds after the worker is credential-bound, in execute mode, and recently online. The observer cannot pass that gate.")
    device = st.text_input("Registered engineering device ID", value="cloud-executor-001", max_chars=128, key="cow-owner-device")
    repo = st.selectbox("Authorized repository", REPOSITORIES, key="cow-owner-repo")
    branch = st.text_input("Protected development branch", value="feature/cow-commissioning", max_chars=140, key="cow-owner-branch")
    actions = st.multiselect("Allowed actions", ACTIONS, default=("repo_status", "pytest"), key="cow-owner-actions")
    minutes = st.selectbox("Lease duration", (30, 60, 120, 240), format_func=lambda v: f"{v} minutes", key="cow-owner-minutes")
    confirm = st.text_input("Type AUTHORIZE COW EXECUTION to activate", max_chars=36, key="cow-owner-confirm-start")
    if st.button("Activate time-limited lease", type="primary", key="cow-owner-activate", disabled=confirm != "AUTHORIZE COW EXECUTION" or not actions):
        try:
            lease = _rpc("cow_owner_execution_start_v1", {
                "p_device_id": device.strip(),
                "p_repository": repo,
                "p_branch": branch.strip(),
                "p_actions": actions,
                "p_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=int(minutes))).isoformat(),
                "p_confirmation": confirm,
            })
        except OwnerLeaseControlUnavailable as exc:
            st.error(str(exc))
        else:
            st.success(f"Owner execution lease recorded: {lease}")
            st.rerun()

    active = [i for i in history if isinstance(i, dict) and i.get("effective_status") == "ACTIVE"]
    if active:
        st.markdown("#### Stop execution now")
        option = st.selectbox("Active lease", active, format_func=lambda i: f"{i.get('worker')} | expires {i.get('expires_at')}", key="cow-owner-revoke-select")
        stop = st.text_input("Type REVOKE COW EXECUTION to stop", max_chars=36, key="cow-owner-confirm-revoke")
        if st.button("Revoke lease", key="cow-owner-revoke", disabled=stop != "REVOKE COW EXECUTION"):
            try:
                success = _rpc("cow_owner_execution_revoke_v1", {
                    "p_lease_id": option["lease_id"],
                    "p_confirmation": stop,
                })
            except OwnerLeaseControlUnavailable as exc:
                st.error(str(exc))
            else:
                if success is True:
                    st.success("Execution authority revoked. The worker must deny further governed operations.")
                else:
                    st.warning("No active execution lease was changed.")
                st.rerun()
