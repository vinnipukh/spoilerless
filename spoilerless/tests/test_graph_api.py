from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import secrets
import time
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable
from pydantic import ValidationError

from spoilerless.app.api.deps import get_optional_current_user
from spoilerless.app.api.exceptions import install_repository_error_handlers
from spoilerless.app.api.graph import (
    get_graph_service,
    get_progress_service,
    router as graph_router,
)
from spoilerless.app.cache import graph_cache
from spoilerless.app.cache.graph_cache import (
    _cache_key,
    get_cached_graph,
    invalidate_series,
    set_cached_graph,
)
from spoilerless.app.core.config import get_settings
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.domain.graph import GraphResponse
from spoilerless.app.domain.visualization import PROJECTION_VERSION, VisualizationDTO
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.spoiler.policy import filter_public_metadata


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


@pytest.fixture
def cached_live_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _FakeRedis]]:
    """Graph-route client with the cache-aside path enabled against a fake
    Redis (no live Neo4j).

    The graph router runs against ``_FakeGraphService`` serving the
    checked-in safe fixture, and graph_cache's get_redis is pointed at an
    in-memory ``_FakeRedis``. This keeps the INFRA-02 endpoint-level cache
    contract (hit byte-identical to miss) deterministic and offline.
    """
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)
    with TestClient(_stub_graph_app()) as client:
        yield client, fake


def test_error_responses() -> None:
    app = FastAPI()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise ServiceUnavailable("bolt://secret-user:secret-pass@database:7687 MATCH (n)")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "DATABASE_UNAVAILABLE",
            "message": "The graph database is unavailable.",
        }
    }
    assert "secret" not in response.text
    assert "MATCH" not in response.text


def test_app_starts_degraded_and_docs_remain_available(monkeypatch) -> None:
    main_module = importlib.import_module("spoilerless.app.main")
    monkeypatch.setattr(main_module, "Neo4jDatabase", UnavailableDatabase)

    with TestClient(main_module.app) as client:
        health = client.get("/health")
        docs = client.get("/docs")

    assert health.status_code == 503
    assert health.json() == {
        "status": "degraded",
        "database": "unavailable",
        "service": "spoilerless-backend",
    }
    assert docs.status_code == 200


def test_security_headers_on_every_response(monkeypatch) -> None:
    """PROB-17/#38: every response carries the five baseline security headers."""
    main_module = importlib.import_module("spoilerless.app.main")
    monkeypatch.setattr(main_module, "Neo4jDatabase", UnavailableDatabase)

    with TestClient(main_module.app) as client:
        for path in ("/health", "/docs", "/api/series/unknown/graph?visible_until_order=1"):
            response = client.get(path)
            headers = response.headers
            assert headers.get("Content-Security-Policy", "").startswith("default-src 'self'")
            assert headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
            assert headers.get("X-Content-Type-Options") == "nosniff"
            assert headers.get("X-Frame-Options") == "DENY"
            assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_cors_preflight_is_explicit_no_wildcard_with_credentials(monkeypatch) -> None:
    """PROB-17/#38: preflight for an allowed origin lists explicit methods/headers.

    No wildcard may be combined with allow_credentials=True.
    """
    main_module = importlib.import_module("spoilerless.app.main")
    monkeypatch.setattr(main_module, "Neo4jDatabase", UnavailableDatabase)

    with TestClient(main_module.app) as client:
        response = client.options(
            "/api/series/series_dexter/graph",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    allow_headers = response.headers.get("access-control-allow-headers", "")
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
        assert method in allow_methods, f"expected {method} in {allow_methods}"
    assert "*" not in allow_methods
    for header in (
        "Content-Type",
        "Authorization",
        "X-LLM-Api-Key",
        "X-LLM-Provider",
        "X-LLM-Base-URL",
        "X-LLM-Model",
    ):
        assert header.lower() in allow_headers.lower(), f"expected {header} in {allow_headers}"
    assert "*" not in allow_headers


def test_google_client_id_equality_check_fires_only_when_both_set(monkeypatch) -> None:
    """PROB-30/#55: the equality gate raises ONLY when both ids are set and differ.

    Uses a fresh Settings instance — get_settings() is lru_cached and must
    not leak state between tests.
    """
    from spoilerless.app.core.config import Settings, verify_google_client_id_equality

    # Both set and equal -> no raise.
    monkeypatch.setenv("VITE_GOOGLE_CLIENT_ID", "same-client-id")
    verify_google_client_id_equality(Settings(google_client_id="same-client-id"))

    # Both set and different -> RuntimeError (the #42 audience-mismatch class).
    monkeypatch.setenv("VITE_GOOGLE_CLIENT_ID", "other-client-id")
    with pytest.raises(RuntimeError, match="mismatch"):
        verify_google_client_id_equality(Settings(google_client_id="same-client-id"))

    # Only the backend id set -> no raise (local runs without the frontend id).
    monkeypatch.delenv("VITE_GOOGLE_CLIENT_ID")
    verify_google_client_id_equality(Settings(google_client_id="same-client-id"))

    # Only the frontend id set -> no raise.
    monkeypatch.setenv("VITE_GOOGLE_CLIENT_ID", "frontend-only-id")
    verify_google_client_id_equality(Settings(google_client_id=""))


def test_database_module_has_no_driver_singleton(monkeypatch) -> None:
    import spoilerless.app.graph.database as database_module

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
    # PROB-04/#12: an ANONYMOUS order-4 probe is clamped to boundary 1 (200),
    # never a probe failure — so the non-persisted 422 must be exercised with
    # an authenticated session (requested order is honored for logged-in users).
    anon_nonpersisted = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=4"
    )
    raw = asyncio.run(_prepare_boundary_session(3))
    try:
        nonpersisted = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=4",
            headers=_boundary_headers(raw),
        )
    finally:
        asyncio.run(_clean_boundary_session(3))

    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "SERIES_NOT_FOUND"
    for response in (missing, malformed):
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"
    # Anonymous clamp: boundary 4 request yields boundary-1 content (200).
    assert anon_nonpersisted.status_code == 200
    assert anon_nonpersisted.json()["effective_view_order"] == 1
    # After 11-01, authenticated 4 with progress 3 clamps to 3 and succeeds (200) —
    # the request is clamped via effective_view_order, not rejected.
    assert nonpersisted.status_code == 200
    assert nonpersisted.json()["effective_view_order"] == 3


