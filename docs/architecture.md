# Architecture (Current MVP)

## Components

- `synapse`: Matrix homeserver
- `gateway_api`: FastAPI control plane (auth binding, matrix proxy, policy, audit, agent runtime)
  - includes `Agent Studio` domain: per-user secretary/specialist registry, memory store, skill runtime
- `opa`: policy decision point (Rego + data API)
- `immudb`: immutable audit storage
- `minio`: object storage (media evolution path)
- `prometheus`: metrics scrape
- `grafana`: dashboards
- `clients/cli`: developer CLI (gateway-backed)
- `services/gateway_api/app/web`: developer web console (gateway-backed)

## Security Boundary

- All sensitive user operations are routed through `gateway_api`.
- Gateway enforces `Bearer` Matrix token and resolves caller identity via Matrix `whoami`.
- `user_id` spoofing is blocked (`policy/*` and `agent/*` enforce token/user binding).
- OPA is internal-only (not exposed on host port by default).

## Core Data Flows

### Matrix Action Flow (register/login/create/send/sync/upload)
1. Client calls gateway `/api/v1/matrix/*`
2. Gateway calls Synapse API
3. Gateway writes allow/deny event to immudb
4. Gateway returns normalized response

### Policy Flow
1. Client calls `/api/v1/policy/grants|revoke`
2. Gateway writes grant docs into OPA data (`data.prism.grants`)
3. Gateway writes audit event into immudb
4. Revoke is enforced on subsequent agent access

### Agent Flow
1. Client calls `/api/v1/agent/summarize`
2. Gateway sends policy input to OPA (`read_messages`)
3. On allow, gateway reads room messages server-side via Matrix token
4. Gateway summarizes and writes tool/data-access audits
5. On deny, gateway returns `403` and still writes deny audit

### Secretary + Specialist Flow
1. Client bootstraps `/api/v1/agents/bootstrap`
2. Gateway ensures one secretary profile per user (OPA data document)
3. User creates specialist profiles (`/api/v1/agents`)
4. Secretary collects room updates (`/api/v1/agents/{id}/memory/collect`) with OPA allow checks
5. Specialist runs skills (`/api/v1/agents/{id}/skills/run`) with memory + optional room context
6. Gateway audits policy checks, memory writes, skill start/finish, and optional room send actions

### Audit Verify Flow
1. Client calls `/api/v1/audit/verify`
2. Gateway loads ordered events from immudb
3. Gateway validates hash-chain continuity and recomputed chain hash
4. Gateway returns verification summary + immudb state tx hash

## Observability

- OpenTelemetry instrumentation for FastAPI + httpx clients
- Prometheus scrape target: `gateway_api:8000/metrics`
- Grafana default datasource provisioned to Prometheus

## Extensibility Notes

- Agent tools are pluggable in `app/agent`
- Skill runtime follows `SkillRegistry + SkillRouter + SkillExecutor` pipeline in `app/agent/skills`
- Agent profiles and memory use OPA data API for MVP persistence (`data.prism.agent_registry`, `data.prism.agent_memory`)
- Matrix client wrappers are centralized in `app/matrix/client.py`
- Current summarizer is rule-based placeholder; LLM provider can be added behind same policy/audit gates
