from __future__ import annotations

import json
from collections import Counter
from typing import Any

import streamlit as st

from .models import Role
from .owner_continuity import ContinuityDomain, ImportBundle, parse_ai_export


OWNER_SECTIONS = (
    "Executive",
    "Institution",
    "Private",
    "Continuity",
)

PRIVATE_AREAS = (
    "Employment / Career",
    "Housing",
    "Personal Finances",
    "Chapter 2",
    "Private Legal",
)

INSTITUTION_AREAS = (
    "Coletti & Co.",
    "ColettiOS",
    "Dispatcher",
)


def _require_owner(principal) -> None:
    if principal.role != Role.OWNER:
        st.error("Owner Workspace is restricted to the owner account.")
        st.stop()


def _bundle_key() -> str:
    return "_owner_continuity_import_bundle"


def _get_bundle() -> ImportBundle | None:
    value = st.session_state.get(_bundle_key())
    return value if isinstance(value, ImportBundle) else None


def _render_overview(bundle: ImportBundle | None) -> None:
    st.title("Owner Workspace")
    st.caption("Owner-only operating environment · institutional control and private life remain separate security domains")

    c1, c2, c3 = st.columns(3)
    c1.metric("Institution", "3 domains")
    c2.metric("Private", "5 areas")
    c3.metric("Continuity", "Shadow mode" if bundle else "Not imported")

    st.subheader("Workspace boundaries")
    left, right = st.columns(2)
    with left:
        st.markdown("**Institution**")
        for item in INSTITUTION_AREAS:
            st.write(f"• {item}")
        st.caption("Business and system state. Eligible for employee access only through explicit role/engagement authorization.")
    with right:
        st.markdown("**Private Owner**")
        for item in PRIVATE_AREAS:
            st.write(f"• {item}")
        st.caption("Owner-only. Employees and clients must receive no retrieval path into these records.")

    if bundle:
        st.subheader("Latest continuity import")
        counts = bundle.domain_counts()
        a, b, c, d = st.columns(4)
        a.metric("Messages", bundle.messages_discovered)
        b.metric("Institutional", counts[ContinuityDomain.INSTITUTIONAL.value])
        c.metric("Owner private", counts[ContinuityDomain.OWNER_PRIVATE.value])
        d.metric("Legal private", counts[ContinuityDomain.LEGAL_PRIVATE.value])
        st.info("Shadow mode is active: imported history can be inspected, but nothing is promoted into authoritative state.")


def _render_institution() -> None:
    st.title("Owner Workspace · Institution")
    st.caption("Owner control plane for the institution. Private-owner material is excluded from this context.")
    selection = st.radio("Institutional domain", INSTITUTION_AREAS, horizontal=True)
    if selection == "Coletti & Co.":
        st.subheader("Coletti & Co.")
        st.write("Commercial operations, services, website, client operations, pricing, referrals, and institutional administration.")
    elif selection == "ColettiOS":
        st.subheader("ColettiOS")
        st.write("Architecture, governance, implementation state, production readiness, DARI, testing, and release control.")
    else:
        st.subheader("Dispatcher")
        st.write("Cross-system coordination, implementation queue, approvals, change control, and operational state.")
    st.caption("v0.1 establishes the owner-facing boundary. Persistent domain summaries will be wired after continuity staging is verified.")


def _render_private() -> None:
    st.title("Owner Workspace · Private")
    st.caption("Private owner life. This workspace is not an employee workspace and is not a Coletti & Co. client engagement.")
    selection = st.selectbox("Private area", PRIVATE_AREAS)
    if selection == "Employment / Career":
        st.subheader("Employment / Career")
        st.write("Outside employment, job search, recruiters, applications, interviews, compensation, and career planning belong here.")
    elif selection == "Housing":
        st.subheader("Housing")
        st.write("Rent, housing search, utilities, landlord matters, and housing planning.")
    elif selection == "Personal Finances":
        st.subheader("Personal Finances")
        st.write("Owner personal cash flow, obligations, balances, budgeting, and planning. This is separate from company accounting.")
    elif selection == "Chapter 2":
        st.subheader("Chapter 2")
        st.write("Personal planning, capacity, life administration, and owner-only continuity.")
    else:
        st.subheader("Private Legal")
        st.write("Private legal matters, including divorce history, remain owner-only and require stricter source-authority controls before canonical promotion.")
        st.warning("Legal/private history is never automatically promoted from conversational memory.")


