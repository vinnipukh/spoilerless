"""Episode metadata masking tests (07-03 Task 2, META-01..03, D-05, D-21).

Proves the boundary-aware episodes API:
- generic D-08 label above the effective boundary, real title below it,
- ``is_unlocked`` / ``is_current_view`` correctness,
- the D-05 fail-closed formula (request above the persisted view is clamped),
- META-03 conservative fallback for missing title-safety metadata,
- META-02: no synopsis/runtime/image ever synthesized above the boundary.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time

import pytest
from fastapi.testclient import TestClient

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.services.series import SeriesService


class FakeDatabase:
    """In-memory stand-in returning canned SERIES_EPISODES_QUERY records."""

    def __init__(self, records: list[dict]) -> None:
        self._records = records

    async def execute_query(self, _query: str, **_parameters):
        return self._records


def _episode_record(
    episode_order: int,
    *,
    title: str,
    visible_from_order: int,
    code: str | None = None,
    season_number: int = 1,
    episode_number: int | None = None,
) -> dict:
    number = episode_number or episode_order
    return {
        "id": f"dexter_s01e{episode_order:02d}",
        "series_id": "series_dexter",
        "season_number": season_number,
        "episode_number": number,
        "episode_order": episode_order,
        "code": code or f"S01E{episode_order:02d}",
        "title": title,
        "visible_from_order": visible_from_order,
    }


# ── Anonymous boundary behavior ──


def test_boundary_one_masks_spoiler_sensitive_titles(live_client: TestClient) -> None:
    response = live_client.get(
        "/api/series/series_dexter/episodes", params={"visible_until_order": 1}
    )
    assert response.status_code == 200, response.text
    episodes = {e["episode_order"]: e for e in response.json()}

    episode_one = episodes[1]
    assert episode_one["display_title"] == "Dexter"
    assert episode_one["title"] == "Dexter"  # legacy field carries the masked value
    assert episode_one["is_unlocked"] is True
    assert episode_one["is_current_view"] is True

    episode_two = episodes[2]
    assert episode_two["display_title"] == "S01E02 — Episode 2"
    assert episode_two["title"] == "S01E02 — Episode 2"  # never the future title
    assert episode_two["is_unlocked"] is False
    assert episode_two["is_current_view"] is False

    episode_three = episodes[3]
    assert episode_three["display_title"] == "S01E03 — Episode 3"
    assert episode_three["is_unlocked"] is False

    # The future titles must not exist anywhere in the response (META-01).
    serialized = json.dumps(response.json(), sort_keys=True)
    assert "Crocodile" not in serialized
    assert "Popping Cherry" not in serialized


def test_high_boundary_returns_real_titles(live_client: TestClient) -> None:
    # PROB-04/#12: anonymous readers are clamped to boundary 1, so the
    # high-boundary probe authenticates with a matching progress record.
    raw = asyncio.run(_prepare_progress_fixture(watched=3, view=3))
    try:
        response = live_client.get(
            "/api/series/series_dexter/episodes",
            params={"visible_until_order": 3},
            headers={"Cookie": f"session={raw}"},
        )
        assert response.status_code == 200, response.text
        episodes = {e["episode_order"]: e for e in response.json()}

        assert episodes[1]["display_title"] == "Dexter"
        assert episodes[2]["display_title"] == "Crocodile"
        assert episodes[3]["display_title"] == "Popping Cherry"
        assert all(e["is_unlocked"] is True for e in episodes.values())
    finally:
        asyncio.run(_clean_progress_fixture(raw))


def test_unknown_series_episodes_returns_404(live_client: TestClient) -> None:
    response = live_client.get("/api/series/unknown/episodes")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERIES_NOT_FOUND"


# ── D-05 fail-closed effective boundary (authenticated) ──

MASKING_USER_ID = "user:07-03-masking"
MASKING_SUB = "07-03-masking-sub"

MASKING_SESSION_CLEANUP_QUERY = """
MATCH (s:Session {token_hash: $token_hash})
DETACH DELETE s
"""

MASKING_PROGRESS_CLEANUP_QUERY = """
MATCH (p:UserSeriesProgress {user_id: $uid})
DETACH DELETE p
"""

MASKING_USER_CLEANUP_QUERY = """
MATCH (u:AppUser {id: $uid})
DETACH DELETE u
"""

MASKING_SETUP_QUERY = """
MERGE (u:AppUser {id: $uid})
SET u.google_sub = $sub, u.email = $email, u.display_name = 'Masking Test'
MERGE (s:Series {id: 'series_dexter'})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $uid, series_id: 'series_dexter'})
SET p.id = $pid, p.created_at = $now, p.updated_at = $now,
    p.watched_through_order = $watched, p.view_as_of_order = $view,
    p.visible_until_order = $view
