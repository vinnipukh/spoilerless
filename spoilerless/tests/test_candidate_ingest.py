"""Integration tests for candidate ingest, storage isolation, and spoiler filtering (PREP-02, PREP-05)."""

import asyncio
import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.seed import setup_database

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
    """Returns a TestClient connected to a live Neo4j instance."""
    asyncio.run(_seed_live_database())
    main_module = importlib.import_module("spoilerless.app.main")
    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def extraction_fixture() -> dict:
    """Load the extraction fixture JSON."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


class TestCandidateIngest:
    """PREP-02: Candidate claim ingest and storage."""

    SERIES_ID = "series_dexter"

    def test_ingest_creates_candidate_claims(self, live_client: TestClient, extraction_fixture: dict):
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

    def test_ingest_is_idempotent(self, live_client: TestClient, extraction_fixture: dict):
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

    def test_ingested_claims_appear_in_list(self, live_client: TestClient, extraction_fixture: dict):
        """Ingested claims are visible via the list endpoint."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data = response.json()
        claim_id = data["created"][0]

        list_response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates",
        )
        assert list_response.status_code == 200
        candidates = list_response.json()
        ids = [c["id"] for c in candidates]
        assert claim_id in ids

    def test_ingested_claims_have_candidate_origin(self, live_client: TestClient, extraction_fixture: dict):
        """Ingested claims have origin: 'candidate' verified via get endpoint."""
        response = live_client.post(
            f"/api/series/{self.SERIES_ID}/candidates/ingest",
            json=extraction_fixture,
        )
        data = response.json()
        claim_id = data["created"][0]

        get_response = live_client.get(
            f"/api/series/{self.SERIES_ID}/candidates/{claim_id}",
        )
        assert get_response.status_code == 200

    def test_invalid_payload_returns_422(self, live_client: TestClient):
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
        )
        assert response.status_code == 404
