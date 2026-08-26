"""Cache-aside layer for GET /api/series/{series_id}/graph (INFRA-02, 08-06)
and GET /api/series/{series_id}/graph/visualization (10-03, D-29/D-30).

Built on the ONE shared Redis client (``cache/redis_client.py``, 08-05) so
the whole backend keeps a single connection pool. Graph cache keys are
``graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`` — the
effective spoiler boundary is part of the key, so a boundary change alone
always misses correctly with no explicit invalidation needed. Explicit
``invalidate_series()`` covers writes that change graph content at a fixed
boundary.

Visualization projection keys (``viz:...``) additionally carry view type and
projection version, and every cached DTO is re-validated against its own
metadata on read (T10-CACHE-02) so a stale or poisoned entry is never
served. The 10-03 Task 2 epoch (``graph_revision``) and GraphRAG focus
signature dimensions live below.

Caching is a performance layer, never a hard dependency: an empty
``redis_url`` or any Redis error degrades to always querying Neo4j directly
(T-08-06-02).

Call-site inventory for series cache invalidation:
All mutation endpoints call GraphService.invalidate_series_cache(series_id):
- api/candidates.py: ingest_candidates, approve_candidate, reject_candidate, edit_candidate (4 call sites)
- api/change_set.py: confirm_change_set, revert_change_set (2 call sites)
- api/user_content.py: create_custom_node, update_custom_node, delete_custom_node, create_custom_relationship, update_custom_relationship, delete_custom_relationship (6 call sites)
- api/revisions.py: revert_revision (1 call site)

Note: New content mutation paths must invoke GraphService.invalidate_series_cache, not raw cache internals.
Full impossibility-of-forgetting (a write-coordinator pattern wrapping execute_write) is deliberately out of scope.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from spoilerless.app.cache.redis_client import get_redis
from spoilerless.app.core.config import get_settings
from spoilerless.app.domain.visualization import VisualizationDTO

DEFAULT_GRAPH_TTL_SECONDS = 300

# Redis-local per-series cache epoch (10-03 Task 2, D-30): bumped on every
# content-changing write so projection entries written before the write can
# never be served afterwards, even if key deletion races or fails.
EPOCH_KEY_PREFIX = "graph_revision"
# Deterministic signature for requests without a GraphRAG focus set.
FOCUS_NONE_SIGNATURE = "none"


async def _graph_revision(redis: Any, series_id: str) -> int:
    """Current per-series cache epoch; 0 (the default) when never bumped."""
    raw = await redis.get(f"{EPOCH_KEY_PREFIX}:{series_id}")
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


FOCUS_SET_CAP = 64            # distinct focus signatures cached per series
FOCUS_SET_TTL_SECONDS = 3600


async def _focus_capacity_allows(redis: Any, series_id: str, focus_sig: str) -> bool:
    """True when this signature may be cached (member, or set under the cap).

    The per-series signature set bounds cache-key cardinality: an attacker
    enumerating focus_id combinations creates at most FOCUS_SET_CAP distinct
    viz keys per series per TTL window — the 2^256 signature space can no
    longer mint unbounded Redis entries (each miss still pays the fetch, but
    memory growth is bounded).
    """
    key = f"vizfocus:{series_id}"
    if await redis.sismember(key, focus_sig):
        return True
    if await redis.scard(key) >= FOCUS_SET_CAP:
        return False
    await redis.sadd(key, focus_sig)
    await redis.expire(key, FOCUS_SET_TTL_SECONDS)
    return True


def focus_signature(focus_ids: list[str] | None) -> str:
    """Deterministic SHA-256 request signature for a focus set.

    Canonicalizes by validation-free deduplication + lexical sorting, then
    hashes the length-prefixed canonical sequence so ordering and duplicate
    variations of the same focus set share one cache key while distinct
    focus sets never collide. ``None``/empty maps to the fixed ``none``
    signature. Callers validate focus ids against the safe payload at the
    projection layer; the signature only needs them distinct per set.
    """
    if not focus_ids:
        return FOCUS_NONE_SIGNATURE
    canonical = sorted(set(focus_ids))
    payload = "".join(f"{len(part)}:{part}" for part in canonical)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
        # Atomic epoch bump BEFORE deletion: a projection write that raced
        # ahead of this invalidation lands on the old-epoch key, which is
        # never read again (D-30 race separation).
        await redis.incr(f"{EPOCH_KEY_PREFIX}:{series_id}")
        async for key in redis.scan_iter(match=f"graph:{series_id}:*"):
            await redis.delete(key)
        async for key in redis.scan_iter(match=f"viz:{series_id}:*"):
            await redis.delete(key)
    except Exception:
        return


# ---------------------------------------------------------------------------
# Visualization projection cache-aside (10-03, D-29/D-30, T10-CACHE-02/03).
#
# Same cache-aside discipline as the graph cache: Redis optional, errors
# return a miss, values are JSON payloads, writes use a TTL, and the key
# carries every dimension a projection may NOT cross: series, effective
# boundary, view type, projection version, and user scope. A cached DTO is
# additionally validated against the request's metadata contract on read
# (stale/poisoned payloads are rejected as misses, never served) — the DTO
# carries projection_version + effective_view_order (T10-CACHE-02).
#
# Task 2 (D-30) adds the Redis-local per-series ``graph_revision`` epoch and
# the GraphRAG focus request signature to the key dimensions.
# ---------------------------------------------------------------------------

def _visualization_cache_key(
    series_id: str,
    effective_boundary: int,
    view: str,
    projection_version: str,
    user_id: str | None,
    epoch: int,
    focus_sig: str,
) -> str:
    return (
        f"viz:{series_id}:{effective_boundary}:{view}:{projection_version}:"
        f"{user_id or 'anon'}:{epoch}:{focus_sig}"
    )


async def get_cached_visualization(
    series_id: str,
    effective_boundary: int,
    view: str,
    projection_version: str,
    user_id: str | None,
    focus_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """Return the cached VisualizationDTO payload, or None (miss/bypass).

    Any Redis failure (including an unreadable epoch — the key is never
    constructed without one, D-30), invalid JSON, a payload that is not a
    valid ``VisualizationDTO``, or a payload whose metadata contradicts the
    request's key dimensions (projection_version / view_type /
    effective_view_order) is a MISS — a stale or poisoned entry is never
    served (T10-CACHE-02/T10-CACHE-03).
    """
    if not get_settings().redis_url:
        return None
    try:
        redis = get_redis()
        epoch = await _graph_revision(redis, series_id)
        value = await redis.get(
            _visualization_cache_key(
                series_id,
                effective_boundary,
                view,
                projection_version,
                user_id,
                epoch,
                focus_signature(focus_ids),
            )
        )
    except Exception:
        return None
    if value is None:
        return None
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return None
    try:
        dto = VisualizationDTO.model_validate(payload)
    except Exception:
        return None
    metadata = dto.metadata
    if (
        metadata.projection_version != projection_version
        or metadata.view_type != view
        or metadata.effective_view_order != effective_boundary
    ):
        return None
    return payload


async def set_cached_visualization(
    series_id: str,
    effective_boundary: int,
    view: str,
    projection_version: str,
    user_id: str | None,
    response: dict[str, Any],
    ttl_seconds: int = DEFAULT_GRAPH_TTL_SECONDS,
    focus_ids: list[str] | None = None,
) -> None:
    """Store a VisualizationDTO payload (``model_dump(mode="json")``).

    The epoch is read at write time: a write that raced an invalidation
    populates only the old-epoch key, which is never served again (D-30).
    """
    if not get_settings().redis_url:
        return
    try:
        redis = get_redis()
        if focus_ids:
            sig = focus_signature(focus_ids)
            if not await _focus_capacity_allows(redis, series_id, sig):
                return  # compute-fresh, never store: bounded cardinality (D-12)
        epoch = await _graph_revision(redis, series_id)
        await redis.setex(
            _visualization_cache_key(
                series_id,
                effective_boundary,
                view,
                projection_version,
                user_id,
                epoch,
                focus_signature(focus_ids),
            ),
            ttl_seconds,
            json.dumps(response),
        )
    except Exception:
        return
