"""Direct unit tests for the auth dependencies (PROB-18/#40).

Covers the require_current_user 401 path, require_admin 403 path, and the
request.state.user stamping (rate-limit identifier key).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request

from spoilerless.app.api.deps import require_admin, require_current_user
from spoilerless.app.core.errors import http_error


def _make_request(cookie_value: str | None = None) -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    if cookie_value is not None:
        request.cookies["session"] = cookie_value
    return request


class _FakeService:
    def __init__(self, user: dict[str, Any] | None) -> None:
        self._user = user

    async def get_current_user(self, raw_token: str | None, session_ttl: int) -> dict[str, Any] | None:
        return self._user


@pytest.mark.asyncio
async def test_require_current_user_401_without_session() -> None:
    request = _make_request(cookie_value=None)
    service = _FakeService(None)
    with patch(
        "spoilerless.app.api.deps.get_settings",
        return_value=type("S", (), {"session_cookie_name": "session", "session_ttl_seconds": 3600})(),
    ):
        with pytest.raises(Exception) as exc_info:
            await require_current_user(request, service)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 401  # type: ignore[attr-defined]
    assert exc_info.value.detail["code"] == "AUTH_UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_require_current_user_stamps_request_state() -> None:
    request = _make_request(cookie_value="token")
    user = {"id": "user:1", "role": "user"}
    service = _FakeService(user)
    with patch(
        "spoilerless.app.api.deps.get_settings",
        return_value=type("S", (), {"session_cookie_name": "session", "session_ttl_seconds": 3600})(),
    ):
        resolved = await require_current_user(request, service)  # type: ignore[arg-type]
    assert resolved == user
    # The stamp is what rate-limit identifiers key on (services/rate_limit.py).
    assert request.state.user == user


@pytest.mark.asyncio
async def test_require_admin_allows_admin_user() -> None:
    admin = {"id": "user:admin", "role": "admin"}
    assert await require_admin(admin) == admin  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_require_admin_403_for_non_admin() -> None:
    user = {"id": "user:1", "role": "user"}
    with pytest.raises(Exception) as exc_info:
        await require_admin(user)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403  # type: ignore[attr-defined]
    assert exc_info.value.detail["code"] == "FORBIDDEN"


