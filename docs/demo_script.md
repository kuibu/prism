# Prism MVP Demo Script (Current)

## 0) Prepare

```bash
cp .env.example .env
```

## 1) One-command startup + full demo

```bash
make demo
```

This command runs:
- `docker compose up -d --build`
- health checks (`/health/live`, `/health/ready`)
- full flow (`register -> create room -> send -> grant -> summarize allow -> summarize-and-send -> revoke -> summarize deny -> audit verify`)

Expected output includes:
- `DEMO_OK`

## 2) Core test suite

```bash
docker compose run --rm gateway_api pytest -q
```

Expected:
- `47 passed, 6 skipped` (live integration tests are skipped by default)

## 2.1) OpenViking memory backend tests (mocked HTTP)

```bash
docker compose run --rm gateway_api pytest -q \
  app/tests/test_memory_backends.py \
  app/tests/test_agents_hub.py::test_secretary_collect_memory_openviking_backend \
  app/tests/test_agents_hub.py::test_specialist_memory_note_openviking_backend
```

Expected:
- `5 passed`

## 3) Real live integration tests (against running stack)

```bash
make live-test
```

Equivalent:
```bash
PRISM_RUN_LIVE_TESTS=1 .venv/bin/pytest -q services/gateway_api/app/tests/test_live_integration.py
```

Expected:
- `5 passed`

## 4) CLI demo (gateway-backed)

Install CLI (Python 3.11+):
```bash
python3.11 -m venv .venv311
.venv311/bin/pip install -e clients/cli
```

Register + create room + send + sync:
```bash
SUF=$(date +%s)
USER="alice_${SUF}"
PASS="Passw0rd!"
SESSION=/tmp/prism-cli-session.json

.venv311/bin/prism-cli register \
  --user "$USER" \
  --password "$PASS" \
  --gateway-url http://localhost:8080/api/v1 \
  --session-file "$SESSION"

TOKEN=$(python3 -c "import json;print(json.load(open('$SESSION'))['access_token'])")
ROOM=$(curl -sS -X POST http://localhost:8080/api/v1/matrix/rooms \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"name":"cli-room","invite":[],"preset":"private_chat"}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["room_id"])')

.venv311/bin/prism-cli send "$ROOM" "hello from prism-cli" --session-file "$SESSION"
.venv311/bin/prism-cli sync --room-id "$ROOM" --timeout-ms 0 --session-file "$SESSION"
```

Optional file upload:
```bash
echo "demo file" > /tmp/prism-demo.txt
.venv311/bin/prism-cli send-file "$ROOM" /tmp/prism-demo.txt --session-file "$SESSION"
```

## 5) Web demo

Open:
```bash
open http://localhost:8080/web/
```

In browser:
1. Register/Login
2. Create room
3. Send text / upload file
4. Grant + Summarize
5. Revoke + Summarize (expect deny)
6. Query/verify audit

## 5.1) Bridge tab test (Matrix ↔ external connector simulation)

In Web `Bridge Test` tab:
1. Click `Load Platform Capabilities`, `Load Connectors`
2. Create connector:
 - Platform: `Telegram` (or `Slack/Discord`)
 - Bridge Name: `Demo Bridge`
 - Direction: `Bidirectional`
3. Create room mapping:
 - Select connector
 - `Active Room ID`: choose an existing room
 - External Room ID: `telegram_group_demo`
 - External Room Name: `Demo External Group`
 - Relay Prefix: `[TelegramBridge]`
4. Click `Create Mapping`
5. In relay test:
 - External Sender: `alice`
 - External Message: `Hello from bridge test`
 - Click `Simulate Inbound Relay`
6. Verify message appears in chat and message center
7. Click `Preview Outbound Relay` to check Matrix->external payload preview

## 5.2) Telegram real bridge test (Bot API)

Prerequisite:
- Create a Telegram bot via `@BotFather` and get a bot token
- Add bot to your Telegram group/channel
- Get Telegram chat_id (often looks like `-100...`)

In Web `Bridge Test` tab:
1. Platform select `Telegram`, direction select `Bidirectional`
2. Fill `Telegram Bot Token` and (optional) `Telegram API Base URL`
3. Create connector
4. Create mapping:
 - Active Room ID: your Matrix room
 - External Room ID: Telegram chat_id
5. Telegram -> Matrix:
 - Send a text in Telegram
 - Click `Pull Telegram Updates (Real)`
 - Check Matrix chat receives relayed message
6. Matrix -> Telegram:
 - Send a text in Matrix room
 - Click `Send To Telegram (Real)`
 - Check Telegram receives message

## 6) Observability

Prometheus:
```bash
open http://localhost:9090
```

Grafana (default admin/admin):
```bash
open http://localhost:3000
```

Gateway metrics endpoint:
```bash
curl -sS http://localhost:8080/metrics | head
```
