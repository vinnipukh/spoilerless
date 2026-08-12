"""Integration tests for watch-progress persistence (RAG-01).

Runs against the live local Neo4j instance (same assumption as the rest of the
backend suite). Watch progress is backend-authoritative: the boundary is never
accepted as request input on the GraphRAG path, only via this explicit
progress endpoint, and it is resolved server-side from the persisted
UserSeriesProgress record.

All tests are synchronous TestClient calls (the working pattern in
test_graph_api.py): the app's async Neo4j driver is only ever touched inside
TestClient's portal loop.  In-memory repo awaits run via asyncio.run with a
dedicated driver instance that is discarded afterwards — the driver never
crosses event loops.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spoilerless.app.api import deps
from spoilerless.app.api.progress import router as progress_router
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.api.exceptions import install_repository_error_handlers
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.progress import PROGRESS_GET_QUERY, PROGRESS_UPSERT_QUERY
from spoilerless.app.repository.session import InMemorySessionRepository
from spoilerless.app.repository.progress import ProgressRepository
from spoilerless.app.services.auth import AuthService
from spoilerless.app.services.progress import ProgressNotFoundError, ProgressService

from conftest import helper_db, module_cleanup_fixture, run_async, run_query  # noqa: E402

from spoilerless.tests.conftest import NoopGoogleVerifier



class FakeUserRepo:
    """In-memory user repository keyed by google_sub (mirrors test_auth.py)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._id_counter = 0

    async def upsert(
        self, google_sub: str, email: str, display_name: str, avatar_url: str
    ) -> dict[str, Any]:
        existing = self._store.get(google_sub)
        if existing:
            existing["email"] = email
            existing["display_name"] = display_name
            existing["avatar_url"] = avatar_url
            return dict(existing)
        self._id_counter += 1
        record = {
            "id": f"user:{uuid4()}",
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        self._store[google_sub] = record
        return dict(record)

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        for record in self._store.values():
            if record["id"] == user_id:
                return dict(record)
        return None


_ORPHAN_PROGRESS_CLEANUP = [
    # NEVER delete all rows: the shared live DB also holds the user's real
    # progress (runbook: data-loss class). Only orphaned rows — progress
    # whose AppUser does not exist in Neo4j (unit tests use the in-memory
    # FakeUserRepo, so their rows never have a real :AppUser) — are deleted.
    "MATCH (p:UserSeriesProgress) "
    "WHERE NOT EXISTS { MATCH (:AppUser {id: p.user_id}) } "
    "DETACH DELETE p",
]


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db



_cleanup_after_module = module_cleanup_fixture(_ORPHAN_PROGRESS_CLEANUP)
@pytest.fixture
def fake_user_repo() -> FakeUserRepo:
    return FakeUserRepo()


@pytest.fixture
def session_repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture
def progress_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> FastAPI:
    app = FastAPI()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo, verifier=NoopGoogleVerifier())

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    app.include_router(progress_router)
    return app


@pytest.fixture
def client(progress_app: FastAPI) -> Iterator[TestClient]:
    # Context-managed TestClient keeps ONE portal loop alive for the whole
    # test — the app's async Neo4j driver is only ever used inside that loop
    # (test_graph_api.py pattern). Without `with`, starlette starts a fresh
    # per-request loop and pooled driver connections die with the first one.
    with TestClient(progress_app, raise_server_exceptions=False) as client:
        yield client


def _cleanup_user(user_id: str) -> None:
    """Delete the user's Neo4j rows via a dedicated driver+loop.

    The app's driver is only ever used inside TestClient's portal loop; any
    cleanup here uses its own short-lived driver so no connection ever crosses
    an event loop (see test_graph_api.py's _seed_live_database pattern).
    """

    run_query(
        "MATCH (p:UserSeriesProgress {user_id: $uid}) DETACH DELETE p",
        uid=user_id,
    )
    run_query("MATCH (u:AppUser {id: $uid}) DETACH DELETE u", uid=user_id)


