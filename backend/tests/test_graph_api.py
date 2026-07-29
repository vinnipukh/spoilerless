from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable
from pydantic import ValidationError

from backend.app.core.errors import install_database_error_handlers
from backend.app.domain.graph import GraphResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.graph.seed import setup_database


class UnavailableDatabase:
    def open(self) -> None:
        pass

    async def verify_connection(self) -> None:
        raise ServiceUnavailable("bolt://secret-user:secret-pass@database:7687")

    async def execute_query(self, _query: str, **_parameters):
        raise ServiceUnavailable("bolt://secret-user:secret-pass@database:7687 MATCH (n)")

    async def close(self) -> None:
        pass


async def _seed_live_database() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()


@pytest.fixture
def live_client() -> Iterator[TestClient]:
    asyncio.run(_seed_live_database())
    main_module = importlib.import_module("backend.app.main")
    with TestClient(main_module.app) as client:
        yield client


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


def test_graph_model_rejects_dangling_edge() -> None:
    with pytest.raises(ValidationError, match="dangling edges"):
        GraphResponse.model_validate(
            {
                "series": {"id": "series_dexter", "title": "Dexter", "slug": "dexter"},
                "visible_until_order": 1,
                "nodes": [
                    {
                        "id": "node:one",
                        "type": "Character",
                        "label": "One",
                        "visible_from_order": 1,
                        "origin": "canonical",
                    }
                ],
                "edges": [
                    {
                        "id": "edge:dangling",
                        "source": "node:one",
                        "target": "node:missing",
                        "type": "KNOWS",
                        "visible_from_order": 1,
                        "origin": "canonical",
                    }
                ],
                "claims": [],
                "sources": [],
                "evidence": [],
            }
        )


def test_graph_error_shapes(live_client: TestClient) -> None:
    unknown = live_client.get("/api/series/unknown/graph?visible_until_order=1")
    missing = live_client.get("/api/series/series_dexter/graph")
    malformed = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=not-a-number"
    )
    nonpersisted = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=4"
    )

    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "series_not_found"
    for response in (missing, malformed, nonpersisted):
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_visible_until_order"


def test_graph_database_unavailable_is_sanitized(live_client: TestClient) -> None:
    main_module = importlib.import_module("backend.app.main")
    main_module.app.dependency_overrides[get_database] = lambda: UnavailableDatabase()
    try:
        response = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=1"
        )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "secret" not in response.text
    assert "MATCH" not in response.text


@pytest.mark.parametrize(
    ("boundary", "expected", "forbidden"),
    [
        (
            1,
            {"nodes": 11, "edges": 6, "claims": 4, "sources": 1, "evidence": 3},
            ["dexter_s01e02", "S01E02", "Crocodile", "Paul Bennett", "Rudy Cooper", "ice rink"],
        ),
        (
            2,
            {"nodes": 15, "edges": 10, "claims": 5, "sources": 2, "evidence": 5},
            ["dexter_s01e03", "S01E03", "Popping Cherry", "Rudy Cooper", "Harry Morgan", "ice rink"],
        ),
        (3, {"nodes": 20, "edges": 16, "claims": 8, "sources": 3, "evidence": 8}, []),
    ],
)
def test_graph_boundaries_have_full_json_sentinels(
    live_client: TestClient,
    boundary: int,
    expected: dict[str, int],
    forbidden: list[str],
) -> None:
    response = live_client.get(
        f"/api/series/series_dexter/graph?visible_until_order={boundary}"
    )
    payload = response.json()
    serialized = json.dumps(payload, sort_keys=True)

    assert response.status_code == 200, payload
    assert payload["visible_until_order"] == boundary
    for collection, count in expected.items():
        assert len(payload[collection]) == count
    for sentinel in forbidden:
        assert sentinel.lower() not in serialized.lower()
    node_ids = {node["id"] for node in payload["nodes"]}
    assert all(
        edge["source"] in node_ids and edge["target"] in node_ids
        for edge in payload["edges"]
    )


def test_claim_validity_is_independent_of_visibility(live_client: TestClient) -> None:
    order_one = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=1"
    ).json()
    order_two = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=2"
    ).json()
    claim_id = "dexter:claim:s01e01:temporary_trust"

    assert claim_id in {claim["id"] for claim in order_one["claims"]}
    assert claim_id not in {claim["id"] for claim in order_two["claims"]}
    assert claim_id not in json.dumps(order_two, sort_keys=True)
