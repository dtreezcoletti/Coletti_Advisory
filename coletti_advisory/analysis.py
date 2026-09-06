from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


REVIEW_STATES = {"DISPUTED", "CONTRADICTED", "QUARANTINED"}
CONTROL_ROLES = {"CONTROL_RECORD", "SYSTEM_METADATA", "MANIFEST", "AUDIT_CONTROL"}
CONTROL_CLASSES = {"SYSTEM METADATA", "CONTROL RECORD", "MANIFEST"}


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


def _is_control_source(source: dict[str, Any]) -> bool:
    metadata = source.get("metadata") or {}
    role = str(metadata.get("source_role") or metadata.get("record_role") or "").strip().upper()
    record_class = str(metadata.get("classification") or "").strip().upper()
    filename = _source_filename(source).lower()
    if role in CONTROL_ROLES or record_class in CONTROL_CLASSES:
        return True
    return filename.endswith("_manifest.json") or filename.endswith("manifest.json")


def _source_index(manifest: dict[str, Any], *, substantive_only: bool = False) -> dict[str, dict[str, Any]]:
    rows = _values(manifest, "sources")
    if substantive_only:
        rows = [source for source in rows if not _is_control_source(source)]
    return {
        str(source.get("source_id")): source
        for source in rows
        if source.get("source_id")
    }


def _is_system_metadata_text(text: str) -> bool:
    normalized = str(text or "").strip()
    return normalized.startswith("[$.") or normalized.startswith("$.")


