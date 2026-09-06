from __future__ import annotations

import html
from typing import Iterable

import streamlit as st

from . import app_shell as legacy
from . import main as app
from .analysis import build_analytical_issues, build_summary
from .models import Permission, Role
from .publication import PublicationStatus, published_reports
from .reporting import build_publication_gate
from .system_lab import render_system_lab
from .workspaces import live_workspace_gate_errors, workspace_environment, workspace_label


CLIENT_PAGES = (
    "Dashboard",
    "My Case",
    "Upload Documents",
    "Requests & To-Do",
    "Progress",
    "Reports",
    "Messages",
    "My Account",
    "Help & Support",
)

EMPLOYEE_PAGES = (
    "Dashboard",
    "Engagements",
    "Secure Intake",
    "Evidence",
    "Review Center",
    "Analysis",
    "Reports",
    "Administration",
)

OWNER_PAGES = (
    "Dashboard",
    "Engagements",
    "Secure Intake",
    "Evidence",
    "Review Center",
    "Analysis",
    "Reports",
    "System Lab",
    "Administration",
)


_PAGE_ICONS = {
    "Dashboard": "⌂",
    "My Case": "▣",
    "Upload Documents": "⇧",
    "Requests & To-Do": "☑",
    "Progress": "◌",
    "Reports": "▤",
    "Messages": "◫",
    "My Account": "♙",
    "Help & Support": "?",
    "Engagements": "▦",
    "Secure Intake": "⇧",
    "Evidence": "◇",
    "Review Center": "✓",
    "Analysis": "⌁",
    "System Lab": "◈",
    "Administration": "⚙",
}


def _experience(principal) -> str:
    if principal.role == Role.OWNER:
        return "owner"
    if principal.role in {Role.CLIENT, Role.READ_ONLY}:
        return "client"
    return "employee"


def _visible_pages(principal) -> list[str]:
    experience = _experience(principal)
    if experience == "client":
        pages = list(CLIENT_PAGES)
        if not principal.can(Permission.UPLOAD):
            pages.remove("Upload Documents")
        return pages

    base = list(OWNER_PAGES if experience == "owner" else EMPLOYEE_PAGES)
    if not principal.can(Permission.UPLOAD) and "Secure Intake" in base:
        base.remove("Secure Intake")
    if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)) and "Evidence" in base:
        base.remove("Evidence")
    if not principal.can(Permission.REVIEW) and "Review Center" in base:
        base.remove("Review Center")
    if not principal.can(Permission.ANALYZE) and "Analysis" in base:
        base.remove("Analysis")
    if not principal.can(Permission.MANAGE_USERS) and "Administration" in base:
        base.remove("Administration")
    if principal.role != Role.OWNER and "System Lab" in base:
        base.remove("System Lab")
    return base


