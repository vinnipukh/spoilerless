from __future__ import annotations

import asyncio
from collections.abc import Iterator
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spoilerless.app.api import deps
from spoilerless.app.api import graph as graph_api
from spoilerless.app.api.share import router as share_router
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.api.exceptions import install_repository_error_handlers
from spoilerless.app.domain.share import ShareTokenRecord
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.seed import setup_database
from spoilerless.app.repository.share import (
    InMemoryShareRepository,
    _hash_token,
)


@pytest.mark.asyncio
async def test_share_repository_hash_storage_and_retrieval() -> None:
    repo = InMemoryShareRepository()
    creator = "user:creator123"

    raw_token, record = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=3,
        ttl_seconds=3600,
    )

    # Raw token is returned, but store has hash
    assert raw_token != record.token_hash
    assert record.token_hash == _hash_token(raw_token)
    assert record.series_id == "series_dexter"
    assert record.visible_until_order == 3
    assert record.created_by == creator
    assert record.revoked_at is None

    # Fetch by token_hash
    fetched = await repo.get_by_token_hash(record.token_hash)
    assert fetched is not None
    assert fetched.id == record.id

    # Fetch by raw_token
    fetched_raw = await repo.get_by_raw_token(raw_token)
    assert fetched_raw is not None
    assert fetched_raw.id == record.id


@pytest.mark.asyncio
async def test_share_repository_expiry_and_revocation() -> None:
    repo = InMemoryShareRepository()
    creator = "user:creator123"

    # Expired token
    raw_exp, rec_exp = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=1,
        ttl_seconds=-10,  # Already expired
    )
    assert rec_exp.is_expired
    assert await repo.get_by_token_hash(rec_exp.token_hash) is None
    assert await repo.get_by_raw_token(raw_exp) is None

    # Revoked token
    raw_rev, rec_rev = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=2,
        ttl_seconds=3600,
    )
    assert not rec_rev.is_revoked
    revoked_ok = await repo.revoke(rec_rev.token_hash)
    assert revoked_ok is True
    assert await repo.get_by_token_hash(rec_rev.token_hash) is None

    # Revoking non-existent / already revoked
    assert await repo.revoke("nonexistent") is False
    assert await repo.revoke(rec_rev.token_hash) is False


@pytest.mark.asyncio
async def test_share_repository_list_active_and_sweep() -> None:
    repo = InMemoryShareRepository()
    creator1 = "user:creator1"
    creator2 = "user:creator2"

    raw1, rec1 = await repo.create(creator1, "series_dexter", 1, ttl_seconds=3600)
    raw2, rec2 = await repo.create(creator1, "series_dexter", 2, ttl_seconds=3600)
    raw3, rec3 = await repo.create(creator2, "series_dexter", 3, ttl_seconds=3600)

    # list_active creator scoped
    c1_tokens = await repo.list_active(creator1)
    assert len(c1_tokens) == 2
    assert {t.id for t in c1_tokens} == {rec1.id, rec2.id}

    c2_tokens = await repo.list_active(creator2)
    assert len(c2_tokens) == 1
    assert c2_tokens[0].id == rec3.id

    # Revoke one of creator1's tokens
    await repo.revoke(rec1.token_hash)
    c1_active = await repo.list_active(creator1)
    assert len(c1_active) == 1
    assert c1_active[0].id == rec2.id

    # Sweep
    swept = await repo.sweep_expired()
    assert swept == 1  # rec1 was revoked


# ── Integration tests for Share API routes ──


async def _seed_database() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    asyncio.run(_seed_database())
    db = Neo4jDatabase()
    db.open()
    yield db


class _FakeProgressService:
    """In-memory progress stand-in for share-create clamp tests (CR-01)."""

    def __init__(self, record) -> None:
        self._record = record

    async def get(self, user_id: str, series_id: str):
        return self._record


