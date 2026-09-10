from __future__ import annotations

import html
import mimetypes
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

from .analysis import (
    build_analytical_issues,
    build_cross_record_comparison,
    build_operations_reconstruction,
    build_records_reconstruction,
    build_summary,
)
from .document_processing import extract_candidate_statements
from .models import Permission
from .working_copy import WorkingCopyUnavailable, read_source_for_working_copy
from .workspaces import workspace_label


_TEXT_SUFFIXES = {".txt", ".md", ".log", ".tsv", ".xml", ".html", ".htm", ".csv", ".json"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _source_metadata(source: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = source.get("metadata")
    return metadata if isinstance(metadata, Mapping) else {}


def _ingested_material_rows(manifest: dict, queue: dict[str, dict], engagement_id: str) -> list[dict]:
    """Build an operator-facing staging view from durable sources plus the live extraction queue."""
    rows: list[dict] = []
    sources = manifest.get("sources") or {}

    for source_id, source in sources.items():
        pending = queue.get(source_id)
        metadata = _source_metadata(source)
        rows.append(
            {
                "Case ID": engagement_id,
                "Source ID": source_id,
                "Material": (pending or {}).get("filename")
                or metadata.get("filename")
                or source.get("filename")
                or source.get("name")
                or source_id,
                "Classification": metadata.get("classification")
                or source.get("classification")
                or source.get("source_type")
                or "—",
                "Extraction": (pending or {}).get("extraction_method") or "Registered",
                "Candidates": len((pending or {}).get("candidates") or []),
                "Review status": "Pending extracted-statement review" if pending else "Registered source",
            }
        )

    known_ids = set(sources)
    for source_id, pending in queue.items():
        if source_id in known_ids:
            continue
        rows.append(
            {
                "Case ID": engagement_id,
                "Source ID": source_id,
                "Material": pending.get("filename") or source_id,
                "Classification": "—",
                "Extraction": pending.get("extraction_method") or "Queued",
                "Candidates": len(pending.get("candidates") or []),
                "Review status": "Pending extracted-statement review",
            }
        )

    return rows


def _selected_rows(event) -> list[int]:
    try:
        return list(event.selection.rows)
    except Exception:
        return []


def _working_copy_header(*, engagement_id: str, source_id: str, filename: str, content_hash: str) -> None:
    fingerprint = f"{content_hash[:16]}…" if content_hash else "not recorded"
    safe_case = html.escape(engagement_id, quote=True)
    safe_source = html.escape(source_id, quote=True)
    safe_filename = html.escape(filename, quote=True)
    safe_fingerprint = html.escape(fingerprint, quote=True)
    st.markdown(
        f"""
        <div style="border:1px solid #d9d0c4;border-left:4px solid #b18138;background:#fffefa;padding:1rem 1.15rem;margin:.35rem 0 1rem;border-radius:5px">
          <div style="font-family:Georgia,serif;font-size:1.05rem;letter-spacing:.04em;color:#161817">COLETTIOS WORKING COPY</div>
          <div style="font-size:.73rem;color:#777168;margin-top:.25rem">Internal workspace derivative · Not the original source record</div>
          <div style="font-size:.75rem;color:#313230;margin-top:.7rem"><strong>Case:</strong> {safe_case} &nbsp;·&nbsp; <strong>Source:</strong> {safe_source}</div>
          <div style="font-size:.72rem;color:#777168;margin-top:.2rem"><strong>Original:</strong> {safe_filename} &nbsp;·&nbsp; <strong>Source fingerprint:</strong> {safe_fingerprint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_native_working_copy(filename: str, data: bytes) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix in _IMAGE_SUFFIXES:
        st.image(data, caption=f"Working view · {filename}", use_container_width=True)
        return

    if suffix in _TEXT_SUFFIXES:
        text = data.decode("utf-8-sig", errors="replace")
        st.text_area(
            "Working material",
            value=text,
            height=460,
            disabled=True,
            key=f"working-copy-text:{hash((filename, len(data)))}",
        )
        return

    if suffix == ".pdf":
        extraction = extract_candidate_statements(filename, data, max_candidates=300)
        if extraction.candidates:
            rendered = "\n\n".join(
                f"[{candidate.locator}]\n{candidate.text}"
                for candidate in extraction.candidates
            )
            st.text_area(
                "Working material · PDF text view",
                value=rendered,
                height=520,
                disabled=True,
                key=f"working-copy-pdf:{hash((filename, len(data)))}",
            )
        else:
            st.info("This PDF has no extractable text for the inline working view. The immutable original remains preserved in encrypted storage.")
        for warning in extraction.warnings:
            st.caption(warning)
        return

    extraction = extract_candidate_statements(filename, data, max_candidates=300)
    if extraction.candidates:
        rendered = "\n\n".join(
            f"[{candidate.locator}]\n{candidate.text}"
            for candidate in extraction.candidates
        )
        st.text_area(
            "Working material · extracted view",
            value=rendered,
            height=460,
            disabled=True,
            key=f"working-copy-generic:{hash((filename, len(data)))}",
        )
    else:
        mime = mimetypes.guess_type(filename)[0] or "unknown format"
        st.info(
            f"The verified working copy was opened from encrypted storage, but {mime} does not have an inline renderer in this workspace yet. "
            "ColettiOS will not silently convert or alter the source."
        )
        for warning in extraction.warnings:
            st.caption(warning)


def _render_material_viewer(
    *,
    principal,
    engagement_id: str,
    storage,
    manifest: dict,
    queue: dict[str, dict],
    rows: list[dict],
    event,
) -> None:
    selected = _selected_rows(event)
    if not selected:
        st.caption("Select a material row above to open its ColettiOS Working Copy and source details.")
        return

    row_index = selected[0]
    if row_index < 0 or row_index >= len(rows):
        return
    row = rows[row_index]
    source_id = str(row["Source ID"])
    source = (manifest.get("sources") or {}).get(source_id) or {}
    metadata = _source_metadata(source)
    pending = queue.get(source_id) or {}
    filename = str(row["Material"])
    content_hash = str(source.get("content_hash") or "")

    with st.container(border=True):
        st.subheader(str(row["Material"]))
        c1, c2, c3 = st.columns(3)
        c1.metric("Case ID", row["Case ID"])
        c2.metric("Source ID", source_id)
        c3.metric("Review status", row["Review status"])
        st.caption(
            f"Classification: {row['Classification']} · Extraction: {row['Extraction']} · "
            f"Encrypted storage: {'Yes' if metadata.get('encrypted') else 'Not recorded'}"
        )

        if not source:
            st.warning("This queued item is not yet present in the refreshed source manifest, so the authoritative source object cannot be opened yet.")
        elif not principal.can_access(engagement_id):
            st.error("Workspace authorization failed. Working copy was not opened.")
        else:
            try:
                data = read_source_for_working_copy(
                    storage,
                    organization_id=principal.organization_id,
                    engagement_id=engagement_id,
                    source_id=source_id,
                    filename=filename,
                    content_hash=content_hash,
                )
            except WorkingCopyUnavailable as exc:
                st.warning(str(exc))
            else:
                _working_copy_header(
                    engagement_id=engagement_id,
                    source_id=source_id,
                    filename=filename,
                    content_hash=content_hash,
                )
                _render_native_working_copy(filename, data)
                st.caption(
                    "Working-copy rule: decrypted bytes exist only for this authorized render. No edits are written back to the immutable source object, and no decrypted duplicate is persisted by this viewer."
                )

        candidates = pending.get("candidates") or []
        if candidates:
            with st.expander("Extraction candidates linked to this material", expanded=False):
                for candidate in candidates:
                    locator = candidate.get("locator") or candidate.get("candidate_id") or "Extracted text"
                    text = candidate.get("text") or ""
                    st.markdown(f"**{locator}**")
                    st.write(text)

        storage_uri = metadata.get("storage_uri")
        if storage_uri:
            st.caption(f"Authoritative encrypted object: {storage_uri}")


def _results_rows(manifest: dict, queue: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    needs_analysis: list[dict] = []

    for item in build_records_reconstruction(manifest):
        row = {
            "Result type": "Record statement",
            "Finding": item.get("Record-derived statement", ""),
            "Sources": item.get("Supporting sources", ""),
            "Status": item.get("Review status", "Working"),
        }
        findings.append(row)
        if str(row["Status"]).lower() not in {"corroborated — basis recorded", "complete"}:
            needs_analysis.append({**row, "Why analysis is needed": "Record statement is not yet fully resolved/corroborated."})

    for item in build_cross_record_comparison(manifest):
        row = {
            "Result type": "Inconsistency",
            "Finding": item.get("Why it matters") or item.get("Classification") or "Cross-record inconsistency",
            "Sources": " | ".join(str(value) for value in (item.get("Sources A"), item.get("Sources B")) if value),
            "Status": item.get("Resolution state", "OPEN"),
        }
        findings.append(row)
        if str(row["Status"]).upper() not in {"RESOLVED", "COMPLETE", "CLOSED"}:
            needs_analysis.append({**row, "Why analysis is needed": "Cross-record inconsistency remains open or requires reviewer reconciliation."})

    for item in build_analytical_issues(manifest):
        row = {
            "Result type": item.get("Classification") or item.get("Issue type") or "Analytical issue",
            "Finding": item.get("Description") or item.get("Why it matters") or item.get("Issue") or "Open analytical issue",
            "Sources": item.get("Supporting sources", ""),
            "Status": item.get("Resolution state") or item.get("Status") or "OPEN",
        }
        if row not in findings:
            findings.append(row)
        needs_analysis.append({**row, "Why analysis is needed": "ColettiOS classified this item as requiring analytical/reviewer attention."})

    for source_id, pending in queue.items():
        count = len(pending.get("candidates") or [])
        if not count:
            continue
        needs_analysis.append(
            {
                "Result type": "Extraction review",
                "Finding": f"{count} extracted candidate statement(s) from {pending.get('filename') or source_id}",
                "Sources": source_id,
                "Status": "PENDING REVIEW",
                "Why analysis is needed": "Extracted material has not yet been human-verified and promoted to source-linked propositions.",
            }
        )

    return findings, needs_analysis


def _render_results(manifest: dict, queue: dict[str, dict]) -> None:
    summary = build_summary(manifest)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources", summary.get("sources", 0))
    c2.metric("Record statements", summary.get("propositions", 0))
    c3.metric("Inconsistencies", summary.get("inconsistencies", 0))
    c4.metric("Open issues", summary.get("open_issues", 0))

    findings, needs_analysis = _results_rows(manifest, queue)
    st.subheader("What ColettiOS Found")
    st.caption(
        "These are source-linked system results from the current case state. They are not independently promoted into professional conclusions."
    )
    if findings:
        st.dataframe(findings, use_container_width=True, hide_index=True)
    else:
        st.info("ColettiOS has not produced source-linked results for this case yet.")

    st.subheader("Needs Analysis")
    st.caption("Items that still require human verification, reconciliation, interpretation, or explicit disposition before downstream review/publication.")
    if needs_analysis:
        st.dataframe(needs_analysis, use_container_width=True, hide_index=True)
    else:
        st.success("No current result is flagged for additional analysis from the available case state.")

    with st.expander("Operations / source-state detail", expanded=False):
        operations = build_operations_reconstruction(manifest)
        if operations:
            st.dataframe(operations, use_container_width=True, hide_index=True)
        else:
            st.caption("No operational reconstruction rows are currently available.")


def render_owner_evidence_workspace(shell, **kwargs) -> None:
    """Owner Evidence Workspace: ingest → results → analysis, with source-safe human gates."""
    principal = kwargs["principal"]
    engagement_id = kwargs["engagement_id"]
    core = kwargs["core"]
    storage = kwargs["storage"]
    manifest = dict(kwargs["manifest"])

    if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)):
        st.error("Your role does not permit access to the internal evidence workspace.")
        st.stop()

    st.title("Evidence Workspace")
    st.caption(f"Active case · {workspace_label(engagement_id)} · {engagement_id}")

    queue = shell.legacy._processing_queue()
    ingestion_tab, results_tab, analysis_tab = st.tabs(("Ingested Materials", "Results", "Analysis"))

    with ingestion_tab:
        pending_count = len(queue)
        st.caption(
            f"{pending_count} source(s) currently have extracted material waiting for review. "
            "New uploads and Google Drive imports land here after registration."
        )
        rows = _ingested_material_rows(manifest, queue, engagement_id)
        if rows:
            event = st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="owner-ingested-materials-table",
            )
            _render_material_viewer(
                principal=principal,
                engagement_id=engagement_id,
                storage=storage,
                manifest=manifest,
                queue=queue,
                rows=rows,
                event=event,
            )
        else:
            st.info("No material has been ingested into this workspace yet. Use Record Ingestion in the sidebar to add a source.")

        st.divider()
        shell.legacy._render_extraction_review(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
        )

        st.divider()
        st.subheader("Registered Sources")
        sources = list((manifest.get("sources") or {}).values())
        if sources:
            st.dataframe(sources, use_container_width=True, hide_index=True)
        else:
            st.info("No registered sources are currently available in this workspace.")

    with results_tab:
        _render_results(manifest, queue)

    with analysis_tab:
        shell.app._render_analysis(manifest)
        st.divider()
        shell.legacy._render_contradiction_reconciliation(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
            manifest=manifest,
        )


def patch_owner_evidence_workspace(owner_runtime) -> None:
    """Patch only the owner Evidence page; employee/client routes remain unchanged."""
    if getattr(owner_runtime, "_ingested_materials_workspace_patched", False):
        return

    original_render_owner_page = owner_runtime._render_owner_page

    def _render_owner_page(shell, page: str, **kwargs):
        if page == "Evidence":
            return render_owner_evidence_workspace(shell, **kwargs)
        return original_render_owner_page(shell, page, **kwargs)

    owner_runtime._render_owner_page = _render_owner_page
    owner_runtime._ingested_materials_workspace_patched = True
