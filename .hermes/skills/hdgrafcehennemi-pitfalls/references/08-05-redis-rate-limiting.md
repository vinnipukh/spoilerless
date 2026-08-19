# fastapi-limiter 0.2.0 / pyrate-limiter 4.4.0 — Redis rate limiting (08-05)

Verified 2026-08-04 against the installed wheels. RESEARCH Assumption A5 was REAL:
the plan's assumed API (`FastAPILimiter.init(redis, identifier=..., http_callback=...)`,
`RateLimiter(times, seconds)`) does not exist in the pinned version.

## Installed API reality (fastapi-limiter 0.2.0 = pyrate-limiter rewrite)

- `fastapi_limiter/__init__.py` is EMPTY (0 bytes). **`FastAPILimiter` does not exist.**
- `fastapi_limiter.depends.RateLimiter(limiter, identifier=default_identifier, callback=default_callback, blocking=False)`
  — `limiter` is a `pyrate_limiter.Limiter`; NO `(times, seconds)` constructor.
- `RateLimiter.__call__(request, response)`: scans `request.app.routes` for
  `route.path == request.scope["path"]` (fails for parameterized paths — dep_index
  stays 0, key degrades to `rate_key:0:0`, still functional), then
  `limiter.try_acquire_async(key, blocking=...)`; on False → `await self.callback(request, response)`.
- `fastapi_limiter.callback.default_callback` raises a BARE `HTTPException(429, "Too Many Requests")`
  — NOT the repo's sanitized envelope; always supply your own callback.
- `fastapi_limiter.identifier.default_identifier` = X-Forwarded-For first hop → client.host, + ":" + path.

## pyrate-limiter 4.4.0 facts

- Top-level exports: `Limiter`, `Rate`, `Duration`, `RedisBucket`, `InMemoryBucket`,
  `SingleBucketFactory`, `BucketFactory`, `AbstractBucket`, `RateItem`.
- Redis storage: `RedisBucket.init(rates, redis, bucket_key)` — with `redis.asyncio`
  it returns a coroutine that **awaits `redis.script_load(LuaScript.PUT_ITEM)`**,
  so constructing it requires a LIVE Redis. Build limiters at app STARTUP
  (lifespan), NEVER at module import (import fires at pytest collection).
- Bucket ops are Lua `EVALSHA` over a ZSET per bucket_key → atomic across workers
  (D-14). One bucket holds ONE Rate config; per-window counters need one
  bucket/limiter per window (a multi-rate bucket imposes every window on every key).
- `Limiter(bucket_factory | bucket | rate | rates, buffer_ms=50)`. Passing a raw
  AbstractBucket auto-wraps in `SingleBucketFactory(bucket, schedule_leak=True)` —
  for an async RedisBucket that registers it with a Leaker and calls
  `asyncio.create_task` (REQUIRES a running event loop). Pass
  `SingleBucketFactory(bucket, schedule_leak=False)` to skip; with leak on, it runs
  every 10 s (daemon thread for sync buckets, asyncio task for async).
- `Limiter.try_acquire_async(key, blocking=False)` → bool.
- Rate intervals are MILLISECONDS: `Rate(times, Duration.SECOND * seconds)`.

## Working wiring pattern (shipped in 08-05)

- `backend/app/cache/redis_client.py`: `@lru_cache get_redis() -> redis.asyncio.Redis`
  from `Redis.from_url(get_settings().redis_url, decode_responses=False)` — the ONE
  shared client (the 08-06 graph cache imports it too). `Redis.from_url("")` raises
  ValueError → callers must guard on `settings.redis_url`.
