from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_authoritative_case_lifecycle_migration_defines_full_sop_sequence():
    sql = (ROOT / "supabase" / "migrations" / "20260911203500_case_lifecycle_portal_integration_v1.sql").read_text(encoding="utf-8")
    for checkpoint in (
        "INTAKE",
        "SCREENING",
        "ACCEPTANCE",
        "CLIENT_ONBOARDING",
        "ENGAGEMENT_GATES",
        "CASE_OPENING",
        "RECORD_COLLECTION",
        "RECONSTRUCTION",
        "HUMAN_REVIEW",
        "REPORT_PREPARATION",
        "PUBLICATION_HANDOFF",
        "CLOSEOUT",
        "ARCHIVE",
    ):
        assert f"'{checkpoint}'" in sql
    assert "case_lifecycle_snapshot_v1" in sql
    assert "transition_case_checkpoint_v1" in sql
    assert "prior lifecycle checkpoint incomplete" in sql
    assert "private.can_access_case" in sql


def test_integrated_runtime_has_distinct_client_employee_admin_owner_paths():
    runtime = (ROOT / "coletti_advisory" / "portal_runtime.py").read_text(encoding="utf-8")
    assert 'return "owner"' in runtime
    assert 'return "admin"' in runtime
    assert 'return "client"' in runtime
    assert 'return "employee"' in runtime
    assert '"Clients"' in runtime
    assert '"Cases"' in runtime
    assert "run_integrated_portal_workspace" in runtime


def test_portal_lifecycle_uses_same_rpc_and_role_scoped_controls():
    py = (ROOT / "coletti_advisory" / "portal_case_lifecycle.py").read_text(encoding="utf-8")
    js = (ROOT / "web" / "assets" / "portal_lifecycle_v1.js").read_text(encoding="utf-8")
    for content in (py, js):
        assert "case_lifecycle_snapshot_v1" in content
        assert "transition_case_checkpoint_v1" in content
    assert "OPERATIONAL_STAFF_CHECKPOINTS" in py
    assert "protected" in py.lower()
    assert "Employee Portal" in js
    assert "Admin Console" in js
    assert "Client Portal" in js
    assert "Owner Console" in js


def test_public_home_preserved_while_secure_routes_boot_operational_spa():
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "Records Reconstruction &amp;" in index
    assert "secureRoute" in index
    assert "./assets/app.js" in index
    assert "./assets/portal_routing_v1.js" in index
    assert "./assets/portal_lifecycle_v1.js" in index
    assert "professional_boundary_v1.css" in index
