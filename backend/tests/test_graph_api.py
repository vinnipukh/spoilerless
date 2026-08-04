from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import secrets
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable
from pydantic import ValidationError

from backend.app.core.errors import install_database_error_handlers
from backend.app.cache import graph_cache
from backend.app.cache.graph_cache import (
    _cache_key,
    get_cached_graph,
    invalidate_series,
    set_cached_graph,
)
from backend.app.core.config import get_settings
from backend.app.domain.graph import GraphResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.graph.seed import setup_database
from backend.app.spoiler.policy import filter_public_metadata


class UnavailableDatabase:
    def __init__(self, _settings=None) -> None:
        pass

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
                "effective_view_order": 1,
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


def test_graph_node_image_fields_are_optional_and_default_null() -> None:
    node = GraphResponse.model_validate(
        {
            "series": {"id": "series_dexter", "title": "Dexter", "slug": "dexter"},
            "visible_until_order": 1,
            "effective_view_order": 1,
            "nodes": [
                {
                    "id": "node:one",
                    "type": "Character",
                    "label": "One",
                    "visible_from_order": 1,
                    "origin": "canonical",
                }
            ],
            "edges": [],
            "claims": [],
            "sources": [],
            "evidence": [],
        }
    ).nodes[0]

    assert node.image_url is None
    assert node.image_source_url is None


def test_graph_node_accepts_explicit_image_fields() -> None:
    node = GraphResponse.model_validate(
        {
            "series": {"id": "series_dexter", "title": "Dexter", "slug": "dexter"},
            "visible_until_order": 1,
            "effective_view_order": 1,
            "nodes": [
                {
                    "id": "node:one",
                    "type": "Character",
                    "label": "One",
                    "visible_from_order": 1,
                    "origin": "canonical",
                    "image_url": "https://static.wikia.nocookie.net/dexter/images/example.jpg",
                    "image_source_url": "https://dexter.fandom.com/wiki/Example",
                }
            ],
            "edges": [],
            "claims": [],
            "sources": [],
            "evidence": [],
        }
    ).nodes[0]

    assert node.image_url == "https://static.wikia.nocookie.net/dexter/images/example.jpg"
    assert node.image_source_url == "https://dexter.fandom.com/wiki/Example"


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
    for response in (missing, malformed):
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_request"
    assert nonpersisted.status_code == 422
    assert nonpersisted.json()["detail"]["code"] == "invalid_visible_until_order"


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


def test_graph_nodes_include_image_fields(live_client: TestClient) -> None:
    response = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=3"
    )
    payload = response.json()

    assert response.status_code == 200, payload
    assert len(payload["nodes"]) > 0
    for node in payload["nodes"]:
        assert "image_url" in node
        assert "image_source_url" in node

    # D-14 curation (07-06): only the 6 order-1 characters carry a curated
    # Fandom portrait; the 3 future characters (Paul vfo 2, Rudy vfo 3,
    # Harry vfo 3) deliberately have no seed portrait, so at boundary 3 they
    # serialize with null image fields. Every other node type stays null.
    characters = [node for node in payload["nodes"] if node["type"] == "Character"]
    assert len(characters) == 9
    portraited_ids = {
        "dexter:character:dexter_morgan",
        "dexter:character:debra_morgan",
        "dexter:character:angel_batista",
        "dexter:character:maria_laguerta",
        "dexter:character:james_doakes",
        "dexter:character:rita_bennett",
    }
    for character in characters:
        if character["id"] in portraited_ids:
            assert character["image_url"], character
            assert character["image_url"].startswith(
                "https://static.wikia.nocookie.net/dexter/"
            )
            assert character["image_source_url"].startswith(
                "https://dexter.fandom.com/wiki/"
            )
        else:
            assert character["image_url"] is None, character
            assert character["image_source_url"] is None, character

    non_characters = [node for node in payload["nodes"] if node["type"] != "Character"]
    assert non_characters
    for node in non_characters:
        assert node["image_url"] is None
        assert node["image_source_url"] is None


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


