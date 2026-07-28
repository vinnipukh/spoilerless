from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.graph.database import neo4j_db
from app.api.series import router as series_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    neo4j_db.verify_connection()
    yield
    neo4j_db.close()


app = FastAPI(
    title="HD Graf Cehennemi API",
    version="0.1.0",
    lifespan=lifespan,
)

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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "hdgrafcehennemi-backend",
        "database": "connected",
    }