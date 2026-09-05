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

The application inspects the bucket at startup and fails closed if Uniform bucket-level access, Public access prevention, or Object Versioning are not active, or if the service account cannot inspect the bucket.

## Provisioning procedure

Provisioning is intentionally separate from application startup. The repository contains:

- `infra/gcp/storage-runtime-role.yaml` — the least-privilege runtime permission contract;
- `infra/gcp/bootstrap_storage.sh` — creates/configures the production bucket, service account, custom runtime role, and production master key;
- `infra/gcp/verify_storage.sh` — independently verifies the bucket controls, public-principal absence, and runtime role binding.

Run the bootstrap from an authenticated Google Cloud Shell or workstation with the Google Cloud CLI installed. Three values must be selected explicitly before provisioning:

- `PROJECT_ID` — the Google Cloud project that owns the production resources;
- `BUCKET_NAME` — a globally unique, non-sensitive bucket name;
- `BUCKET_LOCATION` — the intended durable bucket location.

Example shape:

```bash
export PROJECT_ID="your-project-id"
export BUCKET_NAME="your-globally-unique-production-bucket"
export BUCKET_LOCATION="your-selected-location"
bash infra/gcp/bootstrap_storage.sh
```

The bootstrap does **not** create a downloadable service-account JSON key by default. That key is only created when `CREATE_SERVICE_ACCOUNT_KEY=1` is supplied at the moment the Streamlit deployment secret store is ready to receive it. This avoids creating a long-lived credential earlier than necessary.

After provisioning, run:

```bash
PROJECT_ID="$PROJECT_ID" BUCKET_NAME="$BUCKET_NAME" bash infra/gcp/verify_storage.sh
```

The verifier must return `PRODUCTION STORAGE GATE: INFRASTRUCTURE CONTROLS PASS` before deployment credentials are installed.

## Application secrets required

Configure these only in the Streamlit deployment secret store, never in Git:

- `GCS_BUCKET`
- `GCP_SERVICE_ACCOUNT_JSON`
- `STORAGE_MASTER_KEY`

`STORAGE_MASTER_KEY` must be URL-safe base64 representing exactly 32 random bytes. It must not be reused from demo/test environments.

The generated production master-key file and any generated service-account JSON file are credential material, not repository artifacts. The repository ignores standard generated paths under `infra/gcp/`, and the bootstrap defaults to writing them outside the repository in the operator's home directory.

## Runtime permission boundary

The production application service account receives a project-defined custom role on the production bucket only. The role currently contains:

- `storage.buckets.get`;
- `storage.objects.create`;
- `storage.objects.get`;
- `storage.objects.list`;
- `storage.objects.update`;
- `storage.objects.delete`.

It does not receive bucket IAM administration or bucket configuration permissions. Provisioning authority remains separate from runtime authority.

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
- no `allUsers` or `allAuthenticatedUsers` bucket IAM binding remains;
- the application service account has the expected bucket-scoped runtime role;
- production Streamlit secrets contain valid bucket, service-account, and master-key values;
- the application starts without a production storage gate error;
- a controlled synthetic production-path upload confirms ciphertext storage, SHA-256 preservation, engagement isolation, and no overwrite behavior.

Do not switch `APP_MODE` to `production` solely because the code-level storage tests pass. The external bucket and deployment secrets must also pass this acceptance check.
