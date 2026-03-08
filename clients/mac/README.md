# Prism macOS Desktop Client

This desktop app wraps the existing Prism web frontend (`/web/`) as a native macOS app shell.

## Prerequisites

- macOS
- Node.js 18+
- Prism backend running (`docker compose up -d --build`)

## Install

```bash
cd /Users/a/repos/prism/clients/mac
npm install
```

## Run in development mode

```bash
cd /Users/a/repos/prism/clients/mac
PRISM_WEB_URL=http://localhost:8080/web/ npm run dev
```

If `PRISM_WEB_URL` is omitted, the default is `http://localhost:8080/web/`.

## Build macOS app package

```bash
cd /Users/a/repos/prism/clients/mac
npm run dist:mac
```

Build outputs are written to:

```text
clients/mac/dist/
```

## Release-grade features included

- Native application menu and keyboard shortcuts
- Hardened runtime packaging
- macOS code-signing hooks (Developer ID)
- Apple notarization hook (API key mode or Apple ID mode)
- Built-in auto-update client (`electron-updater`)

## Signing + Notarization env vars

Code signing is handled by `electron-builder` (standard `CSC_*` env vars).  
Notarization is handled in `scripts/notarize.cjs`.

Important:

- In release workflow, signing and notarization are **mandatory** (`PRISM_REQUIRE_SIGNING=1`, `PRISM_REQUIRE_NOTARIZATION=1`).
- If credentials are missing, build fails immediately (no silent skip).

Set one of the following notarization credential groups:

1. App Store Connect API key mode

```bash
export APPLE_API_KEY=/absolute/path/AuthKey_XXXXXX.p8
export APPLE_API_KEY_ID=XXXXXX
export APPLE_API_ISSUER=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
export APPLE_TEAM_ID=TEAMID1234   # optional in API key mode
```

2. Apple ID mode

```bash
export APPLE_ID=you@example.com
export APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx
export APPLE_TEAM_ID=TEAMID1234
```

Then build:

```bash
cd /Users/a/repos/prism/clients/mac
npm run dist:mac
```

## Auto-update publish config

Choose one publish provider before `npm run dist:mac:publish`.

Generic provider:

```bash
export PRISM_MAC_PUBLISH_PROVIDER=generic
export PRISM_MAC_UPDATE_URL=https://your-domain.com/prism-updates/
```

GitHub Releases provider:

```bash
export PRISM_MAC_PUBLISH_PROVIDER=github
export PRISM_GH_OWNER=your-org-or-user
export PRISM_GH_REPO=prism
export PRISM_GH_PRIVATE=0
export PRISM_GH_RELEASE_TYPE=release
```

Then publish build artifacts:

```bash
cd /Users/a/repos/prism/clients/mac
npm run dist:mac:publish
```

## GitHub Actions production release (recommended)

Workflow file:

```text
.github/workflows/mac-release.yml
```

Required repository secrets:

- `APPLE_DEVELOPER_ID_CERT_P12_BASE64`
- `APPLE_DEVELOPER_ID_CERT_PASSWORD`
- `APPLE_API_KEY_P8_BASE64`
- `APPLE_API_KEY_ID`
- `APPLE_API_ISSUER`
- `APPLE_TEAM_ID`

Set secrets with helper script:

```bash
cd /Users/a/repos/prism
scripts/setup_mac_release_secrets.sh \
  --repo kuibu/prism \
  --cert-p12 /path/to/DeveloperID_Application.p12 \
  --cert-password '***' \
  --api-key-p8 /path/to/AuthKey_XXXXXX.p8 \
  --api-key-id XXXXXX \
  --api-issuer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
  --team-id TEAMID1234
```

Trigger release:

```bash
gh workflow run mac-release.yml --repo kuibu/prism -f version=0.1.1
```

Watch workflow:

```bash
gh run watch --repo kuibu/prism --exit-status
```

Check readiness before triggering:

```bash
cd /Users/a/repos/prism
make mac-release-check
```