USER_PROJECTION_FIXTURE_QUERY = """
CREATE (character:Character {id: 'user-node:plan03-character', series_id: 'series_dexter',
  label: 'Visible user character', visible_from_order: 1, origin: 'user'})
CREATE (event:Event {id: 'user-node:plan03-event', series_id: 'series_dexter',
  label: 'Visible user event', visible_from_order: 1, origin: 'user'})
CREATE (location:Location {id: 'user-node:plan03-location', series_id: 'series_dexter',
  label: 'Visible user location', visible_from_order: 1, origin: 'user'})
CREATE (organization:Organization {id: 'user-node:plan03-organization', series_id: 'series_dexter',
  label: 'Visible user organization', visible_from_order: 1, origin: 'user'})
CREATE (object:Object {id: 'user-node:plan03-object', series_id: 'series_dexter',
  label: 'Future user object sentinel', visible_from_order: 3, origin: 'user'})
WITH character, event, location, organization, object
UNWIND [
  {id: 'user-rel:plan03-character', source: character.id, target: event.id, predicate: 'PARTICIPATED_IN', visibility: 1},
  {id: 'user-rel:plan03-event', source: event.id, target: location.id, predicate: 'OCCURRED_INJECTION_BLOCKED', visibility: 1},
  {id: 'user-rel:plan03-location', source: location.id, target: organization.id, predicate: 'KNOWS', visibility: 1},
  {id: 'user-rel:plan03-organization', source: organization.id, target: character.id, predicate: 'HELPS', visibility: 1},
  {id: 'user-rel:plan03-object', source: object.id, target: character.id, predicate: 'MENTIONED', visibility: 3}
] AS row
CREATE (:Claim {id: row.id, series_id: 'series_dexter', subject_id: row.source,
  object_id: row.target, predicate: row.predicate, claim_type: 'user_authored',
  visible_from_order: row.visibility, origin: 'user'})
WITH DISTINCT character, event
CREATE (source:Source {id: 'plan03:user-source', series_id: 'series_dexter', label: 'User source',
  episode_id: 'dexter_s01e01', source_type: 'manual', locator: 'private', retrieved_at: 'now',
  visible_from_order: 1, origin: 'user'})
CREATE (evidence:EvidenceFragment {id: 'plan03:user-evidence', series_id: 'series_dexter',
  label: 'User evidence', episode_id: 'dexter_s01e01', source_id: source.id, text: 'private',
  locator: 'private', content_hash: 'private', visible_from_order: 1, origin: 'user'})
CREATE (rich:Claim {id: 'user-rel:plan03-evidenced', series_id: 'series_dexter',
  subject_id: character.id, object_id: event.id, predicate: 'WITNESSED',
  claim_type: 'user_authored', visible_from_order: 1, origin: 'user'})
CREATE (rich)-[:SUPPORTED_BY {visible_from_order: 1}]->(evidence)
CREATE (rich)-[:REFERS_TO {visible_from_order: 1}]->(source)
CREATE (:Claim {id: 'plan03:canonical-no-evidence', series_id: 'series_dexter',
  subject_id: character.id, object_id: event.id, predicate: 'KNOWS', claim_type: 'explicit_fact',
  visible_from_order: 1, origin: 'canonical'})
CREATE (:Claim {id: 'plan03:candidate-no-evidence', series_id: 'series_dexter',
  subject_id: character.id, object_id: event.id, predicate: 'KNOWS', claim_type: 'explicit_fact',
  visible_from_order: 1, origin: 'candidate'})
CREATE (:Claim {id: 'user-rel:plan03-missing-visibility', series_id: 'series_dexter',
  subject_id: character.id, object_id: event.id, predicate: 'KNOWS',
  claim_type: 'user_authored', origin: 'user'})
"""

USER_PROJECTION_CLEANUP_QUERY = """
MATCH (resource)
WHERE coalesce(resource.id, '') STARTS WITH 'user-node:plan03'
   OR coalesce(resource.id, '') STARTS WITH 'user-rel:plan03'
   OR coalesce(resource.id, '') STARTS WITH 'plan03:'
DETACH DELETE resource
"""


async def _prepare_user_projection_fixture() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(USER_PROJECTION_CLEANUP_QUERY)
        await database.execute_query(USER_PROJECTION_FIXTURE_QUERY)
    finally:
        await database.close()


async def _clean_user_projection_fixture() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(USER_PROJECTION_CLEANUP_QUERY)
    finally:
        await database.close()


