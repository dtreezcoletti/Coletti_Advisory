# Authentication & Security Release Gate

## Already present

- ✅ secrets excluded from Git
- ✅ audit actors exist in ColettiOS
- ✅ commercial repo explicitly owns authentication
- ✅ Streamlit provides browser-session separation

## Implemented in the replacement commercial path

- ✅ real login through Streamlit OIDC
- ✅ password verification delegated to the configured identity provider; Coletti & Co. never stores plaintext passwords
- ✅ OIDC identity verification delegated to Streamlit/Authlib, including the provider flow and signed identity token processing
- ✅ explicit `iat` / `exp` identity-token lifetime enforcement on every authenticated rerun
- ✅ application session expiration
- ✅ re-authentication after identity-token or application-session expiry
- ✅ logout through `st.logout()`; current Streamlit also signs out of the identity provider when supported by the configured OIDC provider
- ✅ application authorization revocation through `AUTHZ_REGISTRY_JSON` (`enabled=false`)
- ✅ RBAC enforcement
- ✅ engagement-level authorization
- ✅ authenticated upload pipeline
- ✅ AES-256-GCM encrypted storage implementation
- ✅ verified SHA-256 file hashing
- ✅ authenticated audit actor propagation

## Portal correction

OLD:

```text
Client Authentication
[ dropdown containing client names ]
```

NEW (after a real OIDC login):

```text
Authenticated as:
Demetriés Coletti
Role: Owner

Authorized workspace:
[ Coletti & Co. Synthetic Demo ▼ ]
```

The workspace selector is authorization, not identity. Users may only see engagements granted to their authenticated account.

## Production gate

Production mode fails closed unless all three are true:

1. a real authenticated principal is present and its token/session lifetime is valid;
2. durable encrypted Google Cloud Storage is configured; and
3. the commercial app is connected to the separately deployed private ColettiOS service adapter.

Synthetic mode is intentionally available without OIDC so the public demonstration can be viewed without exposing approved client data. Demo uploads are explicitly synthetic-only and use encrypted ephemeral storage.
