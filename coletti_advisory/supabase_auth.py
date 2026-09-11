from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

from .models import Principal, Role, normalize_engagements, utc_now_iso


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str
    expires_at: int
    user: dict[str, Any]


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default


def configured() -> bool:
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_ANON_KEY"))


def _headers(*, access_token: str | None = None) -> dict[str, str]:
    anon_key = _secret("SUPABASE_ANON_KEY")
    headers = {"apikey": anon_key, "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def sign_in_password(email: str, password: str) -> SupabaseSession:
    url = _secret("SUPABASE_URL").rstrip("/")
    response = requests.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers=_headers(),
        json={"email": email.strip().lower(), "password": password},
        timeout=20,
    )
    if response.status_code >= 400:
        raise PermissionError("Supabase authentication failed")
    payload = response.json()
    expires_at = int(payload.get("expires_at") or 0)
    if not expires_at:
        expires_at = int(datetime.now(timezone.utc).timestamp()) + int(payload.get("expires_in") or 3600)
    return SupabaseSession(
        access_token=str(payload["access_token"]),
        refresh_token=str(payload["refresh_token"]),
        expires_at=expires_at,
        user=dict(payload["user"]),
    )


def refresh_session(refresh_token: str) -> SupabaseSession:
    url = _secret("SUPABASE_URL").rstrip("/")
    response = requests.post(
        f"{url}/auth/v1/token?grant_type=refresh_token",
        headers=_headers(),
        json={"refresh_token": refresh_token},
        timeout=20,
    )
    if response.status_code >= 400:
        raise PermissionError("Supabase session refresh failed")
    payload = response.json()
    expires_at = int(payload.get("expires_at") or 0)
    if not expires_at:
        expires_at = int(datetime.now(timezone.utc).timestamp()) + int(payload.get("expires_in") or 3600)
    return SupabaseSession(
        access_token=str(payload["access_token"]),
        refresh_token=str(payload["refresh_token"]),
        expires_at=expires_at,
        user=dict(payload["user"]),
    )


