"""Shared redis.asyncio client singleton (08-05).

This module is deliberately the ONE Redis connection point in the backend:
rate limiting (``services/rate_limit.py``) imports ``get_redis()`` from here,
and the later graph-query response-cache plan (INFRA-02) will import it too —
never construct a second ``redis.asyncio`` client elsewhere.

``get_redis()`` is ``lru_cache``-decorated, mirroring the existing
``core/config.py::get_settings`` singleton pattern, so the whole app shares a
single connection pool. The URL is expected to be an Upstash ``rediss://``
TLS connection string; an empty ``redis_url`` (local dev without Upstash)
disables every Redis-backed feature — callers must guard on
``settings.redis_url`` before calling ``get_redis()``, since
``Redis.from_url("")`` raises ``ValueError``.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from backend.app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    """Return the shared ``redis.asyncio`` client (``rediss://`` Upstash URL).

    ``decode_responses`` stays ``False`` (bytes): pyrate-limiter's Lua bucket
    script passes numeric timestamps and scores, which round-trip cleanly as
    bytes/int and avoid any str/int coercion surprises.
    """
    return Redis.from_url(get_settings().redis_url, decode_responses=False)
