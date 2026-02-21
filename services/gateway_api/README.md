# prism-gateway-api

FastAPI service providing policy, audit, and agent gateways.

## Key endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/matrix/register`
- `POST /api/v1/matrix/login`
- `POST /api/v1/matrix/rooms/{room_id}/messages`
- `POST /api/v1/policy/grants`
- `POST /api/v1/policy/revoke`
- `POST /api/v1/agent/summarize`
- `POST /api/v1/agent/summarize-and-send`
- `GET /api/v1/audit/events`
- `GET /api/v1/audit/verify`

See root docs for details:
- `docs/api_reference.md`
