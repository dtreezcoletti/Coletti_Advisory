from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_control_contains_authoritative_client_and_case_migrations():
    migrations = ROOT / "supabase" / "migrations"
    required = (
        "20260911181526_clients_operating_spec_v1.sql",
        "20260911182131_clients_operating_spec_v1_actions.sql",
        "20260911182155_clients_operating_spec_v1_detail_email.sql",
        "20260911182348_clients_operating_spec_v1_case_scope.sql",
        "20260911182657_clients_operating_spec_v1_privacy_hardening.sql",
        "20260911182940_clients_operating_spec_v1_acceptance_automation.sql",
        "20260911183432_clients_operating_spec_v1_fk_index.sql",
        "20260911203500_case_lifecycle_portal_integration_v1.sql",
        "20260911204700_case_lifecycle_portal_integration_fk_indexes_v1.sql",
    )
    for name in required:
        assert (migrations / name).exists(), name


def test_case_lifecycle_is_one_authoritative_13_checkpoint_sequence():
    sql = (ROOT / "supabase" / "migrations" / "20260911203500_case_lifecycle_portal_integration_v1.sql").read_text(encoding="utf-8")
    checkpoints = (
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
    )
    for checkpoint in checkpoints:
        assert f"'{checkpoint}'" in sql
    assert "case_lifecycle_snapshot_v1" in sql
    assert "transition_case_checkpoint_v1" in sql
    assert "prior lifecycle checkpoint incomplete" in sql


def test_browser_and_streamlit_portals_read_same_lifecycle_authority():
    browser = (ROOT / "web" / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    streamlit = (ROOT / "coletti_advisory" / "portal_case_lifecycle.py").read_text(encoding="utf-8")
    assert "case_lifecycle_snapshot_v1" in browser
    assert "case_lifecycle_snapshot_v1" in streamlit
    assert "transition_case_checkpoint_v1" in streamlit


def test_distinct_client_employee_admin_owner_runtime_is_installed():
    runtime = (ROOT / "coletti_advisory" / "portal_runtime.py").read_text(encoding="utf-8")
    app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    for experience in ("owner", "admin", "client", "employee"):
        assert f'return "{experience}"' in runtime
    assert "run_integrated_portal_workspace(experience_shell)" in app
    assert "patch_clients_operating_surface" in app
    assert "patch_admin_client_navigation" in app


def test_supabase_logout_and_admin_navigation_are_closed_out():
    runtime = (ROOT / "coletti_advisory" / "portal_runtime.py").read_text(encoding="utf-8")
    nav = (ROOT / "coletti_advisory" / "admin_navigation_fix.py").read_text(encoding="utf-8")
    assert "supabase_auth.sign_out()" in runtime
    assert 'st.session_state["_portal_requested_page"]' in nav
    assert "Role.ADMIN" in nav


def test_clients_v1_controlled_documents_are_present():
    assert (ROOT / "docs" / "CLIENTS_OPERATING_SPEC_v1.md").exists()
    assert (ROOT / "docs" / "CLIENT_LIFECYCLE_SOP_v1.md").exists()
