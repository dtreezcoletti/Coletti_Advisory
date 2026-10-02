from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20261002210000_production_truth_and_function_hardening_v1.sql"
LOGIN = ROOT / "web/login/index.html"
OWNER = ROOT / "web/owner/index.html"


def test_owner_snapshot_reads_release_authority_instead_of_hardcoding_false():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "rm.production_authorized" in sql
    assert "rm.human_approval_required" in sql
    assert "rm.release_status" in sql
    assert "rm.environment" in sql
    assert "'production_authorized', false" not in sql
    assert "'case_lifecycle_catalog'" in sql
    assert "'implementation_lifecycle'" in sql


def test_internal_function_search_paths_are_pinned():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "alter function archive.prevent_immutable_change() set search_path = '';" in sql
    assert "alter function search.hybrid_message_candidates(text, integer) set search_path = '';" in sql


def test_staff_authentication_stays_same_origin_and_owner_surface_exists():
    login = LOGIN.read_text(encoding="utf-8")
    owner = OWNER.read_text(encoding="utf-8")
    assert "${location.origin}/owner/#/admin/home" in login
    assert "${location.origin}/owner/#/workspace/home" in login
    assert "data-portal=\"owner\"" in owner
    assert "/assets/portal_routing_v1.js" in owner


def test_reconciliation_uses_current_status_vocabulary():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "im.database_status in ('VERIFIED','NOT_REQUIRED')" in sql
    assert "status_vocabulary','VERIFIED_NOT_REQUIRED'" in sql
    assert "Database Confirmed" not in sql
