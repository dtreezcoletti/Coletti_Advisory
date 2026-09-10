from __future__ import annotations

import io
import zipfile

import pytest

from coletti_advisory.connection_architecture import (
    DESTINATION_REGISTRY,
    assert_drill_through_registered,
    page_for,
    role_has_capability,
)
from coletti_advisory.models import Role
from coletti_advisory.operational_lifecycle import (
    LIFECYCLE_STAGES,
    can_promote,
    language_for,
    lifecycle_display,
)
from coletti_advisory.universal_ingestion import IngestionSafetyError, inspect_zip


def _zip(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return stream.getvalue()


def test_operational_lifecycle_is_exact_approved_sequence():
    assert LIFECYCLE_STAGES == (
        "DESIGNED",
        "CODED",
        "DATA_WIRED",
        "PERMISSION_TESTED",
        "DRILL_THROUGH_VERIFIED",
        "CROSS_INTERFACE_VERIFIED",
        "GOLDEN_PATH_PASSED",
        "MESSY_PATH_PASSED",
        "OPERATIONAL",
    )
    assert lifecycle_display() == (
        "Designed → Coded → Data Wired → Permission Tested → Drill-Through Verified → "
        "Cross-Interface Verified → Golden Path Passed → Messy Path Passed → Operational"
    )


def test_operational_cannot_be_promoted_without_deployment_verification():
    assert not can_promote("MESSY_PATH_PASSED", "OPERATIONAL")
    assert can_promote("MESSY_PATH_PASSED", "OPERATIONAL", deployment_verified=True)
    assert not can_promote("CODED", "DRILL_THROUGH_VERIFIED")


def test_connected_language_begins_at_drill_through_stage():
    assert "connected" not in language_for("DATA_WIRED")["allowed"]
    assert "connected" in language_for("DRILL_THROUGH_VERIFIED")["allowed"]


def test_every_core_operating_object_has_a_canonical_destination():
    object_types = (
        "decision", "approval", "blocker", "carryover", "due_today", "source", "record", "case",
        "report", "invoice", "receivable", "payment", "contract", "expense", "revenue", "capacity",
        "employee", "assignment", "knowledge", "policy", "implementation", "notification", "integration",
        "deployment", "fix", "referral", "communication",
    )
    assert_drill_through_registered(object_types)
    assert set(object_types) <= set(DESTINATION_REGISTRY)
    assert page_for("decision", Role.OWNER) == "Decisions"
    assert page_for("decision", Role.REVIEWER) == "Review Center"


def test_google_drive_and_zip_are_universal_for_upload_capable_profiles():
    for role in (Role.CLIENT, Role.ANALYST, Role.REVIEWER, Role.ADMIN, Role.OWNER):
        assert role_has_capability(role, "records_upload")
        assert role_has_capability(role, "google_drive_import")
        assert role_has_capability(role, "zip_archive_import")
    assert not role_has_capability(Role.READ_ONLY, "records_upload")


def test_zip_inspection_preserves_paths_and_nested_archives():
    nested = _zip({"inner/statement.txt": b"nested statement"})
    package = _zip({
        "bank/statement.pdf": b"%PDF synthetic",
        "emails/export.csv": b"date,subject\n2026-01-01,test",
        "nested.zip": nested,
    })
    inspection = inspect_zip(package)
    assert inspection.file_count == 3
    paths = {item.path for item in inspection.items}
    assert "bank/statement.pdf" in paths
    nested_item = next(item for item in inspection.items if item.path == "nested.zip")
    assert nested_item.nested[0].path == "inner/statement.txt"


def test_zip_rejects_path_traversal():
    package = _zip({"../escape.txt": b"bad"})
    with pytest.raises(IngestionSafetyError, match="Unsafe archive path"):
        inspect_zip(package)


def test_zip_rejects_executable_payloads():
    package = _zip({"documents/readme.txt": b"ok", "payload.exe": b"MZ"})
    with pytest.raises(IngestionSafetyError, match="Executable or package"):
        inspect_zip(package)


def test_corrupt_zip_fails_closed():
    with pytest.raises(IngestionSafetyError, match="corrupt or unsupported"):
        inspect_zip(b"not-a-zip")
