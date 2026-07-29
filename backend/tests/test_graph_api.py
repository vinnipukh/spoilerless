from __future__ import annotations

import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from backend.app.core.errors import install_database_error_handlers


class UnavailableDatabase:
    def open(self) -> None:
        pass

    async def verify_connection(self) -> None:
        raise ServiceUnavailable("bolt://secret-user:secret-pass@database:7687")

    async def close(self) -> None:
        pass


def test_error_responses() -> None:
    app = FastAPI()
    install_database_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise ServiceUnavailable("bolt://secret-user:secret-pass@database:7687 MATCH (n)")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "database_unavailable",
            "message": "The graph database is unavailable.",
        }
    }
    assert "secret" not in response.text
    assert "MATCH" not in response.text


def test_app_starts_degraded_and_docs_remain_available(monkeypatch) -> None:
    main_module = importlib.import_module("backend.app.main")
    monkeypatch.setattr(main_module, "Neo4jDatabase", UnavailableDatabase)

    with TestClient(main_module.app) as client:
        health = client.get("/health")
        docs = client.get("/docs")

    assert health.status_code == 503
    assert health.json() == {
        "status": "degraded",
        "database": "unavailable",
        "service": "hdgrafcehennemi-backend",
    }
    assert docs.status_code == 200


def test_database_module_has_no_driver_singleton(monkeypatch) -> None:
    import backend.app.graph.database as database_module

    calls = []
    monkeypatch.setattr(
        database_module.AsyncGraphDatabase,
        "driver",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    importlib.reload(database_module)

    assert calls == []
    assert not hasattr(database_module, "neo4j_db")
