"""Route-level tests for the series API (PROB-18/#40).

Exercises list/get episodes with the post-09-04 anonymous-boundary rules
(anonymous clamped to boundary 1 — PROB-04/#12). Uses the live DB client
pattern from test_episode_masking.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.seed import setup_database


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


def test_series_list_returns_dexter(live_client: TestClient) -> None:
    response = live_client.get("/api/series")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert "series_dexter" in ids


def test_series_get_unknown_returns_404(live_client: TestClient) -> None:
    response = live_client.get("/api/series/unknown-series")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERIES_NOT_FOUND"


def test_anonymous_episode_list_is_clamped_to_boundary_one(
    live_client: TestClient,
) -> None:
    """PROB-04/#12: an anonymous request above boundary 1 must yield
    boundary-1 content — the client-chosen boundary never widens the spoiler
    window without a session."""
    baseline = live_client.get(
        "/api/series/series_dexter/episodes", params={"visible_until_order": 1}
    )
    widened = live_client.get(
        "/api/series/series_dexter/episodes", params={"visible_until_order": 3}
    )
    assert baseline.status_code == widened.status_code == 200
    baseline_episodes = {e["id"]: e for e in baseline.json()}
    widened_episodes = {e["id"]: e for e in widened.json()}
    assert baseline_episodes.keys() == widened_episodes.keys()
    # Both serve the boundary-1 masking (episode 2 masked identically).
    assert baseline_episodes["dexter_s01e02"]["display_title"] == (
        widened_episodes["dexter_s01e02"]["display_title"]
    )
    assert baseline_episodes["dexter_s01e02"]["is_unlocked"] is False


def test_episode_list_unknown_series_returns_404(live_client: TestClient) -> None:
    response = live_client.get(
        "/api/series/unknown-series/episodes", params={"visible_until_order": 1}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERIES_NOT_FOUND"
