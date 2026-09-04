# Authentication & Security Release Gate

## Already present

- ✅ secrets excluded from Git
- ✅ audit actors exist in ColettiOS
- ✅ commercial repo explicitly owns authentication
- ✅ Streamlit provides browser-session separation

## Implemented in the replacement commercial path

- ✅ real login through Streamlit OIDC
- ✅ password verification delegated to the configured identity provider; Coletti & Co. never stores plaintext passwords
- ✅ signed OIDC identity/session validation
- ✅ application session expiration
- ✅ re-authentication after application session expiry
- ✅ logout
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

1. a real authenticated principal is present;
2. durable encrypted Google Cloud Storage is configured; and
3. the commercial app is connected to the separately deployed private ColettiOS service adapter.

Synthetic mode is intentionally available without OIDC so the public demonstration can be viewed without exposing or accepting real client data.
