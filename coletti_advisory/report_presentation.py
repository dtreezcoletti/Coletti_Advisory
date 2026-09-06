from __future__ import annotations

import html
import json
from typing import Any, Iterable

import streamlit as st


REPORT_CSS = r"""
<style>
.cc-report-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .7rem;
    margin: .55rem 0 1rem;
}
.cc-report-summary-card {
    border: 1px solid var(--cc-line, #dcd5ca);
    background: var(--cc-card, #fffdf9);
    padding: .9rem 1rem;
    min-height: 88px;
    border-radius: 5px;
}
.cc-report-summary-label {
    color: #77716a;
    font-size: .66rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: .35rem;
}
.cc-report-summary-value {
    font-family: Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif;
    color: var(--cc-ink, #171715);
    font-size: 1.65rem;
    line-height: 1.05;
}
.cc-report-note {
    border-left: 2px solid var(--cc-gold, #94703b);
    background: rgba(148, 112, 59, .055);
    padding: .85rem 1rem;
    margin: .25rem 0 .8rem;
    color: #4d4943;
    line-height: 1.55;
}
.cc-report-table-wrap {
    width: 100%;
    overflow-x: auto;
    margin: .35rem 0 1rem;
    border: 1px solid var(--cc-line, #dcd5ca);
    border-radius: 5px;
    background: var(--cc-card, #fffdf9);
}
.cc-report-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: auto;
    font-size: .78rem;
}
.cc-report-table th {
    text-align: left;
    padding: .72rem .72rem;
    color: #706b64;
    font-size: .66rem;
    font-weight: 600;
    letter-spacing: .04em;
    background: #f6f2eb;
    border-bottom: 1px solid var(--cc-line, #dcd5ca);
    white-space: nowrap;
}
.cc-report-table td {
    vertical-align: top;
    padding: .72rem .72rem;
    color: var(--cc-ink, #171715);
    border-bottom: 1px solid #ebe5dc;
    line-height: 1.42;
    overflow-wrap: anywhere;
}
.cc-report-table tr:last-child td { border-bottom: 0; }
.cc-gate-panel {
    border: 1px solid var(--cc-line, #dcd5ca);
    border-left: 3px solid var(--cc-gold, #94703b);
    background: var(--cc-card, #fffdf9);
    padding: 1rem 1.05rem;
    margin: .35rem 0 1rem;
    border-radius: 4px;
}
.cc-gate-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .75rem;
    margin-bottom: .9rem;
}
.cc-gate-title {
    font-family: Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif;
    font-size: 1.05rem;
}
.cc-gate-status {
    border: 1px solid #d7c7ad;
    background: #f5eee3;
    padding: .3rem .55rem;
    border-radius: 999px;
    color: #75562d;
    font-size: .64rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    white-space: nowrap;
}
.cc-gate-status.ready {
    border-color: #c7d4ca;
    background: #edf3ef;
    color: #486153;
}
.cc-gate-counts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .55rem;
    margin-bottom: .85rem;
}
.cc-gate-count {
    padding: .65rem .7rem;
    background: #faf7f1;
    border: 1px solid #e7dfd3;
}
.cc-gate-count strong {
    display: block;
    font-family: Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif;
    font-size: 1.3rem;
    font-weight: 500;
    margin-bottom: .1rem;
}
.cc-gate-count span { color: #77716a; font-size: .66rem; }
.cc-gate-blockers {
    margin: .7rem 0;
    padding: .75rem .85rem;
    background: #fbf7f0;
    border: 1px solid #e8ded0;
}
.cc-gate-blockers-title {
    font-size: .67rem;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #75562d;
    margin-bottom: .4rem;
}
.cc-gate-blockers ul { margin: .2rem 0 .05rem 1.05rem; padding: 0; }
.cc-gate-blockers li { margin: .28rem 0; line-height: 1.4; }
.cc-gate-rule { color: #6f6a63; font-size: .72rem; line-height: 1.5; }

@media (max-width: 820px) {
    .cc-report-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; }
    .cc-report-summary-card { min-height: 78px; padding: .78rem .8rem; }
    .cc-report-summary-value { font-size: 1.4rem; }
    .cc-report-table-wrap { border: 0; background: transparent; overflow: visible; }
    .cc-report-table, .cc-report-table tbody, .cc-report-table tr, .cc-report-table td {
        display: block;
        width: 100%;
    }
    .cc-report-table thead { display: none; }
    .cc-report-table tr {
        border: 1px solid var(--cc-line, #dcd5ca);
        background: var(--cc-card, #fffdf9);
        border-radius: 5px;
        margin: 0 0 .65rem;
        padding: .2rem .75rem;
    }
    .cc-report-table td {
        display: grid;
        grid-template-columns: minmax(108px, 34%) minmax(0, 1fr);
        gap: .65rem;
        padding: .56rem 0;
        border-bottom: 1px solid #ebe5dc;
        font-size: .76rem;
    }
    .cc-report-table td:last-child { border-bottom: 0; }
    .cc-report-table td::before {
        content: attr(data-label);
        color: #7a746d;
        font-size: .61rem;
        font-weight: 600;
        letter-spacing: .06em;
        text-transform: uppercase;
        line-height: 1.35;
    }
    .cc-gate-head { align-items: flex-start; flex-direction: column; }
    .cc-gate-counts { grid-template-columns: 1fr; }
}

@media (max-width: 390px) {
    .cc-report-summary-grid { grid-template-columns: 1fr; }
    .cc-report-table td { grid-template-columns: 1fr; gap: .18rem; }
}
</style>
"""


