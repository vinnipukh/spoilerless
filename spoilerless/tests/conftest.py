from __future__ import annotations

import asyncio
import importlib
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spoilerless.app.graph.database import Neo4jDatabase  # noqa: E402
from spoilerless.app.graph.seed import setup_database  # noqa: E402


@pytest.fixture(autouse=True)
def _csrf_bypass_default(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Default the CSRF ``verify_origin`` guard to the wildcard bypass so
    API tests that don't care about origin validation pass without an
    Origin header (the documented test pattern; see test_auth.py).

    Runs before every test; CSRF-specific tests override
    ``FRONTEND_ORIGINS`` themselves via monkeypatch/setenv, which restores
    this value afterwards (monkeypatch semantics).  Skipped for
    ``test_config`` — its production-safe-defaults assertion must see the
    pristine unset-env default.
    """
    if "test_config" in request.node.module.__name__:
        return
    monkeypatch.setenv("FRONTEND_ORIGINS", "*")
    from spoilerless.app.core.config import get_settings

    get_settings.cache_clear()


class NoopGoogleVerifier:
    """AuthService requires a verifier (PROB-09/#77); tests that never
    exercise Google verification share this one no-op."""

    async def verify(self, credential: str, client_id: str) -> dict[str, object]:
        return {}

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


# ── Shared seeded live client (DRY: one re-seed per module, not per test) ──
# A full `setup_database` run against the shared live AuraDB takes ~12s, so a
# function-scoped fixture that re-seeds per test costs minutes per file (the
# 75-minute suite class). Seeding is idempotent (MERGE-based, proven by
# test_seed_idempotency), and the graph tests below are read-only, so one
# module-scoped seed + client is equivalent and ~N× faster.
async def seed_live_database() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()


@pytest.fixture
def live_client() -> Iterator[TestClient]:
    """TestClient over the freshly seeded main app.

    Function-scoped: the app's lifespan / ``get_database`` dependency
    interplay breaks when one client is shared across tests (driver left
    uninitialized on later requests), and tests set per-test cookies. The
    full re-seed per test is the price of isolation — seeding is ~12s.
    """
    asyncio.run(seed_live_database())
    main_module = importlib.import_module("spoilerless.app.main")
    with TestClient(main_module.app) as client:
        yield client


def cleanup_with_fresh_driver(
    queries: list[tuple[str, dict] | str],
) -> None:
    """Run teardown queries on their own short-lived driver+loop.

    Each entry is a bare Cypher string or a ``(query, params)`` pair. The
    app's driver connections live inside TestClient's portal loop and crash
    if reused cross-loop, so cleanup must never borrow the app driver.
    """

    async def _run() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            for entry in queries:
                if isinstance(entry, tuple):
                    query, params = entry
                    await clean.execute_query(query, **params)
                else:
                    await clean.execute_query(entry)
        finally:
            await clean.close()

    asyncio.run(_run())


def module_cleanup_fixture(queries: list[tuple[str, dict] | str]):
    """Factory for an autouse module-scoped teardown running ``queries`` once.

    Replaces the per-test ``database`` teardown that opened a second driver
    and re-ran the same DELETE set for every test (the suite's hidden cost:
    ~2-8 live queries × per test × per file).
    """

    @pytest.fixture(scope="module", autouse=True)
    def _cleanup_after_module() -> Iterator[None]:
        yield
        cleanup_with_fresh_driver(queries)

    return _cleanup_after_module


# ── Shared helper query runner (DRY: one driver + one loop for the suite) ──
# Test-body DB probes (``_fresh_query`` family) used to spawn a brand-new
# driver + loop per call, i.e. a fresh TLS handshake (~1s) per probe. A
# module-level asyncio.Runner keeps ONE loop, and the shared driver's pooled
# connections stay bound to it, so every probe after the first reuses the
# connection — suite-wide cost drops from N handshakes to 1. The app's own
# driver (inside TestClient's portal loop) is never touched here.
_HELPER_RUNNER = asyncio.Runner()
_HELPER_DB = Neo4jDatabase()


def run_query(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* on a fresh short-lived driver.

    The shared-driver variant caused intermittent read-after-write misses on
    AuraDB (probes missing app-driver writes, only in full-suite runs), so
    probes keep the original fresh-driver semantics: reliable, at the cost of
    one TLS handshake per probe.
    """

    async def _go() -> list[dict[str, Any]]:
        db = Neo4jDatabase()
        db.open()
        try:
            return await db.execute_query(query, **params)
        finally:
            await db.close()

    return asyncio.run(_go())


def helper_db() -> Neo4jDatabase:
    """The shared helper driver (connections live on the helper loop)."""
    _HELPER_DB.open()
    return _HELPER_DB


def run_async(coro_factory) -> Any:
    """Run a coroutine on the shared helper loop (e.g. service probes)."""
    return _HELPER_RUNNER.run(coro_factory())
