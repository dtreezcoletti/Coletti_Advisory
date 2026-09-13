from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260913051500_fix_stable_identifier_trigger_cross_table_fields.sql"


def test_shared_stable_identifier_trigger_uses_dynamic_row_fields():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "to_jsonb(old)->>'client_id'" in sql
    assert "to_jsonb(new)->>'client_id'" in sql
    assert "to_jsonb(old)->>'case_id'" in sql
    assert "to_jsonb(new)->>'case_id'" in sql
    assert "to_jsonb(old)->>'source_id'" in sql
    assert "to_jsonb(new)->>'source_id'" in sql


def test_shared_trigger_does_not_directly_dereference_table_specific_fields():
    sql = MIGRATION.read_text(encoding="utf-8")
    for expression in (
        "old.client_id",
        "new.client_id",
        "old.case_id",
        "new.case_id",
        "old.source_id",
        "new.source_id",
    ):
        assert expression not in sql
