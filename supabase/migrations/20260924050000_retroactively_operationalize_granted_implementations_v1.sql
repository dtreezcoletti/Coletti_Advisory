-- Retroactive operationalization of granted work.
-- Governing rule: GRANTED = OPERATIONAL.
-- This migration intentionally preserves component evidence statuses while advancing
-- the implementation_state and clearing only the current execution blocker.
--
-- Historical blocker details are retained in source_snapshot for auditability.

create or replace function private.retroactively_operationalize_granted_implementations_v1()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_count integer := 0;
begin
  update registry.implementation_matrix im
  set implementation_state = 'OPERATIONAL',
      operational_since = coalesce(im.operational_since, now()),
      last_reconciled_at = now(),
      blocker = null,
      next_action = null,
      source_snapshot = coalesce(im.source_snapshot,'{}'::jsonb)
        || jsonb_build_object(
          'retroactive_operationalization',
          jsonb_build_object(
            'rule', 'GRANTED_MEANS_OPERATIONAL',
            'applied_at', now(),
            'prior_state', im.implementation_state,
            'prior_blocker', im.blocker
          )
        ),
      updated_at = now()
  from registry.decisions d
  where im.source_record_id = d.record_id
    and d.status = 'ACTIVE'
    and lower(coalesce(d.decision_text,'')) ~ '(granted|approved|authorized)'
    and im.implementation_state in ('PROPOSED','APPROVED','IMPLEMENTING');

  get diagnostics v_count = row_count;

  return jsonb_build_object(
    'rule', 'GRANTED_MEANS_OPERATIONAL',
    'rows_operationalized', v_count,
    'applied_at', now()
  );
end;
$$;

revoke all on function private.retroactively_operationalize_granted_implementations_v1() from public, anon, authenticated;
grant execute on function private.retroactively_operationalize_granted_implementations_v1() to service_role;

select private.retroactively_operationalize_granted_implementations_v1();
