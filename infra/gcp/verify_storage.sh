#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${BUCKET_NAME:?Set BUCKET_NAME}"

SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-coletti-advisory-storage}"
ROLE_ID="${ROLE_ID:-ColettiAdvisoryStorageRuntime}"
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
ROLE_NAME="projects/${PROJECT_ID}/roles/${ROLE_ID}"
BUCKET_URI="gs://${BUCKET_NAME}"

command -v gcloud >/dev/null 2>&1 || { echo "gcloud CLI is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

bucket_json="$(mktemp)"
iam_json="$(mktemp)"
trap 'rm -f "${bucket_json}" "${iam_json}"' EXIT

gcloud storage buckets describe "${BUCKET_URI}" \
  --project "${PROJECT_ID}" \
  --format=json > "${bucket_json}"

gcloud storage buckets get-iam-policy "${BUCKET_URI}" \
  --project "${PROJECT_ID}" \
  --format=json > "${iam_json}"

python3 - "${bucket_json}" "${iam_json}" "${SA_EMAIL}" "${ROLE_NAME}" <<'PY'
import json
import pathlib
import sys

bucket = json.loads(pathlib.Path(sys.argv[1]).read_text())
policy = json.loads(pathlib.Path(sys.argv[2]).read_text())
sa_email = sys.argv[3]
role_name = sys.argv[4]

iam = bucket.get("iamConfiguration") or bucket.get("iam_configuration") or {}
uniform_cfg = (
    iam.get("uniformBucketLevelAccess")
    or iam.get("uniform_bucket_level_access")
    or iam.get("bucketPolicyOnly")
    or iam.get("bucket_policy_only")
    or {}
)
pap = str(iam.get("publicAccessPrevention") or iam.get("public_access_prevention") or "").lower()
versioning = bucket.get("versioning") or {}

errors = []
if not bool(uniform_cfg.get("enabled")):
    errors.append("uniform bucket-level access is not enabled")
if pap != "enforced":
    errors.append(f"public access prevention is {pap or 'unset'}, not enforced")
if not bool(versioning.get("enabled")):
    errors.append("object versioning is not enabled")

runtime_binding = False
for binding in policy.get("bindings", []):
    members = set(binding.get("members", []))
    if "allUsers" in members or "allAuthenticatedUsers" in members:
        errors.append(f"public principal remains in bucket IAM binding for {binding.get('role')}")
    if binding.get("role") == role_name and f"serviceAccount:{sa_email}" in members:
        runtime_binding = True

if not runtime_binding:
    errors.append("production storage service account is missing the expected bucket-scoped runtime role")

if errors:
    print("PRODUCTION STORAGE GATE: FAIL")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("PRODUCTION STORAGE GATE: INFRASTRUCTURE CONTROLS PASS")
print("- uniform bucket-level access: enabled")
print("- public access prevention: enforced")
print("- object versioning: enabled")
print("- public IAM principals: none")
print("- runtime service-account binding: present")
print("\nRemaining before final storage PASS: validate the deployed app credential and run the controlled encrypted production-path upload.")
PY
