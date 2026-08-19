"""Redis-backed rate limiting for login, chat-send, and content-write routes.

08-RESEARCH Assumption A5 verified against the installed
``fastapi-limiter==0.2.0`` (2026-08-04): 0.2.0 is the pyrate-limiter rewrite —
there is no ``FastAPILimiter.init(redis, identifier=..., http_callback=...)``
anymore, and ``RateLimiter`` no longer takes ``(times, seconds)``. The
library's surviving contract is the identifier + callback dependency shape,
which this module keeps, on top of pyrate-limiter's atomic ``RedisBucket``
(a single Lua script ``EVALSHA``'d against the shared Upstash Redis — correct
across multiple Render workers, D-14). The ``Limiter`` can only be built once
a Redis client exists, so ``init_rate_limiter()`` binds it at app startup;
until then (or when ``REDIS_URL`` is empty) every ``RateLimiter`` dependency
is a no-op — local dev without Upstash runs unthrottled instead of crashing.

The dependency instances below are module-level singletons imported by the
route modules, so API tests can also neutralize them via
``app.dependency_overrides`` or the conftest autouse ``__call__`` no-op.
"""

from __future__ import annotations

import logging

from fastapi import Request, Response
from pyrate_limiter import Duration, Limiter, Rate, RedisBucket, SingleBucketFactory

from spoilerless.app.cache.redis_client import get_redis
from spoilerless.app.core.errors import http_error

logger = logging.getLogger(__name__)

# How many requests per window each route group allows.
LOGIN_LIMIT = 10
LOGIN_WINDOW_SECONDS = 300  # 10 / 5 minutes per IP
CHAT_SEND_LIMIT = 20
CHAT_SEND_WINDOW_SECONDS = 60  # 20 / minute per user
CONTENT_WRITE_LIMIT = 30
CONTENT_WRITE_WINDOW_SECONDS = 60  # 30 / minute per user-or-IP


async def rate_limit_identifier(request: Request) -> str:
    """Rate-limit key per request.

    ``require_current_user`` stamps ``request.state.user`` with the resolved
    AppUser record (see ``api/deps.py``), so authenticated requests key on the
    user id; anonymous requests (e.g. user_content routes, which gain an
    ownership dependency only in Phase 9) fall back to the client IP.
    BUG-BE-02: request.client may be None on ASGI/unix-socket test clients.
    """
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user['id']}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


async def rate_limit_callback(
    request: Request,
    response: Response,
    pexpire: int = 0,
) -> None:
    """Reject with 429 using the existing sanitized error envelope.

    Reuses the exact lowercase ``too_many_requests`` code already used at
    ``spoilerless/app/api/chat.py``'s ``_too_many_requests()`` and
    ``spoilerless/app/core/errors.py``'s ``_ERROR_SPECS[429]`` — never a new
    uppercase code (``ErrorDetail.code``'s regex is ``^[a-z][a-z0-9_]*$``).
    """
    raise http_error(429, "TOO_MANY_REQUESTS", "Too many requests. Please slow down.")


class RateLimiter:
    """FastAPI dependency enforcing ``times`` requests per ``seconds`` window.

    The backing pyrate-limiter ``Limiter`` (Redis-backed, one ZSET per window)
    is bound by ``init_rate_limiter()`` at startup. While it is ``None`` the
    dependency is a no-op, implementing the plan's "empty ``redis_url``
    disables rate limiting rather than crashing startup".
    """

    def __init__(self, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds
        self._limiter: Limiter | None = None

    @property
    def bucket_key(self) -> str:
        return f"hdgraf:rate_limit:{self.times}/{self.seconds}"

    async def __call__(self, request: Request, response: Response) -> None:
        limiter = self._limiter
        if limiter is None:
            # D-05: never a SILENT no-op for login/chat/content-write in
            # production. Local dev (empty REDIS_URL) keeps the documented
            # no-op; non-production or explicit fail-open keeps degrade.
            from spoilerless.app.core.config import get_settings

            settings = get_settings()
            if not settings.redis_url:
                return  # dev contract: empty REDIS_URL = disabled
            if settings.environment != "production" or settings.rate_limit_fail_open:
                logger.warning(
                    "rate_limit: Redis unavailable — rate limiting disabled for this request"
                )
                return
            raise http_error(
                503,
                "rate_limit_unavailable",
                "Rate limiting is unavailable; try again shortly.",
            )
        rate_key = await rate_limit_identifier(request)
        key = f"{rate_key}:{self.bucket_key}"
        try:
            success = await limiter.try_acquire_async(key, blocking=False)
        except Exception:
            from spoilerless.app.core.config import get_settings

            settings = get_settings()
            if not settings.redis_url:
                return
            if settings.environment != "production" or settings.rate_limit_fail_open:
                logger.warning(
                    "rate_limit: Redis unavailable — rate limiting disabled for this request",
                    exc_info=True,
                )
                return
            raise http_error(
                503,
                "rate_limit_unavailable",
                "Rate limiting is unavailable; try again shortly.",
            )
        if not success:
            await rate_limit_callback(request, response, pexpire=0)


# Per-route-group windows (08-05 plan): login per IP; chat-send per user;
# content-write per user-or-IP (user_content routes have no user dependency
# until Phase 9, so the identifier falls back to IP there).
login_rate_limiter = RateLimiter(times=LOGIN_LIMIT, seconds=LOGIN_WINDOW_SECONDS)
chat_send_rate_limiter = RateLimiter(times=CHAT_SEND_LIMIT, seconds=CHAT_SEND_WINDOW_SECONDS)
content_write_rate_limiter = RateLimiter(times=CONTENT_WRITE_LIMIT, seconds=CONTENT_WRITE_WINDOW_SECONDS)


async def init_rate_limiter() -> None:
    """Bind the shared Redis-backed Limiter to every RateLimiter instance.

    Called from ``main.py``'s lifespan right after ``database.open()``,
    guarded on a non-empty ``redis_url``. Each window gets its own
    ``RedisBucket`` (one ZSET per window) so the login, chat-send and
    content-write counters stay independent; the leak is scheduled by
    pyrate-limiter's daemon Leaker so ZSETs never grow unboundedly.

    A Redis connectivity failure here is degraded, not fatal: the limiter
    stays unbound (a no-op) and the app still serves — matching the
    documented "empty redis_url disables rate limiting" contract. Without
    this guard, an Upstash hiccup at startup would raise inside lifespan
    and Render would treat the whole deploy as failed.
    """
    try:
        redis_client = get_redis()
        for instance in (
            login_rate_limiter,
            chat_send_rate_limiter,
            content_write_rate_limiter,
        ):
            bucket = await RedisBucket.init(
                rates=[Rate(instance.times, Duration.SECOND * instance.seconds)],
                redis=redis_client,
                bucket_key=instance.bucket_key,
            )
            instance._limiter = Limiter(SingleBucketFactory(bucket))
    except Exception:
        from spoilerless.app.core.config import get_settings

        settings = get_settings()
        # In production with fail-closed, log ERROR to highlight that every
        # limited route will 503; do NOT raise — per-request 503 is the
        # designed failure mode (startup blip must not kill deploy).
        if settings.redis_url and settings.environment == "production" and not settings.rate_limit_fail_open:
            logger.error(
                "init_rate_limiter: Redis unavailable at startup — rate limiting unavailable and every limited route will 503",
                exc_info=True,
            )
        else:
            logger.warning(
                "init_rate_limiter: Redis unavailable at startup — rate limiting disabled",
                exc_info=True,
            )
