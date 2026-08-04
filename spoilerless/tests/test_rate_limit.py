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
    rate_limit_callback,
    rate_limit_identifier,
)

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
    assert exc_info.value.detail["code"] == "too_many_requests"
    assert "message" in exc_info.value.detail
