from __future__ import annotations

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
    from backend.app.services.rate_limit import RateLimiter

    async def _noop(request: Request, response: Response) -> None:
        return None

    monkeypatch.setattr(RateLimiter, "__call__", _noop)
