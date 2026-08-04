"""Cache-aside layer for GET /api/series/{series_id}/graph (INFRA-02, 08-06).

Built on the ONE shared Redis client (``cache/redis_client.py``, 08-05) so
the whole backend keeps a single connection pool. Cache keys are
``graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`` — the
effective spoiler boundary is part of the key, so a boundary change alone
always misses correctly with no explicit invalidation needed. Explicit
``invalidate_series()`` covers writes that change graph content at a fixed
boundary.

Caching is a performance layer, never a hard dependency: an empty
``redis_url`` or any Redis error degrades to always querying Neo4j directly
(T-08-06-02).
"""

from __future__ import annotations

import json
from typing import Any

from backend.app.cache.redis_client import get_redis
from backend.app.core.config import get_settings

DEFAULT_GRAPH_TTL_SECONDS = 300


def _cache_key(series_id: str, effective_boundary: int, user_id: str | None) -> str:
    return f"graph:{series_id}:{effective_boundary}:{user_id or 'anon'}"


async def get_cached_graph(
    series_id: str, effective_boundary: int, user_id: str | None
) -> dict[str, Any] | None:
    """Return the cached GraphResponse payload for a key tuple, or None."""
    if not get_settings().redis_url:
        return None
    try:
        value = await get_redis().get(_cache_key(series_id, effective_boundary, user_id))
    except Exception:
        # A cache failure must never surface as a request failure — fall
        # through to Neo4j (T-08-06-02).
        return None
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


async def set_cached_graph(
    series_id: str,
    effective_boundary: int,
    user_id: str | None,
    response: dict[str, Any],
    ttl_seconds: int = DEFAULT_GRAPH_TTL_SECONDS,
) -> None:
    """Store a GraphResponse payload (``model_dump(mode="json")``) with a TTL."""
    if not get_settings().redis_url:
        return
    try:
        await get_redis().setex(
            _cache_key(series_id, effective_boundary, user_id),
            ttl_seconds,
            json.dumps(response),
        )
    except Exception:
        return


async def invalidate_series(series_id: str) -> None:
    """Delete every cached graph entry for a series (coarse per-series).

    Over-invalidating on any content-changing write is safe (T-08-06-01);
    precisely tracking which (boundary, user) combinations a write affects
    would mean re-deriving GraphService's own visibility logic a second
    time, and under-invalidating could serve a stale spoiler-relevant
    response.
    """
    if not get_settings().redis_url:
        return
    try:
        redis = get_redis()
        async for key in redis.scan_iter(match=f"graph:{series_id}:*"):
            await redis.delete(key)
    except Exception:
        return
