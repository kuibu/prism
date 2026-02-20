# Architecture (MVP)

## Iteration 1 Scope

- Matrix homeserver: Synapse
- Backend control plane: `gateway_api` (FastAPI)
- Policy engine: OPA sidecar
- Immutable audit store: immudb
- Object storage: MinIO (wired, feature use in later iterations)

## Components

- `clients/cli`: developer CLI for Matrix and gateway interactions
- `services/gateway_api`: policy, audit, and agent gateway API
- `synapse`: Matrix protocol server
- `opa`: policy decision point
- `immudb`: immutable audit event database
- `minio`: media/object storage

## Data Flow (Iteration 1)

1. Client calls `gateway_api /api/v1/health/ready`
2. `gateway_api` probes OPA via HTTP `/health`
3. `gateway_api` probes immudb via TCP port `3322`
4. Gateway returns consolidated readiness status

Later iterations add message flow, policy enforcement flow, and audit chain flow.
