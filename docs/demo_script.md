# Prism MVP Demo Script

## Iteration 1: Infra bootstrap + connectivity

1. Initialize env:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up -d --build
```

3. Verify service status:

```bash
docker compose ps
```

4. Check gateway liveness:

```bash
curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
```

5. Check readiness (OPA + immudb connectivity):

```bash
curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
```

6. Optional: direct OPA check:

```bash
curl -sS http://localhost:8181/health
```

## Iteration 2: AuditEvent write/query/verify + non-404 MVP routes

1. Write an audit event:

```bash
curl -sS -X POST http://localhost:8080/api/v1/audit/events \
  -H 'content-type: application/json' \
  -d '{
    "actor_type": "user",
    "actor_id": "@alice:localhost",
    "action_type": "send_message",
    "resource_type": "room",
    "resource_id": "!room:localhost",
    "decision": "allow",
    "reason_code": "ok",
    "user_id": "@alice:localhost",
    "room_id": "!room:localhost",
    "input_data": {"body": "hello"},
    "output_data": {"event_id": "evt123"}
  }' | python3 -m json.tool
```

2. Query audit events:

```bash
curl -sS "http://localhost:8080/api/v1/audit/events?actor_id=@alice:localhost&limit=20" | python3 -m json.tool
```

3. Verify audit chain:

```bash
curl -sS "http://localhost:8080/api/v1/audit/verify?actor_id=@alice:localhost" | python3 -m json.tool
```

4. Create and revoke a policy grant:

```bash
GRANT=$(curl -sS -X POST http://localhost:8080/api/v1/policy/grants \
  -H 'content-type: application/json' \
  -d '{
    "user_id":"@alice:localhost",
    "agent_id":"agent.summary",
    "data_category":"room_messages",
    "purpose":"daily_summary",
    "rate_limit_per_minute":60
  }')
echo "$GRANT" | python3 -m json.tool
GRANT_ID=$(echo "$GRANT" | python3 -c "import json,sys; print(json.load(sys.stdin)['grant_id'])")
curl -sS -X POST http://localhost:8080/api/v1/policy/revoke \
  -H 'content-type: application/json' \
  -d "{\"user_id\":\"@alice:localhost\",\"grant_id\":\"$GRANT_ID\",\"reason\":\"user_request\"}" | python3 -m json.tool
```

5. Call agent summarize endpoint (policy-dependent):

```bash
curl -sS -X POST http://localhost:8080/api/v1/agent/summarize \
  -H 'content-type: application/json' \
  -d '{
    "agent_id":"agent.summary",
    "user_id":"@alice:localhost",
    "room_id":"!room:localhost",
    "purpose":"daily_summary",
    "messages":["finish API","review PR","write docs"],
    "max_items":5
  }' | python3 -m json.tool
```

6. Check that previously-missing routes exist:

```bash
for endpoint in \
  /api/v1/policy/grants \
  /api/v1/policy/revoke \
  /api/v1/audit/events \
  /api/v1/audit/verify \
  /api/v1/agent/summarize \
  /api/v1/matrix/sync
do
  code=$(curl -s -o /tmp/prism_route.out -w '%{http_code}' "http://localhost:8080${endpoint}")
  echo "${endpoint} -> HTTP ${code}"
done
```

## Iteration 3: OPA grant/revoke + 实际策略判定（非内存策略）

1. 创建授权（写入 OPA data）：

```bash
GRANT=$(curl -sS -X POST http://localhost:8080/api/v1/policy/grants \
  -H 'content-type: application/json' \
  -d '{
    "user_id":"@alice:localhost",
    "agent_id":"agent.summary",
    "data_category":"room_messages",
    "purpose":"daily_summary",
    "rate_limit_per_minute":60
  }')
echo "$GRANT" | python3 -m json.tool
GRANT_ID=$(echo "$GRANT" | python3 -c "import json,sys; print(json.load(sys.stdin)['grant_id'])")
```

2. 授权后触发智能体摘要（应 allow）：

```bash
curl -sS -X POST http://localhost:8080/api/v1/agent/summarize \
  -H 'content-type: application/json' \
  -d '{
    "agent_id":"agent.summary",
    "user_id":"@alice:localhost",
    "room_id":"!room:localhost",
    "purpose":"daily_summary",
    "messages":["finish API","review PR","write docs"],
    "max_items":5
  }' | python3 -m json.tool
```

3. 撤销授权并再次调用（应 deny，原因 `grant_revoked`）：

```bash
curl -sS -X POST http://localhost:8080/api/v1/policy/revoke \
  -H 'content-type: application/json' \
  -d "{\"user_id\":\"@alice:localhost\",\"grant_id\":\"$GRANT_ID\",\"reason\":\"user_request\"}" | python3 -m json.tool

curl -sS -X POST http://localhost:8080/api/v1/agent/summarize \
  -H 'content-type: application/json' \
  -d '{
    "agent_id":"agent.summary",
    "user_id":"@alice:localhost",
    "room_id":"!room:localhost",
    "purpose":"daily_summary",
    "messages":["finish API","review PR","write docs"],
    "max_items":5
  }' | python3 -m json.tool
```

4. 查看策略与审计结果：

```bash
curl -sS "http://localhost:8080/api/v1/policy/grants?user_id=@alice:localhost&include_revoked=true" | python3 -m json.tool
curl -sS "http://localhost:8080/api/v1/audit/events?action_type=agent_summarize&actor_id=agent.summary" | python3 -m json.tool
```

5. 运行网关测试（包含 Iteration 3 集成测试）：

```bash
docker compose run --rm gateway_api pytest -q
```