- `backend/app/services/rate_limit.py`:
  - `rate_limit_identifier(request)`: `user = getattr(request.state, "user", None)`;
    `"user:{id}"` if user else `"ip:{client.host}"`.
  - `rate_limit_callback(request, response, pexpire=0)`: raises
    `http_error(429, "too_many_requests", ...)` — the EXISTING lowercase code
    (ErrorDetail.code regex `^[a-z][a-z0-9_]*$`; never invent an uppercase code).
  - `class RateLimiter`: `__init__(times, seconds)`; `self._limiter = None` until
    `init_rate_limiter()` binds it; `__call__` no-ops while `_limiter is None`
    (⇒ empty `redis_url` disables rate limiting, per plan). Key:
    `f"{rate_key}:{bucket_key}"`, `limiter.try_acquire_async(key, blocking=False)`,
    on False → `await rate_limit_callback(...)`.
  - Windows (plan): login 10/300 s per IP; chat-send 20/60 s per user;
    content-write 30/60 s per user-or-IP. One module-level `RateLimiter` instance
    per window, imported by routes and used as `Depends(instance)`.
  - `init_rate_limiter()`: for each instance, `bucket = await RedisBucket.init(...)`
    then `instance._limiter = Limiter(SingleBucketFactory(bucket))` (default leak is
    fine here — the lifespan loop is running).
- `backend/app/main.py` lifespan: `if settings.redis_url: await init_rate_limiter()`
  right after `database.open()`.
- `backend/app/api/deps.py`: `require_current_user` sets `request.state.user = user`
  before returning — WITHOUT this the identifier's per-user branch silently never
  fires for authenticated chat/content requests (Rule-2 gap found during execution;
  the plan's behavior test assumed the stamping existed).
- `backend/app/core/config.py`: `redis_url: str = Field(default="", description=...)`.

## Test pattern — no live Redis anywhere

- `backend/tests/conftest.py` autouse fixture:

  ```python
  @pytest.fixture(autouse=True)
  def _disable_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
      from backend.app.services.rate_limit import RateLimiter
      async def _noop(request: Request, response: Response) -> None:
          return None
      monkeypatch.setattr(RateLimiter, "__call__", _noop)
  ```

  FastAPI resolves `Depends(instance)` through the instance → dispatches to the
  CLASS `__call__`, so ONE class-level patch covers every suite — including
  real-app `TestClient(main_module.app)` tests whose lifespan runs (with empty
  `redis_url` lifespan skips init anyway). Do NOT try `dependency_overrides` keyed
  on `RateLimiter` the class — each route holds a distinct instance, so class-keyed
  overrides never match.
- Pure functions are unit-tested directly with fake `_State`/`_Client` request
  stand-ins, no network (test_rate_limit.py: 4 tests; RED = collection ImportError
  of the not-yet-created module, a valid TDD RED).

## Verification evidence (08-05)

- `pytest backend/tests/test_auth.py backend/tests/test_chat_api.py backend/tests/test_user_content_api.py backend/tests/test_rate_limit.py -q` → 107 passed
- Full suite: 436 passed / 3 failed — all `test_seed_idempotency.py`, PRE-EXISTING
  debt: 8 candidate-origin residue nodes in the shared live DB (3 Claim + 3
  EvidenceFragment + 2 Source — read-only query
  `MATCH (n) WHERE NOT n.origin IN ['canonical'] RETURN labels(n)[0], n.origin, count(*)`);
  identical numbers already documented in deferred-items.md / STATE.md before this
  session; 08-05 adds zero Neo4j rows.
- TDD gate: `test(08-05)` RED (ImportError at collection) → `feat(08-05)` GREEN; commits a672d17 / 1f8a3e9.

## Diagnostics gotchas

- neo4j driver 6.x: `AsyncSession.run(...)` returns a COROUTINE —
  `result = await s.run(q); rows = await result.data()`. Skipping the await yields
  `AttributeError: 'coroutine' object has no attribute 'data'` (plus an
  un-awaited-coroutine warning). Hit in a read-only DB diagnostic one-liner.
- If `python -c` inspection commands get blocked on approval, read the installed
  package sources directly under `.venv/Lib/site-packages/` — that was needed
  anyway for the A5 verification.
