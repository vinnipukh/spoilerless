from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from typing import Literal


from spoilerless.app.api.graph import router as graph_router
from spoilerless.app.api.series import router as series_router
from spoilerless.app.api.user_content import router as user_content_router
from spoilerless.app.api.auth import router as auth_router
from spoilerless.app.api.revisions import router as revision_router
from spoilerless.app.api.candidates import router as candidates_router
from spoilerless.app.api.progress import router as progress_router
from spoilerless.app.api.chat import router as chat_router
from spoilerless.app.api.change_set import router as change_set_router
from spoilerless.app.api.settings import router as settings_router
from spoilerless.app.core.config import get_settings
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.llm.provider import install_llm_error_handlers
from spoilerless.app.repository.session import Neo4jSessionRepository
from spoilerless.app.services.rate_limit import init_rate_limiter

SERVICE_NAME = "spoilerless-backend"

log = logging.getLogger(__name__)

# Header names that MUST NOT appear in request logs.
_DENIED_HEADER_PREFIXES = ("x-llm-",)
_DENIED_HEADER_NAMES = {"cookie", "set-cookie", "authorization"}


async def _request_logging_middleware(request: Request, call_next) -> Response:
    """Log one INFO line per request: method, path, status, duration (ms).

    Never logs the full header dict, any ``X-LLM-*`` / ``Cookie`` /
    ``Set-Cookie`` / ``Authorization`` header value, or the request body.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Build a safe subset of headers to log (allowlist, small fixed set).
    safe_headers: dict[str, str] = {}
    for name in ("user-agent", "content-type", "accept"):
        value = request.headers.get(name)
        if value:
            safe_headers[name] = value

    log.info(
        "%s %s %d %.0fms %s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        safe_headers,
    )
    return response


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    database: Literal["connected", "unavailable"]
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database = Neo4jDatabase(settings)
    database.open()
    app.state.neo4j = database
    app.state.session_repo = Neo4jSessionRepository(database)
    if settings.redis_url:
        # Redis-backed rate limiting (08-05). Guarded on a non-empty
        # redis_url so local dev without Upstash runs unthrottled instead of
        # crashing startup; RateLimiter dependencies no-op until then.
        await init_rate_limiter()
    try:
        try:
            await database.verify_connection()
        except Exception:
            # Degraded startup is intentional; /health reports current connectivity.
            pass
        yield
    finally:
        await database.close()


app = FastAPI(
    title="Spoilerless API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(series_router)
app.include_router(graph_router)
app.include_router(user_content_router)
app.include_router(auth_router)
app.include_router(revision_router)
app.include_router(candidates_router)
app.include_router(progress_router)
app.include_router(chat_router)
app.include_router(change_set_router)
app.include_router(settings_router)

settings = get_settings()
_allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(_request_logging_middleware)
install_database_error_handlers(app)
install_llm_error_handlers(app)


@app.get("/health", response_model=HealthResponse, summary="Check service and database health",
         responses={503: {"model": HealthResponse, "description": "Database is unavailable."}})
async def health_check(request: Request) -> HealthResponse | JSONResponse:
    database: Neo4jDatabase = request.app.state.neo4j
    try:
        await database.verify_connection()
    except Exception:
        return JSONResponse(status_code=503, content=HealthResponse(
            status="degraded", database="unavailable", service=SERVICE_NAME
        ).model_dump())
    return HealthResponse(
        status="ok", database="connected", service=SERVICE_NAME
    )