def _apply_brand_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --cc-ink: #17191a;
            --cc-muted: #6e706f;
            --cc-paper: #fbfaf7;
            --cc-card: #ffffff;
            --cc-line: #e8e4dd;
            --cc-gold: #b88435;
            --cc-gold-soft: #efe1c9;
            --cc-green: #4d7762;
            --cc-green-soft: #e9f1ec;
            --cc-blue: #617f8d;
            --cc-rose: #a66f64;
            --cc-shadow: 0 10px 30px rgba(30, 31, 30, .055);
        }

        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .stApp { background: var(--cc-paper); color: var(--cc-ink); }
        .block-container { max-width: 1460px; padding-top: 1.2rem; padding-bottom: 3rem; }
        h1, h2, h3, .cc-serif { font-family: Georgia, "Times New Roman", serif !important; color: var(--cc-ink); letter-spacing: -.02em; }
        h1 { font-weight: 500 !important; }
        h2, h3 { font-weight: 500 !important; }
        [data-testid="stHeader"] { background: rgba(251,250,247,.94); border-bottom: 1px solid var(--cc-line); }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stSidebar"] { background: #fdfcf9; border-right: 1px solid var(--cc-line); min-width: 250px; max-width: 250px; }
        [data-testid="stSidebar"] > div:first-child { padding-top: .7rem; }
        [data-testid="stSidebar"] hr { border-color: var(--cc-line); }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .18rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: .62rem .7rem;
            border-radius: 7px;
            transition: background .12s ease, color .12s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #f4f0e8; }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(90deg, #a96f20, #d2a45c);
            color: #fff;
            box-shadow: 0 6px 16px rgba(184,132,53,.15);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: #fff !important; }
        [data-testid="stSidebar"] [role="radiogroup"] input { display: none; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div { border-color: var(--cc-line); background: white; }
        .stButton > button, .stDownloadButton > button {
            border-radius: 7px !important;
            border: 1px solid #d9d4cb !important;
            min-height: 2.6rem;
            font-weight: 600;
            box-shadow: none !important;
        }
        .stButton > button[kind="primary"] { background: #171d21 !important; color: white !important; border-color: #171d21 !important; }
        [data-testid="stMetric"] {
            background: var(--cc-card);
            border: 1px solid var(--cc-line);
            border-radius: 9px;
            padding: .9rem 1rem;
            box-shadow: var(--cc-shadow);
        }
        [data-testid="stDataFrame"] { border: 1px solid var(--cc-line); border-radius: 9px; overflow: hidden; background: white; }
        div[data-testid="stExpander"] { border: 1px solid var(--cc-line); border-radius: 9px; background: white; }
        div[data-testid="stTabs"] button { font-weight: 600; }
        .cc-logo { padding: .35rem .25rem .85rem; }
        .cc-logo-name { font-family: Georgia, "Times New Roman", serif; font-size: 1.5rem; letter-spacing: -.02em; }
        .cc-logo-tag { font-size: .54rem; color: #8b8174; letter-spacing: .28em; text-transform: uppercase; margin-top: .15rem; }
        .cc-topline { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.05rem 0 1rem; }
        .cc-topline-title { font-family: Georgia, "Times New Roman", serif; font-size:1.12rem; }
        .cc-pill { border:1px solid var(--cc-line); background:#fff; border-radius:999px; padding:.43rem .75rem; color:#5f615f; font-size:.78rem; }
        .cc-kicker { color:#9b7a49; text-transform:uppercase; letter-spacing:.28em; font-size:.67rem; font-weight:700; }
        .cc-hero {
            display:grid; grid-template-columns: minmax(0, 1.35fr) minmax(260px, .65fr);
            min-height: 220px; border:1px solid var(--cc-line); border-radius:9px; overflow:hidden;
            background:linear-gradient(112deg,#f7f3eb 0%,#fff 55%,#f3eee5 100%); box-shadow:var(--cc-shadow); margin-bottom:1rem;
        }
        .cc-hero-copy { padding:2.2rem 2.3rem; }
        .cc-hero h1 { font-size:clamp(2.25rem,4vw,4rem); margin:.35rem 0 .3rem; line-height:.98; }
        .cc-hero-sub { font-family:Georgia,"Times New Roman",serif; font-size:1.18rem; margin:.25rem 0 .55rem; }
        .cc-hero-body { color:var(--cc-muted); max-width:670px; line-height:1.55; }
        .cc-hero-art { position:relative; min-height:220px; background:
            linear-gradient(90deg,rgba(255,255,255,.12),rgba(255,255,255,.5)),
            radial-gradient(circle at 28% 27%,#dad5ca 0 1px,transparent 2px),
            linear-gradient(115deg,#e8e0d4 0 20%,#faf8f3 20% 42%,#d7d1c6 42% 58%,#f6f3ed 58% 100%);
        }
        .cc-hero-art:after { content:"EVIDENCE  •  CLARITY  •  PERSPECTIVE  •  FORWARD"; position:absolute; right:1.15rem; top:1.7rem; width:9rem; padding-left:.8rem; border-left:2px solid #c49855; color:#59534a; line-height:2.05; letter-spacing:.17em; font-size:.63rem; }
        .cc-grid-4 { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem; margin:.8rem 0 1rem; }
        .cc-stat { background:#fff; border:1px solid var(--cc-line); border-radius:9px; padding:1rem 1.05rem; box-shadow:var(--cc-shadow); min-height:100px; }
        .cc-stat-row { display:flex; align-items:center; gap:.8rem; }
        .cc-stat-icon { width:42px; height:42px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f5eee2; color:#9a6d2e; font-size:1.15rem; }
        .cc-stat-value { font-family:Georgia,"Times New Roman",serif; font-size:1.7rem; line-height:1; }
        .cc-stat-label { font-size:.76rem; color:var(--cc-muted); margin-top:.25rem; }
        .cc-panel { background:#fff; border:1px solid var(--cc-line); border-radius:9px; padding:1rem 1.15rem; box-shadow:var(--cc-shadow); margin:.75rem 0; }
        .cc-panel-title { font-family:Georgia,"Times New Roman",serif; font-size:1.1rem; margin-bottom:.75rem; }
        .cc-stage-wrap { display:flex; align-items:flex-start; justify-content:space-between; gap:.3rem; padding:.55rem .15rem .15rem; }
        .cc-stage { flex:1; text-align:center; min-width:0; position:relative; }
        .cc-stage:not(:last-child):after { content:""; position:absolute; top:12px; left:60%; width:80%; height:2px; background:#ddd9d2; z-index:0; }
        .cc-stage.done:not(:last-child):after { background:#81a08d; }
        .cc-stage-dot { width:25px;height:25px;border-radius:50%;margin:0 auto .45rem;background:#d9d9d7;border:3px solid #efefec;position:relative;z-index:1; }
        .cc-stage.done .cc-stage-dot { background:#659078; border-color:#e5eee8; }
        .cc-stage.current .cc-stage-dot { background:#b88435; border-color:#f2e5cf; box-shadow:0 0 0 2px #b88435; }
        .cc-stage-name { font-size:.72rem; font-weight:700; }
        .cc-stage-status { font-size:.63rem; color:#8a8b88; margin-top:.2rem; }
        .cc-list-row { display:grid; grid-template-columns:30px minmax(0,1fr) auto; align-items:center; gap:.65rem; padding:.65rem .1rem; border-bottom:1px solid #efede8; }
        .cc-list-row:last-child { border-bottom:none; }
        .cc-list-icon { width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#eef3ef;color:#557764;font-size:.75rem; }
        .cc-list-title { font-size:.82rem; font-weight:700; }
        .cc-list-sub { font-size:.7rem; color:#8b8d8a; margin-top:.12rem; }
        .cc-status { font-size:.66rem; padding:.25rem .55rem; border-radius:999px; background:var(--cc-green-soft); color:#4e735e; white-space:nowrap; }
        .cc-owner-banner { background:#171d21; color:#f5f1e9; border-radius:9px; padding:1rem 1.2rem; margin-bottom:1rem; display:flex; justify-content:space-between; gap:1rem; align-items:center; }
        .cc-owner-banner strong { font-family:Georgia,"Times New Roman",serif; font-size:1.2rem; font-weight:500; }
        .cc-owner-banner span { color:#c9c7c0; font-size:.76rem; }
        .cc-small { color:var(--cc-muted); font-size:.78rem; }
        @media (max-width: 1000px) {
            .cc-grid-4 { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .cc-hero { grid-template-columns:1fr; }
            .cc-hero-art { min-height:135px; }
            .cc-stage-wrap { overflow-x:auto; justify-content:flex-start; }
            .cc-stage { min-width:115px; }
        }
        @media (max-width: 650px) {
            .block-container { padding-left:.8rem; padding-right:.8rem; }
            .cc-grid-4 { grid-template-columns:1fr 1fr; gap:.55rem; }
            .cc-hero-copy { padding:1.45rem 1.25rem; }
            .cc-hero h1 { font-size:2.35rem; }
            .cc-topline { align-items:flex-start; flex-direction:column; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="cc-logo">
          <div class="cc-logo-name">Coletti &amp; Co.</div>
          <div class="cc-logo-tag">Records. Clarity. Forward.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_identity(principal, engagement_id: str) -> None:
    if principal.authenticated:
        role_label = "Owner" if principal.role == Role.OWNER else principal.role.value.replace("_", " ").title()
        st.sidebar.markdown(
            f"<div class='cc-small'>Authenticated as</div><div style='font-weight:700;margin:.1rem 0'>{_esc(principal.display_name)}</div>"
            f"<div class='cc-small'>Role: {_esc(role_label)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.caption("Synthetic demo session · no client identity or client data")


def _select_engagement(principal) -> str:
    options = list(principal.engagement_ids)
    selected = st.sidebar.selectbox("Authorized workspace", options, format_func=workspace_label)
    if not principal.can_access(selected):
        st.error("Workspace authorization failed.")
        st.stop()
    st.sidebar.caption(f"{workspace_environment(selected)} workspace")
    st.sidebar.divider()
    return selected


def _topbar(principal, experience: str) -> None:
    title = {"client": "Client Portal", "employee": "Team Workspace", "owner": "Owner Console"}[experience]
    role = "Full Access" if experience == "owner" else principal.role.value.replace("_", " ").title()
    st.markdown(
        f"""
        <div class="cc-topline">
          <div class="cc-topline-title">{_esc(title)}</div>
          <div class="cc-pill">{_esc(principal.display_name)} &nbsp;·&nbsp; {_esc(role)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _hero(*, kicker: str, title: str, subtitle: str, body: str) -> None:
    st.markdown(
        f"""
        <section class="cc-hero">
          <div class="cc-hero-copy">
            <div class="cc-kicker">{_esc(kicker)}</div>
            <h1>{_esc(title)}</h1>
            <div class="cc-hero-sub">{_esc(subtitle)}</div>
            <div class="cc-hero-body">{_esc(body)}</div>
          </div>
          <div class="cc-hero-art"></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _stats(items: Iterable[tuple[str, str, str]]) -> None:
    cards = []
    for icon, value, label in items:
        cards.append(
            f"<div class='cc-stat'><div class='cc-stat-row'><div class='cc-stat-icon'>{_esc(icon)}</div>"
            f"<div><div class='cc-stat-value'>{_esc(value)}</div><div class='cc-stat-label'>{_esc(label)}</div></div></div></div>"
        )
    st.markdown(f"<div class='cc-grid-4'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _source_rows(manifest: dict, limit: int = 5) -> str:
    sources = list((manifest.get("sources") or {}).values())[-limit:]
    if not sources:
        return "<div class='cc-small'>No documents have been submitted yet.</div>"
    rows = []
    for source in reversed(sources):
        meta = source.get("metadata") or {}
        filename = meta.get("filename") or source.get("source_id") or "Source record"
        classification = meta.get("classification") or "Record"
        rows.append(
            "<div class='cc-list-row'>"
            "<div class='cc-list-icon'>▤</div>"
            f"<div><div class='cc-list-title'>{_esc(filename)}</div><div class='cc-list-sub'>{_esc(classification)}</div></div>"
            "<div class='cc-status'>Received</div></div>"
        )
    return "".join(rows)


def _client_stage(records: dict, manifest: dict) -> tuple[int, list[tuple[str, str]]]:
    sources = len(manifest.get("sources") or {})
    statuses = [record.status for record in records.values()]
    published = len(published_reports(records))
    if published:
        current = 5
    elif any(status == PublicationStatus.APPROVED for status in statuses):
        current = 4
    elif any(status == PublicationStatus.IN_REVIEW for status in statuses):
        current = 3
    elif sources:
        current = 2
    else:
        current = 0
    stages = [
        ("Intake", "Complete" if current > 0 else "In progress"),
        ("Record Collection", "Complete" if current > 1 else ("In progress" if current == 1 else "Pending")),
        ("Processing", "Complete" if current > 2 else ("In progress" if current == 2 else "Pending")),
        ("Human Review", "Complete" if current > 3 else ("In progress" if current == 3 else "Pending")),
        ("Report Preparation", "Complete" if current > 4 else ("In progress" if current == 4 else "Pending")),
        ("Final Report", "Available" if current == 5 else "Pending"),
    ]
    return current, stages


def _progress_panel(records: dict, manifest: dict) -> None:
    current, stages = _client_stage(records, manifest)
    parts = []
    for idx, (name, status) in enumerate(stages):
        cls = "done" if idx < current else ("current" if idx == current else "")
        parts.append(
            f"<div class='cc-stage {cls}'><div class='cc-stage-dot'></div>"
            f"<div class='cc-stage-name'>{_esc(name)}</div><div class='cc-stage-status'>{_esc(status)}</div></div>"
        )
    st.markdown(
        f"<div class='cc-panel'><div class='cc-panel-title'>Case Progress</div><div class='cc-stage-wrap'>{''.join(parts)}</div></div>",
        unsafe_allow_html=True,
    )


def _client_dashboard(principal, engagement_id: str, manifest: dict, records: dict) -> None:
    first_name = (principal.display_name or "there").strip().split()[0]
    if first_name.lower() == "synthetic":
        first_name = "Client"
    _hero(
        kicker="Client Portal",
        title=f"Welcome, {first_name}.",
        subtitle="Thank you for trusting Coletti & Co.",
        body="We turn complex records into clarity, so you can move forward with confidence.",
    )
    current, _ = _client_stage(records, manifest)
    open_requests = 0
    _stats(
        [
            ("▣", workspace_label(engagement_id), "Your Case"),
            ("◌", f"{min(current + 1, 6)} of 6", "Stages Reached"),
            ("▤", str(len(manifest.get("sources") or {})), "Documents Submitted"),
            ("□", str(open_requests), "Open Requests"),
        ]
    )
    _progress_panel(records, manifest)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown("<div class='cc-panel-title'>Recent Activity</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='cc-panel'><div class='cc-list-row'><div class='cc-list-icon'>✓</div><div><div class='cc-list-title'>Your workspace is active</div><div class='cc-list-sub'>Secure records processing and review are available.</div></div><div class='cc-status'>Active</div></div></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("<div class='cc-panel-title'>Your Documents</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cc-panel'>{_source_rows(manifest)}</div>", unsafe_allow_html=True)


def _employee_dashboard(principal, engagement_id: str, manifest: dict, records: dict, reports: dict) -> None:
    summary = build_summary(manifest)
    gate = build_publication_gate(manifest)
    _hero(
        kicker="Coletti & Co. Team",
        title="Review with clarity.",
        subtitle=workspace_label(engagement_id),
        body="Source intake, reconstruction, contradiction review, human judgment, and controlled publication in one workspace.",
    )
    _stats(
        [
            ("▤", str(summary["sources"]), "Sources"),
            ("◇", str(summary["propositions"]), "Source-linked Propositions"),
            ("!", str(summary["inconsistencies"]), "Inconsistencies"),
            ("✓", str(gate["review_required_count"]), "Items Requiring Review"),
        ]
    )
    c1, c2 = st.columns([1.05, .95], gap="large")
    with c1:
        st.markdown("### Review Queue")
        issues = build_analytical_issues(manifest)
        if issues:
            st.dataframe(issues, use_container_width=True, hide_index=True)
        else:
            st.info("No analytical issues are currently awaiting review.")
    with c2:
        st.markdown("### Publication Status")
        st.metric("Draft reports", len(reports))
        st.metric("Published reports", len(published_reports(records)))
        st.caption("Client publication remains gated by explicit human review and approval.")


def _owner_dashboard(principal, engagement_id: str, manifest: dict, records: dict, reports: dict, app_mode: str, storage_backend: str, core_backend: str) -> None:
    summary = build_summary(manifest)
    gate = build_publication_gate(manifest)
    st.markdown(
        "<div class='cc-owner-banner'><div><strong>Owner access</strong><br><span>Executive, operational, review, system-lab, security, and administration controls are available.</span></div><div class='cc-pill'>FULL ACCESS</div></div>",
        unsafe_allow_html=True,
    )
    _hero(
        kicker="Owner Console",
        title="Coletti & Co. command view.",
        subtitle=workspace_label(engagement_id),
        body="The commercial workspace, ColettiOS evidence workflow, publication controls, and security administration are visible from one owner-only interface.",
    )
    _stats(
        [
            ("▤", str(summary["sources"]), "Sources"),
            ("!", str(summary["inconsistencies"]), "Inconsistencies"),
            ("✓", str(gate["review_required_count"]), "Review Queue"),
            ("▣", str(len(published_reports(records))), "Published Reports"),
        ]
    )
    c1, c2 = st.columns([1.15, .85], gap="large")
    with c1:
        st.markdown("### Operating Workflow")
        st.write("Intake → source-linked propositions → cross-record review → human review → report approval → client publication")
        st.caption("No report bypasses the human-review and publication gates.")
        st.markdown("### Recent Sources")
        st.markdown(f"<div class='cc-panel'>{_source_rows(manifest)}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### Runtime")
        st.metric("Mode", app_mode.upper())
        st.metric("Storage", storage_backend)
        st.metric("Core adapter", core_backend)
        st.caption("Use System Lab for clean-room validation and production-readiness checks.")


def _render_engagements(principal) -> None:
    st.title("Engagements")
    rows = [
        {
            "Workspace": workspace_label(eid),
            "Environment": workspace_environment(eid),
            "ID": eid,
            "Status": "ACTIVE",
        }
        for eid in principal.engagement_ids
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_client_case(engagement_id: str, manifest: dict, records: dict) -> None:
    st.title("My Case")
    st.caption("A client-safe view of your engagement. Internal propositions, reviewer notes, contradiction rationale, and draft reports remain private to Coletti & Co.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Case", workspace_label(engagement_id))
    c2.metric("Documents submitted", len(manifest.get("sources") or {}))
    c3.metric("Reports available", len(published_reports(records)))
    _progress_panel(records, manifest)


def _render_client_requests() -> None:
    st.title("Requests & To-Do")
    st.info("No open client requests are currently assigned in this workspace.")
    st.caption("When Coletti & Co. requests a missing record, clarification, or acknowledgment, it will appear here without exposing internal analysis.")


def _render_client_messages() -> None:
    st.title("Messages")
    st.info("Secure messaging is not yet connected to a durable message store in this build.")
    st.caption("The portal intentionally does not simulate or invent client communications.")


def _render_account(principal, engagement_id: str) -> None:
    st.title("My Account")
    st.write(f"**Name:** {principal.display_name}")
    st.write(f"**Role:** {principal.role.value.replace('_', ' ').title()}")
    st.write(f"**Authorized workspace:** {workspace_label(engagement_id)}")
    st.write(f"**Environment:** {workspace_environment(engagement_id)}")
    if principal.authenticated:
        st.write(f"**Email:** {principal.email}")


def _render_help() -> None:
    st.title("Help & Support")
    st.markdown("**Uploading records**")
    st.write("Use Upload Documents to submit source records to your authorized workspace.")
    st.markdown("**Reports**")
    st.write("Only reports explicitly reviewed, approved, and published by Coletti & Co. appear in the client portal.")
    st.markdown("**Security**")
    st.write("Workspace access is role- and engagement-scoped; production access remains subject to the configured authentication and infrastructure gates.")


def _render_administration(app_mode: str, storage_backend: str, core_backend: str, manifest: dict, principal) -> None:
    if not principal.can(Permission.MANAGE_USERS):
        st.error("Your role does not permit administration.")
        st.stop()
    st.title("Administration & Security")
    st.write(f"Mode: **{app_mode}** · Storage: **{storage_backend}** · Core adapter: **{core_backend}**")
    st.subheader("Authentication & Security Release Gate")
    for label, implemented in app.SECURITY_CONTROLS:
        st.write(f"{'✅' if implemented else '🔨'} {label}")
    st.subheader("Audit log")
    st.dataframe(manifest.get("audit_log", []), use_container_width=True)


def run() -> None:
    st.set_page_config(
        page_title="Coletti & Co. | Secure Portal",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_brand_theme()

    app_mode, storage_backend, core_backend, principal, core, storage, publication_store = app._runtime()
    _sidebar_brand()
    _sidebar_identity(principal, principal.engagement_ids[0])
    engagement_id = _select_engagement(principal)

    gate_errors = live_workspace_gate_errors(
        engagement_id,
        app_mode=app_mode,
        storage_backend=storage_backend,
        core_backend=core_backend,
        authenticated=principal.authenticated,
    )
    if gate_errors:
        st.error("Coletti & Co. Live is configured but locked until the production gate is open.")
        for error in gate_errors:
            st.write(f"• {error}")
        st.stop()

    experience = _experience(principal)
    pages = _visible_pages(principal)
    page = st.sidebar.radio(
        "Navigation",
        pages,
        format_func=lambda value: f"{_PAGE_ICONS.get(value, '•')}   {value}",
        label_visibility="collapsed",
    )
    if principal.authenticated:
        st.sidebar.divider()
        if st.sidebar.button("Log out", use_container_width=True):
            st.logout()

    _topbar(principal, experience)
    manifest = core.manifest(engagement_id)
    internal_user = experience in {"employee", "owner"}
    reports = app.build_report_bundle(manifest) if internal_user else {}
    records = app._load_publication_records(publication_store, principal, engagement_id)
    if internal_user:
        records = app.sync_drafts(records, reports)
        app._save_publication_records(publication_store, principal, engagement_id, records)

    if page == "Dashboard":
        if experience == "client":
            _client_dashboard(principal, engagement_id, manifest, records)
        elif experience == "employee":
            _employee_dashboard(principal, engagement_id, manifest, records, reports)
        else:
            _owner_dashboard(
                principal,
                engagement_id,
                manifest,
                records,
                reports,
                app_mode,
                storage_backend,
                core_backend,
            )

    elif page == "My Case":
        _render_client_case(engagement_id, manifest, records)
    elif page == "Upload Documents":
        legacy._render_secure_intake(
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )
    elif page == "Requests & To-Do":
        _render_client_requests()
    elif page == "Progress":
        st.title("Progress")
        _progress_panel(records, manifest)
        st.caption("Progress is deliberately client-safe and does not expose internal review notes or draft conclusions.")
    elif page == "Messages":
        _render_client_messages()
    elif page == "My Account":
        _render_account(principal, engagement_id)
    elif page == "Help & Support":
        _render_help()
    elif page == "Engagements":
        _render_engagements(principal)
    elif page == "Secure Intake":
        legacy._render_secure_intake(
            app_mode=app_mode,
            principal=principal,
            engagement_id=engagement_id,
            storage=storage,
            core=core,
        )
    elif page == "Evidence":
        legacy._render_evidence_workspace(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
            manifest=manifest,
        )
    elif page == "Review Center":
        if not principal.can(Permission.REVIEW):
            st.error("Your role does not permit review access.")
            st.stop()
        app._render_review_center(manifest, reports, records, publication_store, principal, engagement_id)
    elif page == "Analysis":
        if not principal.can(Permission.ANALYZE):
            st.error("Your role does not permit analysis access.")
            st.stop()
        app._render_analysis(manifest)
    elif page == "Reports":
        if internal_user:
            app._render_internal_reports(manifest, reports, records)
        else:
            app._render_client_reports(records)
    elif page == "System Lab":
        if principal.role != Role.OWNER:
            st.error("System Lab is owner-only.")
            st.stop()
        render_system_lab(
            principal=principal,
            manifest=manifest,
            app_mode=app_mode,
            storage_backend=storage_backend,
            core_backend=core_backend,
            engagement_id=engagement_id,
        )
    elif page == "Administration":
        _render_administration(app_mode, storage_backend, core_backend, manifest, principal)
