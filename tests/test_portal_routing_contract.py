from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_role_aware_portal_routing_contract():
    js = (WEB / "assets" / "portal_routing_v1.js").read_text(encoding="utf-8")
    assert "owner" in js
    assert "admin" in js
    assert "analyst" in js
    assert "reviewer" in js
    assert "/admin/home" in js
    assert "/workspace/home" in js
    assert "/portal/home" in js
    assert "route.startsWith('/portal/')" in js


def test_canonical_authenticated_shell_is_unified():
    workspace = (WEB / "workspace" / "index.html").read_text(encoding="utf-8")
    assert 'data-portal="unified"' in workspace
    assert "/assets/styles.css" in workspace
    assert "/assets/portal_integration_v2.css" in workspace
    assert "/assets/portal_routing_v1.js" in workspace
    assert "/assets/app.js" in workspace
    assert "/assets/portal_integration_v2.js" in workspace
    assert 'id="main"' in workspace
    assert 'id="toast-region"' in workspace
    assert "location.hash = '#/sign-in'" in workspace


def test_legacy_role_entrypoints_redirect_to_unified_workspace():
    for relative in ("portal/index.html", "owner/index.html", "employee/index.html", "admin/index.html"):
        html = (WEB / relative).read_text(encoding="utf-8")
        assert "/workspace/" in html
        assert "location.replace('/workspace/'" in html
        assert "onrender.com" not in html


def test_universal_login_routes_every_role_to_one_authenticated_shell():
    html = (WEB / "login" / "index.html").read_text(encoding="utf-8")
    assert "${APP_ORIGIN}/workspace/#/admin/home" in html
    assert "${APP_ORIGIN}/workspace/#/workspace/home" in html
    assert "${APP_ORIGIN}/workspace/#/portal/home" in html
    assert "/owner/#/" not in html
    assert "/portal/#/" not in html

def test_portal_sop_reads_authoritative_lifecycle_snapshot():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    assert ".rpc('case_lifecycle_snapshot_v1'" in js
    assert "authoritative lifecycle state shared across authorized portals" in js
    assert "dashboard does not create duplicate case state" in js
    assert "current_checkpoint" in js
    assert "open_requests" in js
    assert "published_reports" in js


def test_portal_sop_does_not_create_a_second_lifecycle_store():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    for lifecycle_table in (
        "case_lifecycle_checkpoint_catalog",
        "case_lifecycle_checkpoints",
        "case_lifecycle_events",
    ):
        assert f"from('{lifecycle_table}')" not in js
    for internal_table in (
        "evidence_work_items",
        "review_narratives",
        "qa_checklists",
        "publication_handoffs",
    ):
        assert internal_table not in js
    assert ".insert(" not in js
    assert ".update(" not in js
    assert ".delete(" not in js


def test_checkpoint_drillthrough_covers_full_case_sop():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
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
        assert checkpoint in js
    assert "#/portal/uploads" in js
    assert "#/portal/reports" in js
    assert "#/workspace/documents" in js
    assert "#/workspace/evidence" in js
    assert "#/workspace/qa" in js
    assert "#/workspace/publishing" in js
    assert "#/admin/publications" in js
    assert "#/admin/audit" in js


def test_admin_and_owner_surfaces_have_shared_case_context_switching():
    js = (WEB / "assets" / "portal_integration_v2.js").read_text(encoding="utf-8")
    assert "ensureAdminCaseSelector" in js
    assert "case_assignments" in js
    assert "case_memberships" in js
    assert 'id="case-selector"' in js
    assert "coletti.activeCase" in js


def test_operational_visual_system_supports_long_authoritative_lifecycle():
    css = (WEB / "assets" / "portal_integration_v2.css").read_text(encoding="utf-8")
    assert "--portal-paper" in css
    assert "--portal-gold" in css
    assert "grid-auto-flow:column" in css
    assert "grid-auto-columns" in css
    assert ".portal-surface-kicker" in css
    assert ".portal-brand-block" in css


def test_public_home_remains_separate_from_authenticated_operational_shell():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "/assets/site.css" in index
    assert "/assets/site.js" in index
    assert "/assets/app.js" not in index


def test_password_recovery_token_hash_is_exchanged_in_canonical_login():
    html = (WEB / "login" / "index.html").read_text(encoding="utf-8")
    assert "verifyOtp({token_hash:tokenHash,type:'recovery'})" in html
    assert "history.replaceState(null,'',location.pathname+'?type=recovery')" in html
    assert "resetPasswordForEmail(email,{redirectTo:`${APP_ORIGIN}/login/`})" in html


def test_legacy_recovery_gate_preserves_parameters_and_uses_single_auth_surface():
    recovery_gate = (WEB / "recovery-gate" / "index.html").read_text(encoding="utf-8")
    assert "location.replace(target)" in recovery_gate
    assert "'/login/'+location.search+location.hash" in recovery_gate
    assert "createClient" not in recovery_gate

    not_found = (WEB / "404.html").read_text(encoding="utf-8")
    assert '"/recovery-gate":"/login/"' in not_found

    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "source: /recovery-gate" in render
    assert "destination: /recovery-gate/index.html" in render
