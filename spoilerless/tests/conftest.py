from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi import Request, Response

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spoilerless.app.graph.database import Neo4jDatabase  # noqa: E402

# ── Scratch-series isolation helpers (PROB-06/22, D-07) ──────────────────────
# Candidate/seed tests must never write to the live series_dexter graph (the
# #14/#15/#46 pollution class). A scratch series gets its own Series +
# Episode nodes so the candidate boundary-validation (D-09,
# api/candidates.py::_require_resolved_boundary) resolves against a persisted
# episode order; teardown deletes every node with the scratch series_id, any
# origin='candidate' residue (the #14 root cause), and any UserSeriesProgress
# rows the test created (progress rows carry series_id but no
# visible_from_order and trip the seed-integrity audit — the documented
# full-suite contamination path). Runs on a FRESH driver/loop so they are
# safe inside sync TestClient tests (never the app's portal-loop driver).
CANDIDATE_SCRATCH_SERIES = "series_scratch_candidates"
REVIEW_SCRATCH_SERIES = "series_scratch_review"


def bootstrap_scratch_series(
    series_id: str, episode_orders: tuple[int, ...] = (1, 2, 3)
) -> None:
    """Idempotently create the scratch :Series + :Episode nodes (fresh loop)."""

    async def _run() -> None:
        db = Neo4jDatabase()
        db.open()
        try:
            await db.verify_connection()
            await db.execute_query(
                "MERGE (s:Series {id: $series_id}) "
                "SET s.title = $title, s.slug = $slug, s.origin = 'test'",
                series_id=series_id,
                title=f"Scratch series {series_id}",
                slug=series_id.replace("series_scratch_", "scratch-"),
            )
            for order in episode_orders:
                await db.execute_query(
                    """
                    MERGE (e:Episode {id: $episode_id})
                    SET e.series_id = $series_id, e.code = $code, e.title = $title,
                        e.episode_order = $order, e.visible_from_order = $order,
                        e.origin = 'test'
                    WITH e
                    MATCH (s:Series {id: $series_id})
                    MERGE (e)-[:PART_OF {id: $part_of_id, series_id: $series_id,
                          visible_from_order: $order, origin: 'test'}]->(s)
                    """,
                    episode_id=f"{series_id}:episode:{order}",
                    series_id=series_id,
                    code=f"SCRATCH{order}",
                    title=f"Scratch Episode {order}",
                    order=order,
                    part_of_id=f"{series_id}:episode:{order}:part_of",
                )
        finally:
            await db.close()

    asyncio.run(_run())


def teardown_scratch_series(series_id: str) -> None:
    """Delete everything the scratch-series tests created (fresh loop).

    (a) every node under the scratch series_id (Series, Episode, Claims,
        Sources, EvidenceFragments, Revisions, and any progress rows),
    (b) any origin='candidate' residue left anywhere (the #14 root cause),
    (c) any UserSeriesProgress rows carrying the scratch series_id.
    """

    async def _run() -> None:
        db = Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                "MATCH (n {series_id: $series_id}) DETACH DELETE n",
                series_id=series_id,
            )
            await db.execute_query(
                "MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n"
            )
            await db.execute_query(
                "MATCH (p:UserSeriesProgress {series_id: $series_id}) "
                "DETACH DELETE p",
                series_id=series_id,
            )
        finally:
            await db.close()

    asyncio.run(_run())


@pytest.fixture(autouse=True)
def _disable_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize the Redis-backed RateLimiter dependency for every test.

    No test starts a live Redis (no ``REDIS_URL`` locally), so every
    ``RateLimiter(...)`` dependency on a rate-limited route would otherwise
    hit the library's uninitialized-limiter path. FastAPI resolves the
    dependency through the instance, which dispatches to the class
    ``__call__`` — patching it to a no-op keeps rate-limited routes testable
    without Redis. The limiter's own pure functions
    (``rate_limit_identifier`` / ``rate_limit_callback``) are unit-tested in
    ``test_rate_limit.py``, which does not exercise ``__call__``.
    """
    from spoilerless.app.services.rate_limit import RateLimiter

    async def _noop(request: Request, response: Response) -> None:
        return None

    monkeypatch.setattr(RateLimiter, "__call__", _noop)
