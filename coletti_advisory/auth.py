from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import streamlit as st

from .models import Principal, Role, normalize_engagements, utc_now_iso


@dataclass(frozen=True)
class AuthorizationRecord:
    email: str
    display_name: str
    organization_id: str
    role: Role
    engagement_ids: tuple[str, ...]
    enabled: bool = True


class AuthorizationRegistry:
    def __init__(self, records: dict[str, AuthorizationRecord]) -> None:
        self._records = {k.lower(): v for k, v in records.items()}

    @classmethod
    def from_json(cls, raw: str) -> "AuthorizationRegistry":
        payload = json.loads(raw or "{}")
        records: dict[str, AuthorizationRecord] = {}
        for email, item in payload.items():
            records[email.lower()] = AuthorizationRecord(
                email=email.lower(),
                display_name=str(item.get("display_name") or email),
                organization_id=str(item["organization_id"]),
                role=Role(str(item["role"])),
                engagement_ids=normalize_engagements(item.get("engagement_ids", [])),
                enabled=bool(item.get("enabled", True)),
            )
        return cls(records)

    def resolve(self, email: str) -> AuthorizationRecord | None:
        return self._records.get(email.lower())


def validate_oidc_claim_times(
    claims: dict[str, Any],
    *,
    now: datetime | None = None,
    clock_skew_seconds: int = 60,
) -> None:
    """Enforce OIDC identity-token issuance and expiration claims.

    Streamlit exposes parsed identity-token claims through st.user but does not
    implicitly expire authentication when the token's ``exp`` time passes. The
    commercial boundary therefore checks ``iat`` and ``exp`` on every rerun.
    """
    now = now or datetime.now(timezone.utc)
    now_ts = now.timestamp()
    try:
        issued_at = float(claims["iat"])
        expires_at = float(claims["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("OIDC identity token is missing valid iat/exp claims") from exc

    if issued_at > now_ts + clock_skew_seconds:
        raise ValueError("OIDC identity token issuance time is in the future")
    if expires_at <= issued_at:
        raise ValueError("OIDC identity token expiration is invalid")
    if now_ts >= expires_at - clock_skew_seconds:
        raise ValueError("OIDC identity token has expired")


def _secrets_get(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _auth_is_configured() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def _user_claim(name: str, default=None):
    try:
        return st.user.get(name, default)
    except Exception:
        return getattr(st.user, name, default)


def _user_value(name: str, default: str = "") -> str:
    return str(_user_claim(name, default) or default)


def require_authenticated_principal(*, app_mode: str, session_ttl_minutes: int) -> Principal | None:
    """Use Streamlit OIDC for identity; authorization remains application-owned.

    Password verification, cryptographic identity-token validation, nonce/state
    handling, and provider-session behavior are delegated to the configured OIDC
    provider and Streamlit. Coletti & Co. separately enforces token expiration,
    application-session lifetime, account authorization, roles, and engagement
    access.

    In demo mode, missing OIDC configuration returns None so the synthetic demo
    can remain public. Production mode fails closed.
    """
    if not _auth_is_configured():
        if app_mode == "demo":
            return None
        st.error("Authentication is not configured. Production access is disabled.")
        st.stop()

    if not st.user.is_logged_in:
        st.title("Coletti & Co.")
        st.caption("Secure ColettiOS workspace")
        if st.button("Log in", type="primary"):
            provider = str(_secrets_get("AUTH_PROVIDER", "google"))
            st.login(provider)
        st.stop()

    claims = {"iat": _user_claim("iat"), "exp": _user_claim("exp")}
    try:
        validate_oidc_claim_times(claims)
    except ValueError:
        st.warning("Your identity token expired or is invalid. Please authenticate again.")
        st.logout()
        st.stop()

    now = datetime.now(timezone.utc)
    started_key = "_coletti_auth_started_at"
    if started_key not in st.session_state:
        st.session_state[started_key] = now.isoformat()
    started = datetime.fromisoformat(st.session_state[started_key])
    if now - started > timedelta(minutes=session_ttl_minutes):
        st.warning("Your Coletti & Co. application session expired. Please authenticate again.")
        st.logout()
        st.stop()

    email = _user_value("email").lower()
    if not email:
        st.error("The identity provider did not return an email address.")
        st.stop()

    registry_raw = str(_secrets_get("AUTHZ_REGISTRY_JSON", "{}"))
    record = AuthorizationRegistry.from_json(registry_raw).resolve(email)
    if record is None or not record.enabled:
        st.error("Your identity is verified, but this account is not authorized for Coletti & Co.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    session_id = st.session_state.setdefault("_coletti_session_id", f"sess-{uuid4().hex}")
    subject = _user_value("sub") or hashlib.sha256(email.encode()).hexdigest()[:24]
    display_name = _user_value("name") or record.display_name
    return Principal(
        user_id=f"usr-{subject}",
        email=email,
        display_name=display_name,
        organization_id=record.organization_id,
        role=record.role,
        engagement_ids=record.engagement_ids,
        session_id=session_id,
        authenticated_at=st.session_state[started_key],
        authenticated=True,
    )


def demo_principal() -> Principal:
    return Principal(
        user_id="demo-session",
        email="demo@synthetic.invalid",
        display_name="Synthetic Demo",
        organization_id="org-synthetic",
        role=Role.OWNER,
        engagement_ids=("eng-synthetic-demo",),
        session_id="demo-session",
        authenticated_at=utc_now_iso(),
        authenticated=False,
    )
