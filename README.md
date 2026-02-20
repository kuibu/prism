# Prism: AI-Native + Transparent-Security Matrix MVP

This repository implements an iterative MVP for a next-generation WeChat-like app based on Matrix.

## Iteration 1 status

Completed:

- Docker Compose stack for Synapse, OPA, immudb, MinIO, and `gateway_api`
- FastAPI gateway skeleton with health and readiness probes
- OPA and immudb connectivity checks in gateway readiness API
- Initial docs, policy bundle, and CLI scaffolding

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
```

## Repository layout

- `/docker-compose.yml`: local stack bootstrap
- `/services/gateway_api`: FastAPI gateway service
- `/clients/cli`: Python developer CLI
- `/policies/opa`: OPA Rego policies and data
- `/docs`: architecture, threat model, API reference, demo script

See `/docs/demo_script.md` for step-by-step demo commands.
