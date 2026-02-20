# Prism
## AI-Native + Transparent Security Messaging (Matrix)  
## AI 原生 + 透明安全消息系统（基于 Matrix）

Prism is an MVP for a next-generation WeChat-like product built on Matrix, with security-by-default, immutable audit, policy-based agent access control, and practical developer operations.

Prism 是一个“下一代微信”方向的可运行 MVP：基于 Matrix 协议，默认安全、不可篡改审计、策略驱动智能体访问控制，并且强调工程可落地与可运维性。

---

## Why This Project Matters | 项目意义

### EN
- Most AI assistants in chat apps are opaque: users cannot clearly know what data was read, why it was read, and whether permissions were respected.
- Prism treats **AI agents as first-class actors** and makes every sensitive action auditable and policy-gated.
- The goal is not just “chat + bot”, but a foundation for **trustworthy AI communication infrastructure**.

### 中文
- 现有聊天产品中的 AI 助手普遍“不透明”：用户很难知道读了什么数据、为什么读、权限是否被遵守。
- Prism 把**智能体当作一级对象**，并让每个敏感动作都经过策略判定且可审计追溯。
- 目标不只是“聊天 + 机器人”，而是构建**可信 AI 通信基础设施**。

---

## MVP Goals | MVP 目标

### EN
1. Matrix-based messaging baseline (Synapse).
2. Immutable audit for sensitive actions (immudb).
3. OPA-backed grant/revoke and runtime policy decisions.
4. Agent runtime with controlled tool access (`read_messages` + `summarize` path).
5. One-command local startup and repeatable validation.

### 中文
1. 基于 Matrix/Synapse 的消息能力底座。
2. 对敏感动作进行不可篡改审计（immudb）。
3. 基于 OPA 的授权/撤权与实时策略判定。
4. 受控智能体运行时（`read_messages` + `summarize` 流程）。
5. 本地一键启动与可重复验证。

---

## Current Status (Iteration 4) | 当前状态（迭代 4）

### Implemented | 已实现
- `docker compose` local stack: Synapse, OPA, immudb, MinIO, `gateway_api`.
- FastAPI gateway APIs:
  - Health: `/api/v1/health/live`, `/api/v1/health/ready`
  - Audit: `/api/v1/audit/events`, `/api/v1/audit/verify`
  - Policy: `/api/v1/policy/grants`, `/api/v1/policy/revoke`
  - Agent: `/api/v1/agent/summarize`
  - Matrix proxy: `/api/v1/matrix/sync`
- Python CLI (`clients/cli`) commands:
  - `prism-cli login`
  - `prism-cli sync`
  - `prism-cli send`
- OPA policy uses persisted grant data (`data.prism.grants`) for allow/deny decisions.
- Revocation is enforced immediately on subsequent agent access.
- Audit chain hashing and verification implemented with immudb SQL table backend.
- Integrated tests for core policy/audit/agent/matrix paths.

### Validation done on latest code | 最新代码已验证
- Containerized tests: `docker compose run --rm gateway_api pytest -q` -> pass.
- Real API scenario loop:
  - grant -> allow
  - revoke -> deny
  - rate-limit deny
  - matrix sync failure audit
  - audit verify (actor/global)
- Matrix smoke (register/create room/send/sync) validated after Synapse config hardening.
- CLI smoke validated with real Matrix flow (`login -> send -> sync`).

---

## Repository Structure | 仓库结构

```text
repo/
  docker-compose.yml
  services/
    gateway_api/
      app/
        main.py
        api/
        core/
        policy/
        audit/
        agent/
        matrix/
        tests/
      Dockerfile
      pyproject.toml
  clients/
    cli/
      pyproject.toml
      src/
  policies/
    opa/
      policy.rego
      data.json
      README.md
  docs/
    architecture.md
    threat_model.md
    api_reference.md
    demo_script.md
```

---

## Quick Start | 快速开始

### 1) Prepare env | 准备环境
```bash
cp .env.example .env
```

### 2) Start all services | 启动全部服务
```bash
docker compose up -d --build
docker compose ps
```

### 3) Health checks | 健康检查
```bash
curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
```

### 4) Run tests | 运行测试
```bash
docker compose run --rm gateway_api pytest -q
```

For end-to-end step-by-step commands, see `docs/demo_script.md`.

完整端到端演示命令请参考 `docs/demo_script.md`。

---

## Security Model (MVP) | 安全模型（MVP）

### EN
- Least privilege by default.
- Explicit grant/revoke for agent data access.
- Every sensitive operation must be auditable.
- Deny decisions are audited with reason codes.
- Audit chain integrity verification API is provided.

### 中文
- 默认最小权限。
- 智能体访问需要显式授权/可随时撤权。
- 敏感操作必须可审计。
- 拒绝决策（deny）同样写入审计并带原因码。
- 提供审计链完整性校验接口。

---

## Components | 关键组件

- Matrix homeserver: **Synapse**
- Policy engine: **OPA** (Rego)
- Immutable audit DB: **immudb**
- Gateway API: **FastAPI + Pydantic v2**
- Object storage (reserved path for media evolution): **MinIO**

---

## Key Docs | 核心文档

- Architecture: `docs/architecture.md`
- Threat model: `docs/threat_model.md`
- API reference: `docs/api_reference.md`
- Demo script: `docs/demo_script.md`

---

## Known MVP Limits | 当前限制

### EN
- No full E2EE product implementation yet (framework and audit boundaries are prioritized first).
- Agent summarization is currently rule-based placeholder.
- Web client is not implemented yet (current client is Python CLI).

### 中文
- 尚未实现完整产品级 E2EE（当前优先透明审计与策略边界）。
- 智能体摘要目前是规则/占位实现。
- Web 客户端尚未实现（当前客户端为 Python CLI）。

---

## License | 许可证

MIT License. See `LICENSE`.
