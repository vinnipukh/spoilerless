"""Phase 10-03 cache tests: visualization projection cache-aside (D-29).

Covers the ``viz:`` projection cache in ``spoilerless/app/cache/graph_cache.py``
introduced by 10-03 Task 1: key dimensions (series, effective order, view,
projection version, user scope), miss/hit round-trip, stale-metadata
rejection (T10-CACHE-02), poisoning resistance (T10-CACHE-03), no-op when
Redis is disabled, and Redis error degradation (bypass — a cache failure
must never surface as a request failure, T-08-06-02).

Task 2 (D-30) extends this file with the ``graph_revision`` epoch and the
GraphRAG focus signature dimensions.

No live Redis and no Neo4j: ``graph_cache.get_redis`` is pointed at an
in-memory ``_FakeRedis`` stand-in (the documented 08-06 pattern from
``test_graph_api.py``).
"""

from __future__ import annotations

from typing import Any

import pytest

from spoilerless.app.cache import graph_cache
from spoilerless.app.cache.graph_cache import (
    _visualization_cache_key,
    get_cached_visualization,
    set_cached_visualization,
)
from spoilerless.app.core.config import get_settings
from spoilerless.app.domain.visualization import PROJECTION_VERSION

FOCUS = "graphrag_focus"
FULL = "full"


class _FakeRedis:
    """In-memory stand-in for the shared ``redis.asyncio`` client.

    Mirrors the real client's byte values (decode_responses=False) and the
    surface graph_cache uses: get / setex / scan_iter / delete.
    """

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    async def setex(self, key: str, _ttl: int, value: str | bytes) -> None:
        self._store[key] = value.encode() if isinstance(value, str) else value

    async def scan_iter(self, match: str | None = None):
        prefix = match.split("*", 1)[0] if match else ""
        for key in list(self._store):
            if key.startswith(prefix):
                yield key

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)


def _enable_cache(monkeypatch: pytest.MonkeyPatch, fake: _FakeRedis) -> None:
    """Point graph_cache at a fake Redis and enable the cache guard."""
    monkeypatch.setattr(get_settings(), "redis_url", "rediss://fake:6379")
    monkeypatch.setattr(graph_cache, "get_redis", lambda: fake)


def _dto_payload(view: str = FULL, effective: int = 1) -> dict[str, Any]:
    """A minimal but valid VisualizationDTO payload for a key dimension."""
    return {
        "metadata": {
            "projection_version": PROJECTION_VERSION,
            "view_type": view,
            "series_id": "series_dexter",
            "series_title": "Dexter",
            "episode_order": effective,
            "visible_until_order": effective,
            "effective_view_order": effective,
        },
        "nodes": [],
        "edges": [],
        "groups": [],
        "timeline": [],
        "focus": None,
    }


def test_visualization_cache_key_separates_all_dimensions() -> None:
    key = _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None)
    assert key == f"viz:series_dexter:1:{FULL}:{PROJECTION_VERSION}:anon"
    # Series
    assert key != _visualization_cache_key("series_other", 1, FULL, PROJECTION_VERSION, None)
    # Effective boundary
    assert key != _visualization_cache_key("series_dexter", 2, FULL, PROJECTION_VERSION, None)
    # View type — a hit must never cross view types (D-30)
    assert key != _visualization_cache_key("series_dexter", 1, FOCUS, PROJECTION_VERSION, None)
    # Projection version
    assert key != _visualization_cache_key("series_dexter", 1, FULL, "9.9.9", None)
    # User scope
    assert key != _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, "user:1")
    assert _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, "user:1") == (
        f"viz:series_dexter:1:{FULL}:{PROJECTION_VERSION}:user:1"
    )


async def test_visualization_cache_miss_then_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload = _dto_payload()
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )

    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, payload)
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        == payload
    )


async def test_visualization_cache_rejects_stale_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T10-CACHE-02: a cached DTO whose metadata contradicts the request's
    key dimensions (version / view / effective order) is a miss."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    # Plant a payload under the full/1 key whose metadata claims a different
    # view and boundary (e.g. a poisoned or pre-refactor entry).
    stale = _dto_payload(view="episode_overview", effective=2)
    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, stale)

    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )


async def test_visualization_cache_rejects_poisoned_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T10-CACHE-03: invalid JSON and non-DTO JSON under a valid key are
    misses, never served."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    key = _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None)
    fake._store[key] = b"{not json"
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )

    fake._store[key] = b'{"nodes": "wrong shape"}'
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )


async def test_visualization_cache_noop_when_redis_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "redis_url", "")
    calls: list[object] = []
    monkeypatch.setattr(
        graph_cache, "get_redis", lambda: calls.append(object()) or _FakeRedis()
    )

    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )
    await set_cached_visualization(
        "series_dexter", 1, FULL, PROJECTION_VERSION, None, _dto_payload()
    )

    assert calls == []


async def test_visualization_cache_redis_error_bypasses_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-08-06-02/D-30: a Redis failure is a miss/bypass, never a request
    failure."""
    monkeypatch.setattr(get_settings(), "redis_url", "rediss://fake:6379")

    class _BrokenRedis:
        async def get(self, _key: str) -> bytes | None:
            raise RuntimeError("redis down")

        async def setex(self, *_args, **_kwargs) -> None:
            raise RuntimeError("redis down")

    monkeypatch.setattr(graph_cache, "get_redis", lambda: _BrokenRedis())

    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )
    # Write-through failure is swallowed too.
    await set_cached_visualization(
        "series_dexter", 1, FULL, PROJECTION_VERSION, None, _dto_payload()
    )
