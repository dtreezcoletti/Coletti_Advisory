from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20261002212500_operational_brief_email_queue_v1.sql"


def test_operational_brief_queue_is_idempotent_dst_safe_and_provider_separated():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "at time zone 'America/Chicago'" in sql
    assert "on conflict (idempotency_key) do nothing" in sql
    assert "'OWNER_PRIMARY'" in sql
    assert "'resend'" in sql
    assert "'QUEUED'" in sql
    assert "cron.schedule" in sql
    assert "'*/10 * * * *'" in sql
    assert "DAILY_0900" in sql
    assert "DAILY_1900" in sql
    assert "RESEND_API_KEY" not in sql


def test_operational_brief_queue_is_not_client_callable():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "revoke all on function private.queue_operational_brief_emails_v1(timestamptz) from public, anon, authenticated;" in sql
    assert "grant execute on function private.queue_operational_brief_emails_v1(timestamptz) to postgres;" in sql
