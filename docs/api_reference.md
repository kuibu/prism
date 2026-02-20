# API Reference (Iteration 1)

Base URL: `http://localhost:8080/api/v1`

## `GET /health/live`

Returns gateway process liveness.

Response example:

```json
{
  "status": "ok",
  "service": "gateway_api"
}
```

## `GET /health/ready`

Checks gateway readiness and dependency connectivity.

Response fields:

- `status`: `ready` or `degraded`
- `dependencies.opa`: OPA connectivity detail
- `dependencies.immudb`: immudb connectivity detail

Returns HTTP `200` when all dependencies are reachable, otherwise `503`.
