from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


REVIEW_STATES = {"DISPUTED", "CONTRADICTED", "QUARANTINED"}


def _values(manifest: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = manifest.get(key, {})
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _join(values: Iterable[str]) -> str:
    return ", ".join(str(value) for value in values if str(value))


def _source_filename(source: dict[str, Any]) -> str:
    metadata = source.get("metadata") or {}
    return str(metadata.get("filename") or source.get("source_id") or "Unknown source")


def _source_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(source.get("source_id")): source
        for source in _values(manifest, "sources")
        if source.get("source_id")
    }


def _proposition_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(prop.get("proposition_id")): prop
        for prop in _values(manifest, "propositions")
        if prop.get("proposition_id")
    }


def _reconciliation_for(manifest: dict[str, Any], contradiction_id: str) -> dict[str, Any] | None:
    for reconciliation in reversed(_values(manifest, "reconciliations")):
        contradiction_ids = [str(value) for value in reconciliation.get("contradiction_ids", [])]
        if contradiction_id in contradiction_ids:
            return reconciliation
    return None


def _source_display(source_ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> str:
    labels: list[str] = []
    for source_id in source_ids:
        source = sources.get(str(source_id), {})
        filename = _source_filename(source) if source else str(source_id)
        labels.append(f"{source_id} · {filename}")
    return _join(labels)


def _states_for(source_ids: Iterable[str], states: dict[str, Any]) -> list[str]:
    return [str(states.get(str(source_id), "UNCLASSIFIED")) for source_id in source_ids]


def _review_status(source_states: Iterable[str]) -> str:
    normalized = [str(state).upper() for state in source_states]
    if any(state in REVIEW_STATES for state in normalized):
        return "Requires review"
    if normalized and all(state == "CORROBORATED" for state in normalized):
        return "Corroborated"
    return "Working"


def _record_classes(source_ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> set[str]:
    classes: set[str] = set()
    for source_id in source_ids:
        source = sources.get(str(source_id), {})
        metadata = source.get("metadata") or {}
        record_class = str(metadata.get("classification") or "").strip()
        if record_class:
            classes.add(record_class)
    return classes


def _verification_target(source_ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> str:
    classes = _record_classes(source_ids, sources)
    targets: list[str] = []
    if "Financial Record" in classes:
        targets.append("independent record custodian or qualified financial/accounting professional")
    if "Operational Audit" in classes or "Business Record" in classes:
        targets.append("independent record custodian, process owner, or relevant subject-matter professional")
    if "Correspondence" in classes:
        targets.append("originating third party or records custodian")
    if not targets:
        targets.append("independent source/custodian or appropriate qualified professional")
    return "; ".join(dict.fromkeys(targets))


def _verification_guidance(*, issue_type: str, source_ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> tuple[str, str]:
    target = _verification_target(source_ids, sources)
    if issue_type == "Inconsistency":
        recommendation = (
            "Independent third-party verification recommended where available. "
            "If resolving the issue requires licensed or professional judgment, refer the question and supporting records to the appropriate professional."
        )
    elif issue_type == "Unresolved Question":
        recommendation = (
            "Seek independent source or custodian confirmation when available. "
            "Escalate to an appropriate qualified professional when the unresolved question requires professional determination."
        )
    else:
        recommendation = (
            "External verification may be appropriate if the current record set cannot resolve the issue; "
            "professional review is reserved for questions requiring professional judgment."
        )
    return recommendation, target


def build_summary(manifest: dict[str, Any]) -> dict[str, int]:
    contradictions = _values(manifest, "contradictions")
    escalations = _values(manifest, "escalations")
    return {
        "sources": len(_values(manifest, "sources")),
        "propositions": len(_values(manifest, "propositions")),
        "inconsistencies": len(contradictions),
        "open_issues": sum(1 for item in escalations if str(item.get("status", "OPEN")).upper() != "CLOSED"),
    }


def build_state_counts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    counts = Counter(str(value) for value in (manifest.get("source_states") or {}).values())
    return [{"Evidence state": state, "Sources": count} for state, count in sorted(counts.items())]


def build_records_reconstruction(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest)
    states = manifest.get("source_states") or {}
    rows: list[dict[str, Any]] = []
    for proposition in _values(manifest, "propositions"):
        source_ids = [str(value) for value in proposition.get("source_ids", [])]
        proposition_states = _states_for(source_ids, states)
        rows.append(
            {
                "Proposition": proposition.get("proposition_id", ""),
                "Record-derived statement": proposition.get("text", ""),
                "Supporting sources": _source_display(source_ids, sources),
                "Source states": _join(proposition_states),
                "Review status": _review_status(proposition_states),
            }
        )
    return rows


def build_operations_reconstruction(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest)
    states = manifest.get("source_states") or {}
    open_sources: dict[str, list[str]] = {}
    for escalation in _values(manifest, "escalations"):
        if str(escalation.get("status", "OPEN")).upper() == "CLOSED":
            continue
        for source_id in escalation.get("source_ids", []):
            open_sources.setdefault(str(source_id), []).append(str(escalation.get("subject") or escalation.get("task_id") or "Follow-up"))

    rows: list[dict[str, Any]] = []
    for source in _values(manifest, "sources"):
        source_id = str(source.get("source_id", ""))
        metadata = source.get("metadata") or {}
        follow_up = _join(open_sources.get(source_id, [])) or "None"
        row = {
            "Source": source_id,
            "Record": _source_filename(source),
            "Record class": metadata.get("classification", "Unclassified"),
            "Evidence state": states.get(source_id, "UNCLASSIFIED"),
            "Open operational follow-up": follow_up,
        }
        if follow_up != "None":
            recommendation, target = _verification_guidance(
                issue_type="Unresolved Question",
                source_ids=[source_id],
                sources=sources,
            )
            row["Verification recommendation"] = recommendation
            row["Potential verifier"] = target
        else:
            row["Verification recommendation"] = "None generated from the current record state"
            row["Potential verifier"] = "—"
        rows.append(row)
    return rows


def build_cross_record_comparison(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    propositions = _proposition_index(manifest)
    sources = _source_index(manifest)
    rows: list[dict[str, Any]] = []
    for contradiction in _values(manifest, "contradictions"):
        contradiction_id = str(contradiction.get("contradiction_id", ""))
        reconciliation = _reconciliation_for(manifest, contradiction_id)
        left_id = str(contradiction.get("proposition_a", ""))
        right_id = str(contradiction.get("proposition_b", ""))
        left = propositions.get(left_id, {})
        right = propositions.get(right_id, {})
        left_sources = [str(value) for value in left.get("source_ids", [])]
        right_sources = [str(value) for value in right.get("source_ids", [])]
        combined_sources = tuple(dict.fromkeys(left_sources + right_sources))
        recommendation, target = _verification_guidance(
            issue_type="Inconsistency",
            source_ids=combined_sources,
            sources=sources,
        )
        rows.append(
            {
                "Comparison": contradiction_id,
                "Classification": "Inconsistency",
                "Record statement A": left.get("text", left_id),
                "Sources A": _source_display(left_sources, sources),
                "Record statement B": right.get("text", right_id),
                "Sources B": _source_display(right_sources, sources),
                "Why it matters": contradiction.get("reason", ""),
                "Review status": "Reviewer reconciliation recorded" if reconciliation else "Requires review",
                "Reconciliation outcome": (reconciliation or {}).get("outcome", "—"),
                "Reviewer rationale": (reconciliation or {}).get("rationale", "—"),
                "Reconciled by": (reconciliation or {}).get("actor", "—"),
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )
    return rows


def build_analytical_issues(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest)
    rows: list[dict[str, Any]] = []

    for contradiction in _values(manifest, "contradictions"):
        contradiction_id = str(contradiction.get("contradiction_id", ""))
        reconciliation = _reconciliation_for(manifest, contradiction_id)
        prop_index = _proposition_index(manifest)
        source_ids: list[str] = []
        for prop_id in (contradiction.get("proposition_a"), contradiction.get("proposition_b")):
            proposition = prop_index.get(str(prop_id), {})
            source_ids.extend(str(value) for value in proposition.get("source_ids", []))
        unique_ids = tuple(dict.fromkeys(source_ids))
        recommendation, target = _verification_guidance(
            issue_type="Inconsistency",
            source_ids=unique_ids,
            sources=sources,
        )
        rows.append(
            {
                "Issue": contradiction_id,
                "Classification": "Inconsistency",
                "Description": contradiction.get("reason", ""),
                "Supporting sources": _source_display(unique_ids, sources),
                "Status": "Reviewer reconciliation recorded" if reconciliation else "Human review required",
                "Reconciliation outcome": (reconciliation or {}).get("outcome", "—"),
                "Reviewer rationale": (reconciliation or {}).get("rationale", "—"),
                "Reconciled by": (reconciliation or {}).get("actor", "—"),
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )

    for escalation in _values(manifest, "escalations"):
        if str(escalation.get("status", "OPEN")).upper() == "CLOSED":
            continue
        source_ids = tuple(dict.fromkeys(str(value) for value in escalation.get("source_ids", [])))
        recommendation, target = _verification_guidance(
            issue_type="Unresolved Question",
            source_ids=source_ids,
            sources=sources,
        )
        rows.append(
            {
                "Issue": escalation.get("task_id", ""),
                "Classification": "Unresolved Question",
                "Description": escalation.get("reason") or escalation.get("subject", ""),
                "Supporting sources": _source_display(source_ids, sources),
                "Status": escalation.get("status", "OPEN"),
                "Reconciliation outcome": "—",
                "Reviewer rationale": "—",
                "Reconciled by": "—",
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )

    return rows
