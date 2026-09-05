# Coletti & Co. Production Authentication & Authorization

Status: controlled deployment runbook

The `Coletti & Co. Live` workspace must remain locked until production identity and application authorization both pass this gate.

## Identity boundary

Coletti & Co. uses Streamlit OIDC with Google as the configured identity provider. Password verification, provider-side authentication, signed identity-token validation, OAuth/OIDC state and nonce handling, and provider session behavior remain delegated to Google and Streamlit/Authlib.

The application independently requires the authenticated identity token to contain:

- a valid issuance time (`iat`);
- a future expiration time (`exp`);
- a stable subject identifier (`sub`);
- an email address;
- `email_verified=true`.

Expired, malformed, subject-less, email-less, or unverified-email identities fail closed and are logged out.

## Application session boundary

Coletti & Co. separately enforces an application-session lifetime using `SESSION_TTL_MINUTES`. A newly issued OIDC token rotates the application session ID and resets the application-session start time. Expired application sessions require re-authentication.

## Authorization boundary

Authentication does not grant Coletti & Co. access by itself. After identity verification, the application resolves the verified email against `AUTHZ_REGISTRY_JSON`.

Each authorization record controls:

- display name;
- organization ID;
- role;
- authorized engagement/workspace IDs;
- enabled/revoked status.

An authenticated identity absent from the registry, or a record with `enabled=false`, receives no application access. Workspace selection is limited to the engagement IDs assigned to that principal, and engagement authorization is checked again before source intake or Core operations.

For the owner account, the production registry must explicitly include `eng-coletti-co-live`. Client engagements must receive their own engagement IDs rather than sharing the firm live workspace.

## Deployment secrets

Configure these only in Streamlit Community Cloud App settings / Secrets, never in Git:

- `AUTH_PROVIDER="google"`
- `SESSION_TTL_MINUTES`
- `AUTHZ_REGISTRY_JSON`
- `[auth].redirect_uri`
- `[auth].cookie_secret`
- `[auth.google].client_id`
- `[auth.google].client_secret`
- `[auth.google].server_metadata_url`

The Google OAuth client must authorize the exact deployed callback URI used by the Streamlit application.

## Acceptance check

Authentication/authorization is considered production-ready only when all of the following are verified in the deployed app:

1. an unauthenticated visitor cannot enter the production application;
2. Google sign-in completes through the configured callback;
3. an identity without a registry record is denied;
4. a disabled registry record is denied;
5. an authorized owner account receives the owner role and `eng-coletti-co-live` workspace;
6. an authorized client account cannot enter an engagement not assigned to it;
7. expired OIDC tokens require re-authentication;
8. application-session expiration requires re-authentication;
9. a newly issued OIDC token rotates the application session ID;
10. logout ends the application session;
11. the authenticated user ID propagated to ColettiOS is based on the OIDC subject, not a client-supplied display value.

Do not switch `APP_MODE` to `production` solely because authentication unit tests pass. The deployed Google OIDC client and real authorization registry must also pass this acceptance check.
