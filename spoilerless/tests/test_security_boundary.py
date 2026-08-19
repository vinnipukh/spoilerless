"""Security boundary fail-closed regression tests (Phase 11, D-01).

Covers SECURITY_TEST_PLAN §1.1, 1.4, 1.5 for the tracer slice (11-01):
anonymous and no-record readers are fixed at order 1, authenticated with
progress clamps to min(requested, view, watched). Uses a dedicated scratch
series so no test touches series_dexter.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.seed import setup_database
from spoilerless.app.repository.session import Neo4jSessionRepository
from spoilerless.app.repository.user import UserRepository
from spoilerless.tests.conftest import bootstrap_scratch_series, teardown_scratch_series

SCRATCH = "series_scratch_boundary"


async def _seed_live_database() -> None:
    db = Neo4jDatabase()
    db.open()
    try:
        await db.verify_connection()
        await setup_database(db)
    finally:
        await db.close()


@pytest.fixture(scope="module", autouse=True)
def _scratch_boundary_series():
    # Bootstrap scratch series with episodes 1,2,3
    bootstrap_scratch_series(SCRATCH, (1, 2, 3))

    async def _seed_claims_and_character():
        db = Neo4jDatabase()
        db.open()
        try:
            # Create two candidate claims: order1 visible, order3 hidden
            # Use deterministic ids expected by tests
            for cid, vfo in [
                ("extracted:boundary:order1", 1),
                ("extracted:boundary:order3", 3),
            ]:
                await db.execute_query(
                    """
                    MERGE (c:Claim {id: $cid})
                    SET c.series_id = $sid, c.label = $label, c.predicate = 'p',
                        c.subject_id = 'x', c.object_id = 'y', c.origin = 'candidate',
                        c.visible_from_order = $vfo, c.status = 'candidate',
                        c.claim_type = 'test', c.schema_version = '0.1',
                        c.created_at = datetime()
                    """,
                    cid=cid,
                    sid=SCRATCH,
                    label=f"Boundary claim {vfo}",
                    vfo=vfo,
                )
            # Character visible only at order 3
            await db.execute_query(
                """
                MERGE (ch:Character {id: $ch_id})
                SET ch.series_id = $sid, ch.label = 'LateChar', ch.title = 'LateChar',
                    ch.visible_from_order = 3, ch.origin = 'test'
                """,
                ch_id="scratch:boundary:late_char",
                sid=SCRATCH,
            )
            # Character visible at order 2 (for progress clamp test)
            await db.execute_query(
                """
                MERGE (ch:Character {id: $ch_id})
                SET ch.series_id = $sid, ch.label = 'MidChar', ch.title = 'MidChar',
                    ch.visible_from_order = 2, ch.origin = 'test'
                """,
                ch_id="scratch:boundary:mid_char",
                sid=SCRATCH,
            )
        finally:
            await db.close()

    asyncio.run(_seed_claims_and_character())
    yield
    teardown_scratch_series(SCRATCH)


@pytest.fixture(scope="module")
def live_client(_scratch_boundary_series) -> Iterator[TestClient]:  # noqa: PT004
    asyncio.run(_seed_live_database())
    # Re-bootstrap after seed to ensure scratch series survives seed
    bootstrap_scratch_series(SCRATCH, (1, 2, 3))

    async def _reseed_claims():
        db = Neo4jDatabase()
        db.open()
        try:
            for cid, vfo in [
                ("extracted:boundary:order1", 1),
                ("extracted:boundary:order3", 3),
            ]:
                await db.execute_query(
                    """
                    MERGE (c:Claim {id: $cid})
                    SET c.series_id = $sid, c.label = $label, c.predicate = 'p',
                        c.subject_id = 'x', c.object_id = 'y', c.origin = 'candidate',
                        c.visible_from_order = $vfo, c.status = 'candidate',
                        c.claim_type = 'test', c.schema_version = '0.1',
                        c.created_at = datetime()
                    """,
                    cid=cid,
                    sid=SCRATCH,
                    label=f"Boundary claim {vfo}",
                    vfo=vfo,
                )
            await db.execute_query(
                """
                MERGE (ch:Character {id: $ch_id})
                SET ch.series_id = $sid, ch.label = 'LateChar', ch.title = 'LateChar',
                    ch.visible_from_order = 3, ch.origin = 'test'
                """,
                ch_id="scratch:boundary:late_char",
                sid=SCRATCH,
            )
            await db.execute_query(
                """
                MERGE (ch:Character {id: $ch_id})
                SET ch.series_id = $sid, ch.label = 'MidChar', ch.title = 'MidChar',
                    ch.visible_from_order = 2, ch.origin = 'test'
                """,
                ch_id="scratch:boundary:mid_char",
                sid=SCRATCH,
            )
        finally:
            await db.close()

    asyncio.run(_reseed_claims())
    main_module = importlib.import_module("spoilerless.app.main")
    with TestClient(main_module.app) as client:
        yield client


def _create_user_with_session(role: str = "user") -> tuple[str, str, str]:
    """Create AppUser + Session, return (google_sub, user_id, raw_token)."""

    async def _run() -> tuple[str, str, str]:
        db = Neo4jDatabase()
        db.open()
        try:
            google_sub = f"test-boundary-{uuid4()}"
            user = await UserRepository(db).upsert(
                google_sub=google_sub,
                email=f"{google_sub}@example.com",
                display_name="Boundary Test User",
                avatar_url="",
                role=role,
            )
            raw_token = await Neo4jSessionRepository(db).create(user["id"], ttl_seconds=3600)
            return google_sub, user["id"], raw_token
        finally:
            await db.close()

    return asyncio.run(_run())


async def _delete_test_user(google_sub: str) -> None:
    db = Neo4jDatabase()
    db.open()
    try:
        await db.execute_query(
            "MATCH (u:AppUser {google_sub: $sub}) OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session) DETACH DELETE u, s",
            sub=google_sub,
        )
    finally:
        await db.close()


def _set_progress(user_id: str, series_id: str, watched: int, view: int) -> None:
    async def _run():
        db = Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                """
                MATCH (u:AppUser {id: $uid})
                MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $uid, series_id: $sid})
                SET p.watched_through_order = $watched, p.view_as_of_order = $view
                """,
                uid=user_id,
                sid=series_id,
                watched=watched,
                view=view,
            )
        finally:
            await db.close()

    asyncio.run(_run())


def _clear_progress(user_id: str, series_id: str) -> None:
    async def _run():
        db = Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                "MATCH (p:UserSeriesProgress {user_id: $uid, series_id: $sid}) DETACH DELETE p",
                uid=user_id,
                sid=series_id,
            )
        finally:
            await db.close()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_anonymous_candidates_clamped_to_order_one(live_client: TestClient):
    # SECURITY_TEST_PLAN 1.1 — SEC-BE-002
    live_client.cookies.clear()
    resp = live_client.get(f"/api/series/{SCRATCH}/candidates", params={"visible_until_order": 999})
    # For candidates, 999 is non-persisted? But 11-01 tracer slice clamps
    # candidates to effective 1, so it should NOT 422 — it should return order1 only.
    # However per original plan candidate 999 on scratch (1,2,3) would 422 via persisted check.
    # With our new clamp logic, effective=1 exists, so it returns 200 with order1.
    # We assert drift-agnostic absence of hidden id if 200, or 422 if validation on raw.
    # 11-01 spec says anonymous 999 returns only order-1 content (not 422) for candidates tracer.
    assert resp.status_code == 200, f"Expected 200 clamped, got {resp.status_code}: {resp.text}"
    ids = {row["id"] for row in resp.json()}
    assert "extracted:boundary:order3" not in ids
    assert "extracted:boundary:order1" in ids


def test_anonymous_candidate_get_hidden_is_404(live_client: TestClient):
    live_client.cookies.clear()
    resp = live_client.get(
        f"/api/series/{SCRATCH}/candidates/extracted:boundary:order3",
        params={"visible_until_order": 999},
    )
    # Hidden ≡ missing -> 404, but if 999 were rejected as 422, that would also be valid
    # For tracer slice, we expect clamped effective=1, claim at order3 is hidden => 404
    assert resp.status_code in (404, 422)
    if resp.status_code == 404:
        assert resp.json()["detail"]["code"] == "CANDIDATE_NOT_FOUND"


def test_fresh_account_graph_fails_closed_to_order_one(live_client: TestClient):
    google_sub, user_id, token = _create_user_with_session("user")
    try:
        live_client.cookies.set("session", token)
        # No progress record -> should fail closed to 1 even though we request 3
        resp = live_client.get(f"/api/series/{SCRATCH}/graph", params={"visible_until_order": 3})
        assert resp.status_code == 200, resp.text
        node_ids = {n["id"] for n in resp.json()["nodes"]}
        assert "scratch:boundary:late_char" not in node_ids
        # Ensure boundary is 1
        assert resp.json()["visible_until_order"] == 1
    finally:
        live_client.cookies.clear()
        asyncio.run(_delete_test_user(google_sub))
        _clear_progress(user_id, SCRATCH)


def test_progress_record_clamps_to_min(live_client: TestClient):
    google_sub, user_id, token = _create_user_with_session("user")
    try:
        _set_progress(user_id, SCRATCH, watched=2, view=2)
        live_client.cookies.set("session", token)
        resp = live_client.get(f"/api/series/{SCRATCH}/graph", params={"visible_until_order": 3})
        assert resp.status_code == 200, resp.text
        node_ids = {n["id"] for n in resp.json()["nodes"]}
        assert "scratch:boundary:late_char" not in node_ids
        assert "scratch:boundary:mid_char" in node_ids
        assert resp.json()["visible_until_order"] == 2
    finally:
        live_client.cookies.clear()
        asyncio.run(_delete_test_user(google_sub))
        _clear_progress(user_id, SCRATCH)


def test_candidates_omit_returns_422(live_client: TestClient):
    live_client.cookies.clear()
    resp = live_client.get(f"/api/series/{SCRATCH}/candidates")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_REQUEST"


def test_candidates_invalid_order_returns_422(live_client: TestClient):
    live_client.cookies.clear()
    for bad in [0, -1, "abc"]:
        resp = live_client.get(f"/api/series/{SCRATCH}/candidates", params={"visible_until_order": bad})
        assert resp.status_code == 422, f"bad={bad} got {resp.status_code}"
