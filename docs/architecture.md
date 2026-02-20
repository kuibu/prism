# Architecture (MVP)

## Iteration 3 Scope

- Matrix homeserver: Synapse
- Backend control plane: `gateway_api` (FastAPI)
- Policy engine: OPA sidecar
- Immutable audit store: immudb
- Object storage: MinIO

## Components

- `clients/cli`: developer CLI for Matrix and gateway interactions
- `services/gateway_api`: policy, audit, and agent gateway API
- `synapse`: Matrix protocol server
- `opa`: policy decision point
- `immudb`: immutable audit event database
- `minio`: media/object storage

## Key Flows

### Health flow

1. Client calls `GET /api/v1/health/ready`
2. Gateway probes OPA `/health`
3. Gateway probes immudb TCP `3322`
4. Gateway returns `ready` or `degraded`

### Audit write flow (Iteration 2)

1. Client calls `POST /api/v1/audit/events`
2. Gateway computes:
   - `input_hash`
   - `output_hash`
   - `prev_hash` (latest event chain hash)
   - `chain_hash` (deterministic hash over event fields)
3. Gateway inserts event row into immudb SQL table `audit_events`
4. Response includes immutable event payload and immudb tx id

### Audit verify flow (Iteration 2)

1. Client calls `GET /api/v1/audit/verify` with optional filters
2. Gateway queries ordered events from immudb
3. Gateway validates:
   - `prev_hash` continuity
   - per-event `chain_hash` recomputation
4. Gateway returns verification result and current immudb state hash

### Agent policy + audit flow (MVP)

1. Client calls `POST /api/v1/agent/summarize`
2. Gateway sends decision input to OPA
3. If deny: returns 403 and writes deny audit event
4. If allow: runs summarizer and writes allow audit event

### Policy grant/revoke flow (MVP)

1. Client grants or revokes via `/api/v1/policy/*`
2. Gateway writes grant document to OPA data API (`/v1/data/prism/grants/<grant_id>`)
3. Gateway writes corresponding audit event to immudb
4. API returns updated policy state

### Policy decision flow (Iteration 3)

1. `POST /api/v1/agent/summarize` receives tool request
2. Gateway builds OPA input (`agent_id`, `user_id`, `room_id`, `purpose`, `request_count_per_minute`, `ts`)
3. OPA Rego evaluates `data.prism.grants` and returns `allow/deny + reason`
4. Gateway enforces decision and writes audit event for both allow and deny paths