def _message_preview(bundle: ImportBundle, *, limit: int = 250) -> list[dict[str, Any]]:
    rows = []
    for item in bundle.messages[:limit]:
        rows.append(
            {
                "Domain": item.domain.value,
                "Review": "YES" if item.needs_review else "",
                "Kind": item.candidate_kind.value,
                "Role": item.role,
                "Conversation": item.conversation_title,
                "Text": item.text[:240],
                "Confidence": f"{item.confidence:.2f}",
            }
        )
    return rows


def _render_import_results(bundle: ImportBundle) -> None:
    counts = bundle.domain_counts()
    st.success(f"Parsed {bundle.messages_discovered:,} messages across {bundle.conversations_discovered:,} conversations.")
    st.caption(f"Source fingerprint: {bundle.archive_sha256[:20]}…")
    for warning in bundle.warnings:
        st.warning(warning)

    a, b, c, d, e = st.columns(5)
    a.metric("Institutional", counts[ContinuityDomain.INSTITUTIONAL.value])
    b.metric("Owner private", counts[ContinuityDomain.OWNER_PRIVATE.value])
    c.metric("Legal private", counts[ContinuityDomain.LEGAL_PRIVATE.value])
    d.metric("Ambiguous", counts[ContinuityDomain.AMBIGUOUS.value])
    e.metric("Needs review", bundle.review_count)

    role_counts = Counter(item.role for item in bundle.messages)
    with st.expander("Import diagnostics"):
        st.json(
            {
                "mode": "shadow",
                "source_system": bundle.source_system,
                "roles": dict(role_counts),
                "candidate_counts": bundle.candidate_counts(),
                "domain_counts": counts,
            }
        )

    st.subheader("Classification preview")
    st.caption("Preview is intentionally capped. The import manifest contains the complete parsed staging set.")
    st.dataframe(_message_preview(bundle), use_container_width=True, hide_index=True)

    manifest = json.dumps(bundle.staging_manifest(), indent=2, ensure_ascii=False)
    st.download_button(
        "Download shadow staging manifest",
        manifest,
        file_name="owner_continuity_shadow_manifest.json",
        mime="application/json",
    )

    st.warning(
        "Promotion is disabled in v0.1. No imported conversation statement becomes an institutional, personal, or legal fact from this screen."
    )


def _render_continuity() -> None:
    st.title("Owner Workspace · Continuity")
    st.caption("Import ChatGPT/AI history, separate mixed conversations by message, and stage durable context without automatic promotion.")

    st.subheader("Import AI history")
    st.write("Upload the ChatGPT export ZIP directly, or upload the extracted conversations JSON file.")
    uploaded = st.file_uploader(
        "ChatGPT / AI export",
        type=["zip", "json"],
        max_upload_size=250,
        help="The v0.1 parser reads ChatGPT conversation JSON. Raw bytes are processed in-memory in this branch until the private persistence migration is activated.",
        key="owner-continuity-upload",
    )

    analyze = st.button("Analyze in shadow mode", type="primary", disabled=uploaded is None)
    if analyze and uploaded is not None:
        try:
            bundle = parse_ai_export(uploaded.name, uploaded.getvalue())
        except (ValueError, json.JSONDecodeError) as exc:
            st.error(f"Import rejected: {exc}")
        else:
            st.session_state[_bundle_key()] = bundle
            st.rerun()

    bundle = _get_bundle()
    if bundle:
        _render_import_results(bundle)
        if st.button("Clear staged import"):
            st.session_state.pop(_bundle_key(), None)
            st.rerun()
    else:
        st.info("No AI history is staged in this session.")

    with st.expander("v0.1 safety state", expanded=True):
        st.write("✅ Owner-only UI route")
        st.write("✅ Message-level mixed-chat classification")
        st.write("✅ Legal-private conservative routing")
        st.write("✅ ZIP path/size validation")
        st.write("✅ Shadow staging manifest")
        st.write("🔒 Persistent private archive: migration prepared, not activated")
        st.write("🔒 Canonical promotion: OFF")
        st.write("🔒 DARI retrieval from imported history: OFF")


def render_owner_workspace(*, principal) -> None:
    _require_owner(principal)
    section = st.sidebar.radio("Owner mode", OWNER_SECTIONS, key="owner-workspace-section")
    bundle = _get_bundle()
    if section == "Executive":
        _render_overview(bundle)
    elif section == "Institution":
        _render_institution()
    elif section == "Private":
        _render_private()
    else:
        _render_continuity()
