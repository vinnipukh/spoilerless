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
    FOCUS_NONE_SIGNATURE,
    _visualization_cache_key,
    focus_signature,
    get_cached_visualization,
    invalidate_series,
    set_cached_visualization,
)
from spoilerless.app.core.config import get_settings
from spoilerless.app.domain.visualization import PROJECTION_VERSION

FOCUS = "graphrag_focus"
FULL = "full"

# Default key suffix for plain (non-focus) projections: epoch 0 + none.
_SIG = FOCUS_NONE_SIGNATURE


class _FakeRedis:
    """In-memory stand-in for the shared ``redis.asyncio`` client.

    Mirrors the real client's byte values (decode_responses=False) and the
    surface graph_cache uses: get / setex / scan_iter / delete / sismember / scard / sadd / expire.
    """

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._sets: dict[str, set[str]] = {}

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

    async def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())

    async def scard(self, key: str) -> int:
        return len(self._sets.get(key, set()))

    async def sadd(self, key: str, member: str) -> int:
        s = self._sets.setdefault(key, set())
        added = member not in s
        s.add(member)
        return 1 if added else 0

    async def expire(self, key: str, ttl: int) -> bool:
        return True

    async def incr(self, key: str) -> int:
        raw = self._store.get(key, b"0")
        try:
            value = int(raw) + 1
        except (TypeError, ValueError):
            value = 1
        self._store[key] = str(value).encode()
        return value


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
    key = _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None, 0, _SIG)
    assert key == f"viz:series_dexter:1:{FULL}:{PROJECTION_VERSION}:anon:0:{_SIG}"
    # Series
    assert key != _visualization_cache_key("series_other", 1, FULL, PROJECTION_VERSION, None, 0, _SIG)
    # Effective boundary
    assert key != _visualization_cache_key("series_dexter", 2, FULL, PROJECTION_VERSION, None, 0, _SIG)
    # View type — a hit must never cross view types (D-30)
    assert key != _visualization_cache_key("series_dexter", 1, FOCUS, PROJECTION_VERSION, None, 0, _SIG)
    # Projection version
    assert key != _visualization_cache_key("series_dexter", 1, FULL, "9.9.9", None, 0, _SIG)
    # User scope
    assert key != _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, "user:1", 0, _SIG)
    assert _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, "user:1", 0, _SIG) == (
        f"viz:series_dexter:1:{FULL}:{PROJECTION_VERSION}:user:1:0:{_SIG}"
    )
    # Epoch (D-30) — a new revision must never hit an old entry
    assert key != _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None, 1, _SIG)
    assert key != _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None, 7, _SIG)
    # Focus signature (D-30) — focus sets are a cache dimension
    sig_a = focus_signature(["char_1", "char_2"])
    assert key != _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None, 0, sig_a)
    assert sig_a != _SIG


def test_focus_signature_canonicalizes_order_and_duplicates() -> None:
    """D-30: reordered/duplicated focus sets share one signature; distinct
    sets and empty sets never collide; length-prefixing avoids joins."""
    assert focus_signature(["b", "a", "b"]) == focus_signature(["a", "b"])
    assert focus_signature(["a", "b"]) == focus_signature(["b", "a"])
    assert focus_signature(None) == _SIG
    assert focus_signature([]) == _SIG
    assert focus_signature(["a", "b"]) != focus_signature(["a"])
    assert focus_signature(["a", "b"]) != focus_signature(["ab"])
    # Length-prefix: ["a","bc"] must not collide with ["ab","c"]
    assert focus_signature(["a", "bc"]) != focus_signature(["ab", "c"])
    assert focus_signature(["char_1", "char_2"]) != focus_signature(["char_12", "char_"])


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

    key = _visualization_cache_key("series_dexter", 1, FULL, PROJECTION_VERSION, None, 0, _SIG)
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


async def test_epoch_initial_zero_and_bumped_on_invalidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-30: the epoch defaults to 0, and every invalidate_series call
    atomically increments it before deleting graph and projection keys."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload = _dto_payload()
    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, payload)
    assert fake._store.get("graph_revision:series_dexter") is None
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        == payload
    )

    await invalidate_series("series_dexter")
    assert fake._store["graph_revision:series_dexter"] == b"1"
    # Both the graph and projection keys were deleted.
    assert not any(k.startswith("graph:series_dexter:") for k in fake._store)
    assert not any(k.startswith("viz:series_dexter:") for k in fake._store)
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )

    await invalidate_series("series_dexter")
    assert fake._store["graph_revision:series_dexter"] == b"2"

    # A write after invalidation lands on the new epoch and is served.
    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, payload)
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        == payload
    )


async def test_epoch_separation_old_entries_never_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-30 race separation: a projection write that raced an invalidation
    lands on the OLD-epoch key, which is never read again."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload = _dto_payload()
    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, payload)
    epoch_key = "graph_revision:series_dexter"
    assert fake._store.get(epoch_key) is None  # written at epoch 0

    # Invalidation bumps the epoch. The stale epoch-0 entry still physically
    # exists (simulating a racing write or failed deletion) but reads now
    # construct the epoch-1 key, so the old entry can never be served.
    await fake.incr(epoch_key)
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )


async def test_focus_equivalent_sets_share_cache_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-30: reordered/duplicated focus sets are one cache entry."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload = _dto_payload(view=FOCUS)
    await set_cached_visualization(
        "series_dexter", 1, FOCUS, PROJECTION_VERSION, None, payload,
        focus_ids=["char_b", "char_a", "char_b"],
    )
    assert (
        await get_cached_visualization(
            "series_dexter", 1, FOCUS, PROJECTION_VERSION, None,
            focus_ids=["char_a", "char_b"],
        )
        == payload
    )
    assert (
        await get_cached_visualization(
            "series_dexter", 1, FOCUS, PROJECTION_VERSION, None,
            focus_ids=["char_b", "char_a"],
        )
        == payload
    )


async def test_focus_distinct_sets_never_cross(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-30: distinct normalized focus sets are distinct cache entries."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload_a = _dto_payload(view=FOCUS)
    await set_cached_visualization(
        "series_dexter", 1, FOCUS, PROJECTION_VERSION, None, payload_a,
        focus_ids=["char_a"],
    )
    assert (
        await get_cached_visualization(
            "series_dexter", 1, FOCUS, PROJECTION_VERSION, None,
            focus_ids=["char_a"],
        )
        == payload_a
    )
    # Different focus set: miss even though view/order/version match.
    assert (
        await get_cached_visualization(
            "series_dexter", 1, FOCUS, PROJECTION_VERSION, None,
            focus_ids=["char_b"],
        )
        is None
    )
    # Superset vs subset: also distinct.
    assert (
        await get_cached_visualization(
            "series_dexter", 1, FOCUS, PROJECTION_VERSION, None,
            focus_ids=["char_a", "char_b"],
        )
        is None
    )


async def test_epoch_read_failure_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-30: if the epoch itself cannot be read, the cache is bypassed —
    the key is never constructed and the request never fails."""
    fake = _FakeRedis()
    _enable_cache(monkeypatch, fake)

    payload = _dto_payload()
    await set_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None, payload)
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        == payload
    )

    async def broken_get(key: str):
        if key.startswith("graph_revision:"):
            raise RuntimeError("redis down")
        return fake._store.get(key)

    fake.get = broken_get  # type: ignore[method-assign]
    assert (
        await get_cached_visualization("series_dexter", 1, FULL, PROJECTION_VERSION, None)
        is None
    )
