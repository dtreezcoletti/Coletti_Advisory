-- Production truth / security hardening closure, 2026-10-02.
-- Keeps database authority aligned with the latest release manifest and preserves
-- fail-closed internal function resolution.

alter function archive.prevent_immutable_change() set search_path = '';
alter function search.hybrid_message_candidates(text, integer) set search_path = '';

undefined
