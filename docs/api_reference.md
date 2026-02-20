# API Reference (Latest MVP)

Base URL: `http://localhost:8080/api/v1`

## Auth Model

- `matrix/register` and `matrix/login` are anonymous.
- `matrix/whoami`, `matrix/rooms*`, `matrix/sync`, `policy/*`, `agent/summarize` require:
  - `Authorization: Bearer <matrix_access_token>`
- Gateway resolves caller identity via Matrix `/_matrix/client/v3/account/whoami`.
- `user_id` in policy payload must match authenticated caller, otherwise `403 user_id_mismatch`.

## Health

### `GET /health/live`
Process liveness.

### `GET /health/ready`
Dependency readiness (OPA + immudb).

## Matrix Proxy

### `POST /matrix/register`
Register Matrix account via gateway and audit the action.

Request:
```json
{"username":"alice","password":"Passw0rd!"}
```

### `POST /matrix/login`
Login via gateway and audit the action.

Request:
```json
{"username":"alice","password":"Passw0rd!"}
```

### `GET /matrix/whoami`
Returns authenticated Matrix user id.

### `POST /matrix/rooms`
Create room (audited).

Request:
```json
{"name":"demo-room","invite":[],"preset":"private_chat"}
```

### `POST /matrix/rooms/{room_id}/join`
Join room (audited).

### `POST /matrix/rooms/{room_id}/messages`
Send text message (audited).

Request:
```json
{"body":"hello"}
```

### `POST /matrix/rooms/{room_id}/files`
Upload media and send file message (audited for both upload and send).
`multipart/form-data`, field name: `file`.

### `GET /matrix/sync`
Proxy sync (audited).

Query params:
- `room_id` (optional)
- `since` (optional)
- `timeout_ms` (default 0, max 60000)
- `full_state` (default false)

## Policy

### `GET /policy/grants`
List grants for authenticated user by default.

Query:
- `user_id` (optional; if provided must equal caller)
- `agent_id` (optional)
- `include_revoked` (default false)

### `POST /policy/grants`
Create grant in OPA data store (`data.prism.grants`) and write audit event.

Request:
```json
{
  "user_id":"@alice:localhost",
  "agent_id":"agent.summary",
  "data_category":"room_messages",
  "purpose":"daily_summary",
  "rate_limit_per_minute":60
}
```

### `POST /policy/revoke`
Revoke grant and write audit event.

Request:
```json
{"user_id":"@alice:localhost","grant_id":"grant_xxx","reason":"user_request"}
```

## Agent

### `POST /agent/summarize`
Server-side agent flow:
1. OPA decision on `read_messages`
2. Read room messages via Matrix using caller token
3. Summarize
4. Audit read + summarize events

Request:
```json
{
  "agent_id":"agent.summary",
  "room_id":"!room:localhost",
  "purpose":"daily_summary",
  "recent_message_limit":30,
  "max_items":8
}
```

## Audit

### `POST /audit/events`
Low-level direct audit write endpoint.

### `GET /audit/events`
Query by `actor_id`, `user_id`, `room_id`, `action_type`, `decision`, `start_ts`, `end_ts`, `limit`.

### `GET /audit/verify`
Verify hash-chain integrity for selected scope.

Response fields:
- `verified`
- `checked_events`
- `first_event_id`, `last_event_id`, `broken_event_id`, `reason`
- `state_tx_id`, `state_tx_hash`

## Observability

### `GET /metrics`
Prometheus metrics endpoint for gateway.
