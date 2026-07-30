"""Integration tests for candidate review workflow: approve, reject, edit (PREP-03)."""

import asyncio
import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.seed import setup_database

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
    main_module = importlib.import_module("backend.app.main")
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


class TestCandidateApprove:
    """PREP-03: Candidate claim approval."""

    SERIES_ID = "series_dexter"

    def test_approve_returns_200(self, live_client: TestClient, ingested_claim_id: str):
        """Approving a candidate claim returns 200."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/approve",
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_approve_nonexistent_returns_404(self, live_client: TestClient):
        """Approving a non-existent claim returns 404."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id/approve",
        )
        assert response.status_code == 404


class TestCandidateReject:
    """PREP-03: Candidate claim rejection."""

    SERIES_ID = "series_dexter"

    def test_reject_returns_200(self, live_client: TestClient, ingested_claim_id: str):
        """Rejecting a candidate claim returns 200."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}/reject",
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_reject_nonexistent_returns_404(self, live_client: TestClient):
        """Rejecting a non-existent claim returns 404."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id/reject",
        )
        assert response.status_code == 404


class TestCandidateEdit:
    """PREP-03: Candidate claim edit (PATCH)."""

    SERIES_ID = "series_dexter"

    def test_edit_returns_200(self, live_client: TestClient, ingested_claim_id: str):
        """Editing a candidate claim returns 200."""
        response = live_client.patch(
            f"/api/series/{self.SERIES_ID}/candidates/{ingested_claim_id}",
            json={"confidence_level": "high"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_edit_nonexistent_returns_404(self, live_client: TestClient):
        """Editing a non-existent claim returns 404."""
        response = live_client.patch(
            f"/api/series/{self.SERIES_ID}/candidates/nonexistent-id",
            json={"confidence_level": "high"},
        )
        assert response.status_code == 404
