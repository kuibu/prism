#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_mac_release_secrets.sh \
    --repo kuibu/prism \
    --cert-p12 /path/to/DeveloperID.p12 \
    --cert-password '***' \
    --api-key-p8 /path/to/AuthKey_XXXXXX.p8 \
    --api-key-id XXXXXX \
    --api-issuer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
    --team-id TEAMID1234

This script writes GitHub Actions secrets required by .github/workflows/mac-release.yml:
  - APPLE_DEVELOPER_ID_CERT_P12_BASE64
  - APPLE_DEVELOPER_ID_CERT_PASSWORD
  - APPLE_API_KEY_P8_BASE64
  - APPLE_API_KEY_ID
  - APPLE_API_ISSUER
  - APPLE_TEAM_ID
EOF
}

repo=""
cert_p12=""
cert_password=""
api_key_p8=""
api_key_id=""
api_issuer=""
team_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      repo="${2:-}"
      shift 2
      ;;
    --cert-p12)
      cert_p12="${2:-}"
      shift 2
      ;;
    --cert-password)
      cert_password="${2:-}"
      shift 2
      ;;
    --api-key-p8)
      api_key_p8="${2:-}"
      shift 2
      ;;
    --api-key-id)
      api_key_id="${2:-}"
      shift 2
      ;;
    --api-issuer)
      api_issuer="${2:-}"
      shift 2
      ;;
    --team-id)
      team_id="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${repo}" ]]; then
  repo="$(git remote get-url origin 2>/dev/null | sed -E 's#^https://github.com/##; s#\.git$##')"
fi

required_values=(
  "repo:${repo}"
  "cert_p12:${cert_p12}"
  "cert_password:${cert_password}"
  "api_key_p8:${api_key_p8}"
  "api_key_id:${api_key_id}"
  "api_issuer:${api_issuer}"
  "team_id:${team_id}"
)

for entry in "${required_values[@]}"; do
  key="${entry%%:*}"
  value="${entry#*:}"
  if [[ -z "${value}" ]]; then
    echo "Missing required argument: ${key}" >&2
    usage
    exit 1
  fi
done

if [[ ! -f "${cert_p12}" ]]; then
  echo "Developer ID certificate not found: ${cert_p12}" >&2
  exit 1
fi
if [[ ! -f "${api_key_p8}" ]]; then
  echo "Apple API key file not found: ${api_key_p8}" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI first." >&2
  exit 1
fi

echo "Writing macOS release secrets to GitHub repo: ${repo}"

cert_b64="$(base64 < "${cert_p12}" | tr -d '\n')"
key_b64="$(base64 < "${api_key_p8}" | tr -d '\n')"

gh secret set APPLE_DEVELOPER_ID_CERT_P12_BASE64 --repo "${repo}" -b "${cert_b64}"
gh secret set APPLE_DEVELOPER_ID_CERT_PASSWORD --repo "${repo}" -b "${cert_password}"
gh secret set APPLE_API_KEY_P8_BASE64 --repo "${repo}" -b "${key_b64}"
gh secret set APPLE_API_KEY_ID --repo "${repo}" -b "${api_key_id}"
gh secret set APPLE_API_ISSUER --repo "${repo}" -b "${api_issuer}"
gh secret set APPLE_TEAM_ID --repo "${repo}" -b "${team_id}"

echo "Done. You can now trigger the release workflow:"
echo "  gh workflow run mac-release.yml --repo ${repo} -f version=0.1.1"
