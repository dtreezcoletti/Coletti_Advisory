from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

import streamlit as st

from .models import Permission, Principal, Role


STAFF_ROLES = {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.REVIEWER}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_mobile_staff(principal: Principal) -> None:
    """Fail closed unless the current identity is authenticated staff."""
    if not principal.authenticated:
        raise PermissionError("Coletti Mobile requires an authenticated staff session")
    if principal.role not in STAFF_ROLES:
        raise PermissionError("Coletti Mobile owner/employee MVP is staff-only")


def mobile_navigation(principal: Principal) -> tuple[str, ...]:
    require_mobile_staff(principal)
    if principal.role is Role.OWNER:
        return ("Today", "Cases", "DARI", "Needs Me", "Company")
    return ("Today", "Cases", "DARI", "Reviews", "Alerts")


@dataclass(frozen=True)
class MobileSessionEnvelope:
    user_id: str
    role: str
    organization_id: str
    engagement_id: str
    session_id: str
    authenticated_at: str


def mobile_session(principal: Principal, engagement_id: str) -> MobileSessionEnvelope:
    require_mobile_staff(principal)
    if not principal.can_access(engagement_id):
        raise PermissionError("Mobile session is outside the authorized engagement scope")
    return MobileSessionEnvelope(
        user_id=principal.user_id,
        role=principal.role.value,
        organization_id=principal.organization_id,
        engagement_id=engagement_id,
        session_id=principal.session_id,
        authenticated_at=principal.authenticated_at,
    )


@dataclass(frozen=True)
class DariMobileCommand:
    command_id: str
    actor_id: str
    role: str
    engagement_id: str
    session_id: str
    text: str
    case_id: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    human_gate_required: bool = False


def prepare_dari_command(
    principal: Principal,
    engagement_id: str,
    text: str,
    *,
    case_id: str | None = None,
    protected_action: bool = False,
) -> DariMobileCommand:
    session = mobile_session(principal, engagement_id)
    command = str(text).strip()
    if not command:
        raise ValueError("DARI command text is required")
    return DariMobileCommand(
        command_id=f"CMD-{uuid4().hex}",
        actor_id=session.user_id,
        role=session.role,
        engagement_id=session.engagement_id,
        session_id=session.session_id,
        text=command,
        case_id=case_id,
        human_gate_required=protected_action,
    )


@dataclass(frozen=True)
class SecureMobileUpload:
    upload_id: str
    actor_id: str
    engagement_id: str
    filename: str
    classification: str
    byte_length: int
    content_sha256: str
    capture_method: str
    created_at: str = field(default_factory=utc_now_iso)


def prepare_mobile_upload(
    principal: Principal,
    engagement_id: str,
    *,
    filename: str,
    data: bytes,
    classification: str,
    capture_method: str,
    max_bytes: int = 200 * 1024 * 1024,
) -> SecureMobileUpload:
    mobile_session(principal, engagement_id)
    if not principal.can(Permission.UPLOAD):
        raise PermissionError("Role does not permit source uploads")
    if not str(filename).strip():
        raise ValueError("filename is required")
    if not data:
        raise ValueError("empty uploads are not allowed")
    if len(data) > max_bytes:
        raise ValueError("upload exceeds the mobile intake size limit")
    capture = str(capture_method).strip().upper()
    if capture not in {"CAMERA", "FILE_PICKER"}:
        raise ValueError("capture_method must be CAMERA or FILE_PICKER")
    return SecureMobileUpload(
        upload_id=f"MUP-{uuid4().hex}",
        actor_id=principal.user_id,
        engagement_id=engagement_id,
        filename=str(filename).strip(),
        classification=str(classification).strip(),
        byte_length=len(data),
        content_sha256=sha256(data).hexdigest(),
        capture_method=capture,
    )


@dataclass(frozen=True)
class MobileReviewAction:
    action_id: str
    actor_id: str
    engagement_id: str
    subject_id: str
    action: str
    protected: bool
    state: str
    created_at: str = field(default_factory=utc_now_iso)


