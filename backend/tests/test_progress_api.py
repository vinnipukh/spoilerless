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

from backend.app.api import deps
from backend.app.api.progress import router as progress_router
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.session import InMemorySessionRepository
from backend.app.services.auth import AuthService


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


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db

    # Clean up test-created progress nodes (fresh driver + loop — the app
    # driver's connections live in TestClient's portal loop).
    async def _cleanup() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query("MATCH (n:UserSeriesProgress) DETACH DELETE n")
        finally:
            await clean.close()

    asyncio.run(_cleanup())


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
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo)

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

    async def _cleanup() -> None:
        db = Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                "MATCH (p:UserSeriesProgress {user_id: $uid}) DETACH DELETE p",
                uid=user_id,
            )
            await db.execute_query(
                "MATCH (u:AppUser {id: $uid}) DETACH DELETE u", uid=user_id
            )
        finally:
            await db.close()

    asyncio.run(_cleanup())


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
    assert response.json()["detail"]["code"] == "resource_not_found"


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
    assert response.json()["detail"]["code"] == "resource_not_found"


def test_post_progress_rejects_non_positive_boundary(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = _set_progress(client, "series_dexter", 0)
    assert response.status_code == 422

    response = _set_progress(client, "series_dexter", -1)
    assert response.status_code == 422


def test_progress_never_accepts_extra_fields(
    client: TestClient, authed_user: dict[str, Any]
) -> None:
    response = client.post(
        "/api/series/series_dexter/progress",
        json={"visible_until_order": 1, "user_id": "attacker"},
    )
    assert response.status_code == 422
