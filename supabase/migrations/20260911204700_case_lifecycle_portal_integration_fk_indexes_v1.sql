create index if not exists case_lifecycle_checkpoints_checkpoint_idx on public.case_lifecycle_checkpoints(checkpoint_key);
create index if not exists case_lifecycle_events_checkpoint_idx on public.case_lifecycle_events(checkpoint_key);