def prepare_review_action(
    principal: Principal,
    engagement_id: str,
    *,
    subject_id: str,
    action: str,
    protected: bool = False,
) -> MobileReviewAction:
    mobile_session(principal, engagement_id)
    if not principal.can(Permission.REVIEW):
        raise PermissionError("Role does not permit review actions")
    if not str(subject_id).strip() or not str(action).strip():
        raise ValueError("subject_id and action are required")
    return MobileReviewAction(
        action_id=f"MRA-{uuid4().hex}",
        actor_id=principal.user_id,
        engagement_id=engagement_id,
        subject_id=subject_id,
        action=action.strip().upper(),
        protected=protected,
        state="AWAITING_HUMAN_CONFIRMATION" if protected else "STAGED",
    )


@dataclass(frozen=True)
class ProtectedNotification:
    notification_id: str
    category: str
    lock_screen_title: str
    lock_screen_body: str
    authenticated_title: str
    authenticated_body: str
    requires_authentication: bool = True


def protected_notification(
    *,
    category: str,
    authenticated_title: str,
    authenticated_body: str,
) -> ProtectedNotification:
    """Never place client/case-sensitive details on the lock screen."""
    return ProtectedNotification(
        notification_id=f"NTF-{uuid4().hex}",
        category=str(category).strip().upper() or "ACTION",
        lock_screen_title="ColettiOS",
        lock_screen_body="Action required. Open Coletti Mobile to review.",
        authenticated_title=str(authenticated_title).strip(),
        authenticated_body=str(authenticated_body).strip(),
        requires_authentication=True,
    )


@dataclass(frozen=True)
class MobileCalendarItem:
    item_id: str
    title: str
    start_at: str
    end_at: str | None = None
    case_id: str | None = None
    protected_detail: bool = False


def sanitized_calendar_items(items: Iterable[MobileCalendarItem], *, authenticated: bool) -> tuple[Mapping[str, Any], ...]:
    rendered: list[Mapping[str, Any]] = []
    for item in items:
        payload = asdict(item)
        if item.protected_detail and not authenticated:
            payload["title"] = "Protected ColettiOS item"
            payload["case_id"] = None
        rendered.append(payload)
    return tuple(rendered)


def summarize_manifest(manifest: Mapping[str, Any]) -> dict[str, int]:
    return {
        "sources": len(manifest.get("sources") or {}),
        "propositions": len(manifest.get("propositions") or {}),
        "contradictions": len(manifest.get("contradictions") or {}),
        "reconciliations": len(manifest.get("reconciliations") or {}),
    }


def _queue(principal: Principal, engagement_id: str) -> list[dict[str, Any]]:
    """Session-local command staging, isolated by actor and engagement."""
    queues = st.session_state.setdefault("_mobile_dari_command_queues", {})
    key = f"{principal.user_id}:{engagement_id}"
    return queues.setdefault(key, [])


