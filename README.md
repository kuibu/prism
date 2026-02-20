# Prism
## AI-Native + Transparent Security Messaging (Matrix)  
## AI 原生 + 透明安全消息系统（基于 Matrix）

Prism is a runnable MVP for a next-gen WeChat-like product on Matrix with security-by-default:
- immutable audit (immudb)
- policy-controlled agent access (OPA)
- gateway-enforced identity binding
- observable operations (OpenTelemetry + Prometheus + Grafana)

Prism 是一个可运行的“下一代微信”方向 MVP，基于 Matrix，并默认开启透明安全：
- 不可篡改审计（immudb）
- 策略控制的智能体访问（OPA）
- 网关身份绑定（防 user_id 伪造）
- 可观测性（OpenTelemetry + Prometheus + Grafana）

---

## Current MVP Status | 当前 MVP 状态

### Implemented | 已实现
- Gateway-authenticated Matrix proxy APIs:
  - register/login/whoami/create room/join/send text/upload file/sync
- Mandatory immutable audit for sensitive actions:
  - matrix login/create/send/upload/sync
  - policy grant/revoke
  - agent data access + summarize allow/deny
- OPA grant/revoke wired to real OPA data API (`data.prism.grants`)
- Revoke immediately enforced on next agent access
- Agent runtime reads room messages server-side (not client-passed text)
- Web client at `/web` (gateway-backed)
- CLI client (`prism-cli`) gateway-backed commands:
  - `register`, `login`, `send`, `send-file`, `sync`
- Observability stack:
  - gateway `/metrics`
  - Prometheus scrape
  - Grafana pre-provisioned datasource
- Test suite:
  - unit/integration with stubs
  - optional live integration tests against running services

---

## Stack | 技术栈

- Matrix homeserver: Synapse
- Gateway API: FastAPI + Pydantic v2
- Policy: OPA (Rego)
- Immutable audit DB: immudb
- Object storage: MinIO
- Observability: OpenTelemetry + Prometheus + Grafana

---

## Quick Start | 快速开始

### 1) Prepare env | 准备环境
```bash
cp .env.example .env
```

### 2) Start stack | 启动服务
```bash
docker compose up -d --build
docker compose ps
```

### 3) Health checks | 健康检查
```bash
curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
```

### 4) Run core tests | 运行核心测试
```bash
docker compose run --rm gateway_api pytest -q
```

### 5) Run one-command demo | 一键演示
```bash
make demo
```

### 6) Optional live integration tests | 可选真实联调测试
```bash
make live-test
```

---

## Service Endpoints | 服务入口

- Gateway API: `http://localhost:8080`
- Web client: `http://localhost:8080/web/`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (default `admin/admin`)
- Synapse client API: `http://localhost:8008`

Port mapping notes:
- immudb host port defaults to `3332` (container internal still `3322`)
- MinIO host ports default to `9100` (API) and `9101` (console)
- OPA is internal-only by default (no host port exposure)

---

## Repository Layout | 仓库结构

```text
repo/
  docker-compose.yml
  Makefile
  scripts/demo_flow.py
  observability/
    prometheus/prometheus.yml
    grafana/provisioning/datasources/datasource.yml
  services/
    gateway_api/
      app/
        api/
        agent/
        audit/
        core/
        matrix/
        web/
        tests/
  clients/
    cli/
  policies/
    opa/
  docs/
```

---

## Security Defaults | 默认安全策略

- Gateway binds caller identity with Matrix token (`whoami`)
- `policy/*` and `agent/*` enforce user-token consistency
- Sensitive actions must be audited (allow + deny)
- Audit chain verification API available (`/api/v1/audit/verify`)
- OPA not exposed on host port by default

---

## Docs | 文档

- Architecture: `docs/architecture.md`
- Threat model: `docs/threat_model.md`
- API reference: `docs/api_reference.md`
- Demo script: `docs/demo_script.md`
- Licenses: `docs/licenses.md`

---

## License | 许可证

MIT (`LICENSE`)
