from __future__ import annotations

import io
import os
import zipfile
from types import SimpleNamespace

import pytest

from coletti_advisory.core_adapter import SyntheticCoreAdapter
from coletti_advisory.intake import ingest_file
from coletti_advisory.interface_connection_patch import _ingest_payload
from coletti_advisory.models import Principal, Role
from coletti_advisory.storage import EncryptedLocalDemoStorage


def _principal(role: Role, user_id: str, engagements=("eng-shared",)) -> Principal:
    return Principal(
        user_id,
        f"{user_id}@example.test",
        user_id.replace("-", " ").title(),
        "org-test",
        role,
        tuple(engagements),
        f"session-{user_id}",
        "2026-09-10T00:00:00+00:00",
    )


def _zip(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return stream.getvalue()


class _LegacyHarness:
    def __init__(self) -> None:
        self.app = SimpleNamespace(ingest_file=ingest_file)
        self._queue: dict[str, dict] = {}

    def _processing_queue(self) -> dict[str, dict]:
        return self._queue


def test_client_uploaded_record_is_same_canonical_source_seen_by_internal_roles(tmp_path):
    core = SyntheticCoreAdapter()
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    client = _principal(Role.CLIENT, "client-one")
    employee = _principal(Role.ANALYST, "employee-one")
    owner = _principal(Role.OWNER, "owner-one")

    result = ingest_file(
        principal=client,
        engagement_id="eng-shared",
        filename="client-statement.txt",
        data=b"The same source object must be visible through the shared case state.",
        classification="Client Provided Record",
        storage=storage,
        core=core,
        metadata={"ingestion_method": "device_upload"},
    )
    source_id = result["source"]["source_id"]

    # SyntheticCoreAdapter exposes one canonical case manifest. Role-specific
    # interfaces present that state differently; they do not create copies.
    manifest_for_employee = core.manifest(employee.engagement_ids[0])
    manifest_for_owner = core.manifest(owner.engagement_ids[0])
    assert manifest_for_employee["sources"][source_id] == manifest_for_owner["sources"][source_id]
    assert manifest_for_owner["sources"][source_id]["metadata"]["ingestion_method"] == "device_upload"


def test_upload_permission_and_case_isolation_fail_closed(tmp_path):
    core = SyntheticCoreAdapter()
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    read_only = _principal(Role.READ_ONLY, "read-only")
    client = _principal(Role.CLIENT, "client-one", engagements=("eng-client",))

    with pytest.raises(PermissionError, match="not permitted"):
        ingest_file(
            principal=read_only,
            engagement_id="eng-shared",
            filename="blocked.txt",
            data=b"must not register",
            classification="Client Provided Record",
            storage=storage,
            core=core,
        )

    with pytest.raises(PermissionError, match="not authorized"):
        ingest_file(
            principal=client,
            engagement_id="eng-other-client",
            filename="wrong-case.txt",
            data=b"must not cross cases",
            classification="Client Provided Record",
            storage=storage,
            core=core,
        )

    assert core.manifest("eng-other-client")["sources"] == {}


def test_zip_package_preserves_parent_and_child_source_lineage(tmp_path):
    core = SyntheticCoreAdapter()
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    client = _principal(Role.CLIENT, "client-one")
    legacy = _LegacyHarness()
    package = _zip(
        {
            "bank/january.txt": b"January balance 100",
            "bank/february.txt": b"February balance 90",
            "correspondence/note.txt": b"Client note",
        }
    )

    result = _ingest_payload(
        legacy,
        principal=client,
        engagement_id="eng-shared",
        storage=storage,
        core=core,
        filename="client-records.zip",
        data=package,
        classification="Client Provided Record",
        ingestion_method="device_upload",
    )

    manifest = core.manifest("eng-shared")
    parent_id = result["source_id"]
    children = result["child_source_ids"]
    assert result["archive"] is True
    assert len(children) == 3
    assert manifest["sources"][parent_id]["metadata"]["archive_container"] is True
    assert manifest["sources"][parent_id]["metadata"]["archive_member_count"] == 3

    child_paths = set()
    for child_id in children:
        metadata = manifest["sources"][child_id]["metadata"]
        assert metadata["parent_source_id"] == parent_id
        assert metadata["ingestion_method"] == "zip_archive"
        child_paths.add(metadata["archive_path"])
    assert child_paths == {
        "bank/january.txt",
        "bank/february.txt",
        "correspondence/note.txt",
    }


def test_duplicate_archive_filenames_in_different_folders_remain_distinct_sources(tmp_path):
    core = SyntheticCoreAdapter()
    storage = EncryptedLocalDemoStorage(tmp_path, os.urandom(32))
    client = _principal(Role.CLIENT, "client-one")
    legacy = _LegacyHarness()
    package = _zip({"a/statement.txt": b"A", "b/statement.txt": b"B"})

    result = _ingest_payload(
        legacy,
        principal=client,
        engagement_id="eng-shared",
        storage=storage,
        core=core,
        filename="duplicates.zip",
        data=package,
        classification="Client Provided Record",
        ingestion_method="device_upload",
    )
    assert len(result["child_source_ids"]) == 2
    assert len(set(result["child_source_ids"])) == 2
    manifest = core.manifest("eng-shared")
    assert {
        manifest["sources"][source_id]["metadata"]["archive_path"]
        for source_id in result["child_source_ids"]
    } == {"a/statement.txt", "b/statement.txt"}
