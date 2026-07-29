from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


from backend.app.api.series import router as series_router
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase

SERVICE_NAME = "hdgrafcehennemi-backend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = Neo4jDatabase()
    database.open()
    app.state.neo4j = database
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_database_error_handlers(app)


@app.get("/health")
async def health_check(request: Request) -> JSONResponse:
    database: Neo4jDatabase = request.app.state.neo4j
    try:
        await database.verify_connection()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "unavailable",
                "service": SERVICE_NAME,
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "database": "connected",
            "service": SERVICE_NAME,
        },
    )