def test_graph_database_unavailable_is_sanitized(live_client: TestClient) -> None:
    main_module = importlib.import_module("spoilerless.app.main")
    main_module.app.dependency_overrides[get_database] = lambda: UnavailableDatabase()
    try:
        response = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=1"
        )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATABASE_UNAVAILABLE"
    assert "secret" not in response.text
    assert "MATCH" not in response.text


# Exact per-boundary magnitudes are no longer pinned: the S01E01 graph is
# source-enriched and grows over time. The invariants that matter are (a) no
# future-episode content leaks at a lower boundary (spoiler gate), (b) the
# boundary's own episode content is present, and (c) every edge endpoint is a
# visible node. Harry Morgan is intentionally visible from order 1 (the Buddy
# flashback) and is therefore no longer forbidden at boundary 2.
@pytest.mark.parametrize(
    ("boundary", "forbidden", "present"),
    [
        (
            1,
            ["dexter_s01e02", "S01E02", "Crocodile", "Paul Bennett", "Rudy Cooper", "ice rink"],
            ["dexter_s01e01", "Dexter Morgan", "Mike Donovan"],
        ),
        (
            2,
            ["dexter_s01e03", "S01E03", "Popping Cherry", "Rudy Cooper", "ice rink"],
            ["dexter_s01e02", "Crocodile"],
        ),
        (3, [], ["dexter_s01e03", "Popping Cherry"]),
    ],
)
def test_graph_boundaries_have_full_json_sentinels(
    live_client: TestClient,
    boundary: int,
    forbidden: list[str],
    present: list[str],
) -> None:
    # PROB-04/#12 clamps ANONYMOUS readers to boundary 1, so boundaries 2/3
    # are probed with an authenticated session whose persisted progress
    # matches the requested boundary.
    headers: dict[str, str] = {}
    if boundary > 1:
        raw = asyncio.run(_prepare_boundary_session(boundary))
        headers = _boundary_headers(raw)
    try:
        response = live_client.get(
            f"/api/series/series_dexter/graph?visible_until_order={boundary}",
            headers=headers,
        )
    finally:
        if boundary > 1:
            asyncio.run(_clean_boundary_session(boundary))
    payload = response.json()
    serialized = json.dumps(payload, sort_keys=True)

    assert response.status_code == 200, payload
    assert payload["visible_until_order"] == boundary
    for collection in ("nodes", "edges", "claims", "sources", "evidence"):
        assert len(payload[collection]) > 0, collection
    for sentinel in forbidden:
        assert sentinel.lower() not in serialized.lower(), f"leaked: {sentinel}"
    for sentinel in present:
        assert sentinel.lower() in serialized.lower(), f"missing: {sentinel}"
    node_ids = {node["id"] for node in payload["nodes"]}
    assert all(
        edge["source"] in node_ids and edge["target"] in node_ids
        for edge in payload["edges"]
    )


