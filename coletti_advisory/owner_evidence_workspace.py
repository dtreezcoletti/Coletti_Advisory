from __future__ import annotations

import streamlit as st

from .models import Permission


def _ingested_material_rows(manifest: dict, queue: dict[str, dict]) -> list[dict]:
    """Build an operator-facing staging view from durable sources plus the live extraction queue."""
    rows: list[dict] = []
    sources = manifest.get("sources") or {}

    for source_id, source in sources.items():
        pending = queue.get(source_id)
        rows.append(
            {
                "Source ID": source_id,
                "Material": (pending or {}).get("filename")
                or source.get("filename")
                or source.get("name")
                or source_id,
                "Classification": source.get("classification") or source.get("source_type") or "—",
                "Extraction": (pending or {}).get("extraction_method") or "Registered",
                "Candidates": len((pending or {}).get("candidates") or []),
                "Review status": "Pending extracted-statement review" if pending else "Registered source",
            }
        )

    # Defensive fallback: show queued material even if a backend manifest refresh is delayed.
    known_ids = set(sources)
    for source_id, pending in queue.items():
        if source_id in known_ids:
            continue
        rows.append(
            {
                "Source ID": source_id,
                "Material": pending.get("filename") or source_id,
                "Classification": "—",
                "Extraction": pending.get("extraction_method") or "Queued",
                "Candidates": len(pending.get("candidates") or []),
                "Review status": "Pending extracted-statement review",
            }
        )

    return rows


def render_owner_evidence_workspace(shell, **kwargs) -> None:
    """Owner Evidence Workspace with an explicit ingestion-to-review staging surface."""
    principal = kwargs["principal"]
    engagement_id = kwargs["engagement_id"]
    core = kwargs["core"]
    manifest = dict(kwargs["manifest"])

    if not (principal.can(Permission.ANALYZE) or principal.can(Permission.REVIEW)):
        st.error("Your role does not permit access to the internal evidence workspace.")
        st.stop()

    st.title("Evidence Workspace")

    queue = shell.legacy._processing_queue()
    pending_count = len(queue)
    expander_label = f"Ingested Materials · {pending_count} pending review" if pending_count else "Ingested Materials"
    with st.expander(expander_label, expanded=True):
        st.caption(
            "New uploads and Google Drive imports land here after source registration. Review extracted material here before any statement is promoted into ColettiOS propositions."
        )
        rows = _ingested_material_rows(manifest, queue)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No material has been ingested into this workspace yet. Use Record Ingestion in the sidebar to add a source.")

        st.divider()
        shell.legacy._render_extraction_review(
            principal=principal,
            engagement_id=engagement_id,
            core=core,
        )

    st.subheader("Sources")
    sources = list((manifest.get("sources") or {}).values())
    if sources:
        st.dataframe(sources, use_container_width=True, hide_index=True)
    else:
        st.info("No registered sources are currently available in this workspace.")

    st.subheader("Review Propositions")
    propositions = list((manifest.get("propositions") or {}).values())
    if propositions:
        st.dataframe(propositions, use_container_width=True, hide_index=True)
    else:
        st.info("No propositions have been promoted from source records yet.")

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
