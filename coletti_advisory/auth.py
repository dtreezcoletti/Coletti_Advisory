from __future__ import annotations

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
    """Enforce OIDC identity-token issuance and expiration claims."""
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


def _claim_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def validate_oidc_identity_claims(
    claims: dict[str, Any],
    *,
    now: datetime | None = None,
    clock_skew_seconds: int = 60,
) -> None:
    validate_oidc_claim_times(claims, now=now, clock_skew_seconds=clock_skew_seconds)
    if not str(claims.get("sub") or "").strip():
        raise ValueError("OIDC identity token is missing a subject")
    if not str(claims.get("email") or "").strip():
        raise ValueError("OIDC identity token is missing an email address")
    if not _claim_true(claims.get("email_verified")):
        raise ValueError("OIDC identity email is not verified")


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
    verified email identity, application-session lifetime, account authorization,
    roles, and engagement access.

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

    claims = {
        "iat": _user_claim("iat"),
        "exp": _user_claim("exp"),
        "sub": _user_claim("sub"),
        "email": _user_claim("email"),
        "email_verified": _user_claim("email_verified"),
    }
    try:
        validate_oidc_identity_claims(claims)
    except ValueError:
        st.warning("Your identity token expired, is invalid, or does not contain a verified email. Please authenticate again.")
        st.logout()
        st.stop()

    email = str(claims["email"]).lower()
    subject = str(claims["sub"])
    now = datetime.now(timezone.utc)

    token_marker = f"{subject}:{claims['iat']}"
    marker_key = "_coletti_oidc_token_marker"
    started_key = "_coletti_auth_started_at"
    session_key = "_coletti_session_id"
    if st.session_state.get(marker_key) != token_marker:
        st.session_state[marker_key] = token_marker
        st.session_state[started_key] = now.isoformat()
        st.session_state[session_key] = f"sess-{uuid4().hex}"
    elif started_key not in st.session_state:
        st.session_state[started_key] = now.isoformat()

    started = datetime.fromisoformat(st.session_state[started_key])
    if now - started > timedelta(minutes=session_ttl_minutes):
        st.warning("Your Coletti & Co. application session expired. Please authenticate again.")
        st.logout()
        st.stop()

    registry_raw = str(_secrets_get("AUTHZ_REGISTRY_JSON", "{}"))
    record = AuthorizationRegistry.from_json(registry_raw).resolve(email)
    if record is None or not record.enabled:
        st.error("Your identity is verified, but this account is not authorized for Coletti & Co.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    session_id = st.session_state.setdefault(session_key, f"sess-{uuid4().hex}")
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