def test_graph_counts_grow_monotonically_across_boundaries(
    live_client: TestClient,
) -> None:
    previous = 0
    for boundary in (1, 2, 3):
        payload = live_client.get(
            f"/api/series/series_dexter/graph?visible_until_order={boundary}"
        ).json()
        count = len(payload["nodes"])
        assert count >= previous, (boundary, count, previous)
        previous = count


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

    # Source-enrichment characters (minor cast, victims, the unidentified
    # killer) intentionally carry no image — the unknown killer must never
    # receive an identity-revealing portrait. Since the #28 hotlink sweep the
    # seed carries NO images at all (see below).
    characters = [node for node in payload["nodes"] if node["type"] == "Character"]
    # The curated portraits were dropped wholesale in the #28 hotlink sweep
    # (commit 1ddc650) and restored self-hosted on 08-12: seed data must not
    # load third-party CDN assets on a public site (legal + privacy +
    # breakage), so image_url may only be a SELF-HOSTED relative path under
    # /api/static (served by this backend; passes CSP img-src 'self') — never
    # an external CDN (static.wikia.nocookie.net / fandom) or any absolute
    # http(s) URL.
    for character in characters:
        assert character["image_url"] is None or character["image_url"].startswith("/api/static/"), (
            f"{character['id']} carries image_url {character['image_url']!r} — "
            "external hotlinks were removed (PROBLEMS #28); only self-hosted "
            "images under /api/static are allowed"
        )

    non_characters = [node for node in payload["nodes"] if node["type"] != "Character"]
    assert non_characters
    for node in non_characters:
        assert node["image_url"] is None
        assert node["image_source_url"] is None


