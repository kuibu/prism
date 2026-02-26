# API Reference (Latest MVP)

Base URL: `http://localhost:8080/api/v1`

## Auth Model

- `matrix/register` and `matrix/login` are anonymous.
- `matrix/whoami`, `matrix/rooms*`, `matrix/sync`, `policy/*`, `agent/summarize*` require:
  - `Authorization: Bearer <matrix_access_token>`
- `audit/*` requires `Authorization: Bearer <matrix_access_token>` and is scoped to caller:
  - if `user_id` omitted, gateway defaults it to the authenticated user
  - cross-user `user_id` query is rejected with `403 user_id_mismatch`
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

### `POST /agent/summarize-and-send`
Same as `/agent/summarize`, plus:
1. Ensure deterministic bot identity for `agent_id`
2. Send summary back to room as bot account
3. Audit send allow/deny (`agent_send_summary_message`)

## Agent Studio (Secretary + Specialists)

### `GET /agents/skills`
List built-in skill catalog.

### `POST /agents/bootstrap`
Ensure one secretary agent exists for the authenticated user.

### `GET /agents`
List current user's agents.

Query:
- `ensure_secretary` (default `true`)
- `include_disabled` (default `false`)

### `POST /agents`
Create/update an agent profile (secretary or specialist).

### `PATCH /agents/{agent_id}`
Update an existing agent profile.

### `POST /agents/{agent_id}/memory/notes`
Write manual note into agent memory.

### `GET /agents/{agent_id}/memory`
Search or list recent memory entries.

Query:
- `q` optional query
- `limit` default 20

### `POST /agents/{agent_id}/memory/collect`
Collect Matrix room messages into agent memory (OPA-gated, audited).

Request:
```json
{
  "room_ids": [],
  "limit_per_room": 50,
  "include_self_messages": false,
  "purpose": "secretary_collect"
}
```

### `POST /agents/{agent_id}/skills/run`
Run skill with memory context and optional room context (OPA-gated, audited).

Request:
```json
{
  "skill_id": "specialist.todo_extractor",
  "query": "extract todo list",
  "purpose": "todo_followup",
  "room_id": "!room:localhost",
  "room_message_limit": 30,
  "memory_limit": 20,
  "send_to_room": false
}
```

## Audit

### `POST /audit/events`
Low-level direct audit write endpoint (authenticated).  
`actor_type=user` requires `actor_id` to match authenticated user.

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

## Bridge

### `GET /bridges/platforms`
List supported bridge platforms and direction capabilities.

### `GET /bridges/connectors`
List current user's bridge connectors (sensitive token fields are masked).

### `POST /bridges/connectors`
Create connector.

### `PATCH /bridges/connectors/{connector_id}`
Update connector.

### `DELETE /bridges/connectors/{connector_id}`
Delete connector and related links.

### `GET /bridges/links`
List bridge room mappings.

### `POST /bridges/links`
Create room mapping between Matrix room and external room.

### `PATCH /bridges/links/{link_id}`
Update mapping.

### `DELETE /bridges/links/{link_id}`
Delete mapping.

### `POST /bridges/relay/inbound`
Simulate inbound external message -> Matrix relay.

### `POST /bridges/relay/outbound/preview`
Preview Matrix -> external payload mapping.

### `POST /bridges/telegram/poll`
Real Telegram bridge: pull Telegram updates (`getUpdates`) and relay to mapped Matrix room(s).

### `POST /bridges/telegram/send`
Real Telegram bridge: send text to Telegram (`sendMessage`) from direct text or latest Matrix messages.