_SUMMARY_LABELS = {
    "sources": "Sources",
    "propositions": "Record statements",
    "inconsistencies": "Inconsistencies",
    "open_issues": "Open issues",
}


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _display_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple, set)):
        return " · ".join(str(item) for item in value) if value else "—"
    if isinstance(value, dict):
        return "; ".join(f"{_humanize(str(key))}: {_display_value(item)}" for key, item in value.items())
    return str(value)


def summary_items(summary: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (_SUMMARY_LABELS.get(str(key), _humanize(str(key))), _display_value(value))
        for key, value in summary.items()
    ]


def responsive_table_html(rows: Iterable[dict[str, Any]]) -> str:
    normalized = [dict(row) for row in rows]
    if not normalized:
        return ""

    columns: list[str] = []
    for row in normalized:
        for key in row:
            if key not in columns:
                columns.append(key)

    head = "".join(f"<th>{_esc(column)}</th>" for column in columns)
    body_rows: list[str] = []
    for row in normalized:
        cells = "".join(
            f"<td data-label='{_esc(column)}'>{_esc(_display_value(row.get(column)))}</td>"
            for column in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    return (
        "<div class='cc-report-table-wrap'><table class='cc-report-table'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def _render_summary(summary: dict[str, Any]) -> None:
    cards = []
    for label, value in summary_items(summary):
        cards.append(
            "<div class='cc-report-summary-card'>"
            f"<div class='cc-report-summary-label'>{_esc(label)}</div>"
            f"<div class='cc-report-summary-value'>{_esc(value)}</div>"
            "</div>"
        )
    st.markdown(f"<div class='cc-report-summary-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _publication_gate_html(gate: dict[str, Any]) -> str:
    status_raw = str(gate.get("status") or "Review required")
    ready = status_raw.upper().startswith("READY")
    status = "Ready for final human approval" if ready else "Review required"
    blockers = [str(item) for item in gate.get("blockers") or []]
    blocker_html = ""
    if blockers:
        items = "".join(f"<li>{_esc(item)}</li>" for item in blockers)
        blocker_html = (
            "<div class='cc-gate-blockers'><div class='cc-gate-blockers-title'>Items to resolve or review</div>"
            f"<ul>{items}</ul></div>"
        )
    else:
        blocker_html = (
            "<div class='cc-gate-blockers'><div class='cc-gate-blockers-title'>Readiness</div>"
            "<div>No material publication blockers are currently recorded.</div></div>"
        )

    status_class = "cc-gate-status ready" if ready else "cc-gate-status"
    return (
        "<div class='cc-gate-panel'>"
        "<div class='cc-gate-head'><div class='cc-gate-title'>Publication readiness</div>"
        f"<div class='{status_class}'>{_esc(status)}</div></div>"
        "<div class='cc-gate-counts'>"
        f"<div class='cc-gate-count'><strong>{_esc(gate.get('review_required_count', 0))}</strong><span>Items requiring review</span></div>"
        f"<div class='cc-gate-count'><strong>{_esc(gate.get('corroboration_control_count', 0))}</strong><span>Corroboration controls</span></div>"
        f"<div class='cc-gate-count'><strong>{_esc(gate.get('verification_recommendation_count', 0))}</strong><span>Verification referrals</span></div>"
        "</div>"
        f"{blocker_html}"
        f"<div class='cc-gate-rule'>{_esc(gate.get('rule', ''))}</div>"
        "</div>"
    )


def _render_report_section(title: str, value: Any) -> None:
    st.subheader(title)

    if title in {"Engagement Record Summary", "Engagement Summary"} and isinstance(value, dict):
        _render_summary(value)
        return

    if title == "Publication Gate" and isinstance(value, dict):
        st.markdown(_publication_gate_html(value), unsafe_allow_html=True)
        return

    if title == "Report Version":
        version = str(value).replace("-client-ready", "")
        st.markdown(
            f"<div class='cc-report-note'><strong>Version {_esc(version)}</strong> · Client-ready report format</div>",
            unsafe_allow_html=True,
        )
        return

    if title == "Methodology Note":
        st.markdown(f"<div class='cc-report-note'>{_esc(value)}</div>", unsafe_allow_html=True)
        return

    if isinstance(value, list):
        if value:
            st.markdown(responsive_table_html(value), unsafe_allow_html=True)
        else:
            st.info(f"No {title.lower()} are available in this report.")
        return

    if isinstance(value, dict):
        if value:
            rows = [{"Item": _humanize(str(key)), "Detail": _display_value(item)} for key, item in value.items()]
            st.markdown(responsive_table_html(rows), unsafe_allow_html=True)
        else:
            st.info(f"No {title.lower()} are available in this report.")
        return

    st.write(value)


def _render_internal_reports(app_module, manifest: dict, reports: dict, records: dict) -> None:
    st.markdown(REPORT_CSS, unsafe_allow_html=True)
    st.title("Reports")
    st.caption("Controlled report drafting · source-linked · human-reviewed · client publication remains gated")

    gate = app_module.build_publication_gate(manifest)
    published_count = len(app_module.published_reports(records))
    _render_summary(
        {
            "Report drafts": len(reports),
            "Items requiring review": gate["review_required_count"],
            "Client-visible reports": published_count,
        }
    )

    tabs = st.tabs(list(reports.keys()))
    for tab, (report_name, report) in zip(tabs, reports.items()):
        record = records[report_name]
        with tab:
            st.subheader(report_name)
            workflow_state = str(record.status.value).replace("_", " ").title()
            st.caption(f"Working state: {workflow_state} · Revision {record.revision}")

            if record.published_snapshot is not None:
                st.info(
                    "A frozen client-visible version is currently published. This working draft remains separate until a new version is reviewed and explicitly published."
                )
            else:
                st.warning("No client-visible version has been published yet.")

            st.write(report["purpose"])
            st.info(report["boundary"])

            for key, value in report.items():
                if key in {"report_type", "document_status", "purpose", "boundary"}:
                    continue
                _render_report_section(_humanize(key), value)

            export = json.dumps(report, indent=2, default=str)
            safe_name = report_name.lower().replace(" ", "_") + f"_rev_{record.revision}_draft.json"
            st.download_button(
                f"Download structured {report_name} draft",
                export,
                file_name=safe_name,
                mime="application/json",
                key=f"download-{safe_name}",
            )

    with st.expander("Overall publishing readiness"):
        st.markdown(_publication_gate_html(gate), unsafe_allow_html=True)


def _render_client_reports(app_module, records: dict) -> None:
    st.markdown(REPORT_CSS, unsafe_allow_html=True)
    st.title("Reports")
    st.caption("Published Coletti & Co. reports")
    published = app_module.published_reports(records)
    if not published:
        st.info("No reports have been published to this workspace yet.")
        return

    tabs = st.tabs(list(published.keys()))
    for tab, (report_name, report) in zip(tabs, published.items()):
        with tab:
            st.subheader(report_name)
            publication = report.get("publication") or {}
            if publication:
                st.caption(
                    f"Published revision {publication.get('revision', '—')} · {publication.get('published_at', 'publication time unavailable')}"
                )
            st.info(report.get("boundary", "Published report"))
            for key, value in report.items():
                if key in {
                    "report_type",
                    "document_status",
                    "purpose",
                    "boundary",
                    "publication",
                    "publication_gate",
                }:
                    continue
                _render_report_section(_humanize(key), value)

            export = json.dumps(report, indent=2, default=str)
            safe_name = report_name.lower().replace(" ", "_") + "_published.json"
            st.download_button(
                f"Download structured {report_name}",
                export,
                file_name=safe_name,
                mime="application/json",
                key=f"client-download-{safe_name}",
            )


def patch_report_presentation(app_module) -> None:
    """Replace debug-like report rendering with responsive professional presentation."""

    app_module._render_report_section = _render_report_section
    app_module._render_internal_reports = (
        lambda manifest, reports, records: _render_internal_reports(app_module, manifest, reports, records)
    )
    app_module._render_client_reports = lambda records: _render_client_reports(app_module, records)
