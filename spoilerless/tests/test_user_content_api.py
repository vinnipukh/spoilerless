from __future__ import annotations

import asyncio
import importlib
from collections.abc import Callable, Iterator
from typing import Any, Protocol

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.graph.seed import setup_database


TEST_SERIES_ID = "test-series:user-content"
USER_ONLY_CLEANUP_QUERY = """
MATCH (resource)
WHERE resource.origin = 'user'
DETACH DELETE resource
"""
REVISION_CLEANUP_QUERY = """
MATCH (r:Revision)
DETACH DELETE r
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
    await database.execute_query(REVISION_CLEANUP_QUERY)


async def _cleanup_user_content(database: Neo4jDatabase) -> None:
    await database.execute_query(USER_ONLY_CLEANUP_QUERY)
    await database.execute_query(REVISION_CLEANUP_QUERY)


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


def test_custom_node_crud_all_five_types_and_visibility(user_content_client: TestClient) -> None:
    base = "/api/series/series_dexter/custom-nodes"
    ids: list[str] = []
    for node_type in ("Character", "Event", "Location", "Organization", "Object"):
        created = user_content_client.post(
            base, json={"node_type": node_type, "label": f"user {node_type}",
                        "episode_id": "dexter_s01e03"}
        )
        assert created.status_code == 201
        row = created.json()
        ids.append(row["id"])
        assert row["id"].startswith("user-node:")
        assert row["type"] == node_type and row["origin"] == "user"
        assert row["visible_from_order"] == 3
        assert user_content_client.get(f"{base}/{row['id']}", params={"visible_until_order": 2}).status_code == 404
        assert user_content_client.get(f"{base}/{row['id']}", params={"visible_until_order": 3}).status_code == 200
        updated = user_content_client.patch(f"{base}/{row['id']}", json={"label": "renamed"})
        assert updated.status_code == 200 and updated.json()["label"] == "renamed"
    for node_id in ids:
        response = user_content_client.delete(f"{base}/{node_id}")
        assert response.status_code == 204 and response.content == b""


@pytest.mark.parametrize("predicate", [
    "PARTICIPATED_IN", "WITNESSED", "CAUSED", "AFFECTED", "TARGETED", "MENTIONED",
    "KNOWS", "FAMILY_OF", "WORKS_WITH", "TRUSTS", "DISTRUSTS", "HELPS", "OPPOSES",
    "THREATENS", "ATTACKS", "KILLS",
])
def test_custom_relationship_allowed_predicates_crud(
    user_content_client: TestClient, predicate: str
) -> None:
    base = "/api/series/series_dexter/custom-relationships"
    created = user_content_client.post(base, json={
        "source_id": "dexter:character:dexter_morgan",
        "target_id": "dexter:character:debra_morgan",
        "predicate": predicate, "episode_id": "dexter_s01e01",
    })
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["id"].startswith("user-rel:") and row["type"] == predicate
    read = user_content_client.get(f"{base}/{row['id']}", params={"visible_until_order": 1})
    assert read.status_code == 200, read.text
    changed = "TRUSTS" if predicate != "TRUSTS" else "KNOWS"
    patched = user_content_client.patch(f"{base}/{row['id']}", json={"predicate": changed})
    assert patched.status_code == 200 and patched.json()["type"] == changed
    assert user_content_client.delete(f"{base}/{row['id']}").status_code == 204


@pytest.mark.parametrize("predicate", [
    "PART_OF", "PRECEDES", "LOCATED_IN", "SUPPORTED_BY", "CONTRADICTED_BY",
    "DERIVED_FROM", "REFERS_TO", "CORRECTS", "SUPERSEDES", "REVERTS_TO", "NOPE",
])
def test_custom_relationship_rejects_non_user_predicate_groups(
    user_content_client: TestClient, predicate: str
) -> None:
    response = user_content_client.post("/api/series/series_dexter/custom-relationships", json={
        "source_id": "dexter:character:dexter_morgan", "target_id": "dexter:character:debra_morgan",
        "predicate": predicate, "episode_id": "dexter_s01e01",
    })
    assert response.status_code == 422
    assert response.json() == {"detail": {"code": "invalid_request", "message": "Request validation failed."}}


def test_custom_relationship_visibility_max_cross_series_dangling_and_in_use(
    user_content_client: TestClient, second_series: str
) -> None:
    node = user_content_client.post("/api/series/series_dexter/custom-nodes", json={
        "node_type": "Object", "label": "late object", "episode_id": "dexter_s01e03"
    }).json()
    rel_base = "/api/series/series_dexter/custom-relationships"
    rel = user_content_client.post(rel_base, json={
        "source_id": node["id"], "target_id": "dexter:character:dexter_morgan",
        "predicate": "KNOWS", "episode_id": "dexter_s01e01"
    })
    assert rel.status_code == 201 and rel.json()["visible_from_order"] == 3
    rel_id = rel.json()["id"]
    assert user_content_client.get(f"{rel_base}/{rel_id}", params={"visible_until_order": 2}).status_code == 404
    assert user_content_client.delete(f"/api/series/series_dexter/custom-nodes/{node['id']}").status_code == 409
    assert user_content_client.delete(f"{rel_base}/{rel_id}").status_code == 204
    assert user_content_client.delete(f"/api/series/series_dexter/custom-nodes/{node['id']}").status_code == 204
    for payload in (
        {"source_id": "missing", "target_id": "dexter:character:dexter_morgan"},
        {"source_id": "dexter:character:dexter_morgan", "target_id": "missing"},
    ):
        response = user_content_client.post(rel_base, json={**payload, "predicate": "KNOWS", "episode_id": "dexter_s01e01"})
        assert response.status_code == 404
    other = user_content_client.post(f"/api/series/{second_series}/custom-nodes", json={
        "node_type": "Object", "label": "other", "episode_id": f"{second_series}:episode:1"
    }).json()
    response = user_content_client.post(rel_base, json={
        "source_id": other["id"], "target_id": "dexter:character:dexter_morgan",
        "predicate": "KNOWS", "episode_id": "dexter_s01e01"
    })
    assert response.status_code == 404


def test_custom_content_canonical_isolation_and_hidden_missing_equivalence(
    user_content_client: TestClient,
) -> None:
    node_base = "/api/series/series_dexter/custom-nodes"
    canonical = "dexter:character:dexter_morgan"
    assert user_content_client.patch(f"{node_base}/{canonical}", json={"label": "tamper"}).status_code == 409
    assert user_content_client.delete(f"{node_base}/{canonical}").status_code == 409
    rel_base = "/api/series/series_dexter/custom-relationships"
    claim = "dexter:claim:s01e01:dexter_debra_family"
    assert user_content_client.patch(f"{rel_base}/{claim}", json={"predicate": "KNOWS"}).status_code == 409
    assert user_content_client.patch(
        f"{rel_base}/dexter:claim:s01e01:temporary_trust", json={"predicate": "KNOWS"}
    ).status_code == 409
    hidden_relationship = user_content_client.get(
        f"{rel_base}/user-rel:missing", params={"visible_until_order": 2}
    )
    missing_relationship = user_content_client.get(
        f"{rel_base}/user-rel:does-not-exist", params={"visible_until_order": 2}
    )
    assert_hidden_matches_missing(hidden_relationship, missing_relationship)
    _run(database_snapshot(
        "CREATE (:Object {id: 'user-node:missing-visibility', series_id: 'series_dexter', "
        "label: 'hidden metadata', origin: 'user'})"
    ))
    hidden = user_content_client.get(f"{node_base}/user-node:missing", params={"visible_until_order": 2})
    absent = user_content_client.get(f"{node_base}/user-node:does-not-exist", params={"visible_until_order": 2})
    assert_hidden_matches_missing(hidden, absent)
    malformed = user_content_client.get(
        f"{node_base}/user-node:missing-visibility", params={"visible_until_order": 3}
    )
    assert_hidden_matches_missing(malformed, absent)
    for boundary in (0, -1, 4, "bad"):
        assert user_content_client.get(f"{node_base}/user-node:missing", params={"visible_until_order": boundary}).status_code == 422


def test_custom_routes_return_503_when_database_is_unavailable(
    live_client: TestClient, override_database: Callable[[DatabaseOverride], TestClient]
) -> None:
    class Unavailable:
        async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
            from neo4j.exceptions import ServiceUnavailable
            raise ServiceUnavailable("offline")
        async def execute_write(self, work: Any, command: Any) -> Any:
            from neo4j.exceptions import ServiceUnavailable
            raise ServiceUnavailable("offline")
    client = override_database(Unavailable())
    assert client.get("/api/series/series_dexter/custom-nodes/user-node:x", params={"visible_until_order": 1}).status_code == 503
    assert client.get("/api/series/series_dexter/custom-relationships/user-rel:x", params={"visible_until_order": 1}).status_code == 503


@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    _run(_with_database(_seed_and_clean))
    main_module = importlib.import_module("spoilerless.app.main")
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
    main_module = importlib.import_module("spoilerless.app.main")

    def apply(database: DatabaseOverride) -> TestClient:
        main_module.app.dependency_overrides[get_database] = lambda: database
        return live_client

    try:
        yield apply
    finally:
        main_module.app.dependency_overrides.pop(get_database, None)
