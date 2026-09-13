# Owner Workspace + AI Continuity v0.1

Status: feature branch / shadow-mode design

## Objective

Create one Owner Console that can contain both institutional owner controls and a strictly separated private-owner workspace, while also providing a ChatGPT/AI history importer that reduces dependence on conversational memory or a specific AI subscription.

## Private owner domains

The Owner Console private domain is intended to contain:

- Employment / Career (outside employment only)
- Housing
- Personal Finance
- Chapter 2
- Private Legal
- Continuity

These domains must not become employee or client workspaces. Outside employment is private because it concerns the owner working for another employer rather than Coletti & Co.

## Import path

The v0.1 importer accepts:

- a ChatGPT export ZIP containing `conversations.json`; or
- the extracted conversation JSON file directly.

It parses ChatGPT conversation mappings at message level, which allows one conversation to contain institutional, private-owner, private-legal, ambiguous, and archive-only messages.

The importer currently classifies each message into:

- `institutional`
- `owner_private`
- `legal_private`
- `archive_only`
- `ambiguous`

Candidate kinds are:

- `decision`
- `rule`
- `open_issue`
- `fact`
- `working_note`

The initial classifier is deterministic and intentionally conservative. Unknown material defaults to archive/private staging rather than being silently promoted into institutional state.

## Shadow mode

v0.1 MUST begin with:

- capture: OFF until private persistence is activated and verified;
- retrieval: OFF;
- promotion: OFF.

The current UI parser operates in-memory and can generate a complete shadow staging manifest. It does not write to the institutional registry.

## Database migration

`sql/owner_continuity_v0_1.sql` is additive only. It creates:

- `continuity_private`
- `legal_private`

Neither schema should be added to the Supabase exposed Data API schema list.

The migration includes kill switches in `continuity_private.settings`; retrieval and promotion default to false.

The raw archive itself should ultimately be stored as an encrypted owner-private object, with a hash and storage reference in `continuity_private.raw_archives`. Parsed messages and candidates remain owner-private until explicit promotion.

## Promotion rules

No conversational statement is automatically institutional truth.

Professional/institutional candidates should flow through the existing `registry.import_staging` reconciliation and human-review model before canonical promotion.

Private legal candidates require stricter source-authority handling. A conversation can preserve history or an owner assertion, but controlling status must come from an appropriate source and explicit review.

## Rollback

Ordinary rollback is feature disablement, not database restoration:

1. `promotion_enabled = false`
2. `retrieval_enabled = false`
3. `capture_enabled = false`
4. remove/disable the Owner Console continuity route
5. retain imported source and staging records for audit/review

Dropping schemas is not an ordinary rollback and should not be performed once real owner history has been imported.

## Verification before activation

Before applying the migration or importing real history:

1. run the unit tests in `tests/test_owner_continuity.py`;
2. verify ZIP path traversal and size-limit tests;
3. test with a synthetic mixed conversation;
4. confirm private schemas are not exposed through the Data API;
5. verify an employee/client principal has no retrieval route to owner-private content;
6. verify legal/private history remains non-canonical after import;
7. verify disabling retrieval immediately removes imported continuity from AI context;
8. run Supabase security advisors after any DDL is applied.

## Current feature-branch limitation

The branch contains the importer, owner-private page renderers, private navigation contract, additive SQL migration, and tests. The direct runtime entrypoint rewrite was intentionally not forced after the GitHub connector blocked that security-sensitive routing change. The final Owner Console route hook must therefore be reviewed and applied through the repository's normal merge/deployment workflow before this feature becomes visible in the live app.
