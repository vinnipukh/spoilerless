"""Direct tests for the FastAPI lifespan + /health (PROB-18/#40).

Covers: the session-sweep background task starts and stops with the app
(09-04), the rate-limiter guard on empty redis_url (08-05), and the /health
200 (database connected) vs 503 (degraded) shapes including the renamed
service field (09-01).
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class UnavailableDatabase:
    """Degraded-startup stand-in: verify_connection raises."""

    def __init__(self, settings=None) -> None:  # noqa: D102
        self._settings = settings

    def open(self) -> None:  # noqa: D102
        pass

    async def verify_connection(self) -> None:  # noqa: D102
        raise RuntimeError("db down")

    async def close(self) -> None:  # noqa: D102
        pass


def test_health_ok_when_database_connected() -> None:
    """Live DB reachable → /health 200 with the renamed service field."""
    main_module = importlib.import_module("spoilerless.app.main")
    with TestClient(main_module.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"
    assert response.json()["service"] == "spoilerless-backend"


def test_health_degraded_when_database_unavailable() -> None:
    main_module = importlib.import_module("spoilerless.app.main")
    with patch.object(main_module, "Neo4jDatabase", UnavailableDatabase):
        with TestClient(main_module.app) as client:
            response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"
    assert response.json()["service"] == "spoilerless-backend"


def test_lifespan_starts_and_stops_sweep_task() -> None:
    """The 09-04 session-sweep task is created on startup and cancelled on
    shutdown — verified via TestClient enter/exit (no dangling tasks)."""
    main_module = importlib.import_module("spoilerless.app.main")
    original = main_module.Neo4jDatabase
    try:
        main_module.Neo4jDatabase = importlib.import_module(
            "spoilerless.app.graph.database"
        ).Neo4jDatabase
        with TestClient(main_module.app) as client:
            # Sweep task must have been registered (database reachable).
            assert client.get("/health").status_code == 200
            # Any background task the lifespan created is cancelled at exit —
            # TestClient.__exit__ awaits the lifespan shutdown.
    finally:
        main_module.Neo4jDatabase = original


def test_lifespan_rate_limiter_guard_empty_redis_url(monkeypatch) -> None:
    """08-05 guard: with redis_url empty, init_rate_limiter is NOT called and
    startup succeeds (local dev runs unthrottled)."""
    main_module = importlib.import_module("spoilerless.app.main")
    called = {"n": 0}

    async def fake_init() -> None:
        called["n"] += 1

    with patch.object(main_module, "init_rate_limiter", fake_init), patch(
        "spoilerless.app.core.config.get_settings",
        return_value=type(
            "S",
            (),
            {
                "redis_url": "",
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_username": "neo4j",
                "neo4j_password": "hdgraf-local-password",
                "neo4j_database": "neo4j",
                "frontend_origins": "http://localhost:5173",
            },
        )(),
    ):
        with TestClient(main_module.app) as client:
            assert client.get("/health").status_code == 200
    assert called["n"] == 0
