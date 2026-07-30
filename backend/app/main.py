from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import Literal


from backend.app.api.graph import router as graph_router
from backend.app.api.series import router as series_router
from backend.app.api.user_content import router as user_content_router
from backend.app.api.auth import router as auth_router
from backend.app.api.revisions import router as revision_router
from backend.app.core.config import get_settings
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.session import Neo4jSessionRepository

SERVICE_NAME = "hdgrafcehennemi-backend"


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
    title="HD Graf Cehennemi API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(series_router)
app.include_router(graph_router)
app.include_router(user_content_router)
app.include_router(auth_router)
app.include_router(revision_router)

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
install_database_error_handlers(app)


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
