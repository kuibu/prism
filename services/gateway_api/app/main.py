from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.agent.tool_gateway import InMemoryRateCounter
from app.api.router import api_router
from app.audit.immudb_client import ImmudbClient
from app.core.config import get_settings
from app.matrix.client import MatrixClient
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
        username=settings.immudb_username,
        password=settings.immudb_password,
        database=settings.immudb_database,
    )
    app.state.agent_rate_counter = InMemoryRateCounter(window_seconds=60)
    app.state.matrix_client = MatrixClient(
        homeserver_url=settings.matrix_homeserver_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.http_retry_attempts,
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

web_root = Path(__file__).resolve().parent / "web"
if web_root.exists():
    app.mount("/web", StaticFiles(directory=str(web_root), html=True), name="web")


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/web/", status_code=307)