def test_claim_validity_is_independent_of_visibility(live_client: TestClient) -> None:
    order_one = live_client.get(
        "/api/series/series_dexter/graph?visible_until_order=1"
    ).json()
    # PROB-04/#12: boundary 2 is probed with an authenticated session whose
    # persisted progress matches (anonymous readers are clamped to boundary 1).
    raw = asyncio.run(_prepare_boundary_session(2))
    try:
        order_two = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=2",
            headers=_boundary_headers(raw),
        ).json()
    finally:
        asyncio.run(_clean_boundary_session(2))
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
    # PROB-04/#12: boundary 3 is probed with an authenticated session whose
    # persisted progress matches (anonymous readers are clamped to boundary 1).
    raw = asyncio.run(_prepare_boundary_session(3))
    try:
        order_one_response = live_client.get(
            "/api/series/series_dexter/graph", params={"visible_until_order": 1}
        )
        order_three_response = live_client.get(
            "/api/series/series_dexter/graph",
            params={"visible_until_order": 3},
            headers=_boundary_headers(raw),
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
        asyncio.run(_clean_boundary_session(3))
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

BOUNDARY_SESSION_SETUP_QUERY = """
MERGE (u:AppUser {id: $uid})
SET u.google_sub = $sub, u.email = $email, u.display_name = 'Boundary Test'
MERGE (s:Series {id: 'series_dexter'})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $uid, series_id: 'series_dexter'})
SET p.id = $pid, p.created_at = $now, p.updated_at = $now,
    p.watched_through_order = $watched, p.view_as_of_order = $watched,
    p.visible_until_order = $watched
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

BOUNDARY_SESSION_CLEANUP_QUERY = """
MATCH (u:AppUser {id: $uid})
OPTIONAL MATCH (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress)
OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session)
DETACH DELETE u, p, s
"""


async def _prepare_boundary_session(watched_through: int) -> str:
    """Create a user whose persisted progress is watched=view=*watched_through*
    plus a live session; returns the raw session token.

    PROB-04/#12 clamps ANONYMOUS readers to boundary 1, so tests that probe
    boundary 2/3 must authenticate with a matching progress record — mirroring
    the ABOVE_VIEW fixture (fresh random token so the Session token_hash
    uniqueness constraint can never collide with a leftover node).
    """
    raw = f"09-04-boundary-{secrets.token_hex(8)}"
    uid = f"user:09-04-boundary-{watched_through}"
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(
            BOUNDARY_SESSION_CLEANUP_QUERY, uid=uid
        )
        await database.execute_query(
            BOUNDARY_SESSION_SETUP_QUERY,
            uid=uid,
            sub=f"09-04-boundary-sub-{watched_through}",
            email=f"boundary-{watched_through}@test.local",
            pid=f"progress:{uid}",
            session_id=f"session:{uid}:test",
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            now=time.time(),
            ttl=float(3600),
            watched=watched_through,
        )
    finally:
        await database.close()
    return raw


async def _clean_boundary_session(watched_through: int) -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(
            BOUNDARY_SESSION_CLEANUP_QUERY,
            uid=f"user:09-04-boundary-{watched_through}",
        )
    finally:
        await database.close()


def _boundary_headers(raw_token: str) -> dict[str, str]:
    return {"Cookie": f"session={raw_token}"}


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

        # Anonymous caller gets the FIXED boundary 1 (PROB-04/#12) — the
        # client-chosen request must never widen the spoiler window without
        # a session: request 3 resolves to effective 1.
        anon = live_client.get(
            "/api/series/series_dexter/graph",
            params={"visible_until_order": 3},
        )
        assert anon.status_code == 200
        anon_payload = anon.json()
        assert anon_payload["effective_view_order"] == 1
        assert anon_payload["visible_until_order"] == 1
        anon_ids = {node["id"] for node in anon_payload["nodes"]}
        assert "dexter:character:paul_bennett" not in anon_ids
    finally:
        asyncio.run(_clean_above_view_fixture(raw))


def test_anonymous_graph_boundary_is_fixed_at_one(live_client: TestClient) -> None:
    """PROB-04/#12: an anonymous reader can never request an arbitrary
    client-chosen boundary — the effective boundary is fixed at order 1 and
    the cache key flows it, so anonymous cache entries are boundary-1 only.

    A client-chosen ``visible_until_order`` above boundary 1 must yield
    boundary-1 content (server-enforced), never above-boundary nodes.
    """
    for requested in (2, 3, 999):
        response = live_client.get(
            "/api/series/series_dexter/graph",
            params={"visible_until_order": requested},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["effective_view_order"] == 1, requested
        assert payload["visible_until_order"] == 1, requested
        node_ids = {node["id"] for node in payload["nodes"]}
        # Paul Bennett is visible_from_order 2 — must never appear anonymously.
        assert "dexter:character:paul_bennett" not in node_ids, requested


def test_anonymous_episode_list_boundary_is_fixed_at_one(
    live_client: TestClient,
) -> None:
    """PROB-04/#12: the anonymous episode listing is boundary-1-enforced —
    an above-boundary request returns the same masked list as boundary 1."""
    baseline = live_client.get("/api/series/series_dexter/episodes?visible_until_order=1")
    assert baseline.status_code == 200

    widened = live_client.get(
        "/api/series/series_dexter/episodes?visible_until_order=999"
    )
    assert widened.status_code == 200
    assert widened.json() == baseline.json()
    for episode in widened.json():
        if episode["episode_order"] > 1:
            assert episode["is_unlocked"] is False


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

    # PROB-04/#12: boundaries 2/3 are probed with an authenticated session
    # whose persisted progress matches (anonymous readers are clamped to 1).
    raw = asyncio.run(_prepare_boundary_session(3))
    try:
        two = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=2",
            headers=_boundary_headers(raw),
        )
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
        three = live_client.get(
            "/api/series/series_dexter/graph?visible_until_order=3",
            headers=_boundary_headers(raw),
        )
        assert three.status_code == 200
        three_payload = three.json()
        harry = next(
            node
            for node in three_payload["nodes"]
            if node["id"] == "dexter:character:harry_morgan"
        )
        assert harry["image_url"] is None
        assert harry["image_source_url"] is None
    finally:
        asyncio.run(_clean_boundary_session(3))


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
        # the existing safe images for already-revealed characters). Since the
        # #28 hotlink sweep (commit 1ddc650) the seed carries none — external
        # CDN hotlinks were removed; any future portrait must be self-hosted.
        order_one = [character for character in characters if character["visible_from_order"] == 1]
        assert order_one
        for character in order_one:
            image_url = character.get("image_url")
            if image_url is not None:
                assert not image_url.startswith(("http://", "https://")), (
                    f"{character['id']} order-1 portrait {image_url!r} hotlinks "
                    "an external host — self-host images only (PROBLEMS #28)"
                )


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

    async def incr(self, key: str) -> int:
        raw = self._store.get(key)
        value = int(raw) if raw is not None else 0
        value += 1
        self._store[key] = str(value).encode()
        return value


async def _async_noop() -> None:
    return None


def _enable_cache(monkeypatch: pytest.MonkeyPatch, fake: _FakeRedis) -> None:
    """Point graph_cache at a fake Redis and enable the cache guard."""
    monkeypatch.setattr(get_settings(), "redis_url", "rediss://fake:6379")
    monkeypatch.setattr(graph_cache, "get_redis", lambda: fake)


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


# ===================================================================
# 10-03 (D-29) — typed visualization projection route. No live Neo4j:
# the graph router runs against _FakeGraphService serving the checked-in
# safe fixtures, so boundary/focus/cache semantics are exercised with
# deterministic data. The stub filters rows by the requested boundary the
# same way the real NODES/EDGES/CLAIMS queries do.
# ===================================================================

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visualization"

VISUALIZATION_VIEWS = (
    "episode_overview",
    "character_network",
    "plot_threads",
    "investigation",
    "full",
    "graphrag_focus",
)


class _FakeGraphService:
    """GraphService stand-in serving a checked-in safe fixture (no Neo4j)."""

    def __init__(self, fixture_name: str = "s01e01_safe.json") -> None:
        with (FIXTURES_DIR / fixture_name).open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)
        self._graph = GraphResponse.model_validate(fixture["graph"])
        self._max_episode_order = max(
            (
                node.visible_from_order
                for node in self._graph.nodes
                if node.type == "Episode"
            ),
            default=0,
        )

    async def get_series_meta(self, series_id: str) -> dict[str, Any] | None:
        if series_id != self._graph.series.id:
            return None
        return self._graph.series.model_dump()

    async def resolve_boundary(self, series_id: str, visible_until_order: int):
        if series_id != self._graph.series.id:
            return None
        if 1 <= visible_until_order <= self._max_episode_order:
            return {"id": f"{series_id}:episode:{visible_until_order}"}
        return None

    async def fetch_graph(
        self,
        series_id: str,
        visible_until_order: int,
        node_labels: list[str],
        user_relationship_types: list[str],
        effective_view_order: int | None = None,
    ) -> GraphResponse:
        """Return the fixture graph filtered to the requested boundary —
        the same row semantics the real NODES/EDGES/CLAIMS queries apply."""
        effective = (
            effective_view_order if effective_view_order is not None else visible_until_order
        )
        node_ids = {
            node.id
            for node in self._graph.nodes
            if node.visible_from_order <= effective and node.type in node_labels
        }
        nodes = [
            node
            for node in self._graph.nodes
            if node.visible_from_order <= effective and node.type in node_labels
        ]
        edges = [
            edge
            for edge in self._graph.edges
            if edge.visible_from_order <= effective
            and edge.source in node_ids
            and edge.target in node_ids
        ]
        claims = [
            claim
            for claim in self._graph.claims
            if claim.visible_from_order <= effective
        ]
        sources = [
            source
            for source in self._graph.sources
            if source.visible_from_order <= effective
        ]
        evidence = [
            item
            for item in self._graph.evidence
            if item.visible_from_order <= effective
        ]
        return GraphResponse(
            series=self._graph.series,
            visible_until_order=visible_until_order,
            effective_view_order=effective,
            nodes=nodes,
            edges=edges,
            claims=claims,
            sources=sources,
            evidence=evidence,
        )


class _FakeProgressService:
    def __init__(self, record: Any = None) -> None:
        self._record = record

    async def get(self, user_id: str, series_id: str):
        return self._record


class _ProgressRecord:
    def __init__(self, view_as_of_order: int, watched_through_order: int) -> None:
        self.view_as_of_order = view_as_of_order
        self.watched_through_order = watched_through_order


def _stub_graph_app(
    *,
    user: dict[str, Any] | None = None,
    progress: Any = None,
    fixture_name: str = "s01e01_safe.json",
) -> FastAPI:
    """Main-app-shaped FastAPI with the graph router over stub services."""
    app = FastAPI()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.include_router(graph_router)
    app.dependency_overrides[get_optional_current_user] = lambda: user
    app.dependency_overrides[get_graph_service] = lambda: _FakeGraphService(fixture_name)
    app.dependency_overrides[get_progress_service] = lambda: _FakeProgressService(progress)
    return app


def _viz_client(
    *,
    user: dict[str, Any] | None = None,
    progress: Any = None,
    fixture_name: str = "s01e01_safe.json",
) -> TestClient:
    return TestClient(
        _stub_graph_app(user=user, progress=progress, fixture_name=fixture_name)
    )


def _viz_url(view: str, episode_order: int = 1, focus_ids: list[str] | None = None) -> str:
    url = (
        f"/api/series/series_dexter/graph/visualization?view={view}"
        f"&episode_order={episode_order}"
    )
    for focus_id in focus_ids or []:
        url += f"&focus_id={focus_id}"
    return url


def test_visualization_route_episode_overview_validated_end_to_end() -> None:
    """One request returns a validated episode_overview DTO end to end."""
    client = _viz_client()
    response = client.get(_viz_url("episode_overview", episode_order=1))

    assert response.status_code == 200, response.text
    dto = VisualizationDTO.model_validate(response.json())
    assert dto.metadata.projection_version == PROJECTION_VERSION
    assert dto.metadata.view_type == "episode_overview"
    assert dto.metadata.series_id == "series_dexter"
    # Anonymous readers are fixed at order 1 (PROB-04/#12).
    assert dto.metadata.episode_order == 1
    assert dto.metadata.visible_until_order == 1
    assert dto.metadata.effective_view_order == 1
    # Deterministic content: containers + characters (the route carries no
    # editorial event metadata yet, so events are timeline-only).
    assert {node.kind for node in dto.nodes} == {"Series", "Episode", "Character"}
    assert dto.nodes
    assert dto.groups == []
    assert dto.focus is None
    assert dto.timeline == []


@pytest.mark.parametrize("view", VISUALIZATION_VIEWS)
def test_visualization_route_all_views_return_valid_dtos(view: str) -> None:
    """Every D-29 view serializes a strict VisualizationDTO with closure."""
    client = _viz_client(
        user={"id": "user:test"},
        progress=_ProgressRecord(2, 2),
        fixture_name="s01e02_cumulative_safe.json",
    )
    # D-29: focus_id is accepted ONLY for graphrag_focus — other views must
    # not send it (the route refuses it with a typed 422).
    focus_ids = ["char_dexter_morgan"] if view == "graphrag_focus" else None
    response = client.get(_viz_url(view, episode_order=2, focus_ids=focus_ids))

    assert response.status_code == 200, response.text
    dto = VisualizationDTO.model_validate(response.json())
    assert dto.metadata.view_type == view
    assert dto.metadata.effective_view_order == 2
    # Focus semantics: only graphrag_focus carries a focus reference, and it
    # always resolves inside the DTO (T10-FOCUS-02).
    if view == "graphrag_focus":
        assert dto.focus is not None
        assert dto.focus.node_id == "char_dexter_morgan"
        assert dto.focus.node_id in {node.id for node in dto.nodes}
    else:
        assert dto.focus is None


def test_visualization_route_unknown_series_is_404() -> None:
    client = _viz_client()
    response = client.get(
        "/api/series/unknown/graph/visualization?view=episode_overview&episode_order=1"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": {"code": "SERIES_NOT_FOUND", "message": "Series not found."}
    }


def test_visualization_route_requires_view_and_positive_episode_order() -> None:
    client = _viz_client()

    missing_view = client.get(
        "/api/series/series_dexter/graph/visualization?episode_order=1"
    )
    assert missing_view.status_code == 422
    assert missing_view.json()["detail"]["code"] == "INVALID_REQUEST"

    bad_enum = client.get(
        "/api/series/series_dexter/graph/visualization?view=banana&episode_order=1"
    )
    assert bad_enum.status_code == 422
    assert bad_enum.json()["detail"]["code"] == "INVALID_REQUEST"

    missing_order = client.get(
        "/api/series/series_dexter/graph/visualization?view=full"
    )
    assert missing_order.status_code == 422
    assert missing_order.json()["detail"]["code"] == "INVALID_REQUEST"

    zero_order = client.get(
        "/api/series/series_dexter/graph/visualization?view=full&episode_order=0"
    )
    assert zero_order.status_code == 422
    assert zero_order.json()["detail"]["code"] == "INVALID_REQUEST"


def test_visualization_route_invalid_episode_order_is_422() -> None:
    """An effective boundary with no persisted episode is refused with the
    typed INVALID_VISIBLE_UNTIL_ORDER envelope."""
    # Authenticated user whose persisted progress resolves to order 2, but
    # the fixture's max persisted episode order is 1 -> 422.
    client = _viz_client(
        user={"id": "user:test"}, progress=_ProgressRecord(2, 2)
    )
    response = client.get(_viz_url("full", episode_order=3))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"


def test_visualization_route_anonymous_clamped_to_order_one() -> None:
    """Anonymous readers are fixed at order 1 even when requesting a higher
    episode_order (PROB-04/#12)."""
    client = _viz_client()
    response = client.get(_viz_url("full", episode_order=99))

    assert response.status_code == 200, response.text
    dto = VisualizationDTO.model_validate(response.json())
    assert dto.metadata.episode_order == 1
    assert dto.metadata.effective_view_order == 1


def test_visualization_route_authenticated_clamped_by_progress() -> None:
    """Authenticated readers are clamped to persisted progress (D-05)."""
    cumulative = "s01e02_cumulative_safe.json"

    # Progress at order 2 -> requesting order 2 serves order 2.
    client = _viz_client(
        user={"id": "user:test"},
        progress=_ProgressRecord(2, 2),
        fixture_name=cumulative,
    )
    response = client.get(_viz_url("full", episode_order=2))
    assert response.status_code == 200, response.text
    dto = VisualizationDTO.model_validate(response.json())
    assert dto.metadata.effective_view_order == 2
    assert dto.metadata.episode_order == 2

    # Progress at order 1 -> requesting order 2 clamps to 1 (min rule).
    client1 = _viz_client(
        user={"id": "user:test"},
        progress=_ProgressRecord(1, 1),
        fixture_name=cumulative,
    )
    response1 = client1.get(_viz_url("full", episode_order=2))
    assert response1.status_code == 200, response1.text
    dto1 = VisualizationDTO.model_validate(response1.json())
    assert dto1.metadata.effective_view_order == 1
    assert dto1.metadata.episode_order == 1


def test_visualization_route_focus_id_rejected_for_non_focus_views() -> None:
    """focus_id is accepted ONLY for graphrag_focus (D-29)."""
    client = _viz_client()
    response = client.get(
        _viz_url("full", focus_ids=["char_dexter_morgan"])
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_visualization_route_graphrag_focus_requires_focus_id() -> None:
    client = _viz_client()
    response = client.get(_viz_url("graphrag_focus"))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_visualization_route_graphrag_focus_hidden_or_unknown_is_422() -> None:
    """Hidden and unknown focus ids are indistinguishable and both fail
    closed with a sanitized envelope (T10-FOCUS-02)."""
    client = _viz_client()
    response = client.get(
        _viz_url("graphrag_focus", focus_ids=["char_brian_moser"])
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"
    assert "char_brian_moser" not in response.text


def test_visualization_route_graphrag_focus_caps_distinct_ids() -> None:
    client = _viz_client()
    focus_ids = [f"char_{i}" for i in range(21)]
    response = client.get(_viz_url("graphrag_focus", focus_ids=focus_ids))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_visualization_route_cache_hit_matches_miss_byte_for_byte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache-aside on the projection route: hit is byte-identical to miss and
    the key carries series/effective/view/version/scope."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)
    client = TestClient(_stub_graph_app())

    miss = client.get(_viz_url("episode_overview", episode_order=1))
    hit = client.get(_viz_url("episode_overview", episode_order=1))

    assert miss.status_code == hit.status_code == 200
    assert miss.json() == hit.json()
    assert json.dumps(miss.json(), sort_keys=True) == json.dumps(hit.json(), sort_keys=True)
    assert any(
        key.startswith(f"viz:series_dexter:1:episode_overview:{PROJECTION_VERSION}:anon")
        for key in fake._store
    )


def test_visualization_route_cache_redis_failure_still_serves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Redis failure bypasses the cache entirely — the projection still
    serves 200 (T-08-06-02/D-30)."""
    monkeypatch.setattr(get_settings(), "redis_url", "rediss://fake:6379")

    class _BrokenRedis:
        async def get(self, _key: str) -> bytes | None:
            raise RuntimeError("redis down")

        async def setex(self, *_args, **_kwargs) -> None:
            raise RuntimeError("redis down")

    monkeypatch.setattr(graph_cache, "get_redis", lambda: _BrokenRedis())
    client = TestClient(_stub_graph_app())

    response = client.get(_viz_url("episode_overview", episode_order=1))
    assert response.status_code == 200, response.text
    VisualizationDTO.model_validate(response.json())


def test_visualization_route_preserves_graph_route_behavior() -> None:
    """The existing GET /graph GraphResponse contract is untouched by the
    visualization route (same boundary block, same filtered read path)."""
    client = _viz_client()
    graph = client.get("/api/series/series_dexter/graph?visible_until_order=1")
    assert graph.status_code == 200, graph.text
    body = graph.json()
    assert body["series"]["id"] == "series_dexter"
    assert body["visible_until_order"] == 1
    assert body["effective_view_order"] == 1
    assert body["nodes"] and body["edges"]
    GraphResponse.model_validate(body)


# --- FEAT-06 / FEAT-05 routes (plan 09-11) --------------------------------

DEXTER = "dexter:character:dexter_morgan"
DEBRA = "dexter:character:debra_morgan"


def test_path_route_finds_shortest_visible_path(live_client: TestClient) -> None:
    response = live_client.post(
        "/api/series/series_dexter/graph/path",
        json={
            "source_entity_id": DEXTER,
            "target_entity_id": DEBRA,
            "max_hops": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["path"] == [DEXTER, DEBRA]
    assert body["hops"] == 1
    assert len(body["edges"]) == 1


def test_path_route_unconnected_pair_returns_no_path(live_client: TestClient) -> None:
    response = live_client.post(
        "/api/series/series_dexter/graph/path",
        json={
            "source_entity_id": DEXTER,
            "target_entity_id": "dexter:character:rudy_cooper",
            "max_hops": 4,
        },
    )
    assert response.status_code == 200
    assert response.json()["found"] is False


def test_path_route_rejects_max_hops_above_ceiling(live_client: TestClient) -> None:
    response = live_client.post(
        "/api/series/series_dexter/graph/path",
        json={
            "source_entity_id": DEXTER,
            "target_entity_id": DEBRA,
            "max_hops": 99,
        },
    )
    # Server ceiling MAX_PATH_HOPS=4 — the strict model rejects >4 (422).
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


# --- PROB-09/#59: path-route boundary resolves from persisted progress ------
# Regression: find_shortest_path previously passed MAX_PATH_HOPS (4) as the
# requested episode order, clamping every authenticated reader to min(4,
# view_as_of) — and granting users WITHOUT a progress record an unearned
# boundary of 4. With requested_order=None the resolver must return the
# persisted progress itself, and fail closed to 1 when no record exists.


class _FakeBoundaryService:
    """resolve_boundary accepts any order (every order is \"persisted\")."""

    async def resolve_boundary(self, series_id: str, visible_until_order: int) -> dict:
        return {"id": f"ep:{visible_until_order}"}


class _FakeProgressService:
    def __init__(self, record) -> None:
        self._record = record

    async def get(self, user_id: str, series_id: str):
        return self._record


def _run_resolve(user, record, requested_order=None) -> int:
    from spoilerless.app.api.graph import _resolve_effective_boundary

    service = _FakeBoundaryService()
    progress = _FakeProgressService(record)
    return asyncio.run(
        _resolve_effective_boundary(
            service, progress, "series_dexter", user, requested_order
        )
    )


def test_path_boundary_uses_persisted_progress_not_max_hops() -> None:
    # watched/view beyond MAX_PATH_HOPS=4: old code clamped to 4 (the bug);
    # the fix must return the persisted progress (7) unchanged.
    record = types.SimpleNamespace(view_as_of_order=7, watched_through_order=7)
    assert _run_resolve({"id": "u1"}, record) == 7


def test_path_boundary_respects_view_below_watched() -> None:
    # D-05 min rule still applies when no client boundary is present.
    record = types.SimpleNamespace(view_as_of_order=2, watched_through_order=7)
    assert _run_resolve({"id": "u1"}, record) == 2


def test_path_boundary_fails_closed_without_progress_record() -> None:
    # New user with no persisted progress: boundary 1, NOT MAX_PATH_HOPS=4.
    assert _run_resolve({"id": "u1"}, None) == 1


def test_path_boundary_anonymous_is_fixed_at_one() -> None:
    assert _run_resolve(None, None) == 1


def test_boundary_clamp_still_applies_with_client_requested_order() -> None:
    # The graph-GET path (requested_order set) keeps its min-clamp behavior.
    record = types.SimpleNamespace(view_as_of_order=7, watched_through_order=9)
    assert _run_resolve({"id": "u1"}, record, requested_order=10) == 7


def test_export_returns_markdown_with_visible_content(
    live_client: TestClient,
) -> None:
    response = live_client.get(
        "/api/series/series_dexter/export", params={"visible_until_order": 1}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "Content-Disposition" in response.headers
    assert "spoilerless-dexter-" in response.headers["content-disposition"]
    text = response.text
    assert "# Dexter" in text
    assert "## Episodes" in text
    assert "S01E01" in text
    # Boundary-respecting: episode 2's spoiler title must NOT leak.
    assert "Crocodile" not in text


def test_export_target_id_renders_resource_section(
    live_client: TestClient,
) -> None:
    response = live_client.get(
        "/api/series/series_dexter/export",
        params={"visible_until_order": 1, "target_id": DEXTER},
    )
    assert response.status_code == 200
    text = response.text
    assert "## Dexter" in text
    assert "- Type: `Character`" in text
    assert "### Claims" in text


def test_export_unknown_series_returns_404(live_client: TestClient) -> None:
    response = live_client.get(
        "/api/series/unknown-series/export", params={"visible_until_order": 1}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERIES_NOT_FOUND"
