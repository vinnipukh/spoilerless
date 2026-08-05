"""Integration tests for candidate ingest, storage isolation, and spoiler filtering (PREP-02, PREP-05)."""

import asyncio
import importlib
import json
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.seed import setup_database
from spoilerless.app.repository.session import Neo4jSessionRepository
from spoilerless.app.repository.user import UserRepository
from spoilerless.tests.conftest import (
    CANDIDATE_SCRATCH_SERIES,
    bootstrap_scratch_series,
    teardown_scratch_series,
)

FIXTURE_PATH = Path("data/dexter/test/extraction_fixture.json")


async def _seed_live_database() -> None:
    """Seed the database for integration tests, matching existing test pattern."""
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()


@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    """Returns a TestClient connected to a live Neo4j instance.

    The scratch series is bootstrapped before the app starts so the
    candidate boundary-validation (D-09) resolves against its own persisted
    episodes, and torn down (series rows + candidate residue + progress
    rows) after the module — the suite never writes to the live seeded
    series (PROB-06/22, #14/#46).
    """
    asyncio.run(_seed_live_database())
    try:
        bootstrap_scratch_series(CANDIDATE_SCRATCH_SERIES)
        main_module = importlib.import_module("spoilerless.app.main")
        with TestClient(main_module.app) as client:
            yield client
    finally:
        teardown_scratch_series(CANDIDATE_SCRATCH_SERIES)


def _create_user_with_session(role: str = "user") -> tuple[str, str]:
    """Create an :AppUser + :Session row via a fresh driver/loop.

    Returns ``(google_sub, raw_token)``. Candidate ingest is auth-gated
    (09-03, PROB-01) — the cookie set from the raw token authenticates the
    ingest/list requests.
    """

    async def _run() -> tuple[str, str]:
        db = Neo4jDatabase()
        db.open()
        try:
            google_sub = f"test-ingest-{uuid4()}"
            user = await UserRepository(db).upsert(
                google_sub=google_sub,
                email=f"{google_sub}@example.com",
                display_name="Ingest Test User",
                avatar_url="",
                role=role,
            )
            raw_token = await Neo4jSessionRepository(db).create(
                user["id"], ttl_seconds=3600
            )
            return google_sub, raw_token
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


@pytest.fixture
def user_session(live_client: TestClient) -> Iterator[str]:
    """Authenticated session cookie for ingest (auth-gated since 09-03)."""
    google_sub, raw_token = _create_user_with_session("user")
    live_client.cookies.set("session", raw_token)
    yield google_sub
    asyncio.run(_delete_test_user(google_sub))


@pytest.fixture
def extraction_fixture() -> dict:
    """Load the extraction fixture JSON."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


class TestCandidateIngest:
    """PREP-02: Candidate claim ingest and storage."""

    SERIES_ID = CANDIDATE_SCRATCH_SERIES

    def test_ingest_creates_candidate_claims(self, live_client: TestClient, user_session: str, extraction_fixture: dict):
        """Ingesting the fixture creates Claim nodes with origin: 'candidate'."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "created" in data
        assert len(data["created"]) == len(extraction_fixture["claims"])
        assert all(cid.startswith("extracted:") for cid in data["created"])

    def test_ingest_is_idempotent(self, live_client: TestClient, user_session: str, extraction_fixture: dict):
        """Re-ingesting the same fixture returns same IDs without errors."""
        r1 = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data1 = r1.json()

        r2 = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data2 = r2.json()

        assert data1["created"] == data2["created"]
        assert data2["errors"] == []

    def test_ingested_claims_appear_in_list(self, live_client: TestClient, user_session: str, extraction_fixture: dict):
        """Ingested claims are visible via the list endpoint."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data = response.json()
        claim_id = data["created"][0]

        list_response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates",
            params={"visible_until_order": 3},
        )
        assert list_response.status_code == 200
        candidates = list_response.json()
        ids = [c["id"] for c in candidates]
        assert claim_id in ids

    def test_ingested_claims_have_candidate_origin(self, live_client: TestClient, user_session: str, extraction_fixture: dict):
        """Ingested claims have origin: 'candidate' verified via get endpoint."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data = response.json()
        claim_id = data["created"][0]

        get_response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates/{claim_id}",
            params={"visible_until_order": 3},
        )
        assert get_response.status_code == 200

    def test_invalid_payload_returns_422(self, live_client: TestClient, user_session: str):
        """A malformed extraction payload returns 422."""
        bad_payload = {"extractor_name": "test", "extractor_version": "1.0", "run_timestamp": "bad-date", "claims": []}
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=bad_payload,
        )
        assert response.status_code == 422

    def test_candidate_not_found_returns_404(self, live_client: TestClient):
        """A non-existent candidate claim returns 404."""
        response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id",
            params={"visible_until_order": 3},
        )
        assert response.status_code == 404


class TestCandidateReadBoundary:
    """PROB-05/#13: candidate list/get require a RESOLVED spoiler boundary —
    an omitted boundary never defaults to every visibility level."""

    SERIES_ID = CANDIDATE_SCRATCH_SERIES

    def test_list_omitted_boundary_returns_422(self, live_client: TestClient):
        response = live_client.get(f"/api/series/{self.SERIES_ID}/candidates")
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"

    def test_get_omitted_boundary_returns_422(self, live_client: TestClient):
        response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates/some-claim-id"
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"

    def test_list_nonpersisted_boundary_returns_422(self, live_client: TestClient):
        """A boundary that is not a persisted episode order is rejected like
        the graph read path (D-09)."""
        response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates",
            params={"visible_until_order": 999},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"

    def test_get_above_boundary_reads_as_missing(self, live_client: TestClient):
        """A claim whose reveal point is above the resolved boundary reads as
        404 (D-15 — hidden and missing are indistinguishable).

        The claim is seeded directly via Cypher (scratch id + teardown) so the
        test is independent of the ingest-auth posture and of leftover data.
        """
        import asyncio
        from uuid import uuid4

        from spoilerless.app.graph.database import Neo4jDatabase

        claim_id = f"extracted:09-04-boundary:{uuid4().hex[:12]}"

        async def _seed() -> None:
            db = Neo4jDatabase()
            db.open()
            try:
                await db.execute_query(
                    "CREATE (c:Claim {id: $cid, series_id: $sid, origin: 'candidate', "
                    "visible_from_order: 2, label: 'Boundary probe claim', "
                    "created_at: timestamp()})",
                    cid=claim_id,
                    sid=self.SERIES_ID,
                )
            finally:
                await db.close()

        async def _cleanup() -> None:
            db = Neo4jDatabase()
            db.open()
            try:
                await db.execute_query(
                    "MATCH (c:Claim {id: $cid}) DETACH DELETE c", cid=claim_id
                )
            finally:
                await db.close()

        asyncio.run(_seed())
        try:
            hidden = live_client.get(
                f"/api/series/{self.SERIES_ID}/candidates/{claim_id}",
                params={"visible_until_order": 1},
            )
            assert hidden.status_code == 404
            assert hidden.json()["detail"]["code"] == "CANDIDATE_NOT_FOUND"

            visible = live_client.get(
                f"/api/series/{self.SERIES_ID}/candidates/{claim_id}",
                params={"visible_until_order": 2},
            )
            assert visible.status_code == 200
            assert visible.json()["id"] == claim_id
        finally:
            asyncio.run(_cleanup())
