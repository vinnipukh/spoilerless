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

from spoilerless.app.core.config import get_settings
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.session import Neo4jSessionRepository

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


@pytest.mark.asyncio
async def test_same_second_sessions_have_distinct_ids(database: Neo4jDatabase) -> None:
    """PROB-03/#32: two sessions created in the same second must both succeed
    with distinct ids — the old ``session:{user_id}:{int(now)}`` scheme
    collided against the session_id unique constraint."""
    await database.execute_query(
        "CREATE (u:AppUser {id: $uid, google_sub: $sub, email: $email, "
        "display_name: $name, avatar_url: '', created_at: $now, updated_at: $now})",
        uid=TEST_USER_ID,
        sub=f"sub-{uuid4()}",
        email="session-repo-test@example.com",
        name="Session Repo Test",
        now=int(time.time()),
    )

    repo = Neo4jSessionRepository(database)
    token_a = await repo.create(TEST_USER_ID, ttl_seconds=3600)
    token_b = await repo.create(TEST_USER_ID, ttl_seconds=3600)

    # Both raw tokens resolve to distinct rows (no constraint collision).
    record_a = await repo.get(token_a)
    record_b = await repo.get(token_b)
    assert record_a is not None and record_b is not None
    assert record_a.hashed_token != record_b.hashed_token

    rows = await database.execute_query(
        "MATCH (u:AppUser {id: $uid})-[:HAS_SESSION]->(s:Session) "
        "RETURN s.id AS id ORDER BY s.id",
        uid=TEST_USER_ID,
    )
    ids = [row["id"] for row in rows]
    assert len(ids) == 2
    assert len(set(ids)) == 2  # distinct — the #32 regression


@pytest.mark.asyncio
async def test_refresh_does_not_extend_expiry(database: Neo4jDatabase) -> None:
    """PROB-03/#9: refresh bumps last_seen_at only — expires_at never slides."""
    await database.execute_query(
        "CREATE (u:AppUser {id: $uid, google_sub: $sub, email: $email, "
        "display_name: $name, avatar_url: '', created_at: $now, updated_at: $now})",
        uid=TEST_USER_ID,
        sub=f"sub-{uuid4()}",
        email="session-repo-test@example.com",
        name="Session Repo Test",
        now=int(time.time()),
    )

    repo = Neo4jSessionRepository(database)
    raw_token = await repo.create(TEST_USER_ID, ttl_seconds=3600)
    record_before = await repo.get(raw_token)
    assert record_before is not None

    await repo.refresh(raw_token, ttl_seconds=3600)
    record_after = await repo.get(raw_token)
    assert record_after is not None

    assert record_after.expires_at == record_before.expires_at
    assert record_after.last_seen_at >= record_before.last_seen_at


@pytest.mark.asyncio
async def test_sweep_removes_only_expired_and_revoked(database: Neo4jDatabase) -> None:
    """PROB-03/#9: sweep deletes expired/revoked sessions, keeps live ones."""
    await database.execute_query(
        "CREATE (u:AppUser {id: $uid, google_sub: $sub, email: $email, "
        "display_name: $name, avatar_url: '', created_at: $now, updated_at: $now})",
        uid=TEST_USER_ID,
        sub=f"sub-{uuid4()}",
        email="session-repo-test@example.com",
        name="Session Repo Test",
        now=int(time.time()),
    )

    repo = Neo4jSessionRepository(database)
    live_token = await repo.create(TEST_USER_ID, ttl_seconds=3600)
    expired_token = await repo.create(TEST_USER_ID, ttl_seconds=3600)
    revoked_token = await repo.create(TEST_USER_ID, ttl_seconds=3600)

    # Expire one session directly (created_at/expires_at in the past).
    await database.execute_query(
        "MATCH (s:Session {token_hash: $token_hash}) "
        "SET s.expires_at = $past",
        token_hash=__import__("hashlib").sha256(expired_token.encode()).hexdigest(),
        past=time.time() - 10,
    )
    # Revoke another.
    await repo.revoke(revoked_token)

    removed = await repo.sweep_expired()
    assert removed == 2

    assert await repo.get(live_token) is not None
    assert await repo.get(expired_token) is None
    assert await repo.get(revoked_token) is None

    # Idempotent: a second sweep removes nothing.
    assert await repo.sweep_expired() == 0
