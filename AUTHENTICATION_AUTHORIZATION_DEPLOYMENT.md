# Coletti & Co. Production Authentication & Authorization

Status: controlled deployment runbook

## Single authentication authority

Supabase Auth is the sole production authentication and password authority for Coletti & Co.

There is one production sign-in and recovery surface:

- `https://colettico.com/login/`

The application must not operate a second password-reset API, Streamlit/OIDC login, owner-only login service, or proxy-derived recovery URL.

## Redirect contract

Production authentication redirects are pinned to the canonical HTTPS origin:

- Site URL: `https://colettico.com`
- Password recovery: `https://colettico.com/login/`
- Magic-link return: `https://colettico.com/login/`

The exact redirect URL must be present in the Supabase Auth Redirect URLs configuration. Supabase documents that an unapproved `redirectTo` may fall back to the configured Site URL, so both settings must agree with the canonical production host.

Compatibility routes `/recovery/` and `/reset-password/` only forward recovery parameters to `/login/`; they do not implement authentication themselves.

## Application routing after authentication

The authenticated shell is `https://colettico.com/workspace/`.

Role-aware UI routing:
- `owner` / `admin` -> `#/admin/home`
- `analyst` / `reviewer` -> `#/workspace/home`
- `client` -> `#/portal/home`

Routing does not grant authorization. Supabase Auth, authoritative role records, RLS, case membership, and staff assignment remain the enforcement controls.

## Production deployment boundary

Render serves one static application rooted at `web/`. No Python or Streamlit web service is part of the canonical production request path.

## Acceptance checks

Authentication is not VERIFIED or OPERATIONAL until deployed evidence confirms all of the following:

1. `https://colettico.com/login/` loads over HTTPS.
2. A password-reset request is accepted by Supabase.
3. The recovery email returns to `https://colettico.com/login/`, not HTTP and not another app.
4. The `PASSWORD_RECOVERY` event exposes the new-password form.
5. `updateUser({password})` succeeds and a subsequent password sign-in succeeds.
6. An unauthenticated `/workspace/` request is routed to `/login/`.
7. owner/admin, analyst/reviewer, and client identities land only in their permitted workspace routes.
8. `/owner/` and `/portal/` redirect into the same `/workspace/` application.
9. `/recovery/` and `/reset-password/` preserve recovery parameters and forward to `/login/`.
10. No legacy Python/Streamlit service is attached to the canonical domain.

Do not promote production authorization solely because repository tests pass. Deployed browser and role tests must also pass.
