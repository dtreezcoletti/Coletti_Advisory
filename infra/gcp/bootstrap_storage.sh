#!/usr/bin/env bash
set -euo pipefail

# Coletti & Co. production GCS bootstrap.
# Run from the repository root in an authenticated Google Cloud Shell or local
# environment with the gcloud CLI installed.

: "${PROJECT_ID:?Set PROJECT_ID to the Google Cloud project that will own production storage}"
: "${BUCKET_NAME:?Set BUCKET_NAME to a globally unique, non-sensitive bucket name}"
: "${BUCKET_LOCATION:?Set BUCKET_LOCATION explicitly; bucket location is a durable deployment decision}"

SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-coletti-advisory-storage}"
ROLE_ID="${ROLE_ID:-ColettiAdvisoryStorageRuntime}"
ROLE_FILE="${ROLE_FILE:-infra/gcp/storage-runtime-role.yaml}"
MASTER_KEY_OUTPUT="${MASTER_KEY_OUTPUT:-${HOME}/coletti-advisory-storage-master-key.txt}"
CREATE_SERVICE_ACCOUNT_KEY="${CREATE_SERVICE_ACCOUNT_KEY:-0}"
SERVICE_ACCOUNT_KEY_OUTPUT="${SERVICE_ACCOUNT_KEY_OUTPUT:-${HOME}/coletti-advisory-storage-service-account.json}"

command -v gcloud >/dev/null 2>&1 || { echo "gcloud CLI is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
[[ -f "${ROLE_FILE}" ]] || { echo "Role definition not found: ${ROLE_FILE}" >&2; exit 1; }

umask 077
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
ROLE_NAME="projects/${PROJECT_ID}/roles/${ROLE_ID}"
BUCKET_URI="gs://${BUCKET_NAME}"

echo "Configuring project ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "Enabling required APIs"
gcloud services enable storage.googleapis.com iam.googleapis.com --project "${PROJECT_ID}" >/dev/null

if gcloud iam service-accounts describe "${SA_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Service account already exists: ${SA_EMAIL}"
else
  echo "Creating service account: ${SA_EMAIL}"
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Coletti Advisory Production Storage" \
    --project "${PROJECT_ID}" >/dev/null
fi

if gcloud iam roles describe "${ROLE_ID}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Updating custom runtime role: ${ROLE_NAME}"
  gcloud iam roles update "${ROLE_ID}" \
    --project "${PROJECT_ID}" \
    --file "${ROLE_FILE}" >/dev/null
else
  echo "Creating custom runtime role: ${ROLE_NAME}"
  gcloud iam roles create "${ROLE_ID}" \
    --project "${PROJECT_ID}" \
    --file "${ROLE_FILE}" >/dev/null
fi

if gcloud storage buckets describe "${BUCKET_URI}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Bucket already exists: ${BUCKET_URI}"
else
  echo "Creating production bucket: ${BUCKET_URI} in ${BUCKET_LOCATION}"
  gcloud storage buckets create "${BUCKET_URI}" \
    --project "${PROJECT_ID}" \
    --location "${BUCKET_LOCATION}" \
    --uniform-bucket-level-access \
    --public-access-prevention >/dev/null
fi

echo "Enforcing production bucket security controls"
gcloud storage buckets update "${BUCKET_URI}" \
  --project "${PROJECT_ID}" \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --versioning >/dev/null

echo "Granting bucket-scoped runtime access"
gcloud storage buckets add-iam-policy-binding "${BUCKET_URI}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="${ROLE_NAME}" \
  --project "${PROJECT_ID}" >/dev/null

if [[ ! -f "${MASTER_KEY_OUTPUT}" ]]; then
  python3 - "${MASTER_KEY_OUTPUT}" <<'PY'
import base64
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1]).expanduser()
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(base64.urlsafe_b64encode(os.urandom(32)).decode() + "\n")
path.chmod(0o600)
PY
  echo "Generated production STORAGE_MASTER_KEY at ${MASTER_KEY_OUTPUT}"
else
  echo "Existing master-key file preserved: ${MASTER_KEY_OUTPUT}"
fi

if [[ "${CREATE_SERVICE_ACCOUNT_KEY}" == "1" ]]; then
  if [[ -e "${SERVICE_ACCOUNT_KEY_OUTPUT}" ]]; then
    echo "Refusing to overwrite existing service-account key: ${SERVICE_ACCOUNT_KEY_OUTPUT}" >&2
    exit 1
  fi
  echo "Creating application service-account key at ${SERVICE_ACCOUNT_KEY_OUTPUT}"
  gcloud iam service-accounts keys create "${SERVICE_ACCOUNT_KEY_OUTPUT}" \
    --iam-account "${SA_EMAIL}" \
    --project "${PROJECT_ID}" >/dev/null
  chmod 600 "${SERVICE_ACCOUNT_KEY_OUTPUT}"
  echo "Treat this JSON as a production secret. Do not commit or upload it anywhere except the deployment secret store."
else
  echo "Service-account JSON key creation skipped. Set CREATE_SERVICE_ACCOUNT_KEY=1 only when the Streamlit deployment secret is ready to receive it."
fi

echo
echo "Bootstrap complete. Run:"
echo "  PROJECT_ID='${PROJECT_ID}' BUCKET_NAME='${BUCKET_NAME}' bash infra/gcp/verify_storage.sh"
echo
echo "Do not set APP_MODE=production yet. External storage verification must pass first."
