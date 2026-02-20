from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: str
    service: str
    ts: datetime


class ReadinessResponse(BaseModel):
    status: str
    service: str
    ts: datetime
    dependencies: dict[str, dict[str, Any]]


@router.get("/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service="gateway_api",
        ts=datetime.now(timezone.utc),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> JSONResponse | ReadinessResponse:
    opa_status = await request.app.state.opa_client.health()
    immudb_status = await request.app.state.immudb_client.health()
    is_ready = bool(opa_status.get("reachable") and immudb_status.get("reachable"))

    payload = ReadinessResponse(
        status="ready" if is_ready else "degraded",
        service="gateway_api",
        ts=datetime.now(timezone.utc),
        dependencies={
            "opa": opa_status,
            "immudb": immudb_status,
        },
    )

    if is_ready:
        return payload
    return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
