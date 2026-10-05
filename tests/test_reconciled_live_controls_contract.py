from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_registry_memories_is_explicitly_fail_closed() -> None:
    migration = read("supabase/migrations/20261005095000_reconciliation_live_controls_v1.sql")
    assert "alter table registry.memories enable row level security" in migration
    assert "create policy memories_fail_closed" in migration
    assert "using (false)" in migration
    assert "with check (false)" in migration
    assert "revoke all on table registry.memories from anon" in migration
    assert "revoke all on table registry.memories from authenticated" in migration
    assert "revoke all on table registry.memories from service_role" in migration


def test_pons_runtime_preserves_dual_porta_and_human_authority() -> None:
    migration = read("supabase/migrations/20261005095000_reconciliation_live_controls_v1.sql")
    assert "private.pons_request_transfer_impl_v1" in migration
    assert "private.pons_decide_transfer_impl_v1" in migration
    assert "private.pons_record_transfer_impl_v1" in migration
    assert "private.pons_close_pathway_impl_v1" in migration
    assert "both source and destination PORTA approvals are required" in migration
    assert "estates_general_gate','APPROVED'" in migration
    assert "auth.uid() is null or not private.is_admin()" in migration
    assert "grant execute on function public.pons_request_transfer_v1" in migration


def test_consultation_bridge_is_narrow_and_does_not_duplicate_square_event() -> None:
    migration = read("supabase/migrations/20261005095000_reconciliation_live_controls_v1.sql")
    assert "dispatcher.consultation_bookings" in migration
    assert "public.square_consultation_event_v1" in migration
    assert "service role required" in migration
    assert "Consultation Morning — Protected" in migration
    assert "duplicate_consultation_event_prohibited" in migration
    assert "square_consultation_bridge" in migration
    assert "POLICY_APPROVED" in migration
    assert "v_cmd.operation not in ('CREATE','DELETE','RECONCILE')" in migration
    assert "grant execute on function public.square_consultation_event_v1" in migration
    assert "to service_role" in migration
