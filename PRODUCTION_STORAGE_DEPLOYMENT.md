# Coletti & Co. Production Storage Activation

Status: controlled deployment runbook

The `Coletti & Co. Live` workspace must not accept real records until this gate passes.

## Required Google Cloud Storage controls

The production bucket must:

- be private;
- enforce Uniform bucket-level access;
- enforce Public access prevention;
- have Object Versioning enabled;
- be reachable only through the configured service account permissions needed by the application;
- never store plaintext client files from the application;
- use the application client-side AES-256-GCM encryption layer before upload.

The application now inspects the bucket at startup and fails closed if Uniform bucket-level access, Public access prevention, or Object Versioning are not active, or if the service account cannot inspect the bucket.

## Application secrets required

Configure these only in the Streamlit deployment secret store, never in Git:

- `GCS_BUCKET`
- `GCP_SERVICE_ACCOUNT_JSON`
- `STORAGE_MASTER_KEY`

`STORAGE_MASTER_KEY` must be URL-safe base64 representing exactly 32 random bytes. It must not be reused from demo/test environments.

## Storage object behavior

Source records are organized by organization, engagement, and generated source ID. Before upload the application:

1. computes the SHA-256 hash of the plaintext source;
2. binds organization ID, engagement ID, source ID, original filename, and plaintext hash as AES-GCM authenticated data;
3. encrypts the bytes with AES-256-GCM using a fresh nonce;
4. uploads only ciphertext;
5. sets `Cache-Control: no-store`;
6. uses a generation precondition so an existing source object cannot be silently overwritten;
7. records the plaintext SHA-256 hash and encryption metadata with the stored object.

Report publication state is stored in the same private bucket under an engagement-scoped `_state` path and is also encrypted client-side with AES-256-GCM.

## Acceptance check

Production storage is considered ready only when all of the following are true:

- production bucket exists;
- service account can inspect and access it;
- Uniform bucket-level access is enabled;
- Public access prevention is enforced;
- Object Versioning is enabled;
- production Streamlit secrets contain valid bucket, service-account, and master-key values;
- the application starts without a production storage gate error;
- a controlled synthetic production-path upload confirms ciphertext storage, SHA-256 preservation, engagement isolation, and no overwrite behavior.

Do not switch `APP_MODE` to `production` solely because the code-level storage tests pass. The external bucket and deployment secrets must also pass this acceptance check.
