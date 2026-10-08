"""Contract checks for the accepted-intake case/member/assignment handoff.

These are source-level regression checks. They do not establish a real
authenticated client or employee browser acceptance test.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / (
    "20261008170244_auto_grant_accepted_intake_client_case_membership_20261008.sql"
)


def test_client_case_membership_is_granted_to_intake_user():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    normalized = " ".join(sql.split())
    assert "insert into public.case_memberships(case_id,user_id,access_level,active)" in normalized
    assert "values(v_case,i.user_id,'client',true)" in normalized
    assert "on conflict (case_id,user_id) do nothing;" in normalized


def test_client_grant_preserves_existing_engagement_and_identity_gates():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "i.status <> 'accepted'" in sql
    assert "l.user_id=i.user_id" in sql
    assert "l.relationship_role='primary'" in sql
    assert "private.has_controlled_engagement_acceptance_v1(p_intake_id,null)" in sql
    assert "private.is_admin()" in sql


def test_membership_is_created_before_assignment_and_existing_audit():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    membership = sql.index("insert into public.case_memberships(")
    assignment = sql.index("insert into public.case_assignments(")
    audit = sql.index("insert into public.audit_events(")
    assert membership < assignment < audit
    assert "'case_opened_and_assigned'" in sql
