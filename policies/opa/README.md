# OPA Policy (MVP)

This folder contains the policy bundle loaded by the OPA sidecar.

- `policy.rego`: Rego rules used by `gateway_api`
- `data.json`: dynamic data for policy evaluation (`grants` map keyed by `grant_id`)

Quick check:

```bash
curl -s http://localhost:8181/v1/data/prism/allow \
  -H 'content-type: application/json' \
  -d '{"input": {"action": "healthcheck"}}'
```
