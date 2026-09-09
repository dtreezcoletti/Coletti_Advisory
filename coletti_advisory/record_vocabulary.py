from __future__ import annotations

from typing import Any, Iterable

import streamlit as st


# Presentation-only vocabulary map. Internal/API/database compatibility keys are
# intentionally not renamed here.
_PAGE_LABELS = {
    "Evidence": "Records",
}

_LABELS = {
    "Evidence State": "Source State",
    "Evidence state": "Source state",
    "Evidence State Summary": "Source State Summary",
    "Evidence/Publication Readiness Meter": "Record/Publication Readiness Meter",
    "Evidence Passport": "Record Passport",
}


def display_page_label(value: str) -> str:
    return _PAGE_LABELS.get(str(value), str(value))


def display_label(value: str) -> str:
    return _LABELS.get(str(value), str(value))


def display_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate human-facing column labels without mutating source payloads."""
    translated: list[dict[str, Any]] = []
    for row in rows:
        translated.append({display_label(str(key)): value for key, value in dict(row).items()})
    return translated


def patch_report_presentation(report_module) -> None:
    """Translate legacy report keys only at render time.

    Structured compatibility keys such as evidence_state_summary may remain in
    stored snapshots while the client/employee presentation shows Source State.
    """
    if getattr(report_module, "_record_vocabulary_patched", False):
        return

    original_humanize = report_module._humanize
    original_table = report_module.responsive_table_html

    def humanize(value: str) -> str:
        return display_label(original_humanize(value))

    def responsive_table_html(rows: Iterable[dict[str, Any]]) -> str:
        return original_table(display_rows(rows))

    report_module._humanize = humanize
    report_module.responsive_table_html = responsive_table_html
    report_module._record_vocabulary_patched = True


def _source_state_rows(app_module, manifest: dict) -> list[dict[str, Any]]:
    return display_rows(app_module.build_state_counts(manifest))


def patch_app_display(app_module) -> None:
    """Replace visible legacy Evidence wording while preserving workflow logic."""
    if getattr(app_module, "_record_vocabulary_patched", False):
        return

    def render_analysis(manifest: dict) -> None:
        st.title("Analysis")
        st.caption(
            "Internal reconstruction workspace · source-linked · human-reviewed · "
            "not a licensed professional determination"
        )

        summary = app_module.build_summary(manifest)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sources reviewed", summary["sources"])
        c2.metric("Record propositions", summary["propositions"])
        c3.metric("Inconsistencies", summary["inconsistencies"])
        c4.metric("Open issues", summary["open_issues"])

        st.subheader("Reconstruction Overview")
        app_module._show_table(
            _source_state_rows(app_module, manifest),
            empty_message="No source-state data is available for this engagement yet.",
        )

        records_tab, operations_tab, comparison_tab, issues_tab = st.tabs(
            [
                "Records Reconstruction",
                "Operations Reconstruction",
                "Cross-Record Comparison",
                "Analytical Issues",
            ]
        )

        with records_tab:
            st.caption(
                "Record-derived propositions with their supporting source IDs, filenames, "
                "source states, and review status."
            )
            app_module._show_table(
                display_rows(app_module.build_records_reconstruction(manifest)),
                empty_message="No record-derived propositions have been created yet.",
            )

        with operations_tab:
            st.caption(
                "Operational record inputs and unresolved follow-ups. This view does not infer "
                "process deviations unless the records support them."
            )
            app_module._show_table(
                display_rows(app_module.build_operations_reconstruction(manifest)),
                empty_message="No operational record inputs are available yet.",
            )

        with comparison_tab:
            st.caption(
                "Side-by-side record statements where the current record set identifies a conflict requiring review."
            )
            app_module._show_table(
                display_rows(app_module.build_cross_record_comparison(manifest)),
                empty_message="No cross-record inconsistencies are currently recorded.",
            )

        with issues_tab:
            st.caption(
                "Issues are classified without converting them into legal, accounting, investigative, "
                "or other licensed conclusions."
            )
            app_module._show_table(
                display_rows(app_module.build_analytical_issues(manifest)),
                empty_message="No analytical issues are currently open.",
            )

    def render_review_center(manifest: dict, reports: dict, records: dict, store, principal, engagement_id: str) -> None:
        st.title("Review Center")
        st.caption("Human review sits between internal analysis and any client-facing report publication.")

        issues = app_module.build_analytical_issues(manifest)
        gate = app_module.build_publication_gate(manifest)

        c1, c2, c3 = st.columns(3)
        c1.metric("Analytical issues", len(issues))
        c2.metric("Verification routes", gate["verification_recommendation_count"])
        c3.metric("Reports published", len(app_module.published_reports(records)))

        st.subheader("Analytical Review Queue")
        app_module._show_table(display_rows(issues), empty_message="No analytical issues are currently awaiting review.")

        st.subheader("Open ColettiOS Escalations")
        app_module._show_table(
            list((manifest.get("escalations") or {}).values()),
            empty_message="No ColettiOS escalations are currently open.",
        )

        st.subheader("Report Approval & Publishing")
        st.caption(
            "Open issues may remain documented in a report. Publication requires an explicit reviewer decision "
            "that those issues, boundaries, and verification routes are accurately presented."
        )

        for report_name, report in reports.items():
            record = records[report_name]
            with st.expander(
                f"{report_name} · {record.status.value} · Revision {record.revision}",
                expanded=True,
            ):
                st.write(f"Current draft fingerprint: `{record.draft_hash[:16]}…`")
                if record.published_snapshot is not None:
                    st.success(
                        f"A prior client snapshot exists from {record.published_at or 'an earlier publication'}. "
                        "It remains frozen unless explicitly revoked or replaced by a newly approved publication."
                    )

                if record.status in {app_module.PublicationStatus.DRAFT, app_module.PublicationStatus.REVOKED}:
                    note = st.text_input(
                        "Review note",
                        value=record.review_note or "",
                        key=f"review-note-{report_name}",
                        placeholder="Optional note for the review record",
                    )
                    if st.button("Send to Review", key=f"send-review-{report_name}"):
                        app_module.send_to_review(record, actor=principal.user_id, note=note)
                        app_module._save_publication_records(store, principal, engagement_id, records)
                        st.rerun()

                elif record.status == app_module.PublicationStatus.IN_REVIEW:
                    if record.reviewed_at:
                        st.caption(f"Review opened by {record.reviewed_by} at {record.reviewed_at}")
                    acknowledged = st.checkbox(
                        "I reviewed the source-linked analysis, unresolved issues, service boundaries, "
                        "and verification/referral guidance for this report.",
                        key=f"ack-{report_name}",
                    )
                    if st.button("Approve Report", disabled=not acknowledged, key=f"approve-{report_name}"):
                        app_module.approve_report(record, actor=principal.user_id)
                        app_module._save_publication_records(store, principal, engagement_id, records)
                        st.rerun()

                elif record.status == app_module.PublicationStatus.APPROVED:
                    st.success(f"Approved by {record.approved_by} at {record.approved_at}")
                    st.warning(
                        "Publishing creates a frozen client-visible snapshot. Later records will create a new "
                        "draft revision rather than mutate this release."
                    )
                    if st.button("Publish to Client", type="primary", key=f"publish-{report_name}"):
                        app_module.publish_report(record, actor=principal.user_id, report=report)
                        app_module._save_publication_records(store, principal, engagement_id, records)
                        st.rerun()

                elif record.status == app_module.PublicationStatus.PUBLISHED:
                    st.success(f"Published by {record.published_by} at {record.published_at}")
                    if st.button("Revoke Client Publication", key=f"revoke-{report_name}"):
                        app_module.revoke_report(record, actor=principal.user_id)
                        app_module._save_publication_records(store, principal, engagement_id, records)
                        st.rerun()

        st.caption(gate["rule"])

    app_module._render_analysis = render_analysis
    app_module._render_review_center = render_review_center
    app_module._record_vocabulary_patched = True
