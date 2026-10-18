-- Owner-authenticated, read-only ColettiOS operating screens.
-- Does not bypass RLS for the public: execution occurs only after owner JWT authorization.
create or replace function public.owner_portal_operations_snapshot_v1()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if auth.uid() is null or not private.has_role(array['owner']::text[]) then
    raise exception 'Owner role required' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'source', 'supabase.owner_portal_operations_snapshot_v1',
    'observed_at', pg_catalog.now(),
    'invoices', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'id', i.id, 'invoice_number', i.invoice_number, 'case_id', i.case_id,
      'amount_cents', i.amount_cents, 'status', i.status, 'due_date', i.due_date,
      'provider', i.provider, 'created_at', i.created_at
    ) order by i.created_at desc) from public.invoices i), '[]'::jsonb),
    'contracts', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'id', c.id, 'title', c.title, 'case_id', c.case_id, 'contract_type', c.contract_type,
      'counterparty', c.counterparty, 'status', c.status, 'version', c.version,
      'approved_at', c.approved_at, 'updated_at', c.updated_at
    ) order by c.updated_at desc) from public.contract_records c), '[]'::jsonb),
    'pricing', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'id', p.id, 'service_key', p.service_key, 'label', p.label, 'billing_model', p.billing_model,
      'amount_min_cents', p.amount_min_cents, 'amount_max_cents', p.amount_max_cents,
      'active', p.active, 'public_visible', p.public_visible, 'updated_at', p.updated_at
    ) order by p.label) from public.pricing_config p), '[]'::jsonb),
    'services', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'service_key', s.service_key, 'name', s.name, 'summary', s.summary,
      'active', s.active, 'public_visible', s.public_visible
    ) order by s.sort_order, s.name) from public.service_definitions s), '[]'::jsonb),
    'assignments', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'id', a.id, 'case_id', a.case_id, 'staff_user_id', a.staff_user_id,
      'assignment_role', a.assignment_role, 'active', a.active,
      'assigned_at', a.assigned_at, 'updated_at', a.updated_at
    ) order by a.assigned_at desc) from public.case_assignments a), '[]'::jsonb),
    'integrations', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'integration_id', x.integration_id, 'provider', x.provider, 'service', x.service,
      'status', x.status, 'authorization_state', x.authorization_state,
      'scope_class', x.scope_class, 'last_successful_sync', x.last_successful_sync,
      'last_attempt', x.last_attempt, 'last_error', x.last_error, 'updated_at', x.updated_at
    ) order by x.provider, x.service) from registry.external_integrations x), '[]'::jsonb),
    'sops', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'sop_id', p.sop_id, 'owning_domain', p.owning_domain, 'status', p.status,
      'approved_at', p.approved_at, 'updated_at', p.updated_at
    ) order by p.owning_domain, p.updated_at desc) from registry.sops p), '[]'::jsonb)
  );
end;
$function$;
revoke all on function public.owner_portal_operations_snapshot_v1() from public;
revoke all on function public.owner_portal_operations_snapshot_v1() from anon;
grant execute on function public.owner_portal_operations_snapshot_v1() to authenticated;
