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

## Iteration 4: CLI 登录 / sync / 发消息

1. 安装 CLI（本地虚拟环境示例）：

```bash
python3 -m venv .venv
.venv/bin/pip install -e clients/cli
```

2. 创建两个 Matrix 测试用户并建房（使用 Synapse Client API）：

```bash
SUFFIX=$(date +%s)
ALICE="alice_${SUFFIX}"
BOB="bob_${SUFFIX}"
PASS="Passw0rd!"

ALICE_JSON=$(curl -sS -X POST http://localhost:8008/_matrix/client/v3/register \
  -H 'content-type: application/json' \
  -d "{\"username\":\"${ALICE}\",\"password\":\"${PASS}\",\"auth\":{\"type\":\"m.login.dummy\"}}")
BOB_JSON=$(curl -sS -X POST http://localhost:8008/_matrix/client/v3/register \
  -H 'content-type: application/json' \
  -d "{\"username\":\"${BOB}\",\"password\":\"${PASS}\",\"auth\":{\"type\":\"m.login.dummy\"}}")

ALICE_TOKEN=$(echo "$ALICE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
BOB_USER=$(echo "$BOB_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["user_id"])')
ROOM_JSON=$(curl -sS -X POST http://localhost:8008/_matrix/client/v3/createRoom \
  -H "authorization: Bearer ${ALICE_TOKEN}" \
  -H 'content-type: application/json' \
  -d "{\"preset\":\"private_chat\",\"invite\":[\"${BOB_USER}\"]}")
ROOM_ID=$(echo "$ROOM_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["room_id"])')
echo "ROOM_ID=${ROOM_ID}"
```

3. 使用 CLI 登录 Alice：

```bash
.venv/bin/prism-cli login \
  --homeserver http://localhost:8008 \
  --user "${ALICE}" \
  --password "${PASS}" \
  --session-file /tmp/prism-cli-session.json
```

4. 使用 CLI 发消息：

```bash
.venv/bin/prism-cli send "${ROOM_ID}" "hello from prism-cli" \
  --session-file /tmp/prism-cli-session.json
```

5. 使用 CLI 做一次 sync 查看消息：

```bash
.venv/bin/prism-cli sync \
  --room-id "${ROOM_ID}" \
  --timeout-ms 2000 \
  --session-file /tmp/prism-cli-session.json
```

## Web 客户端联调（新增）

1. 启动服务后打开 Web 客户端：

```bash
open http://localhost:8080/web/
```

2. 在页面中填入：
- Homeserver URL: `http://localhost:8008`
- Gateway API URL: `http://localhost:8080/api/v1`

3. 先 `Register`，再 `Sync`，然后：
- `Create Room`（可选填写邀请用户）
- 输入房间 ID + 文本后 `Send`
- 再次 `Sync` 确认消息到达

4. Agent + Policy 联调：
- `Grant` 授权
- `Summarize Current Room`
- `Revoke` 后再次摘要应被拒绝

5. Audit 联调：
- `Query Events`
- `Verify Chain`

6. 自动化联调（无浏览器，覆盖与 Web 客户端一致的核心链路）：

```bash
python3 - <<'PY'
import json
import random
import string
import time
import urllib.error
import urllib.parse
import urllib.request

HS = "http://localhost:8008"
GW = "http://localhost:8080/api/v1"

def req_json(method, url, body=None, token=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}

suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
username = f"webu_{suffix}"
password = "Passw0rd!"
agent_id = "agent.web.demo"
purpose = "daily_summary"

code, reg = req_json("POST", f"{HS}/_matrix/client/v3/register", {
    "username": username,
    "password": password,
    "auth": {"type": "m.login.dummy"},
})
assert code in (200, 201), (code, reg)
user_id = reg["user_id"]

code, login = req_json("POST", f"{HS}/_matrix/client/v3/login", {
    "type": "m.login.password",
    "identifier": {"type": "m.id.user", "user": username},
    "password": password,
})
assert code == 200, (code, login)
token = login["access_token"]

code, room = req_json("POST", f"{HS}/_matrix/client/v3/createRoom", {
    "preset": "private_chat",
    "name": f"web-room-{suffix}",
}, token=token)
assert code == 200, (code, room)
room_id = room["room_id"]

msgs = ["今天完成 Matrix 登录流程", "OPA 授权链路已接通", "需要整理发布清单"]
for idx, msg in enumerate(msgs, 1):
    txn = f"tx{int(time.time() * 1000)}_{idx}"
    code, out = req_json(
        "PUT",
        f"{HS}/_matrix/client/v3/rooms/{urllib.parse.quote(room_id, safe='')}/send/m.room.message/{txn}",
        {"msgtype": "m.text", "body": msg},
        token=token,
    )
    assert code == 200, (code, out)

code, sync = req_json("GET", f"{HS}/_matrix/client/v3/sync?timeout=0", token=token)
assert code == 200, (code, sync)
events = sync.get("rooms", {}).get("join", {}).get(room_id, {}).get("timeline", {}).get("events", [])
bodies = [e.get("content", {}).get("body", "") for e in events if e.get("type") == "m.room.message"]
assert len(bodies) >= 3

code, grant = req_json("POST", f"{GW}/policy/grants", {
    "user_id": user_id,
    "agent_id": agent_id,
    "data_category": "room_messages",
    "purpose": purpose,
    "rate_limit_per_minute": 20,
})
assert code == 201, (code, grant)
grant_id = grant["grant_id"]

code, allow = req_json("POST", f"{GW}/agent/summarize", {
    "agent_id": agent_id,
    "user_id": user_id,
    "room_id": room_id,
    "purpose": purpose,
    "messages": bodies[-20:],
    "max_items": 8,
})
assert code == 200 and allow.get("decision") == "allow", (code, allow)

code, revoke = req_json("POST", f"{GW}/policy/revoke", {
    "user_id": user_id,
    "grant_id": grant_id,
    "reason": "web_integration_test",
})
assert code == 200, (code, revoke)

code, deny = req_json("POST", f"{GW}/agent/summarize", {
    "agent_id": agent_id,
    "user_id": user_id,
    "room_id": room_id,
    "purpose": purpose,
    "messages": bodies[-20:],
    "max_items": 8,
})
assert code == 403, (code, deny)

query = urllib.parse.urlencode({"actor_id": agent_id, "limit": 50})
code, audit = req_json("GET", f"{GW}/audit/events?{query}")
assert code == 200 and len(audit.get("events", [])) >= 2, (code, audit)

code, verify = req_json("GET", f"{GW}/audit/verify?{query}")
assert code == 200 and verify.get("verified") is True, (code, verify)

print("WEB_CLIENT_FLOW_OK")
print(json.dumps({
    "user_id": user_id,
    "room_id": room_id,
    "grant_id": grant_id,
    "audit_events": len(audit.get("events", [])),
    "verified": verify.get("verified"),
    "checked_events": verify.get("checked_events"),
}, ensure_ascii=False, indent=2))
PY
```
