from __future__ import annotations

import asyncio
import importlib
from collections.abc import Callable, Iterator
from typing import Any, Protocol
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.graph.seed import setup_database
from spoilerless.app.repository.session import Neo4jSessionRepository
from spoilerless.app.repository.user import UserRepository


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


def _create_user_with_session(role: str) -> tuple[str, str, str]:
    """Create an :AppUser (with *role*) + :Session row via a fresh driver/loop.

    Returns ``(google_sub, user_id, raw_token)``. The app's
    ``require_current_user`` resolves the same rows from the shared live DB
    at request time, so the cookie set from the returned raw token
    authenticates the request. A fresh driver/loop is used so the app's
    portal-loop driver is never touched from another loop (same two-loop
    rule as test_chat_api.py / test_candidate_review.py).
    """

    async def _run() -> tuple[str, str, str]:
        db = Neo4jDatabase()
        db.open()
        try:
            google_sub = f"test-user-content-{role}-{uuid4()}"
            user = await UserRepository(db).upsert(
                google_sub=google_sub,
                email=f"{google_sub}@example.com",
                display_name="User Content Test User",
                avatar_url="",
                role=role,
            )
            raw_token = await Neo4jSessionRepository(db).create(
                user["id"], ttl_seconds=3600
            )
            return google_sub, user["id"], raw_token
        finally:
            await db.close()

    return asyncio.run(_run())


async def _delete_test_user(google_sub: str) -> None:
    """Remove only the test-created AppUser + its session rows."""
    db = Neo4jDatabase()
    db.open()
    try:
        await db.execute_query(
            "MATCH (u:AppUser {google_sub: $sub}) "
            "OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session) "
            "DETACH DELETE u, s",
            sub=google_sub,
        )
    finally:
        await db.close()


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
    # After 11-02, notes GETs clamp via shared resolver; set progress to 3 so 3 is visible
    user_content_client.post("/api/series/series_dexter/progress", json={"visible_until_order": 3})
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
    user_content_client.post("/api/series/series_dexter/progress", json={"visible_until_order": 3})
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
    assert response.json() == {"detail": {"code": "INVALID_REQUEST", "message": "Request validation failed."}}


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


def test_anonymous_mutations_are_rejected_with_401(
    live_client: TestClient, second_series: str
) -> None:
    """PROB-01 (#1): every mutation route rejects anonymous callers with 401."""
    live_client.cookies.clear()
    base = f"/api/series/{second_series}"
    episode_id = f"{second_series}:episode:1"
    anonymous_calls = [
        ("post", f"{base}/notes", {"target_type": "Character", "target_id": "scratch:character:x", "content": "x"}),
        ("patch", f"{base}/notes/user-note:x", {"content": "x"}),
        ("delete", f"{base}/notes/user-note:x", None),
        ("post", f"{base}/custom-nodes", {"node_type": "Object", "label": "x", "episode_id": episode_id}),
        ("patch", f"{base}/custom-nodes/user-node:x", {"label": "x"}),
        ("delete", f"{base}/custom-nodes/user-node:x", None),
        ("post", f"{base}/custom-relationships", {"source_id": "scratch:a", "target_id": "scratch:b", "predicate": "KNOWS", "episode_id": episode_id}),
        ("patch", f"{base}/custom-relationships/user-rel:x", {"predicate": "TRUSTS"}),
        ("delete", f"{base}/custom-relationships/user-rel:x", None),
    ]
    for method, url, body in anonymous_calls:
        if body is not None:
            response = getattr(live_client, method)(url, json=body)
        else:
            response = getattr(live_client, method)(url)
        assert response.status_code == 401, f"{method.upper()} {url} -> {response.status_code}: {response.text}"
        assert response.json()["detail"]["code"] == "AUTH_UNAUTHENTICATED"