@pytest.fixture
def authed_user(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> Iterator[dict[str, Any]]:
    """Authenticate a fresh user against the app; clean up Neo4j rows on exit."""
    user = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="user@example.com",
            display_name="Test User",
            avatar_url="",
        )
    )
    raw_token = asyncio.run(session_repo.create(user["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)
    yield user
    _cleanup_user(user["id"])


def _set_progress(
    client: TestClient, series_id: str, visible_until_order: int
) -> Any:
    return client.post(
        f"/api/series/{series_id}/progress",
        json={"visible_until_order": visible_until_order},
    )


def _switch_to_other_user(
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    client: TestClient,
) -> dict[str, Any]:
    """Authenticate as a second, distinct user."""
    other = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="other@example.com",
            display_name="Other",
            avatar_url="",
        )
    )
    raw_token = asyncio.run(session_repo.create(other["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)
    return other


# ---------------------------------------------------------------------------
# Auth / ownership
# ---------------------------------------------------------------------------


def test_progress_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/series/series_dexter/progress")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_UNAUTHENTICATED"

    response = client.post(
        "/api/series/series_dexter/progress", json={"visible_until_order": 1}
    )
    assert response.status_code == 401


def test_progress_is_scoped_to_the_authenticated_user(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    authed_user: dict[str, Any],
) -> None:
    # User A writes progress; user B (different session) must not see it.
    response = _set_progress(client, "series_dexter", 2)
    assert response.status_code == 200
    assert response.json()["visible_until_order"] == 2

    other = _switch_to_other_user(fake_user_repo, session_repo, client)
    assert other["id"] != authed_user["id"]

    response = client.get("/api/series/series_dexter/progress")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_progress_get_query_scopes_ownership_inside_the_match_pattern() -> None:
    """The ownership filter must live inside the Cypher node pattern itself —
    never a separate post-fetch check in Python (06-RESEARCH.md Q7)."""
    assert (
        "(p:UserSeriesProgress {user_id: $user_id, series_id: $series_id})"
        in PROGRESS_GET_QUERY
    )
    assert (
        "(p:UserSeriesProgress {user_id: $user_id, series_id: $series_id})"
        in PROGRESS_UPSERT_QUERY
    )


def test_never_watched_and_nonexistent_series_return_identical_404(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """A real series the user never watched and a series_id that does not
    exist anywhere must be indistinguishable to the caller."""
    never_watched = client.get("/api/series/series_dexter/progress")
    nonexistent = client.get("/api/series/series_does_not_exist_at_all/progress")

    assert never_watched.status_code == nonexistent.status_code == 404
    assert (
        never_watched.json()["detail"]["code"]
        == nonexistent.json()["detail"]["code"]
        == "RESOURCE_NOT_FOUND"
    )
    assert never_watched.json() == nonexistent.json()


def test_progress_service_resolve_raises_not_found_for_missing_progress(
    database: Neo4jDatabase,
) -> None:
    """``ProgressService.resolve`` raises the typed error (not a generic
    exception) so every caller can fail closed instead of propagating a raw
    500 (RAG-01)."""
    service = ProgressService(database)

    async def _go() -> None:
        with pytest.raises(ProgressNotFoundError):
            await service.resolve("user:does-not-exist", "series_dexter")

    run_async(_go)


def test_progress_repository_get_is_none_for_missing_record(
    database: Neo4jDatabase,
) -> None:
    """The repository-level read returns ``None`` (never raises, never a
    partial/garbage row) when no record exists for the (user, series) pair."""
    repo = ProgressRepository(database)

    async def _go() -> Any:
        return await repo.get("user:does-not-exist", "series_dexter")

    assert run_async(_go) is None


# ---------------------------------------------------------------------------
# CRUD semantics
# ---------------------------------------------------------------------------


def test_post_creates_progress_and_get_returns_it(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = _set_progress(client, "series_dexter", 1)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == authed_user["id"]
    assert body["series_id"] == "series_dexter"
    assert body["visible_until_order"] == 1
    assert body["id"]
    assert body["updated_at"]

    response = client.get("/api/series/series_dexter/progress")
    assert response.status_code == 200
    assert response.json()["visible_until_order"] == 1


def test_post_progress_equal_value_is_idempotent_update(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """Setting progress equal to the current persisted value succeeds and keeps
    the same resulting value — it is an idempotent update, never an error."""
    first = _set_progress(client, "series_dexter", 1)
    assert first.status_code == 200
    first_id = first.json()["id"]

    second = _set_progress(client, "series_dexter", 1)
    assert second.status_code == 200
    assert second.json()["visible_until_order"] == 1
    assert second.json()["id"] == first_id  # same persisted row, no duplicate


def test_post_progress_updates_value(client: TestClient, authed_user: dict[str, Any]) -> None:
    assert _set_progress(client, "series_dexter", 1).status_code == 200
    response = _set_progress(client, "series_dexter", 3)
    assert response.status_code == 200
    assert response.json()["visible_until_order"] == 3


def test_get_missing_progress_returns_generic_404(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = client.get("/api/series/series_dexter/progress")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_post_progress_rejects_non_positive_boundary(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = _set_progress(client, "series_dexter", 0)
    assert response.status_code == 422

    response = _set_progress(client, "series_dexter", -1)
    assert response.status_code == 422


def test_progress_null_persisted_split_field_fails_closed_to_422(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """PROB-16/#37: a persisted row with a NULL split field (corrupt legacy
    data) fails closed to the documented 422 envelope on BOTH read and write
    paths — previously an uncaught TypeError from ``effective_view_order``
    (a 500). The corrupt row is seeded and removed via a dedicated driver."""
    uid = authed_user["id"]

    run_query(
        "MERGE (u:AppUser {id: $uid}) "
        "MERGE (s:Series {id: $sid}) "
        "MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress "
        "{user_id: $uid, series_id: $sid}) "
        "SET p.id = $pid, p.watched_through_order = 3, "
        "    p.view_as_of_order = NULL, p.visible_until_order = NULL",
        uid=uid,
        sid="series_dexter",
        pid=f"progress:09-04-corrupt:{uuid4()}",
    )
    try:
        # Read path: GET must 422 via the documented envelope, never 500.
        read = client.get("/api/series/series_dexter/progress")
        assert read.status_code == 422, read.text
        assert read.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"

        # Write path: a view-only update reads the corrupt row first and must
        # surface the same 422 envelope.
        write = client.post(
            "/api/series/series_dexter/progress",
            json={"view_as_of_order": 2},
        )
        assert write.status_code == 422, write.text
        assert write.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"
    finally:
        # authed_user teardown removes the AppUser + its progress rows.
        pass


def test_progress_never_accepts_extra_fields(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = client.post(
        "/api/series/series_dexter/progress",
        json={"visible_until_order": 1, "user_id": "attacker"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Concurrency backstop
# ---------------------------------------------------------------------------


def test_concurrent_upserts_for_same_user_series_resolve_without_torn_state(
    database: Neo4jDatabase,
) -> None:
    """Two near-simultaneous upserts for the same (user, series) must resolve
    to one of the two submitted values with no exception and no torn/partial
    write — the MERGE-based upsert's atomic semantics (backstop-level, not an
    exhaustive load test)."""
    repo = ProgressRepository(database)
    user_id = f"user:concurrency-{uuid4()}"
    series_id = "series_dexter"

    async def _go() -> Any:
        await asyncio.gather(
            repo.upsert(
                user_id, series_id, watched_through_order=1, view_as_of_order=1
            ),
            repo.upsert(
                user_id, series_id, watched_through_order=3, view_as_of_order=3
            ),
        )
        return await repo.get(user_id, series_id)

    try:
        final = run_async(_go)
        assert final is not None
        assert final.visible_until_order in (1, 3)
        assert final.watched_through_order in (1, 3)
        assert final.effective_view_order == final.watched_through_order
        assert final.user_id == user_id
        assert final.series_id == series_id
    finally:

        run_query(
            "MATCH (p:UserSeriesProgress {user_id: $uid}) DETACH DELETE p",
            uid=user_id,
        )
        run_query("MATCH (u:AppUser {id: $uid}) DETACH DELETE u", uid=user_id)


# ---------------------------------------------------------------------------
# D-05 split fields + D-21 API contract (07-02)
# ---------------------------------------------------------------------------


def test_post_watched_through_order_writes_split_fields_and_effective(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """Confirming N persists watched_through_order AND view_as_of_order=N and
    the response exposes effective_view_order == N (D-05, D-21)."""
    response = client.post(
        "/api/series/series_dexter/progress", json={"watched_through_order": 2}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["watched_through_order"] == 2
    assert body["view_as_of_order"] == 2
    assert body["effective_view_order"] == 2
    # visible_until_order stays echoed for backward compatibility (D-21).
    assert body["visible_until_order"] == 2

    got = client.get("/api/series/series_dexter/progress").json()
    assert got["watched_through_order"] == 2
    assert got["view_as_of_order"] == 2
    assert got["effective_view_order"] == 2


def test_legacy_visible_until_order_is_an_alias_for_watched_through_order(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """POST with the legacy visible_until_order=2 behaves identically to
    watched_through_order=2 (PROG-04 backward compatibility)."""
    legacy = client.post(
        "/api/series/series_dexter/progress", json={"visible_until_order": 2}
    )
    modern = client.post(
        "/api/series/series_dexter/progress", json={"watched_through_order": 2}
    )
    assert legacy.status_code == modern.status_code == 200
    for body in (legacy.json(), modern.json()):
        assert body["watched_through_order"] == 2
        assert body["view_as_of_order"] == 2
        assert body["effective_view_order"] == 2
        assert body["visible_until_order"] == 2


def test_earlier_selection_changes_only_view_as_of_order_never_watched(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """PROG-01: selecting an earlier already-watched episode changes only
    view_as_of_order and never lowers watched_through_order."""
    assert (
        client.post(
            "/api/series/series_dexter/progress", json={"watched_through_order": 2}
        ).status_code
        == 200
    )
    confirmed = client.post(
        "/api/series/series_dexter/progress",
        json={"watched_through_order": 3, "view_as_of_order": 3},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["effective_view_order"] == 3

    # View-only move back to 1: watched stays 3, effective becomes 1.
    moved = client.post(
        "/api/series/series_dexter/progress", json={"view_as_of_order": 1}
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["watched_through_order"] == 3
    assert body["view_as_of_order"] == 1
    assert body["effective_view_order"] == 1

    # The persisted record agrees on a fresh read.
    got = client.get("/api/series/series_dexter/progress").json()
    assert got["watched_through_order"] == 3
    assert got["view_as_of_order"] == 1
    assert got["effective_view_order"] == 1


def test_non_persisted_watched_through_order_is_rejected(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """D-06: the frontend cannot submit arbitrary hidden orders — the order
    must be a persisted episode order of the series."""
    for bad_order in (4, 99):
        response = client.post(
            "/api/series/series_dexter/progress",
            json={"watched_through_order": bad_order},
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"


def test_view_as_of_order_above_watched_through_order_is_rejected(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """D-05 invariant 1 <= view_as_of_order <= watched_through_order."""
    response = client.post(
        "/api/series/series_dexter/progress",
        json={"watched_through_order": 2, "view_as_of_order": 3},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"


def test_cross_series_progress_update_is_rejected(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """Updating progress against a series that does not exist is rejected with
    the generic not-found envelope (indistinguishable from any missing
    resource)."""
    response = client.post(
        "/api/series/series_does_not_exist_at_all/progress",
        json={"watched_through_order": 1},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_view_only_change_without_existing_record_is_generic_404(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    """A view-only change for a user with no persisted record has nothing to
    move — generic not-found, never an invented boundary."""
    response = client.post(
        "/api/series/series_dexter/progress", json={"view_as_of_order": 1}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_progress_update_rejects_both_boundary_fields_together(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = client.post(
        "/api/series/series_dexter/progress",
        json={"watched_through_order": 2, "visible_until_order": 2},
    )
    assert response.status_code == 422


LEGACY_PROGRESS_SEED_QUERY = """\
MERGE (u:AppUser {id: $uid})
MERGE (s:Series {id: $sid})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $uid, series_id: $sid})
ON CREATE SET p.id = $pid, p.created_at = datetime()
SET p.visible_until_order = $legacy, p.updated_at = datetime()
MERGE (p)-[:FOR_SERIES]->(s)
"""


def test_migration_backfills_split_fields_and_is_idempotent() -> None:
    """D-07: the migration seeds watched_through_order and view_as_of_order
    from the existing visible_until_order on records missing the new
    properties; running it twice changes nothing (idempotent, no deletes).

    A dedicated driver + ONE event loop for the whole test: the driver's
    pooled connections must never cross event loops (runbook rule), so every
    DB touch — seed, migrate, read, cleanup — happens inside one ``_run``.
    """
    user_id = f"user:migration-{uuid4()}"
    series_id = "series_dexter"

    async def _go() -> None:
        db = helper_db()
        repo = ProgressRepository(db)
        await db.execute_query(
            LEGACY_PROGRESS_SEED_QUERY,
            uid=user_id,
            sid=series_id,
            pid=f"progress:legacy-{uuid4()}",
            legacy=2,
        )

        await repo.ensure_migrated()
        first = await repo.get(user_id, series_id)
        assert first is not None
        assert first.watched_through_order == 2
        assert first.view_as_of_order == 2
        assert first.effective_view_order == 2
        assert first.visible_until_order == 2

        # Second run: identical state, no duplicate rows, no drift.
        await repo.ensure_migrated()
        second = await repo.get(user_id, series_id)
        assert second is not None
        assert second.model_dump() == first.model_dump()

        await db.execute_query(
            "MATCH (p:UserSeriesProgress {user_id: $uid}) DETACH DELETE p",
            uid=user_id,
        )
        await db.execute_query(
            "MATCH (u:AppUser {id: $uid}) DETACH DELETE u", uid=user_id
        )

    run_async(_go)
