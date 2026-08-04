"""Integration tests for candidate review workflow: approve, reject, edit (PREP-03).

Since 08-03 (AUTH-03, T-08-03-01), approve/reject/edit require the admin
role, which is derived server-side from ADMIN_EMAILS at login — never from
any request body. These tests authenticate against the REAL app
(``spoilerless.app.main``) with real ``:AppUser`` + ``:Session`` rows created
through the production repositories on a FRESH driver/loop (never the app's
portal-loop driver — same cross-loop rule as test_chat_api.py) and removed
again in fixture teardown.
"""

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

FIXTURE_PATH = Path("data/dexter/test/extraction_fixture.json")


async def _seed_live_database() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()


@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    asyncio.run(_seed_live_database())
    main_module = importlib.import_module("spoilerless.app.main")
    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def ingested_claim_id(live_client: TestClient) -> str:
    """Ingest the fixture and return the first claim ID."""
    with open(FIXTURE_PATH) as f:
        fixture = json.load(f)
    response = live_client.post(
        "/api/series/series_dexter/candidates/ingest",
        json=fixture,
    )
    return response.json()["created"][0]


def _create_user_with_session(role: str) -> tuple[str, str]:
    """Create an :AppUser (with *role*) + :Session row via a fresh driver/loop.

    Returns ``(google_sub, raw_token)``. The app's ``require_current_user``
    resolves the same rows from the shared live DB at request time, so the
    cookie set from the returned raw token authenticates the request.
    """

    async def _run() -> tuple[str, str]:
        db = Neo4jDatabase()
        db.open()
        try:
            google_sub = f"test-{role}-{uuid4()}"
            user = await UserRepository(db).upsert(
                google_sub=google_sub,
                email=f"{google_sub}@example.com",
                display_name="Review Test User",
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
def admin_session(live_client: TestClient) -> Iterator[str]:
    google_sub, raw_token = _create_user_with_session("admin")
    live_client.cookies.set("session", raw_token)
    yield google_sub
    asyncio.run(_delete_test_user(google_sub))


@pytest.fixture
def user_session(live_client: TestClient) -> Iterator[str]:
    google_sub, raw_token = _create_user_with_session("user")
    live_client.cookies.set("session", raw_token)
    yield google_sub
    asyncio.run(_delete_test_user(google_sub))


class TestCandidateApprove:
    """PREP-03: Candidate claim approval — admin-gated since 08-03 (AUTH-03)."""

    SERIES_ID = "series_dexter"

    def test_approve_returns_200(
        self, live_client: TestClient, ingested_claim_id: str, admin_session: str
    ):
        """Approving a candidate claim as an admin returns 200."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/approve",
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_approve_nonexistent_returns_404(
        self, live_client: TestClient, admin_session: str
    ):
        """Approving a non-existent claim returns 404 (admin-authenticated)."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id/approve",
        )
        assert response.status_code == 404

    def test_approve_forbidden_for_non_admin(
        self, live_client: TestClient, ingested_claim_id: str, user_session: str
    ):
        """A non-admin user gets a clear 403 on approve (AUTH-03, T-08-03-01)."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/approve",
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["code"] == "forbidden"


class TestCandidateReject:
    """PREP-03: Candidate claim rejection — admin-gated since 08-03 (AUTH-03)."""

    SERIES_ID = "series_dexter"

    def test_reject_returns_200(
        self, live_client: TestClient, ingested_claim_id: str, admin_session: str
    ):
        """Rejecting a candidate claim as an admin returns 200."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/reject",
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_reject_nonexistent_returns_404(
        self, live_client: TestClient, admin_session: str
    ):
        """Rejecting a non-existent claim returns 404 (admin-authenticated)."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id/reject",
        )
        assert response.status_code == 404

    def test_reject_forbidden_for_non_admin(
        self, live_client: TestClient, ingested_claim_id: str, user_session: str
    ):
        """A non-admin user gets a clear 403 on reject (AUTH-03, T-08-03-01)."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/reject",
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["code"] == "forbidden"


class TestCandidateEdit:
    """PREP-03: Candidate claim edit (PATCH) — admin-gated since 08-03 (AUTH-03)."""

    SERIES_ID = "series_dexter"

    def test_edit_returns_200(
        self, live_client: TestClient, ingested_claim_id: str, admin_session: str
    ):
        """Editing a candidate claim as an admin returns 200."""
        response = live_client.patch(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}",
            json={"confidence_level": "high"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_edit_nonexistent_returns_404(
        self, live_client: TestClient, admin_session: str
    ):
        """Editing a non-existent claim returns 404 (admin-authenticated)."""
        response = live_client.patch(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id",
            json={"confidence_level": "high"},
        )
        assert response.status_code == 404

    def test_edit_forbidden_for_non_admin(
        self, live_client: TestClient, ingested_claim_id: str, user_session: str
    ):
        """A non-admin user gets a clear 403 on edit (AUTH-03, T-08-03-01)."""
        response = live_client.patch(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}",
            json={"confidence_level": "high"},
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["code"] == "forbidden"
