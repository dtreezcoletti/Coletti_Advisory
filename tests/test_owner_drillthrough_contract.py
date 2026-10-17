"""Static safety/visibility contracts for Owner Portal drill-through.
Browser/RLS acceptance remains mandatory before production authorization.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web/assets/app.js").read_text(encoding="utf-8")
MIGRATION = (ROOT / "supabase/migrations/20261017094500_owner_drillthrough_readonly_v1.sql").read_text(encoding="utf-8")


def test_drillthrough_routes_are_owner_gated():
    segment = APP.split("async function adminPage(view) {", 1)[1].split("if(view==='home')", 1)[0]
    assert segment.index("if(!requireAdmin()) return ''") < segment.index("if(view==='sop')")
    for route in ("sop", "cases", "case", "contracts", "kpi"):
        assert f"if(view==='{route}')" in segment


def test_sop_kpis_and_case_dossiers_link_to_read_only_authoritative_sources():
    for token in (
        "admin_sop_register_v1",
        "admin_sop_detail_v1",
        "admin_case_register_v1",
        "admin_case_detail_v1",
        "#/admin/procedures/APPROVED",
        "#/admin/procedures/DRAFT",
        "#/admin/procedures/VERIFIED",
        "#/admin/kpi/",
        "#/admin/case/",
    ):
        assert token in APP
    assert "Procedure text is not registered" in APP
    assert "Original file bytes" not in APP or "downloadable" in APP


def test_archived_synthetic_cases_are_visible_but_never_eligible_for_assignment():
    assert "Archived / closed cases" in APP
    assert "Synthetic regression case" in APP
    assert "ARCHIVED','CLOSED" in APP
    assert "admin_case_assignment_catalog_v1" in APP


def test_new_rpcs_restrict_access_to_authenticated_admin_roles():
    for function in (
        "admin_sop_detail_v1(text)",
        "admin_case_register_v1()",
        "admin_case_detail_v1(text)",
    ):
        assert f"revoke all on function public.{function} from public, anon;" in MIGRATION
        assert f"grant execute on function public.{function} to authenticated;" in MIGRATION
    assert MIGRATION.count("auth.uid() is null") == 3
    assert MIGRATION.count("private.current_user_role()") == 3
    assert "in ('owner','admin')" in MIGRATION
    assert "delete from " not in MIGRATION.lower()
    assert "update registry." not in MIGRATION.lower()


def test_case_files_do_not_claim_document_bytes_without_storage_backing():
    assert "Source inventory is not proof" in APP
    assert "case-upload-preview" in APP
    assert "createSignedUrl(btn.dataset.path,60)" in APP
    assert "recorded" in APP or "registered" in APP
