# API Reference (Iteration 3)

Base URL: `http://localhost:8080/api/v1`

## Health

### `GET /health/live`

Returns gateway process liveness.

### `GET /health/ready`

Checks dependency connectivity for OPA and immudb.

## Audit

### `POST /audit/events`

Writes an immutable audit event to immudb.

Required fields include:

- `actor_type`, `actor_id`
- `action_type`
- `resource_type`, `resource_id`
- `decision`

Optional filters and hashes can also be included.

### `GET /audit/events`

Query audit events by:

- `actor_id`
- `user_id`
- `room_id`
- `action_type`
- `decision`
- `start_ts`, `end_ts`
- `limit`

### `GET /audit/verify`

Verifies chain continuity for the selected event range and returns:

- `verified`
- `checked_events`
- first/last/broken event ids
- current immudb state tx id/hash

## Policy

### `GET /policy/grants`

Lists current grants (filterable by `user_id`, `agent_id`, and `include_revoked`).

### `POST /policy/grants`

Creates a grant record for an agent, persists it into OPA `data.prism.grants`, and logs an audit event.

### `POST /policy/revoke`

Revokes a grant in OPA data, and logs an audit event.

## Agent

### `POST /agent/summarize`

Runs policy decision via OPA before summarization.

- On allow: returns summary + audited allow event
- On deny: returns 403 + audited deny event (for example `grant_revoked`)

## Matrix

### `GET /matrix/sync`

Proxy sync endpoint:

- `access_token` (required)
- `since`, `timeout_ms`, `full_state`
- optional `user_id` and `room_id` for audit context
