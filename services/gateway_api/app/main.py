from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.audit.immudb_client import ImmudbClient
from app.core.config import get_settings
from app.policy.opa_client import OPAClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.opa_client = OPAClient(
        base_url=settings.opa_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.http_retry_attempts,
    )
    app.state.immudb_client = ImmudbClient(
        host=settings.immudb_host,
        port=settings.immudb_port,
        timeout_seconds=settings.immudb_timeout_seconds,
        retry_attempts=settings.immudb_retry_attempts,
    )
    yield
    await app.state.opa_client.close()


app = FastAPI(
    title="Prism Gateway API",
    version="0.1.0",
    description="Gateway for policy, audit, and agent runtime operations",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")
