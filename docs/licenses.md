# Third-party Components and Licenses (Initial)

This list captures major components selected for the MVP stack.

- Synapse (`matrixdotorg/synapse`) - Apache-2.0
- OPA (`openpolicyagent/opa`) - Apache-2.0
- immudb (`codenotary/immudb`) - Apache-2.0
- MinIO (`minio/minio`) - AGPL-3.0
- Prometheus (`prom/prometheus`) - Apache-2.0
- Grafana (`grafana/grafana-oss`) - AGPL-3.0
- FastAPI - MIT
- Uvicorn - BSD-3-Clause
- httpx - BSD-3-Clause
- Pydantic - MIT
- OpenTelemetry API/SDK + instrumentation - Apache-2.0
- prometheus-client (Python) - Apache-2.0

Notes:
- Confirm image tag-specific licenses before production release.
- Add transitive dependency export in later iterations.
