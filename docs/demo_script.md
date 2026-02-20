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