def test_user_relationship_projection_is_edge_only_closed_and_fail_closed(
    live_client: TestClient,
) -> None:
    asyncio.run(_prepare_user_projection_fixture())
    try:
        order_one_response = live_client.get(
            "/api/series/series_dexter/graph", params={"visible_until_order": 1}
        )
        order_three_response = live_client.get(
            "/api/series/series_dexter/graph", params={"visible_until_order": 3}
        )
        assert order_one_response.status_code == order_three_response.status_code == 200
        order_one = order_one_response.json()
        order_three = order_three_response.json()

        one_node_ids = {node["id"] for node in order_one["nodes"]}
        three_node_ids = {node["id"] for node in order_three["nodes"]}
        assert {
            "user-node:plan03-character",
            "user-node:plan03-event",
            "user-node:plan03-location",
            "user-node:plan03-organization",
        } <= one_node_ids
        assert "user-node:plan03-object" not in one_node_ids
        assert "user-node:plan03-object" in three_node_ids

        one_edges = [edge for edge in order_one["edges"] if edge["id"].startswith("user-rel:plan03")]
        three_edges = [edge for edge in order_three["edges"] if edge["id"].startswith("user-rel:plan03")]
        assert {edge["id"] for edge in one_edges} == {
            "user-rel:plan03-character",
            "user-rel:plan03-location",
            "user-rel:plan03-organization",
            "user-rel:plan03-evidenced",
        }
        assert sum(edge["id"] == "user-rel:plan03-evidenced" for edge in three_edges) == 1
        assert "user-rel:plan03-object" not in {edge["id"] for edge in one_edges}
        assert "user-rel:plan03-object" in {edge["id"] for edge in three_edges}
        assert "user-rel:plan03-missing-visibility" not in {edge["id"] for edge in three_edges}

        serialized_one = json.dumps(order_one, sort_keys=True)
        assert "Future user object sentinel" not in serialized_one
        assert "OCCURRED_INJECTION_BLOCKED" not in serialized_one
        assert all(edge["source"] in one_node_ids and edge["target"] in one_node_ids for edge in one_edges)

        non_edge_ids = {
            row["id"]
            for collection in ("claims", "sources", "evidence")
            for row in order_three[collection]
        }
        assert {
            "user-rel:plan03-evidenced",
            "plan03:user-source",
            "plan03:user-evidence",
            "plan03:canonical-no-evidence",
            "plan03:candidate-no-evidence",
        }.isdisjoint(non_edge_ids)
    finally:
        asyncio.run(_clean_user_projection_fixture())


# ===================================================================
# D-05 fail-closed boundary: a request above the persisted view never
# raises the effective boundary (07-02 Task 3)
# ===================================================================

ABOVE_VIEW_USER_ID = "user:07-02-above-view"
ABOVE_VIEW_SUB = "07-02-above-view-sub"

ABOVE_VIEW_CLEANUP_QUERY = """
MATCH (s:Session {token_hash: $token_hash})
DETACH DELETE s
"""

ABOVE_VIEW_USER_CLEANUP_QUERY = """
MATCH (u:AppUser {id: $uid})
DETACH DELETE u
"""

ABOVE_VIEW_SETUP_QUERY = """
MERGE (u:AppUser {id: $uid})
SET u.google_sub = $sub, u.email = $email, u.display_name = 'Above View Test'
MERGE (s:Series {id: 'series_dexter'})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $uid, series_id: 'series_dexter'})
SET p.id = $pid, p.created_at = $now, p.updated_at = $now,
    p.watched_through_order = 3, p.view_as_of_order = 1, p.visible_until_order = 1
WITH u
CREATE (sess:Session {
    id: $session_id,
    token_hash: $token_hash,
    created_at: $now,
    expires_at: $now + $ttl,
    last_seen_at: $now,
    revoked_at: NULL
})
CREATE (u)-[:HAS_SESSION]->(sess)
"""


async def _prepare_above_view_fixture() -> str:
    """Create a user with watched=3 / view=1 progress plus a live session.

    Returns the raw session token (hash of which is stored on the Session node,
    mirroring Neo4jSessionRepository.create). A fresh random token is used per
    run so the Session token_hash uniqueness constraint can never collide with
    a leftover node from an interrupted run.
    """
    raw = f"07-02-above-view-{secrets.token_hex(8)}"
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(ABOVE_VIEW_USER_CLEANUP_QUERY, uid=ABOVE_VIEW_USER_ID)
        await database.execute_query(
            ABOVE_VIEW_SETUP_QUERY,
            uid=ABOVE_VIEW_USER_ID,
            sub=ABOVE_VIEW_SUB,
            email="above-view@test.local",
            pid=f"progress:{ABOVE_VIEW_USER_ID}",
            session_id=f"session:{ABOVE_VIEW_USER_ID}:test",
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            now=time.time(),
            ttl=float(3600),
        )
    finally:
        await database.close()
    return raw


