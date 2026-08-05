from __future__ import annotations

import asyncio
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
from spoilerless.app.core.config import get_settings, verify_google_client_id_equality
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


_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' https://accounts.google.com; "
        "img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; connect-src 'self' https://accounts.google.com; "
        "frame-src https://accounts.google.com; object-src 'none'; "
        "base-uri 'self'; form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


async def _security_headers_middleware(request: Request, call_next) -> Response:
    """Attach baseline security headers to every response (PROB-17/#38).

    CSP is tuned to the app's needs: the Google Identity Services script
    (frontend/index.html) plus self-hosted fonts/scripts and hotlinked
    character images (img-src 'self' data: https:). HSTS is only meaningful
    over HTTPS but is harmless locally.
    """
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


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
    verify_google_client_id_equality(settings)
    database = Neo4jDatabase(settings)
    database.open()
    app.state.neo4j = database
    app.state.session_repo = Neo4jSessionRepository(database)
    if settings.redis_url:
        # Redis-backed rate limiting (08-05). Guarded on a non-empty
        # redis_url so local dev without Upstash runs unthrottled instead of
        # crashing startup; RateLimiter dependencies no-op until then.
        await init_rate_limiter()

    # PROB-03/#9: periodic session sweep — expired/revoked (:Session) nodes
    # are deleted in the background (no slide-on-read keeps expiry meaningful).
    # Guarded like the rate limiter: the task is only started when the app can
    # reach its database, and a failed sweep iteration is logged, never fatal.
    SESSION_SWEEP_INTERVAL_SECONDS = 3600

    async def _session_sweep_loop() -> None:
        while True:
            try:
                await app.state.session_repo.sweep_expired()
            except Exception:
                logger.exception("session sweep iteration failed; will retry")
            await asyncio.sleep(SESSION_SWEEP_INTERVAL_SECONDS)

    sweep_task: asyncio.Task[None] | None = None
    try:
        try:
            await database.verify_connection()
        except Exception:
            # Degraded startup is intentional; /health reports current connectivity.
            # The session sweep task is skipped too (no reachable database).
            pass
        else:
            sweep_task = asyncio.create_task(_session_sweep_loop())
        yield
    finally:
        if sweep_task is not None:
            sweep_task.cancel()
            try:
                await sweep_task
            except asyncio.CancelledError:
                pass
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
    # Explicit method/header lists — never wildcards combined with
    # allow_credentials=True (PROB-17/#38). Header list covers the BYOK
    # X-LLM-* headers the frontend sends (frontend/src/lib/byok.ts).
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-LLM-Api-Key",
        "X-LLM-Provider",
        "X-LLM-Base-URL",
        "X-LLM-Model",
    ],
)
app.middleware("http")(_security_headers_middleware)
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


@app.head("/health", include_in_schema=False)
async def health_check_head(request: Request) -> Response:
    """HEAD variant of the health check for uptime monitors (UptimeRobot etc.).

    FastAPI does not auto-register HEAD for a GET route, so a HEAD probe would
    otherwise get 405. Returns 200 when the database is reachable, 503 when not.
    """
    database: Neo4jDatabase = request.app.state.neo4j
    try:
        await database.verify_connection()
    except Exception:
        return Response(status_code=503)
    return Response(status_code=200)
