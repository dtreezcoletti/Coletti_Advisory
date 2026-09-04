# Legacy Migration Register

Status date: 2026-09-04

## Replacement branch objective

Retire the case-driven Streamlit dashboard and replace the active commercial code path with a synthetic, configuration-driven Coletti & Co. application that consumes ColettiOS through a defined interface.

## Completed on `release/coletti2-migration-2026-09-04`

- legacy case UI removed from the active entrypoint;
- historical/default case constants removed with retired legacy modules;
- duplicated core modules retired from the commercial branch;
- synthetic fixture is the only default engagement;
- Streamlit OIDC authentication path added;
- RBAC and engagement authorization added;
- application session expiration and logout added;
- authenticated actor context propagated through the ColettiOS adapter contract;
- AES-256-GCM encrypted intake storage added;
- SHA-256 source hashing added;
- durable Google Cloud Storage backend implemented for production configuration;
- synthetic adapter retained only for public demonstration mode;
- production mode fails closed without authenticated identity, GCS, and private ColettiOS HTTP adapter;
- CORS/XSRF protections restored in Streamlit configuration.

## Remaining deployment boundary

The public Git history predates this cleanup and may still contain retired historical material. Current-branch cleanup does not erase prior commits. Repository visibility/history remediation is therefore a separate administrative action.

The live `coletti2.streamlit.app` cutover must not accept real client data until OIDC secrets, authorization registry, durable storage credentials, and the private ColettiOS service endpoint are configured.