def test_user_content_is_owner_bound_and_cross_owner_mutations_rejected(
    live_client: TestClient,
    second_series: str,
    user_session: dict[str, str],
) -> None:
    """PROB-02 (#4): records carry the owner user_id; only the owner (or an
    admin) can update/delete them; cross-owner attempts get 403 forbidden."""
    base = f"/api/series/{second_series}"
    episode_id = f"{second_series}:episode:1"
    owner_id = user_session["user_id"]
    owner_token = user_session["token"]

    # --- Owner creates a Character node, an Object node, a relationship,
    # and a note targeting the Character ---
    char = live_client.post(f"{base}/custom-nodes", json={
        "node_type": "Character", "label": "owner character", "episode_id": episode_id,
    })
    assert char.status_code == 201, char.text
    char_id = char.json()["id"]
    assert char.json()["user_id"] == owner_id

    obj = live_client.post(f"{base}/custom-nodes", json={
        "node_type": "Object", "label": "owner object", "episode_id": episode_id,
    })
    assert obj.status_code == 201, obj.text
    obj_id = obj.json()["id"]

    rel = live_client.post(f"{base}/custom-relationships", json={
        "source_id": char_id, "target_id": obj_id, "predicate": "KNOWS",
        "episode_id": episode_id,
    })
    assert rel.status_code == 201, rel.text
    rel_id = rel.json()["id"]
    assert rel.json()["user_id"] == owner_id

    note = live_client.post(f"{base}/notes", json={
        "target_type": "Character", "target_id": char_id, "content": "owner note",
    })
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]
    assert note.json()["user_id"] == owner_id

    # --- A different regular user cannot mutate any of it (403 forbidden) ---
    google_sub_b, _user_b_id, token_b = _create_user_with_session("user")
    try:
        live_client.cookies.set("session", token_b)
        for method, url, body in [
            ("patch", f"{base}/notes/{note_id}", {"content": "hijacked"}),
            ("delete", f"{base}/notes/{note_id}", None),
            ("patch", f"{base}/custom-nodes/{char_id}", {"label": "hijacked"}),
            ("delete", f"{base}/custom-nodes/{char_id}", None),
            ("patch", f"{base}/custom-relationships/{rel_id}", {"predicate": "TRUSTS"}),
            ("delete", f"{base}/custom-relationships/{rel_id}", None),
        ]:
            if body is not None:
                response = getattr(live_client, method)(url, json=body)
            else:
                response = getattr(live_client, method)(url)
            assert response.status_code == 403, (
                f"{method.upper()} {url} -> {response.status_code}: {response.text}"
            )
            assert response.json()["detail"]["code"] == "FORBIDDEN"
    finally:
        asyncio.run(_delete_test_user(google_sub_b))

    # --- Admin bypasses the owner check (documented branch) ---
    google_sub_admin, _admin_id, token_admin = _create_user_with_session("admin")
    try:
        live_client.cookies.set("session", token_admin)
        patched = live_client.patch(f"{base}/custom-nodes/{char_id}", json={"label": "admin renamed"})
        assert patched.status_code == 200, patched.text
        assert patched.json()["label"] == "admin renamed"
        assert live_client.delete(f"{base}/notes/{note_id}").status_code == 204
        assert live_client.delete(f"{base}/custom-relationships/{rel_id}").status_code == 204
    finally:
        asyncio.run(_delete_test_user(google_sub_admin))

    # --- The owner can still update/delete own content ---
    live_client.cookies.set("session", owner_token)
    updated = live_client.patch(f"{base}/custom-nodes/{char_id}", json={"label": "owner renamed"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["user_id"] == owner_id
    assert live_client.delete(f"{base}/custom-nodes/{char_id}").status_code == 204
    assert live_client.delete(f"{base}/custom-nodes/{obj_id}").status_code == 204


def _seed_owner_user_content(client: TestClient, series_id: str) -> dict[str, str]:
    """Create note + custom node + custom relationship as the current (owner) session.

    All content lives on *series_id* whose single episode persists at
    ``visible_from_order`` 1, so every reader (anonymous fixed at order 1,
    authenticated fail-closed at order 1) can read it back. Returns the
    created ids plus the owner ``user_id`` observed on the create responses.
    """
    base = f"/api/series/{series_id}"
    episode_id = f"{series_id}:episode:1"
    node = client.post(f"{base}/custom-nodes", json={
        "node_type": "Character", "label": "privacy probe", "episode_id": episode_id,
    })
    assert node.status_code == 201, node.text
    node_id = node.json()["id"]
    # Relationships must stay intra-series: relate two user-owned nodes.
    target_node = client.post(f"{base}/custom-nodes", json={
        "node_type": "Object", "label": "privacy probe target", "episode_id": episode_id,
    })
    assert target_node.status_code == 201, target_node.text
    relationship = client.post(f"{base}/custom-relationships", json={
        "source_id": node_id, "target_id": target_node.json()["id"],
        "predicate": "KNOWS", "episode_id": episode_id,
    })
    assert relationship.status_code == 201, relationship.text
    relationship_id = relationship.json()["id"]
    note = client.post(f"{base}/notes", json={
        "target_type": "Character", "target_id": node_id, "content": "privacy probe note",
    })
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]
    owner_ids = {row.get("user_id") for row in (node.json(), relationship.json(), note.json())}
    assert len(owner_ids) == 1 and None not in owner_ids, (
        f"create responses must carry exactly one owner user_id: {owner_ids}"
    )
    return {
        "note_id": note_id,
        "node_id": node_id,
        "relationship_id": relationship_id,
        "owner_id": owner_ids.pop(),
    }


def _read_all_user_content(
    client: TestClient, series_id: str, seeded: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read the note list, one note, the custom node and the custom relationship."""
    base = f"/api/series/{series_id}"
    listed_notes = client.get(f"{base}/notes", params={"visible_until_order": 1})
    got_note = client.get(f"{base}/notes/{seeded['note_id']}", params={"visible_until_order": 1})
    got_node = client.get(f"{base}/custom-nodes/{seeded['node_id']}", params={"visible_until_order": 1})
    got_relationship = client.get(
        f"{base}/custom-relationships/{seeded['relationship_id']}",
        params={"visible_until_order": 1},
    )
    for response in (listed_notes, got_note, got_node, got_relationship):
        assert response.status_code == 200, (
            f"GET {response.request.url} -> {response.status_code}: {response.text}"
        )
    return listed_notes.json(), got_note.json(), got_node.json(), got_relationship.json()


def test_anonymous_user_content_reads_scrub_user_id(
    user_content_client: TestClient, second_series: str
) -> None:
    """D-02/THERMO-P0-01: anonymous reads shape responses with ``user_id: null``
    instead of tripping a 500 Pydantic ValidationError on the stripped field."""
    seeded = _seed_owner_user_content(user_content_client, second_series)
    user_content_client.cookies.clear()
    listed, note, node, relationship = _read_all_user_content(
        user_content_client, second_series, seeded
    )
    assert [row["user_id"] for row in listed] == [None]
    for payload in (note, node, relationship):
        assert payload["id"] in seeded.values()
        assert payload["user_id"] is None, payload


def test_non_owner_user_content_reads_scrub_user_id(
    user_content_client: TestClient, second_series: str
) -> None:
    """D-02: another regular (non-admin) user never sees the author user_id."""
    seeded = _seed_owner_user_content(user_content_client, second_series)
    google_sub_b, _user_b_id, token_b = _create_user_with_session("user")
    try:
        user_content_client.cookies.set("session", token_b)
        listed, note, node, relationship = _read_all_user_content(
            user_content_client, second_series, seeded
        )
        assert [row["user_id"] for row in listed] == [None]
        for payload in (note, node, relationship):
            assert payload["user_id"] is None, payload
    finally:
        asyncio.run(_delete_test_user(google_sub_b))


def test_owner_and_admin_reads_preserve_user_id(
    user_content_client: TestClient, second_series: str
) -> None:
    """Owners and admins keep seeing the author user_id on reads."""
    seeded = _seed_owner_user_content(user_content_client, second_series)
    owner_id = seeded["owner_id"]

    # --- Owner read: user_id preserved ---
    listed, note, node, relationship = _read_all_user_content(
        user_content_client, second_series, seeded
    )
    assert [row["user_id"] for row in listed] == [owner_id]
    for payload in (note, node, relationship):
        assert payload["user_id"] == owner_id, payload

    # --- Admin read: user_id preserved ---
    google_sub_admin, _admin_id, token_admin = _create_user_with_session("admin")
    try:
        user_content_client.cookies.set("session", token_admin)
        listed, note, node, relationship = _read_all_user_content(
            user_content_client, second_series, seeded
        )
        assert [row["user_id"] for row in listed] == [owner_id]
        for payload in (note, node, relationship):
            assert payload["user_id"] == owner_id, payload
    finally:
        asyncio.run(_delete_test_user(google_sub_admin))


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
    google_sub, _user_id, raw_token = _create_user_with_session("user")
    live_client.cookies.set("session", raw_token)
    try:
        yield live_client
    finally:
        asyncio.run(_delete_test_user(google_sub))
        _run(_with_database(_cleanup_user_content))


@pytest.fixture
def user_session(live_client: TestClient) -> Iterator[dict[str, str]]:
    """Authenticate ``live_client`` as a regular (non-admin) user."""
    google_sub, user_id, raw_token = _create_user_with_session("user")
    live_client.cookies.set("session", raw_token)
    yield {"google_sub": google_sub, "user_id": user_id, "token": raw_token}
    asyncio.run(_delete_test_user(google_sub))


@pytest.fixture
def admin_session(live_client: TestClient) -> Iterator[dict[str, str]]:
    """Authenticate ``live_client`` as an admin user."""
    google_sub, user_id, raw_token = _create_user_with_session("admin")
    live_client.cookies.set("session", raw_token)
    yield {"google_sub": google_sub, "user_id": user_id, "token": raw_token}
    asyncio.run(_delete_test_user(google_sub))


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
