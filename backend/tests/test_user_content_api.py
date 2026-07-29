from __future__ import annotations

import asyncio
import importlib
from collections.abc import Callable, Iterator
from typing import Any, Protocol

import pytest
from fastapi.testclient import TestClient

from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.graph.seed import setup_database


TEST_SERIES_ID = "test-series:user-content"
USER_ONLY_CLEANUP_QUERY = """
MATCH (resource)
WHERE resource.origin = 'user'
DETACH DELETE resource
"""
SECOND_SERIES_SETUP_QUERY = """
MERGE (series:Series {id: $series_id})
SET series.title = 'User Content Test Series',
    series.slug = 'user-content-test-series',
    series.origin = 'user'
MERGE (episode:Episode {id: $episode_id})
SET episode.series_id = $series_id,
    episode.season_number = 1,
    episode.episode_number = 1,
    episode.episode_order = 1,
    episode.code = 'S01E01',
    episode.title = 'Test Episode',
    episode.visible_from_order = 1,
    episode.origin = 'user'
MERGE (episode)-[part:PART_OF]->(series)
SET part.id = $part_id,
    part.series_id = $series_id,
    part.visible_from_order = 1,
    part.origin = 'user'
"""
SECOND_SERIES_CLEANUP_QUERY = """
MATCH (resource)
WHERE resource.series_id = $series_id OR resource.id = $series_id
DETACH DELETE resource
"""
USER_SNAPSHOT_QUERY = """
MATCH (resource)
WHERE resource.origin = 'user'
RETURN labels(resource) AS labels, properties(resource) AS properties
ORDER BY properties.id
"""


class DatabaseOverride(Protocol):
    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]: ...


def _run(coroutine):
    return asyncio.run(coroutine)


async def _with_database(operation: Callable[[Neo4jDatabase], Any]) -> Any:
    database = Neo4jDatabase()
    database.open()
    try:
        return await operation(database)
    finally:
        await database.close()


async def _seed_and_clean(database: Neo4jDatabase) -> None:
    await database.verify_connection()
    await setup_database(database)
    await database.execute_query(USER_ONLY_CLEANUP_QUERY)


async def _cleanup_user_content(database: Neo4jDatabase) -> None:
    await database.execute_query(USER_ONLY_CLEANUP_QUERY)


async def _create_second_series(database: Neo4jDatabase) -> None:
    await database.execute_query(
        SECOND_SERIES_SETUP_QUERY,
        series_id=TEST_SERIES_ID,
        episode_id=f"{TEST_SERIES_ID}:episode:1",
        part_id=f"{TEST_SERIES_ID}:part-of:1",
    )


async def _cleanup_second_series(database: Neo4jDatabase) -> None:
    await database.execute_query(SECOND_SERIES_CLEANUP_QUERY, series_id=TEST_SERIES_ID)


async def database_snapshot(query: str, **parameters: Any) -> list[dict[str, Any]]:
    async def capture(database: Neo4jDatabase) -> list[dict[str, Any]]:
        return await database.execute_query(query, **parameters)

    return await _with_database(capture)


def direct_database_snapshot(query: str = USER_SNAPSHOT_QUERY, **parameters: Any) -> list[dict[str, Any]]:
    return _run(database_snapshot(query, **parameters))


def assert_hidden_matches_missing(hidden_response, missing_response) -> None:
    assert hidden_response.status_code == missing_response.status_code == 404
    assert hidden_response.json() == missing_response.json()
    for forbidden in ("secret", "MATCH (", "bolt://"):
        assert forbidden not in hidden_response.text
        assert forbidden not in missing_response.text


def test_note_character_lifecycle_and_spoiler_boundary(user_content_client: TestClient) -> None:
    base = "/api/series/series_dexter/notes"
    created = user_content_client.post(
        base,
        json={
            "target_type": "Character",
            "target_id": "dexter:character:rudy_cooper",
            "content": "A spoiler-safe note",
        },
    )
    assert created.status_code == 201
    note = created.json()
    assert note["id"].startswith("user-note:")
    assert note["origin"] == "user"
    assert note["created_at"] == note["updated_at"]
    note_id = note["id"]

    hidden = user_content_client.get(f"{base}/{note_id}", params={"visible_until_order": 2})
    missing = user_content_client.get(
        f"{base}/user-note:does-not-exist", params={"visible_until_order": 2}
    )
    assert_hidden_matches_missing(hidden, missing)
    assert user_content_client.get(
        f"{base}/{note_id}", params={"visible_until_order": 3}
    ).status_code == 200
    assert user_content_client.patch(
        f"{base}/{note_id}", json={"content": "Updated note"}
    ).status_code == 200
    assert user_content_client.delete(f"{base}/{note_id}").status_code == 204
    assert user_content_client.get(
        f"{base}/{note_id}", params={"visible_until_order": 3}
    ).status_code == 404


def test_note_claim_filter_validation_and_canonical_survival(
    user_content_client: TestClient,
) -> None:
    base = "/api/series/series_dexter/notes"
    created = user_content_client.post(
        base,
        json={
            "target_type": "Claim",
            "target_id": "dexter:claim:s01e01:dexter_debra_family",
            "content": "Claim note",
        },
    )
    assert created.status_code == 201
    note_id = created.json()["id"]
    listed = user_content_client.get(
        base,
        params={
            "visible_until_order": 1,
            "target_type": "Claim",
            "target_id": "dexter:claim:s01e01:dexter_debra_family",
        },
    )
    assert listed.status_code == 200 and [row["id"] for row in listed.json()] == [note_id]

    partial = user_content_client.get(
        base, params={"visible_until_order": 1, "target_type": "Claim"}
    )
    assert partial.status_code == 422
    for boundary in (0, -1, "nope", 4):
        assert user_content_client.get(base, params={"visible_until_order": boundary}).status_code == 422

    canonical = user_content_client.get("/api/series/series_dexter/graph", params={"visible_until_order": 1})
    assert canonical.status_code == 200
    assert user_content_client.delete(f"{base}/{note_id}").status_code == 204
    after = user_content_client.get("/api/series/series_dexter/graph", params={"visible_until_order": 1})
    assert after.status_code == 200
    assert after.json()["series"]["id"] == "series_dexter"


@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    _run(_with_database(_seed_and_clean))
    main_module = importlib.import_module("backend.app.main")
    with TestClient(main_module.app) as client:
        yield client
    _run(_with_database(_cleanup_user_content))


@pytest.fixture
def user_content_client(live_client: TestClient) -> Iterator[TestClient]:
    _run(_with_database(_cleanup_user_content))
    try:
        yield live_client
    finally:
        _run(_with_database(_cleanup_user_content))


@pytest.fixture
def second_series() -> Iterator[str]:
    _run(_with_database(_cleanup_second_series))
    _run(_with_database(_create_second_series))
    try:
        yield TEST_SERIES_ID
    finally:
        _run(_with_database(_cleanup_second_series))


@pytest.fixture
def override_database(live_client: TestClient) -> Iterator[Callable[[DatabaseOverride], TestClient]]:
    main_module = importlib.import_module("backend.app.main")

    def apply(database: DatabaseOverride) -> TestClient:
        main_module.app.dependency_overrides[get_database] = lambda: database
        return live_client

    try:
        yield apply
    finally:
        main_module.app.dependency_overrides.pop(get_database, None)
