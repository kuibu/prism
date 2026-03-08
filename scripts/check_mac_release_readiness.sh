#!/usr/bin/env bash
set -euo pipefail

repo="${1:-kuibu/prism}"
required_secrets=(
  APPLE_DEVELOPER_ID_CERT_P12_BASE64
  APPLE_DEVELOPER_ID_CERT_PASSWORD
  APPLE_API_KEY_P8_BASE64
  APPLE_API_KEY_ID
  APPLE_API_ISSUER
  APPLE_TEAM_ID
)

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found"
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "ERROR: gh is not authenticated"
  exit 1
fi

echo "Repo: ${repo}"
echo "Checking GitHub Secrets..."
existing="$(gh secret list --repo "${repo}" 2>/dev/null | awk '{print $1}' || true)"
missing=()
for key in "${required_secrets[@]}"; do
  if ! grep -qx "${key}" <<<"${existing}"; then
    missing+=("${key}")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "MISSING_SECRETS: ${missing[*]}"
else
  echo "SECRETS_OK"
fi

echo "Checking local code signing identities..."
identities="$(security find-identity -v -p codesigning 2>/dev/null | tail -n 1 | awk '{print $1}' || true)"
if [[ "${identities}" == "0" || -z "${identities}" ]]; then
  echo "LOCAL_CODESIGN_IDENTITY: not found"
else
  echo "LOCAL_CODESIGN_IDENTITY: found"
fi

echo "Checking Actions workflow status..."
if gh workflow view mac-release.yml --repo "${repo}" >/dev/null 2>&1; then
  echo "WORKFLOW_EXISTS: yes"
else
  echo "WORKFLOW_EXISTS: no"
fi