def _is_substantive_proposition(
    proposition: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> bool:
    if _is_system_metadata_text(str(proposition.get("text") or "")):
        return False
    source_ids = [str(value) for value in proposition.get("source_ids", [])]
    if not source_ids:
        return False
    return any(source_id in sources for source_id in source_ids)


def _proposition_index(manifest: dict[str, Any], *, substantive_only: bool = False) -> dict[str, dict[str, Any]]:
    source_index = _source_index(manifest, substantive_only=True)
    rows = _values(manifest, "propositions")
    if substantive_only:
        rows = [prop for prop in rows if _is_substantive_proposition(prop, source_index)]
    return {
        str(prop.get("proposition_id")): prop
        for prop in rows
        if prop.get("proposition_id")
    }


def _canonical_contradiction_groups(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    propositions = _proposition_index(manifest, substantive_only=True)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for contradiction in _values(manifest, "contradictions"):
        left = str(contradiction.get("proposition_a") or "")
        right = str(contradiction.get("proposition_b") or "")
        if not left or not right or left == right:
            continue
        if left not in propositions or right not in propositions:
            continue
        key = tuple(sorted((left, right)))
        group = groups.setdefault(
            key,
            {
                "canonical_id": str(contradiction.get("contradiction_id") or ""),
                "proposition_a": key[0],
                "proposition_b": key[1],
                "reason": str(contradiction.get("reason") or ""),
                "contradiction_ids": [],
            },
        )
        contradiction_id = str(contradiction.get("contradiction_id") or "")
        if contradiction_id:
            group["contradiction_ids"].append(contradiction_id)
        if not group["reason"] and contradiction.get("reason"):
            group["reason"] = str(contradiction.get("reason"))
    return list(groups.values())


def _reconciliation_for_any(manifest: dict[str, Any], contradiction_ids: Iterable[str]) -> dict[str, Any] | None:
    wanted = {str(value) for value in contradiction_ids}
    for reconciliation in reversed(_values(manifest, "reconciliations")):
        recorded = {str(value) for value in reconciliation.get("contradiction_ids", [])}
        if wanted & recorded:
            return reconciliation
    return None


def _source_display(source_ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> str:
    labels: list[str] = []
    for source_id in source_ids:
        source = sources.get(str(source_id), {})
        if not source:
            continue
        labels.append(f"{source_id} · {_source_filename(source)}")
    return _join(labels)


def _states_for(source_ids: Iterable[str], states: dict[str, Any]) -> list[str]:
    return [str(states.get(str(source_id), "UNCLASSIFIED")) for source_id in source_ids]


def _corroboration_basis(source_id: str, source: dict[str, Any]) -> str:
    metadata = source.get("metadata") or {}
    basis = metadata.get("corroborating_source_ids") or metadata.get("corroboration_basis") or []
    if isinstance(basis, str):
        return basis.strip()
    if isinstance(basis, (list, tuple)):
        return _join(str(value) for value in basis)
    return ""


def _review_status(source_ids: Iterable[str], states: dict[str, Any], sources: dict[str, dict[str, Any]]) -> str:
    ids = [str(value) for value in source_ids]
    normalized = [str(states.get(source_id, "UNCLASSIFIED")).upper() for source_id in ids]
    if any(state in REVIEW_STATES for state in normalized):
        return "Requires review"
    if normalized and all(state == "CORROBORATED" for state in normalized):
        if all(_corroboration_basis(source_id, sources.get(source_id, {})) for source_id in ids):
            return "Corroborated — basis recorded"
        return "Corroboration basis not recorded"
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


def _resolution_state(reconciliation: dict[str, Any] | None) -> str:
    if not reconciliation:
        return "OPEN"
    outcome = str(reconciliation.get("outcome") or "").lower()
    rationale = str(reconciliation.get("rationale") or "").lower()
    combined = f"{outcome} {rationale}"
    if any(token in combined for token in ("unresolved", "remains open", "pending confirmation")):
        return "OPEN_AFTER_REVIEW"
    if any(token in combined for token in ("independent", "custodian confirmed", "verified", "corroborat")):
        return "CORROBORATED_RESOLUTION"
    if any(token in combined for token in ("client", "clarif", "provided context", "missing context")):
        return "EXPLAINED"
    return "REVIEWER_RESOLVED"


def _verification_state(resolution_state: str) -> str:
    if resolution_state == "CORROBORATED_RESOLUTION":
        return "COMPLETE"
    return "RECOMMENDED"


def _verification_guidance(
    *,
    issue_type: str,
    source_ids: Iterable[str],
    sources: dict[str, dict[str, Any]],
    resolution_state: str = "OPEN",
) -> tuple[str, str]:
    if resolution_state == "CORROBORATED_RESOLUTION":
        return "No additional verification generated from the current resolution state.", "—"
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
    sources = _source_index(manifest, substantive_only=True)
    propositions = _proposition_index(manifest, substantive_only=True)
    contradictions = _canonical_contradiction_groups(manifest)
    escalations = [
        item
        for item in _values(manifest, "escalations")
        if str(item.get("status", "OPEN")).upper() != "CLOSED"
        and any(str(source_id) in sources for source_id in item.get("source_ids", []))
    ]
    return {
        "sources": len(sources),
        "propositions": len(propositions),
        "inconsistencies": len(contradictions),
        "open_issues": len(escalations),
    }


def build_state_counts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest, substantive_only=True)
    states = manifest.get("source_states") or {}
    counts = Counter(str(states.get(source_id, "UNCLASSIFIED")) for source_id in sources)
    return [{"Evidence state": state, "Sources": count} for state, count in sorted(counts.items())]


def build_records_reconstruction(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest, substantive_only=True)
    states = manifest.get("source_states") or {}
    rows: list[dict[str, Any]] = []
    for proposition in _proposition_index(manifest, substantive_only=True).values():
        source_ids = [str(value) for value in proposition.get("source_ids", []) if str(value) in sources]
        rows.append(
            {
                "Proposition": proposition.get("proposition_id", ""),
                "Record-derived statement": proposition.get("text", ""),
                "Supporting sources": _source_display(source_ids, sources),
                "Source states": _join(_states_for(source_ids, states)),
                "Review status": _review_status(source_ids, states, sources),
                "Corroboration basis": _join(
                    _corroboration_basis(source_id, sources[source_id])
                    for source_id in source_ids
                    if str(states.get(source_id, "")).upper() == "CORROBORATED"
                ) or "—",
            }
        )
    return rows


def build_operations_reconstruction(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest, substantive_only=True)
    states = manifest.get("source_states") or {}
    open_sources: dict[str, list[str]] = {}
    for escalation in _values(manifest, "escalations"):
        if str(escalation.get("status", "OPEN")).upper() == "CLOSED":
            continue
        for source_id in escalation.get("source_ids", []):
            source_id = str(source_id)
            if source_id in sources:
                open_sources.setdefault(source_id, []).append(
                    str(escalation.get("subject") or escalation.get("task_id") or "Follow-up")
                )

    rows: list[dict[str, Any]] = []
    for source_id, source in sources.items():
        metadata = source.get("metadata") or {}
        follow_up = _join(open_sources.get(source_id, [])) or "None"
        row = {
            "Source": source_id,
            "Record": _source_filename(source),
            "Record class": metadata.get("classification", "Unclassified"),
            "Evidence state": states.get(source_id, "UNCLASSIFIED"),
            "Corroboration basis": _corroboration_basis(source_id, source) or "—",
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
    propositions = _proposition_index(manifest, substantive_only=True)
    sources = _source_index(manifest, substantive_only=True)
    rows: list[dict[str, Any]] = []
    for group in _canonical_contradiction_groups(manifest):
        reconciliation = _reconciliation_for_any(manifest, group["contradiction_ids"])
        resolution_state = _resolution_state(reconciliation)
        left = propositions[group["proposition_a"]]
        right = propositions[group["proposition_b"]]
        left_sources = [str(value) for value in left.get("source_ids", []) if str(value) in sources]
        right_sources = [str(value) for value in right.get("source_ids", []) if str(value) in sources]
        combined_sources = tuple(dict.fromkeys(left_sources + right_sources))
        recommendation, target = _verification_guidance(
            issue_type="Inconsistency",
            source_ids=combined_sources,
            sources=sources,
            resolution_state=resolution_state,
        )
        rows.append(
            {
                "Comparison": group["canonical_id"],
                "Related comparison IDs": _join(group["contradiction_ids"]),
                "Classification": "Inconsistency",
                "Record statement A": left.get("text", group["proposition_a"]),
                "Sources A": _source_display(left_sources, sources),
                "Record statement B": right.get("text", group["proposition_b"]),
                "Sources B": _source_display(right_sources, sources),
                "Why it matters": group.get("reason", ""),
                "Review status": "Human review required" if not reconciliation else "Human review recorded",
                "Resolution state": resolution_state,
                "Reconciliation outcome": (reconciliation or {}).get("outcome", "—"),
                "Reviewer rationale": (reconciliation or {}).get("rationale", "—"),
                "Reviewed by": (reconciliation or {}).get("actor", "—"),
                "Verification state": _verification_state(resolution_state),
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )
    return rows


def build_analytical_issues(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _source_index(manifest, substantive_only=True)
    propositions = _proposition_index(manifest, substantive_only=True)
    rows: list[dict[str, Any]] = []

    for group in _canonical_contradiction_groups(manifest):
        reconciliation = _reconciliation_for_any(manifest, group["contradiction_ids"])
        resolution_state = _resolution_state(reconciliation)
        source_ids: list[str] = []
        for prop_id in (group["proposition_a"], group["proposition_b"]):
            proposition = propositions[prop_id]
            source_ids.extend(
                str(value) for value in proposition.get("source_ids", []) if str(value) in sources
            )
        unique_ids = tuple(dict.fromkeys(source_ids))
        recommendation, target = _verification_guidance(
            issue_type="Inconsistency",
            source_ids=unique_ids,
            sources=sources,
            resolution_state=resolution_state,
        )
        rows.append(
            {
                "Issue": group["canonical_id"],
                "Related issue IDs": _join(group["contradiction_ids"]),
                "Classification": "Inconsistency",
                "Description": group.get("reason", ""),
                "Supporting sources": _source_display(unique_ids, sources),
                "Status": "Human review required" if not reconciliation else "Human review recorded",
                "Resolution state": resolution_state,
                "Reconciliation outcome": (reconciliation or {}).get("outcome", "—"),
                "Reviewer rationale": (reconciliation or {}).get("rationale", "—"),
                "Reviewed by": (reconciliation or {}).get("actor", "—"),
                "Verification state": _verification_state(resolution_state),
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )

    for escalation in _values(manifest, "escalations"):
        if str(escalation.get("status", "OPEN")).upper() == "CLOSED":
            continue
        source_ids = tuple(
            dict.fromkeys(
                str(value) for value in escalation.get("source_ids", []) if str(value) in sources
            )
        )
        if not source_ids:
            continue
        recommendation, target = _verification_guidance(
            issue_type="Unresolved Question",
            source_ids=source_ids,
            sources=sources,
        )
        rows.append(
            {
                "Issue": escalation.get("task_id", ""),
                "Related issue IDs": "—",
                "Classification": "Unresolved Question",
                "Description": escalation.get("reason") or escalation.get("subject", ""),
                "Supporting sources": _source_display(source_ids, sources),
                "Status": escalation.get("status", "OPEN"),
                "Resolution state": "OPEN",
                "Reconciliation outcome": "—",
                "Reviewer rationale": "—",
                "Reviewed by": "—",
                "Verification state": "RECOMMENDED",
                "Verification recommendation": recommendation,
                "Potential verifier": target,
            }
        )

    return rows