def test_share_api_create_read_revoke_flow(database: Neo4jDatabase) -> None:
    app = FastAPI()
    repo = InMemoryShareRepository()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.include_router(share_router)

    mock_user = {
        "id": "user:share_tester",
        "email": "tester@example.com",
        "display_name": "Share Tester",
        "role": "user",
    }

    app.dependency_overrides[deps.get_database] = lambda: database
    app.dependency_overrides[deps.get_share_repo] = lambda: repo
    app.dependency_overrides[deps.require_current_user] = lambda: mock_user
    # CR-01: creator has watched through order 2, so boundary 2 is in-window.
    app.dependency_overrides[graph_api.get_progress_service] = lambda: (
        _FakeProgressService(
            type("R", (), {"view_as_of_order": 2, "watched_through_order": 2})()
        )
    )

    with TestClient(app) as client:
        # 1. Create a share link for boundary 2
        res = client.post(
            "/api/share",
            json={"series_id": "series_dexter", "visible_until_order": 2},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert "token" in data
        raw_token = data["token"]
        assert data["series_id"] == "series_dexter"
        assert data["visible_until_order"] == 2
        assert data["url"] == f"/share/{raw_token}"

        # 2. GET unauthenticated snapshot graph via share token
        graph_res = client.get(f"/api/share/{raw_token}/graph")
        assert graph_res.status_code == 200, graph_res.text
        graph_data = graph_res.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert graph_data["series"]["id"] == "series_dexter"
        assert graph_data["visible_until_order"] == 2

        # 3. GET list active share links for user
        list_res = client.get("/api/share")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 1
        assert items[0]["visible_until_order"] == 2

        # 4. Revoke token
        revoke_res = client.delete(f"/api/share/{raw_token}")
        assert revoke_res.status_code == 200
        assert revoke_res.json()["status"] == "revoked"

        # 5. GET snapshot graph after revocation -> 404
        revoked_graph_res = client.get(f"/api/share/{raw_token}/graph")
        assert revoked_graph_res.status_code == 404
        err = revoked_graph_res.json()
        assert err["detail"]["code"] == "TOKEN_NOT_FOUND"


def test_share_api_create_clamps_boundary_to_creator_progress(
    database: Neo4jDatabase,
) -> None:
    """CR-01 (09-REVIEW): a share token must never widen the creator's window.

    A creator who has only watched through order 1 cannot mint a token for
    order 60; the stored boundary must equal their effective view (1). A
    creator with no progress record at all fails closed to boundary 1.
    """
    app = FastAPI()
    repo = InMemoryShareRepository()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.include_router(share_router)

    mock_user = {"id": "user:clamp_tester", "email": "c@example.com", "role": "user"}
    app.dependency_overrides[deps.get_database] = lambda: database
    app.dependency_overrides[deps.get_share_repo] = lambda: repo
    app.dependency_overrides[deps.require_current_user] = lambda: mock_user

    with TestClient(app) as client:
        # Creator with progress at order 1 requests order 60 -> clamped to 1.
        app.dependency_overrides[graph_api.get_progress_service] = lambda: (
            _FakeProgressService(
                type("R", (), {"view_as_of_order": 1, "watched_through_order": 1})()
            )
        )
        res = client.post(
            "/api/share",
            json={"series_id": "series_dexter", "visible_until_order": 60},
        )
        assert res.status_code == 201, res.text
        assert res.json()["visible_until_order"] == 1

        # Creator with NO progress record fails closed to boundary 1.
        app.dependency_overrides[graph_api.get_progress_service] = lambda: (
            _FakeProgressService(None)
        )
        res = client.post(
            "/api/share",
            json={"series_id": "series_dexter", "visible_until_order": 2},
        )
        assert res.status_code == 201, res.text
        assert res.json()["visible_until_order"] == 1


def test_share_api_invalid_boundary_and_forbidden_revoke(database: Neo4jDatabase) -> None:
    app = FastAPI()
    repo = InMemoryShareRepository()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.include_router(share_router)

    user1 = {"id": "user:owner", "role": "user"}
    user2 = {"id": "user:other", "role": "user"}

    app.dependency_overrides[deps.get_database] = lambda: database
    app.dependency_overrides[deps.get_share_repo] = lambda: repo

    with TestClient(app) as client:
        # CR-01: an out-of-window episode order is clamped (fail-closed to the
        # creator's boundary — here no progress record => boundary 1), never
        # stored as requested.
        app.dependency_overrides[deps.require_current_user] = lambda: user1
        app.dependency_overrides[graph_api.get_progress_service] = lambda: (
            _FakeProgressService(None)
        )
        clamped_res = client.post(
            "/api/share",
            json={"series_id": "series_dexter", "visible_until_order": 999999},
        )
        assert clamped_res.status_code == 201
        assert clamped_res.json()["visible_until_order"] == 1

        # Valid create by user1
        create_res = client.post(
            "/api/share",
            json={"series_id": "series_dexter", "visible_until_order": 1},
        )
        token = create_res.json()["token"]

        # Attempt revoke by user2 -> 403 FORBIDDEN
        app.dependency_overrides[deps.require_current_user] = lambda: user2
        forbidden_res = client.delete(f"/api/share/{token}")
        assert forbidden_res.status_code == 403
        assert forbidden_res.json()["detail"]["code"] == "FORBIDDEN"
