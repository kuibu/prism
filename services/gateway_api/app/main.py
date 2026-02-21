from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.agent.tool_gateway import InMemoryRateCounter
from app.api.router import api_router
from app.audit.immudb_client import ImmudbClient
from app.core.config import get_settings
from app.matrix.admin import AgentBotManager
from app.matrix.client import MatrixClient
from app.policy.opa_client import OPAClient

HTTP_REQUEST_COUNT = Counter(
    "prism_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "prism_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


def _setup_observability(app: FastAPI) -> None:
    if getattr(app.state, "observability_ready", False):
        return

    resource = Resource.create({"service.name": "prism-gateway-api"})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    app.state.observability_ready = True


def _teardown_observability(app: FastAPI) -> None:
    if not getattr(app.state, "observability_ready", False):
        return
    try:
        FastAPIInstrumentor.uninstrument_app(app)
    except Exception:
        pass
    try:
        HTTPXClientInstrumentor().uninstrument()
    except Exception:
        pass
    app.state.observability_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
    app.state.agent_bot_manager = AgentBotManager(
        matrix_client=app.state.matrix_client,
        username_prefix=settings.matrix_agent_bot_username_prefix,
        password_secret=settings.matrix_agent_bot_password_secret,
    )
    _setup_observability(app)
    yield
    await app.state.opa_client.close()
    _teardown_observability(app)


app = FastAPI(
    title="Prism Gateway API",
    version="0.1.0",
    description="Gateway for policy, audit, and agent runtime operations",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        path = request.url.path
        route = request.scope.get("route")
        template = getattr(route, "path", None)
        if isinstance(template, str) and template != "":
            path = template
        method = request.method
        HTTP_REQUEST_COUNT.labels(
            method=method,
            path=path,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_LATENCY_SECONDS.labels(method=method, path=path).observe(duration)


web_root = Path(__file__).resolve().parent / "web"
if web_root.exists():
    app.mount("/web", StaticFiles(directory=str(web_root), html=True), name="web")


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/web/", status_code=307)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