WITH u
CREATE (sess:Session {
    id: $session_id,
    token_hash: $token_hash,
    created_at: $now,
    expires_at: $now + $ttl,
    last_seen_at: $now,
    revoked_at: NULL
})
CREATE (u)-[:HAS_SESSION]->(sess)
"""


async def _prepare_progress_fixture(watched: int, view: int) -> str:
    """Create a user with (watched, view) progress plus a live session.

    Returns the raw session token; a fresh random token per run avoids the
    Session ``token_hash`` uniqueness constraint colliding with leftovers.
    """
    raw = f"07-03-masking-{secrets.token_hex(8)}"
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(MASKING_USER_CLEANUP_QUERY, uid=MASKING_USER_ID)
        await database.execute_query(
            MASKING_SETUP_QUERY,
            uid=MASKING_USER_ID,
            sub=MASKING_SUB,
            email="masking@test.local",
            pid=f"progress:{MASKING_USER_ID}",
            session_id=f"session:{MASKING_USER_ID}:test",
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            watched=watched,
            view=view,
            now=time.time(),
            ttl=float(3600),
        )
    finally:
        await database.close()
    return raw


async def _clean_progress_fixture(raw_token: str) -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.execute_query(
            MASKING_SESSION_CLEANUP_QUERY,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        )
        await database.execute_query(MASKING_PROGRESS_CLEANUP_QUERY, uid=MASKING_USER_ID)
        await database.execute_query(MASKING_USER_CLEANUP_QUERY, uid=MASKING_USER_ID)
    finally:
        await database.close()


def test_request_below_persisted_view_resolves_to_request(
    live_client: TestClient,
) -> None:
    """Persisted view=2, watched=3, request=1 -> effective 1 (only ep 1 unlocked)."""
    raw = asyncio.run(_prepare_progress_fixture(watched=3, view=2))
    try:
        response = live_client.get(
            "/api/series/series_dexter/episodes",
            params={"visible_until_order": 1},
            headers={"Cookie": f"session={raw}"},
        )
        assert response.status_code == 200, response.text
        episodes = {e["episode_order"]: e for e in response.json()}
        assert episodes[1]["is_unlocked"] is True
        assert episodes[1]["is_current_view"] is True
        assert episodes[2]["is_unlocked"] is False
        assert episodes[3]["is_unlocked"] is False
    finally:
        asyncio.run(_clean_progress_fixture(raw))


def test_request_above_persisted_view_is_fail_closed(live_client: TestClient) -> None:
    """D-05: persisted view=1, watched=3, request=3 -> effective 1, never 3.

    The request order is part of the min — a client asking above the selected
    view must NOT be served the watched boundary (the D-05 fail-closed rule).
    """
    raw = asyncio.run(_prepare_progress_fixture(watched=3, view=1))
    try:
        response = live_client.get(
            "/api/series/series_dexter/episodes",
            params={"visible_until_order": 3},
            headers={"Cookie": f"session={raw}"},
        )
        assert response.status_code == 200, response.text
        episodes = {e["episode_order"]: e for e in response.json()}
        assert episodes[1]["is_unlocked"] is True
        assert episodes[1]["is_current_view"] is True
        assert episodes[2]["display_title"] == "S01E02 — Episode 2"
        assert episodes[2]["is_unlocked"] is False
        assert episodes[3]["is_unlocked"] is False

        # Anonymous caller gets the FIXED boundary 1 (PROB-04/#12) — the
        # client-chosen request must never widen the spoiler window without
        # a session: request 3 resolves to effective 1.
        anon = live_client.get(
            "/api/series/series_dexter/episodes",
            params={"visible_until_order": 3},
        )
        anon_episodes = {e["episode_order"]: e for e in anon.json()}
        assert anon_episodes[2]["display_title"] == "S01E02 — Episode 2"
        assert anon_episodes[3]["is_unlocked"] is False
    finally:
        asyncio.run(_clean_progress_fixture(raw))


# ── Service-level masking rules (no DB writes) ──


@pytest.mark.asyncio
async def test_missing_title_safety_metadata_falls_back_to_generic_label() -> None:
    """META-03: a record without title_is_spoiler fails conservatively."""
    future = _episode_record(99, title="Future Title", visible_from_order=99)
    service = SeriesService(FakeDatabase([future]))  # type: ignore[arg-type]

    masked = await service.list_episodes("series_dexter", effective_view_order=1)
    assert masked[0]["display_title"] == "S01E99 — Episode 99"
    assert masked[0]["title"] == "S01E99 — Episode 99"
    assert masked[0]["is_unlocked"] is False

    unlocked = await service.list_episodes("series_dexter", effective_view_order=99)
    assert unlocked[0]["display_title"] == "Future Title"
    assert unlocked[0]["is_unlocked"] is True


@pytest.mark.asyncio
async def test_no_synopsis_runtime_image_above_boundary() -> None:
    """META-02: absent fields stay absent — nothing is ever synthesized."""
    records = [
        _episode_record(1, title="Dexter", visible_from_order=1),
        _episode_record(2, title="Crocodile", visible_from_order=2),
    ]
    service = SeriesService(FakeDatabase(records))  # type: ignore[arg-type]

    masked = await service.list_episodes("series_dexter", effective_view_order=1)
    for episode in masked:
        for forbidden in ("synopsis", "runtime", "image_url", "image_source_url"):
            assert forbidden not in episode, f"{forbidden} leaked in {episode}"


def test_live_response_has_no_synopsis_runtime_image_fields(
    live_client: TestClient,
) -> None:
    response = live_client.get(
        "/api/series/series_dexter/episodes", params={"visible_until_order": 1}
    )
    assert response.status_code == 200, response.text
    serialized = json.dumps(response.json(), sort_keys=True).lower()
    for forbidden in ("synopsis", "runtime", "image"):
        assert forbidden not in serialized, f"{forbidden!r} leaked in the response"
