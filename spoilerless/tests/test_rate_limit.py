"""Unit tests for the rate-limit wiring's pure functions (08-05, Task 3).

No live Redis is needed: sliding/fixed-window correctness itself is
pyrate-limiter's tested responsibility — this repo owns only the identifier
(per-user vs per-IP) and the 429 envelope callback. The dependency class
itself is neutralized for API tests by the conftest ``_disable_rate_limiter``
autouse fixture (``RateLimiter.__call__`` → no-op), so no test in the suite
opens a connection to Redis.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from spoilerless.app.services.rate_limit import (
    RateLimiter,
    rate_limit_callback,
    rate_limit_identifier,
)

# conftest's autouse _disable_rate_limiter fixture patches
# RateLimiter.__call__ to a no-op for the whole suite; capture the original
# class method here so the __call__ behavior tests can exercise it directly.
_ORIGINAL_CALL = RateLimiter.__call__

_MISSING = object()


class _State:
    def __init__(self, user: object = _MISSING) -> None:
        if user is not _MISSING:
            self.user = user


class _Client:
    def __init__(self, host: str) -> None:
        self.host = host


class _Request:
    """Minimal stand-in for starlette Request — only what the pure
    functions read (``request.state.user``, ``request.client.host``)."""

    def __init__(
        self,
        state_user: object = _MISSING,
        client_host: str = "203.0.113.7",
    ) -> None:
        self.state = _State(state_user)
        self.client = _Client(client_host)


async def test_identifier_keys_authenticated_user() -> None:
    request = _Request(state_user={"id": "user:1"})
    assert await rate_limit_identifier(request) == "user:user:1"


async def test_identifier_falls_back_to_client_ip_when_user_none() -> None:
    request = _Request(state_user=None)
    assert await rate_limit_identifier(request) == "ip:203.0.113.7"


async def test_identifier_falls_back_to_ip_when_state_has_no_user() -> None:
    request = _Request()
    assert await rate_limit_identifier(request) == "ip:203.0.113.7"


async def test_callback_raises_429_with_existing_error_code() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await rate_limit_callback(_Request(), response=None)
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "TOO_MANY_REQUESTS"
    assert "message" in exc_info.value.detail


class _RaisingLimiter:
    """Limiter stand-in whose acquire always raises — simulates a Redis
    outage/upstream failure at request time (PROB-23, SEVENTEENTH PASS)."""

    async def try_acquire_async(self, key: str, blocking: bool) -> bool:
        raise RuntimeError("redis connection refused")


class _DenyingLimiter:
    """Limiter stand-in that returns False — the normal quota-exceeded path."""

    async def try_acquire_async(self, key: str, blocking: bool) -> bool:
        return False


class _AllowingLimiter:
    """Limiter stand-in that returns True — the normal in-quota path."""

    async def try_acquire_async(self, key: str, blocking: bool) -> bool:
        return True


async def test_redis_outage_degrades_to_noop_not_500() -> None:
    """PROB-23: a Redis failure inside try_acquire must never surface as a
    500 — the route continues (fail-open), matching the graph cache's
    degrade-to-Neo4j behavior."""
    from spoilerless.app.services.rate_limit import RateLimiter

    limiter = RateLimiter(times=10, seconds=300)
    limiter._limiter = _RaisingLimiter()
    # conftest's autouse _disable_rate_limiter replaces the class __call__
    # with a no-op; invoke the captured original directly.
    await _ORIGINAL_CALL(limiter, _Request(), response=None)  # must not raise


async def test_denied_acquire_still_returns_429() -> None:
    """The 429 path is untouched: quota-exceeded still raises the envelope."""
    from spoilerless.app.services.rate_limit import RateLimiter

    limiter = RateLimiter(times=10, seconds=300)
    limiter._limiter = _DenyingLimiter()
    with pytest.raises(HTTPException) as exc_info:
        await _ORIGINAL_CALL(limiter, _Request(), response=None)
    assert exc_info.value.status_code == 429


async def test_allowed_acquire_passes_through() -> None:
    from spoilerless.app.services.rate_limit import RateLimiter

    limiter = RateLimiter(times=10, seconds=300)
    limiter._limiter = _AllowingLimiter()
    await _ORIGINAL_CALL(limiter, _Request(), response=None)  # must not raise


async def test_init_rate_limiter_degrades_on_redis_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PROB-23: a Redis failure at startup must not crash the app's lifespan
    — the limiter stays unbound (no-op) and the service still serves."""
    from spoilerless.app.services.rate_limit import (
        RateLimiter,
        init_rate_limiter,
        login_rate_limiter,
    )

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("upstash unreachable")

    monkeypatch.setattr(
        "spoilerless.app.services.rate_limit.RedisBucket.init", _boom
    )
    monkeypatch.setattr(
        "spoilerless.app.services.rate_limit.get_redis",
        lambda: object(),
    )
    login_rate_limiter._limiter = None
    await init_rate_limiter()  # must not raise
    assert login_rate_limiter._limiter is None