def _rest_get(path: str, *, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url = _secret("SUPABASE_URL").rstrip("/")
    response = requests.get(
        f"{url}/rest/v1/{path}",
        headers=_headers(access_token=access_token),
        params=params,
        timeout=20,
    )
    if response.status_code >= 400:
        raise PermissionError(f"Supabase authorization lookup failed for {path}")
    payload = response.json()
    if not isinstance(payload, list):
        raise PermissionError(f"Unexpected Supabase authorization payload for {path}")
    return [dict(item) for item in payload]


def _rpc(name: str, *, access_token: str, payload: dict[str, Any]) -> Any:
    url = _secret("SUPABASE_URL").rstrip("/")
    response = requests.post(
        f"{url}/rest/v1/rpc/{name}",
        headers=_headers(access_token=access_token),
        json=payload,
        timeout=20,
    )
    if response.status_code >= 400:
        raise PermissionError(f"Supabase RPC failed: {name}")
    return response.json()


def _save_session(session: SupabaseSession) -> None:
    st.session_state["_coletti_supabase_access_token"] = session.access_token
    st.session_state["_coletti_supabase_refresh_token"] = session.refresh_token
    st.session_state["_coletti_supabase_expires_at"] = session.expires_at
    st.session_state["_coletti_supabase_user"] = session.user


def _load_session() -> SupabaseSession | None:
    access = st.session_state.get("_coletti_supabase_access_token")
    refresh = st.session_state.get("_coletti_supabase_refresh_token")
    expires_at = st.session_state.get("_coletti_supabase_expires_at")
    user = st.session_state.get("_coletti_supabase_user")
    if not access or not refresh or not expires_at or not isinstance(user, dict):
        return None
    session = SupabaseSession(
        access_token=str(access),
        refresh_token=str(refresh),
        expires_at=int(expires_at),
        user=dict(user),
    )
    now = int(datetime.now(timezone.utc).timestamp())
    if session.expires_at <= now + 60:
        session = refresh_session(session.refresh_token)
        _save_session(session)
    return session


def current_access_token() -> str | None:
    session = _load_session()
    return session.access_token if session is not None else None


def allocate_source_id(case_id: str, source_type: str) -> str:
    access_token = current_access_token()
    if not access_token:
        raise PermissionError("A Supabase Auth session is required to allocate a canonical source ID")
    value = _rpc(
        "allocate_source_id",
        access_token=access_token,
        payload={"p_case_id": case_id, "p_source_type": source_type},
    )
    if not isinstance(value, str) or not value.strip():
        raise PermissionError("Supabase did not return a canonical source ID")
    return value.strip().upper()


def _resolve_principal(session: SupabaseSession) -> Principal:
    user_id = str(session.user.get("id") or "").strip()
    email = str(session.user.get("email") or "").strip().lower()
    if not user_id or not email:
        raise PermissionError("Authenticated Supabase user is missing identity fields")

    profiles = _rest_get(
        "profiles",
        access_token=session.access_token,
        params={
            "id": f"eq.{user_id}",
            "select": "id,display_name,organization_id,role,status",
            "limit": "1",
        },
    )
    if len(profiles) != 1:
        raise PermissionError("Authenticated user does not have exactly one Coletti profile")
    profile = profiles[0]
    if str(profile.get("status") or "").upper() not in {"ACTIVE", "ENABLED"}:
        raise PermissionError("Coletti profile is not active")

    try:
        role = Role(str(profile["role"]).lower())
    except (KeyError, ValueError) as exc:
        raise PermissionError("Coletti profile has an unsupported role") from exc

    memberships = _rest_get(
        "case_memberships",
        access_token=session.access_token,
        params={"active": "eq.true", "select": "case_id"},
    )
    assignments = _rest_get(
        "case_assignments",
        access_token=session.access_token,
        params={"active": "eq.true", "select": "case_id"},
    )
    engagement_ids = normalize_engagements(
        [str(row.get("case_id") or "") for row in memberships + assignments]
    )

    session_id = st.session_state.setdefault(
        "_coletti_supabase_session_id", f"sess-{uuid4().hex}"
    )
    authenticated_at = st.session_state.setdefault(
        "_coletti_supabase_authenticated_at", utc_now_iso()
    )
    return Principal(
        user_id=user_id,
        email=email,
        display_name=str(profile.get("display_name") or email),
        organization_id=str(profile.get("organization_id") or "coletti-co"),
        role=role,
        engagement_ids=engagement_ids,
        session_id=session_id,
        authenticated_at=authenticated_at,
        authenticated=True,
    )


def sign_out() -> None:
    access = st.session_state.get("_coletti_supabase_access_token")
    if access:
        try:
            requests.post(
                f"{_secret('SUPABASE_URL').rstrip('/')}/auth/v1/logout",
                headers=_headers(access_token=str(access)),
                timeout=10,
            )
        except requests.RequestException:
            pass
    for key in list(st.session_state):
        if str(key).startswith("_coletti_supabase_"):
            del st.session_state[key]


def require_principal(*, app_mode: str) -> Principal | None:
    """Use Supabase Auth as the primary production identity and RBAC path."""
    if not configured():
        if app_mode == "demo":
            return None
        raise RuntimeError("Supabase Auth is not configured")

    session = _load_session()
    if session is None:
        st.title("Coletti & Co.")
        st.caption("Secure ColettiOS workspace")
        with st.form("coletti_supabase_login", clear_on_submit=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            try:
                session = sign_in_password(email, password)
                _save_session(session)
                st.rerun()
            except (PermissionError, requests.RequestException):
                st.error("Authentication failed.")
        st.stop()

    try:
        return _resolve_principal(session)
    except (PermissionError, requests.RequestException):
        sign_out()
        st.error("Your authenticated account is not authorized for this workspace.")
        st.stop()
        return None
