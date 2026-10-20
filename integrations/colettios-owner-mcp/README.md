# ColettiOS Owner MCP — Staging-only authentication gateway

Status: **source scaffold only — not deployed, not connected, not authorized to execute**.
Institution: Coletti & Co. Commercial Application (not reusable ColettiOS Core).

## Purpose

Create a secure, resource-specific OAuth 2.1 connection that lets an eligible ChatGPT
custom MCP client authenticate *as the existing Supabase Owner user*. ChatGPT sign-in
by itself is **not** a ColettiOS token. Owner consent at Supabase is still required.

This first implementation exposes **one authenticated, read-only identity proof tool**:
`verify_colettios_owner`. It never provisions workers, assigns leases, writes to
production, or grants Executive Executor permission.

## Environment and boundaries

Deploy only as an isolated **staging** Cloudflare Worker. Do not route public
`colettico.com`, merge this branch, or deploy against production until the
separate production release gate authorizes it.

Required runtime bindings (configure out of band, never commit their values):

- `SUPABASE_URL`: existing Supabase Auth issuer base URL, without a trailing slash.
- `SUPABASE_PUBLISHABLE_KEY`: publishable (non-secret) API key for user-scoped
  Supabase REST access. Never use `service_role` in the MCP gateway.
- `MCP_RESOURCE_URL`: canonical *HTTPS* staging resource URL ending in `/mcp`.
- `EXPECTED_OWNER_SUB`: the exact UUID of the human Owner's verified
  `auth.users.id`, selected through a trusted owner session, not an email guess.
- `ALLOWED_OAUTH_CLIENT_ID`: exact OAuth client ID approved for this
  ChatGPT MCP connection. Do not enable broad dynamic client registration.
- `DEPLOYMENT_STAGE=staging`: hard fail if any other value.

The project currently contains two `owner` profiles. Both being owner-role
profiles is **not** sufficient to infer which is the intended human Owner.
The OAuth token subject must match `EXPECTED_OWNER_SUB`.

## Authentication path

1. Connect an eligible ChatGPT custom MCP client to this Worker.
2. Worker advertises an RFC 9728 OAuth protected-resource document pointing
   to the existing Supabase Auth OAuth 2.1 authorization server.
3. Supabase authenticates the human using the existing portal identity,
   presents client approval, and issues a resource-scoped token using PKCE.
4. Worker validates **signature, issuer, exact resource audience, expiry,
   client ID, session ID**, and Owner subject. It then uses the **same
   user-scoped access token** (not a service-role key) to read only the user's
   own `public.profiles` row under RLS; requires `role=owner` and `status=ACTIVE`.
5. Only then may the read-only identity proof tool return a success result.

Supabase OAuth must be configured to issue tokens with
`aud=MCP_RESOURCE_URL` or another independently validated resource binding;
**never weaken the Worker to accept ordinary portal tokens whose audience is
only `authenticated`.** Verify the OAuth server's resource parameter and
audience support before enabling the connection. An incompatible provider
configuration must remain blocked.

The Worker needs an asymmetric Supabase signing key exposed via the
issuer JWKS endpoint. If JWTs are issued with a symmetric-only key, do not
accept them via a browser-side secret or disable verification; configure an
appropriate asymmetric key strategy first.

## Mandatory acceptance tests

- Anonymous request: 401 with OAuth protected-resource metadata challenge.
- Wrong resource audience, issuer, signature, expired token, wrong client ID,
  absent session or revoked/not-current Owner: denied.
- Client or second owner-profile token: denied, even if role is owner.
- Verified Owner token + exact registered client ID + scoped audience +
  active profile: identity tool succeeds, exposing no user PII.
- Read-only tools operate; write/provision/lease tools do **not** exist.
- Supabase RLS denies cross-user profile access.
- Disconnect and token expiry stop use; refresh behavior is tested.
- No production routes, migrations, or credentials changed.
- A full staging evidence record is captured before any next phase.

**Operational caveat:** A successfully authenticated Owner is not automatically
an authorized execution lease. Each future write tool requires additional
Dispatcher lease validation, resource scoping, immutable audit logging,
idempotency, expiry enforcement, rollback, and separate acceptance tests.

**ChatGPT plan prerequisite:** As of October 20, 2026, custom full MCP write
actions are documented for ChatGPT Business/Enterprise/Edu, not Plus.
Do not treat the OAuth design as evidence that the account has that feature.

## Release process

1. Provision an independent staging deployment and enable Supabase OAuth 2.1
   with a controlled authorization endpoint and exact client registration.
2. Verify the Owner's exact Supabase user ID via the trusted Owner Portal.
3. Confirm token audience/resource support, issuer discovery, `offline_access`
   / refresh behavior, and JWKS algorithm before connecting.
4. Generate and commit a dependency lockfile **before build or deployment**.
5. Run `npm ci`, `npm run check`, threat-model review, and invalid-token tests.
6. Connect using the ChatGPT custom MCP management UI **only if eligible**,
   complete the user's OAuth consent, and invoke `verify_colettios_owner`.
7. Preserve acceptance evidence; request separate authorization for any
   later write-capable integration.

This source branch intentionally changes **no live infrastructure**.