def render_mobile_companion(
    *,
    principal: Principal,
    engagement_id: str,
    manifest: Mapping[str, Any],
    classifications: Iterable[str],
    ingest_file: Callable[..., Mapping[str, Any]],
    storage: Any,
    core: Any,
) -> None:
    """Responsive pre-production owner/employee mobile companion.

    DARI commands are staged as permission-scoped envelopes until the separately
    governed DARI backend is integrated. Uploads use the existing authoritative
    intake callback; this page does not create a second storage authority.
    """
    try:
        session = mobile_session(principal, engagement_id)
    except PermissionError as exc:
        st.error(str(exc))
        st.stop()

    st.title("Coletti Mobile")
    st.caption("Owner / employee operational companion · pre-production")
    st.info("Uses the same authenticated identity, engagement permissions, storage and ColettiOS authority as the web workspace.")

    navigation = mobile_navigation(principal)
    section = st.segmented_control("Mobile", navigation, default=navigation[0], label_visibility="collapsed")
    summary = summarize_manifest(manifest)

    if section == "Today":
        st.subheader("Today")
        cols = st.columns(2)
        cols[0].metric("Sources", summary["sources"])
        cols[1].metric("Open contradictions", summary["contradictions"])
        st.caption("Calendar execution remains controlled by Dispatcher. This surface is read/command oriented until live calendar integration is activated.")

    elif section == "Cases":
        st.subheader("Authorized Case")
        st.write(f"Workspace: **{engagement_id}**")
        st.json(summary, expanded=False)
        st.caption("Natural-language registry lookup is supplied by the stacked staff command-path dependency; this page never broadens case access.")

    elif section == "DARI":
        st.subheader("DARI")
        command = st.text_area("Ask or command DARI", placeholder="What needs my attention on this case?")
        protected = st.checkbox("This request may involve a protected action", value=False)
        queue = _queue(principal, engagement_id)
        if st.button("Stage DARI command", type="primary", disabled=not command.strip()):
            envelope = prepare_dari_command(
                principal,
                engagement_id,
                command,
                case_id=engagement_id,
                protected_action=protected,
            )
            queue.append(asdict(envelope))
            if envelope.human_gate_required:
                st.warning("Command staged. The protected action still requires the applicable human decision gate.")
            else:
                st.success("DARI command staged for the authorized backend.")
        if queue:
            st.caption(f"Staged for this authorized workspace: {len(queue)}")

    elif section in {"Reviews", "Needs Me"}:
        st.subheader(section)
        if not principal.can(Permission.REVIEW):
            st.info("Your role has no review actions in this mobile surface.")
        else:
            contradictions = manifest.get("contradictions") or {}
            if contradictions:
                st.dataframe(list(contradictions.values()), hide_index=True, use_container_width=True)
            else:
                st.success("No recorded contradictions currently require review in this workspace.")
            st.caption("Publication and other protected approvals are never auto-executed by the mobile surface.")

    elif section == "Alerts":
        st.subheader("Alerts")
        st.info("Push delivery provider is not activated. Notification payload policy is implemented so lock-screen content remains non-sensitive.")

    elif section == "Company":
        st.subheader("Company")
        if principal.role is not Role.OWNER:
            st.error("Company view is owner-only.")
            st.stop()
        st.json({"workspace": engagement_id, **summary}, expanded=False)

    st.divider()
    st.subheader("Scan / Upload")
    if not principal.can(Permission.UPLOAD):
        st.caption("Your role does not permit source uploads.")
        return

    capture_mode = st.radio("Capture", ("File", "Camera"), horizontal=True)
    data: bytes | None = None
    filename: str | None = None
    capture_method = "FILE_PICKER"
    if capture_mode == "Camera":
        capture_method = "CAMERA"
        image = st.camera_input("Capture a source image")
        if image is not None:
            data = image.getvalue()
            filename = getattr(image, "name", None) or f"mobile-capture-{uuid4().hex[:8]}.jpg"
    else:
        uploaded = st.file_uploader("Choose a source record", max_upload_size=200, key="mobile-mvp-upload")
        if uploaded is not None:
            data = uploaded.getvalue()
            filename = uploaded.name

    classification_options = tuple(classifications)
    classification = st.selectbox("Classification", classification_options) if classification_options else "SOURCE_DOCUMENT"
    if data and filename:
        envelope = prepare_mobile_upload(
            principal,
            engagement_id,
            filename=filename,
            data=data,
            classification=classification,
            capture_method=capture_method,
        )
        st.caption(f"Ready · {envelope.byte_length / 1024:.1f} KB · SHA-256 {envelope.content_sha256[:12]}…")
        acknowledged = st.checkbox("I verified this capture belongs in the authorized workspace.", key="mobile-upload-ack")
        if st.button("Register mobile source", type="primary", disabled=not acknowledged):
            result = ingest_file(
                principal=principal,
                engagement_id=engagement_id,
                filename=filename,
                data=data,
                classification=classification,
                storage=storage,
                core=core,
            )
            source = result.get("source", {})
            st.success(f"Source registered through the existing authoritative intake path · {source.get('source_id', 'registered')}")

    st.caption(f"Authenticated session: {session.role} · {session.session_id}")
