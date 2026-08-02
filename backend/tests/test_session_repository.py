"""Integration test for the Neo4j-persistent session repository (T-AUTH-01).

Regression test for the HAS_SESSION relationship-direction bug: ``create()``
builds ``(:AppUser)-[:HAS_SESSION]->(:Session)`` and ``get()`` must traverse it
backwards (``(s)<-[:HAS_SESSION]-(u)``). The previous ``(s)-[:HAS_SESSION]->(u)``
direction never matched, so ``user_id`` came back ``None`` and every
authenticated request returned 401 — while all unit tests stayed green because
they use the in-memory repository.

This test runs against the real Neo4j database, exactly like the other live
integration tests (test_graph_api.py pattern: fresh driver + loop, cleanup in
teardown).
"""

from __future__ import annotations

import asyncio
import time
from typing import Iterator
from uuid import uuid4

import pytest

from backend.app.core.config import get_settings
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.session import Neo4jSessionRepository

TEST_USER_ID = f"user:session-repo-test:{uuid4()}"


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase(get_settings())
    db.open()
    yield db

    async def _cleanup() -> None:
        clean = Neo4jDatabase(get_settings())
        clean.open()
        try:
            await clean.execute_query(
                "MATCH (u:AppUser {id: $uid}) DETACH DELETE u", uid=TEST_USER_ID
            )
        finally:
            await clean.close()

    asyncio.run(_cleanup())


@pytest.mark.asyncio
async def test_neo4j_session_lookup_resolves_owner_user(database: Neo4jDatabase) -> None:
    now = int(time.time())
    await database.execute_query(
        "CREATE (u:AppUser {id: $uid, google_sub: $sub, email: $email, "
        "display_name: $name, avatar_url: '', created_at: $now, updated_at: $now})",
        uid=TEST_USER_ID,
        sub=f"sub-{uuid4()}",
        email="session-repo-test@example.com",
        name="Session Repo Test",
        now=now,
    )

    repo = Neo4jSessionRepository(database)
    raw_token = await repo.create(TEST_USER_ID, ttl_seconds=3600)

    record = await repo.get(raw_token)

    assert record is not None
    # Regression: user_id must be the owning user, not None (direction bug).
    assert record.user_id == TEST_USER_ID
