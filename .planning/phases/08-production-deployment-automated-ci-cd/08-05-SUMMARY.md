---
phase: 08-production-deployment-automated-ci-cd
plan: 05
subsystem: security
tags: [redis, rate-limit, fastapi-limiter, pyrate-limiter, sec-03]
status: complete
completed: 2026-08-04
requirements-completed: [SEC-03]

coverage:
  - id: D1
    description: "Rate-limit identifier keys per-user (request.state.user) or per-IP fallback, and the 429 callback reuses the existing too_many_requests envelope"
    requirement: SEC-03
    verification:
      - kind: unit
        ref: "backend/tests/test_rate_limit.py#test_identifier_keys_authenticated_user, test_identifier_falls_back_to_client_ip_when_user_none, test_identifier_falls_back_to_ip_when_state_has_no_user, test_callback_raises_429_with_existing_error_code"
        status: pass
    human_judgment: false
  - id: D2
    description: "Login, chat-send (post_message + stream_message), and every content-write mutation route carry a Redis-backed RateLimiter dependency; init_rate_limiter wired into main.py lifespan guarded on redis_url; existing suites green without a live Redis (conftest autouse no-op override)"
    requirement: SEC-03
    verification:
      - kind: integration
        ref: "pytest backend/tests/test_auth.py backend/tests/test_chat_api.py backend/tests/test_user_content_api.py backend/tests/test_rate_limit.py -q → 107 passed"
        status: pass
    human_judgment: false
---

# Phase 08 — Plan 08-05 Summary: Redis-backed, multi-worker-safe rate limiting

**Login (10 req / 5 min per IP), chat-send (20 req / min per user), and
content-write (30 req / min per user-or-IP) now enforce Redis-backed rate
limits via pyrate-limiter's atomic Lua-scripted RedisBucket, with 429 served
in the existing `too_many_requests` envelope — and the whole suite stays
green without a live Redis (conftest autouse `RateLimiter.__call__` no-op).**

## Accomplishments

- `redis` 8.1.0 + `fastapi-limiter` 0.2.0 added to `pyproject.toml`/`uv.lock` (`uv add`, pyproject/uv.lock carried no uncommitted sibling changes — clean merge)
- `backend/app/cache/redis_client.py`: `@lru_cache` `get_redis() -> redis.asyncio.Redis` singleton — the single shared Redis connection point for this plan and the later 08-06 graph cache plan (INFRA-02)
- `backend/app/services/rate_limit.py`: `rate_limit_identifier` (per-user via `request.state.user`, per-IP fallback), `rate_limit_callback` (429 with the existing lowercase `too_many_requests` code), `RateLimiter(times, seconds)` dependency class (no-op until the Redis `Limiter` is bound, so empty `REDIS_URL` disables rather than crashes), and `init_rate_limiter()` binding one RedisBucket per window at startup
- `backend/app/core/config.py`: new `redis_url` field (empty disables rate limiting + the future cache)
- `backend/app/main.py`: lifespan calls `await init_rate_limiter()` right after `database.open()`, guarded on `if settings.redis_url`
- Dependencies added: `google_auth` (auth.py); `post_message` + `stream_message` (chat.py); all 9 POST/PATCH/DELETE routes in user_content.py
- `backend/app/api/deps.py`: `require_current_user` now stamps `request.state.user = user` — required for the identifier's per-user branch (plan behavior)
- `backend/tests/conftest.py`: autouse fixture no-ops `RateLimiter.__call__` so every test (incl. the real-app `test_user_content_api.py` TestClient with lifespan) runs without Redis
- `backend/tests/test_rate_limit.py`: 4 pure-function tests (no network)

## Task Commits

1. **Task 1: Verify redis and fastapi-limiter package legitimacy** — approved by prior executor via live PyPI verification (2026-08-04, checkpoint report); not re-verified per handoff
2. **Task 2: Redis client, rate limiter wiring, dependency on rate-limited routes** (tdd) — `a672d17` (test RED: test_rate_limit.py) + `1f8a3e9` (feat GREEN)
3. **Task 3: Rate-limit wiring unit tests** — artifact `backend/tests/test_rate_limit.py` produced by Task 2's TDD RED commit and verified green standalone (4 passed); no separate commit needed (see Deviations)