async def _clean_above_view_fixture(raw_token: str) -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(
            ABOVE_VIEW_CLEANUP_QUERY,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        )
        await database.execute_query(
            "MATCH (p:UserSeriesProgress {user_id: $uid}) DETACH DELETE p",
            uid=ABOVE_VIEW_USER_ID,
        )
        await database.execute_query(
            ABOVE_VIEW_USER_CLEANUP_QUERY, uid=ABOVE_VIEW_USER_ID
        )
    finally:
        await database.close()


def test_graph_request_above_persisted_view_is_fail_closed(live_client: TestClient) -> None:
    """D-05: view=1, watched=3, request=3 -> effective 1, never 3 (07-02)."""
    raw = asyncio.run(_prepare_above_view_fixture())
    try:
        # Authenticated: the request above the selected view is clamped to it.
        response = live_client.get(
            "/api/series/series_dexter/graph",
            params={"visible_until_order": 3},
            headers={"Cookie": f"session={raw}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["effective_view_order"] == 1
        assert payload["visible_until_order"] == 1
        node_ids = {node["id"] for node in payload["nodes"]}
        # Paul Bennett is visible_from_order 2 — must NOT appear at effective 1.
        assert "dexter:character:paul_bennett" not in node_ids

        # Anonymous caller keeps the backward-compatible behavior (no persisted
        # record to clamp against): request 3 resolves to effective 3.
        anon = live_client.get(
            "/api/series/series_dexter/graph",
            params={"visible_until_order": 3},
        )
        assert anon.status_code == 200
        anon_payload = anon.json()
        assert anon_payload["effective_view_order"] == 3
        anon_ids = {node["id"] for node in anon_payload["nodes"]}
        assert "dexter:character:paul_bennett" in anon_ids
    finally:
        asyncio.run(_clean_above_view_fixture(raw))


def test_boundary_one_responses_carry_no_future_signals(live_client: TestClient) -> None:
    """07-05 SEARCH-02/D-16 sweep: serialized boundary-1 responses contain no
    hidden-count, future-title, last-appearance, or life-status signal at the
    key level — absence is contractual, not just unrendered."""
    graph = live_client.get("/api/series/series_dexter/graph?visible_until_order=1")
    assert graph.status_code == 200
    graph_payload = graph.json()
    graph_text = json.dumps(graph_payload).lower()
    for forbidden in ("last_appearance", "total", "dead", "alive", "spoiler", "hidden_count"):
        assert forbidden not in graph_text, forbidden

    episodes = live_client.get("/api/series/series_dexter/episodes?visible_until_order=1")
    assert episodes.status_code == 200
    for episode in episodes.json():
        if episode["episode_order"] > 1:
            # Masked display_title per D-08 generic label; never the raw title.
            expected = (
                f"S{episode['season_number']:02d}E{episode['episode_number']:02d}"
                f" — Episode {episode['episode_number']}"
            )
            assert episode["display_title"] == expected, episode
            assert episode["is_unlocked"] is False
    episodes_text = json.dumps(episodes.json()).lower()
    assert "last_appearance" not in episodes_text


# ===================================================================
# D-14 / MEDIA-01 media safety — image fields above the effective
# boundary are dropped before serialization (07-06 Task 1)
# ===================================================================

def test_filter_public_metadata_drops_image_fields_above_boundary() -> None:
    """D-14/MEDIA-01: filter_public_metadata drops image_url/image_source_url
    for a record above the effective boundary and preserves them at/below it.

    fetch_graph passes every node row through this projection
    (defense-in-depth on top of the boundary-filtered NODES_QUERY), so this
    unit test is the deterministic proof that an above-boundary portrait can
    never serialize — even if the DB row carries it.
    """
    record = {
        "id": "dexter:character:paul_bennett",
        "label": "Paul Bennett",
        "visible_from_order": 2,
        "origin": "canonical",
        "image_url": (
            "https://static.wikia.nocookie.net/dexter/images/8/80/"
            "Paul_Bennett_7.PNG/revision/latest?cb=20190309143221"
        ),
        "image_source_url": "https://dexter.fandom.com/wiki/Paul_Bennett",
    }

    hidden = filter_public_metadata(record, effective_view_order=1)
    assert "image_url" not in hidden
    assert "image_source_url" not in hidden
    # Only spoiler-sensitive media fields are dropped — the safe label stays.
    assert hidden["label"] == "Paul Bennett"
    assert hidden["id"] == record["id"]

    revealed = filter_public_metadata(record, effective_view_order=2)
    assert revealed["image_url"] == record["image_url"]
    assert revealed["image_source_url"] == record["image_source_url"]


def test_graph_hidden_character_image_urls_never_serialized(
    live_client: TestClient,
) -> None:
    """D-14/MEDIA-01: a hidden character's image URL or filename never appears
    anywhere in the serialized graph response — not as a field value, not as
    text. Hidden nodes are absent by query; revealed nodes keep their portrait.
    """
    # Boundary 1: Paul (vfo 2), Rudy (vfo 3) and Harry (vfo 3) are all hidden —
    # none of their image filenames/URLs may appear anywhere in the payload.
    one = live_client.get("/api/series/series_dexter/graph?visible_until_order=1")
    assert one.status_code == 200
    one_text = json.dumps(one.json(), sort_keys=True)
    for hidden_fragment in ("Paul_Bennett_7.PNG", "Brianmoser1.png", "HarryFace.jpg"):
        assert hidden_fragment not in one_text, hidden_fragment

    # Boundary 2: Paul is revealed. Per D-14 curation (07-06) Paul, Rudy and
    # Harry carry NO seed portrait (future characters), so their serialized
    # image fields must be null — the fragment may never appear at any
    # boundary. Only the order-1 characters' portraits exist.
    two = live_client.get("/api/series/series_dexter/graph?visible_until_order=2")
    assert two.status_code == 200
    two_payload = two.json()
    for hidden_fragment in ("Paul_Bennett_7.PNG", "Brianmoser1.png", "HarryFace.jpg"):
        assert hidden_fragment not in json.dumps(two_payload, sort_keys=True), hidden_fragment
    paul = next(
        node
        for node in two_payload["nodes"]
        if node["id"] == "dexter:character:paul_bennett"
    )
    assert paul["image_url"] is None
    assert paul["image_source_url"] is None
    # The order-1 revealed characters keep their portraits.
    two_text = json.dumps(two_payload, sort_keys=True)
    assert "Dexter_Morgan" in two_text or "Season_7_Photo_Promo" in two_text

    # Boundary 3: everything is revealed — Harry's serialized image fields
    # are still null (no future-character portraits in seed, D-14).
    three = live_client.get("/api/series/series_dexter/graph?visible_until_order=3")
    assert three.status_code == 200
    three_payload = three.json()
    harry = next(
        node
        for node in three_payload["nodes"]
        if node["id"] == "dexter:character:harry_morgan"
    )
    assert harry["image_url"] is None
    assert harry["image_source_url"] is None


# ===================================================================
# D-14 seed curation rule — no above-order-1 resource pre-links a
# future portrait in seed data (07-06 Task 3)
# ===================================================================

class TestSeedImageCuration:
    """D-14/D-16: seed data must never pre-link a future character's portrait.

    Curation rule: any seeded resource whose visible_from_order > 1 must have
    image_url null in the seed data — a future character's image must not be
    inferable from seed presence. The rule is enforced here (the plan's
    regression lock) so a future seed edit cannot silently re-add a portrait
    for an unrevealed character.
    """

    def test_no_seed_image_for_resources_visible_above_order_one(self) -> None:
        seed_path = (
            Path(__file__).resolve().parents[2]
            / "data" / "dexter" / "seed" / "characters.json"
        )
        with seed_path.open("r", encoding="utf-8") as stream:
            characters = json.load(stream)
        assert characters, "seed characters.json must not be empty"

        above_order_one = [
            character for character in characters if character["visible_from_order"] > 1
        ]
        assert above_order_one, "expected at least one above-order-1 character"

        for character in above_order_one:
            assert character.get("image_url") is None, (
                f"{character['id']} is visible from order "
                f"{character['visible_from_order']} but carries image_url"
            )
            assert character.get("image_source_url") is None, (
                f"{character['id']} is visible from order "
                f"{character['visible_from_order']} but carries image_source_url"
            )

        # Sanity: order-1 characters may carry curated portraits (D-14 keeps
        # the existing safe images for already-revealed characters).
        order_one = [character for character in characters if character["visible_from_order"] == 1]
        assert order_one
        assert any(character.get("image_url") for character in order_one)


# ===================================================================
# INFRA-02 — cache-aside layer in front of GET /api/series/{id}/graph
# (08-06). No live Redis: graph_cache's get_redis is pointed at an
# in-memory _FakeRedis (no-op pattern) or left disabled (empty
# redis_url) — the endpoint must behave identically either way.
# ===================================================================


class _FakeRedis:
    """In-memory stand-in for the shared ``redis.asyncio`` client.

    Mirrors the real client's byte values (decode_responses=False) and
    only the surface graph_cache uses: get / setex / scan_iter / delete.
    """

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    async def setex(self, key: str, _ttl: int, value: str | bytes) -> None:
        self._store[key] = value.encode() if isinstance(value, str) else value

    async def scan_iter(self, match: str | None = None):
        prefix = match.split("*", 1)[0] if match else ""
        for key in list(self._store):
            if key.startswith(prefix):
                yield key

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)


async def _async_noop() -> None:
    return None


def _enable_cache(monkeypatch: pytest.MonkeyPatch, fake: _FakeRedis) -> None:
    """Point graph_cache at a fake Redis and enable the cache guard."""
    monkeypatch.setattr(get_settings(), "redis_url", "rediss://fake:6379")
    monkeypatch.setattr(graph_cache, "get_redis", lambda: fake)


@pytest.fixture
def cached_live_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _FakeRedis]]:
    """live_client with the cache-aside path enabled against a fake Redis.

    A non-empty redis_url would make main's lifespan call
    init_rate_limiter() and open a real Upstash connection, so that startup
    hook is neutralized too — the graph endpoint's cache helpers are what
    these tests exercise, not the rate limiter.
    """
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)
    main_module = importlib.import_module("backend.app.main")
    monkeypatch.setattr(main_module, "init_rate_limiter", _async_noop)
    asyncio.run(_seed_live_database())
    with TestClient(main_module.app) as client:
        yield client, fake


