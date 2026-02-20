# Threat Model (STRIDE, Current MVP)

## Scope

- Gateway-authenticated Matrix actions
- Policy grant/revoke and OPA evaluation
- Agent data access and summarization tools
- Immutable audit storage and verification

## STRIDE Matrix

### Spoofing

Threat:
- Caller forges `user_id` in policy/agent payload.

Mitigations:
- Gateway requires `Authorization: Bearer <matrix token>`.
- Gateway resolves actual user via Matrix `whoami`.
- `policy/*` and `agent/*` reject mismatched `user_id` (`403 user_id_mismatch`).

### Tampering

Threat:
- Modify historical audit logs or policy state off-path.

Mitigations:
- Audit events stored in immudb (append-only behavior).
- Per-event hash chaining (`prev_hash`, `chain_hash`) + verify API.
- OPA host port is not exposed by default; policy writes go through gateway API.

### Repudiation

Threat:
- Actor denies performing sensitive operations.

Mitigations:
- Sensitive actions (matrix login/create/send/sync/upload, policy grant/revoke, agent tool access) are audited.
- Deny decisions are audited with reason codes.

### Information Disclosure

Threat:
- Agent over-reads room data or leaked secrets in logs.

Mitigations:
- OPA policy check before each agent read.
- `recent_message_limit` and request rate constraints enforced.
- Security helpers support sensitive key redaction patterns.

### Denial of Service

Threat:
- Abuse of agent endpoints or matrix proxy.

Mitigations:
- In-memory per-key request counter for agent calls.
- Bounded input sizes (`max_items`, message/file size limits, request schema validation).
- HTTP client retries/timeouts for dependency calls.

### Elevation of Privilege

Threat:
- Agent continues reading after revoke.

Mitigations:
- Grant state stored centrally in OPA data and checked on every call.
- Revoke writes audit evidence.
- Post-revoke access attempts are denied and audited (`grant_revoked`).

## Residual Risks (MVP)

- No full production-grade E2EE workflow yet.
- No production IAM/JWT federation yet (Matrix token trust boundary used for MVP).
- Abuse prevention and moderation are baseline only (not full anti-abuse stack).