**Plan metadata:** `.planning/ROADMAP.md` + `.planning/STATE.md` updated in the docs commit (below)

## Verification

- TDD gate: `test(08-05): add failing tests for rate-limit identifier/callback` → `a672d17` (RED = collection ImportError, valid); `feat(08-05): Redis-backed rate limiter on login/chat-send/content-write routes` → `1f8a3e9` (GREEN). RED→GREEN sequence present in git log ✓
- `pytest backend/tests/test_auth.py backend/tests/test_chat_api.py backend/tests/test_user_content_api.py backend/tests/test_rate_limit.py -q` → **107 passed** (12.7s)
- `pytest backend/tests/test_rate_limit.py -q` → **4 passed** (Task 3 standalone)
- `pytest backend/tests/ -q` → **436 passed, 3 failed** — all 3 in `test_seed_idempotency.py`, the pre-existing documented test-pollution debt (8 candidate-origin nodes: 3 Claim + 3 EvidenceFragment + 2 Source left in the shared live DB by `test_candidate_ingest.py`'s untorn-down fixture; identical failure and residue numbers already documented in `deferred-items.md` and STATE.md Blockers before this session). 08-05 adds zero Neo4j rows; rate-limiter deps are no-ops in tests. Out of scope per GSD scope boundary — not fixed.
- `main.py` lifespan guard verified by diff + by `test_user_content_api.py`'s real-app TestClient exercising lifespan with empty `redis_url` (green)

## Files Created/Modified

- `pyproject.toml`, `uv.lock` — +redis 8.1.0, +fastapi-limiter 0.2.0 (+pyrate-limiter 4.4.0 transitive)
- `backend/app/cache/__init__.py`, `backend/app/cache/redis_client.py` — shared Redis singleton (new)
- `backend/app/services/rate_limit.py` — identifier/callback + RateLimiter deps + init_rate_limiter (new)
- `backend/app/core/config.py` — `redis_url` setting
- `backend/app/main.py` — lifespan `init_rate_limiter()` guarded on redis_url
- `backend/app/api/deps.py` — `request.state.user` stamping in require_current_user
- `backend/app/api/auth.py` — `login_rate_limiter` on google_auth
- `backend/app/api/chat.py` — `chat_send_rate_limiter` on post_message/stream_message
- `backend/app/api/user_content.py` — `content_write_rate_limiter` on all 9 mutation routes
- `backend/tests/conftest.py` — autouse `RateLimiter.__call__` no-op fixture
- `backend/tests/test_rate_limit.py` — 4 pure-function tests (new)

## Decisions Made

- **fastapi-limiter 0.2.0 API adaptation (RESEARCH Assumption A5 verified):** the installed 0.2.0 is the pyrate-limiter rewrite — `FastAPILimiter.init(redis, identifier=..., http_callback=...)` does not exist and `RateLimiter` no longer takes `(times, seconds)`. Kept the plan's identifier+callback contract and its `RateLimiter(...)` dependency shape, but backed it with pyrate-limiter's atomic `RedisBucket` (one Lua-scripted ZSET per window) bound at startup by `init_rate_limiter()`. The dependency is a no-op until bound — implementing the plan's "empty redis_url disables rate limiting" exactly.
- **Shared per-window buckets:** one `RedisBucket` per window (login/chat/content) so the three counter sets stay independent (a single multi-rate bucket would have imposed every window on every route group).
- **Tests never touch Redis:** conftest autouse fixture (not per-file overrides) so the full suite — including real-app TestClient tests — runs without REDIS_URL; pure functions unit-tested directly.
- **`require_current_user` stamps `request.state.user`:** without it the identifier's per-user branch could never fire for authenticated chat/content requests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `request.state.user` stamping in `require_current_user`**
- **Found during:** Task 2 (rate limiter wiring)
- **Issue:** the plan's `rate_limit_identifier` reads `request.state.user`, but no dependency ever set it — chat/content identifiers would have silently fallen back to IP for every authenticated user, defeating per-user limits.
- **Fix:** `require_current_user` sets `request.state.user = user` before returning (deps.py).
- **Files modified:** backend/app/api/deps.py
- **Verification:** identifier unit tests (user branch) + 107-test suite green.
- **Committed in:** 1f8a3e9

**2. [Rule 3 - Blocking] fastapi-limiter 0.2.0 API differs from the plan's assumed API (A5)**
- **Found during:** Task 2, immediately after `uv add` (`FastAPILimiter` ImportError — verified the installed source: `__init__.py` is empty; `depends.RateLimiter(limiter, identifier, callback, blocking)`).
- **Issue:** the plan's `FastAPILimiter.init(...)`/`RateLimiter(times, seconds)` wiring does not exist in the pinned version; a Limiter requires a Redis bucket that can only be built at startup.
- **Fix:** implemented the plan's contract (identifier + callback + `RateLimiter(...)` deps + `init_rate_limiter` in lifespan guarded on `redis_url`) on the installed API — pyrate-limiter's RedisBucket engine, per-window limiters bound at startup, no-op until bound.
- **Files modified:** backend/app/services/rate_limit.py (new), backend/app/cache/redis_client.py (new), backend/app/main.py
- **Verification:** full 107-test target suite green; main.py lifespan guard verified.
- **Committed in:** 1f8a3e9

**3. [Rule 3 - Blocking] Test-fixture limiter neutralization applied suite-wide, not just test_auth.py**
- **Found during:** Task 2 (existing test suites hit the now-rate-limited routes)
- **Issue:** the plan's action scoped the override to test_auth.py's fixture, but test_chat_api.py and the real-app test_user_content_api.py (and any chat_router-including change_set test) hit rate-limited routes too — an uninitialized limiter would raise there as well.
- **Fix:** one conftest autouse fixture no-ops `RateLimiter.__call__` for the whole suite (FastAPI resolves the dependency through the instance → class `__call__`), covering every existing and future test file; matches the plan's accepted alternative ("override the RateLimiter dependency … to a no-op").
- **Files modified:** backend/tests/conftest.py
- **Verification:** full suite 436 passed (3 pre-existing debt failures unrelated).
- **Committed in:** 1f8a3e9

### Task numbering note

Task 3's artifact (`backend/tests/test_rate_limit.py`) was necessarily produced as Task 2's TDD RED commit (the plan marks Task 2 `tdd="true"` with the same pure-function behavior tests). Task 3's verification (`pytest backend/tests/test_rate_limit.py -x`) passes standalone (4 passed); no additional commit was required. GSD TDD gate (test→feat commits in order) satisfied.

---

**Total deviations:** 3 auto-fixed (1 missing-critical, 2 blocking)
**Impact on plan:** All auto-fixes were required for the plan's behavior to work on the installed library version and for the existing suites to stay green. No scope creep; the plan's acceptance criteria are all met.

## Issues Encountered

- **Assumption A5 was real:** fastapi-limiter 0.2.0's documented-by-README API did not match the installed package (the rewrite removed `FastAPILimiter`). Resolved by reading the installed source (`fastapi_limiter/depends.py`, `pyrate_limiter/buckets/redis_bucket.py`, `limiter.py`) and adapting (see Decision above).
- **Full-suite seed debt:** 3 pre-existing failures in `test_seed_idempotency.py` (documented; residue = 8 candidate-origin nodes in the shared live DB). Verified via read-only query (3 Claim + 3 EvidenceFragment + 2 Source, origin='candidate') that 08-05 introduced none of them; not fixed (out of scope, shared DB).
- One provider-gate hiccup (a python -c inspection command was blocked/timed out waiting for approval) — worked around by reading the installed package sources directly, which was needed anyway for the A5 verification.

## User Setup Required

**External service requires manual configuration (already collected in 08-01's user_setup):** set `REDIS_URL` (Upstash `rediss://` TLS connection string) on the Render service to activate rate limiting. Empty/absent `REDIS_URL` disables rate limiting by design — the app boots and runs unthrottled. `get_redis()` is shared with the upcoming 08-06 graph-cache plan.

## Next Phase Readiness

- `backend/app/cache/redis_client.py::get_redis()` is the single Redis connection point the 08-06 graph query response cache plan will import — the shared-client requirement (INFRA-02) is pre-staged.
- `redis_url` config field is in place; the cache plan only adds its own lifespan/read/write wiring.
- Blockers: none for 08-06. The 3 `test_seed_idempotency.py` failures remain open pre-existing debt (deferred-items.md); the next integration plan should clean candidate/test nodes or reset the test DB before the seed module per the repo runbook.

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