async def test_get_cached_graph_miss_then_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    assert await get_cached_graph("series_dexter", 1, None) is None

    await set_cached_graph("series_dexter", 1, None, {"nodes": []})
    assert await get_cached_graph("series_dexter", 1, None) == {"nodes": []}


async def test_cache_key_separates_series_boundary_and_user() -> None:
    assert _cache_key("series_dexter", 1, None) == "graph:series_dexter:1:anon"
    assert _cache_key("series_dexter", 1, "user:1") == "graph:series_dexter:1:user:1"
    assert _cache_key("series_dexter", 1, None) != _cache_key("series_dexter", 2, None)
    assert _cache_key("series_dexter", 1, "user:1") != _cache_key("series_dexter", 1, None)
    assert _cache_key("series_dexter", 1, "user:1") != _cache_key("series_other", 1, "user:1")


async def test_cache_helpers_are_noops_when_redis_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "redis_url", "")
    calls: list[object] = []
    monkeypatch.setattr(
        graph_cache, "get_redis", lambda: calls.append(object()) or _FakeRedis()
    )

    assert await get_cached_graph("series_dexter", 1, None) is None
    await set_cached_graph("series_dexter", 1, None, {"nodes": []})
    await invalidate_series("series_dexter")

    assert calls == []


def test_graph_endpoint_cache_hit_matches_miss_byte_for_byte(
    cached_live_client: tuple[TestClient, _FakeRedis],
) -> None:
    client, fake = cached_live_client

    miss = client.get("/api/series/series_dexter/graph?visible_until_order=1")
    hit = client.get("/api/series/series_dexter/graph?visible_until_order=1")

    assert miss.status_code == hit.status_code == 200
    assert miss.json() == hit.json()
    assert json.dumps(miss.json(), sort_keys=True) == json.dumps(hit.json(), sort_keys=True)
    assert any(key.startswith("graph:series_dexter:1:anon") for key in fake._store)
