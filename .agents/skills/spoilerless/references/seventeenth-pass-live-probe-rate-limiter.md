# Live-probe recipe — deployed backend "X is broken" + rate-limiter degrade class (SEVENTEENTH PASS)

## Context
User reported "Google OAuth breaks again, seems to break every 24 hours."
Root cause was NOT Google — it was the Redis-backed rate limiter 500ing
login. Session proved: probe live FIRST, deployed build = origin/main, NOT
local HEAD (branch routinely 40+ commits ahead; 09-16 SUMMARY claimed a push
to 26224e68 but origin/main tip was ef91fee — always verify `git ls-remote origin main`).

## Live-probe sequence (reproducible recipe)
1. CSRF guard: state-changing probes MUST send
   `-H "Origin: https://app.spoilerless.net"`. Without it you get
   `403 AUTH_ORIGIN_NOT_ALLOWED` — expected, not the bug.
2. Map route-by-route: 500 on a should-422 request (e.g. `{}` body) means the
   exception fires in a DEPENDENCY before body validation. Compare siblings:
   logout POST → 204, /me → 401; the only dep login has that logout lacks =
   `login_rate_limiter`. Isolated by elimination.
3. Local repro: same code + no REDIS_URL → 422/401 correct = env difference.
   Same REDIS_URL as shell env (never repo — INFRA-05) → still correct = URL
   is not the problem. Wrong password → startup crash in lifespan
   (`init_rate_limiter` raises) = proves the Redis init path, and proves a
   bad URL kills the whole Render deploy (not just the feature).
4. Burst probe: 8 rapid POSTs → `[401]×7 [429]` = Redis limiter bound and
   working. 429 IS the success signal. After burst, limiter window (10/5min
   per IP) stays tripped — wait it out before re-testing.

## Root cause class — Redis-backed feature must degrade, never 500 (PROB-23)
`RateLimiter.__call__` had NO try/except around `try_acquire_async`. Any
Redis error — Upstash free-tier DAILY quota reset (the "breaks every 24
hours" pattern), connection drop, auth failure — propagated as an unhandled
500 on login/chat-send/content-write routes.

The graph cache (`cache/graph_cache.py`) degrades gracefully
(`except Exception: return None` → query Neo4j); the limiter did NOT. That
asymmetry hid the failure class: one Redis-backed feature degrades, siblings
don't. REGEX OF THE CLASS: when adding degrade-gracefully to one
Redis-backed feature, check sibling features (rate limiter, session sweep,
share sweep) for the same unhandled-raise path.

Fix (applied, local-only — NOT yet pushed at session end):
- `spoilerless/app/services/rate_limit.py::RateLimiter.__call__`: try/except
  around try_acquire_async → log warning, fail-open (skip throttling for
  that request). 429 path untouched.
- `init_rate_limiter()`: try/except → limiter stays unbound (no-op) and app
  still serves; matches documented "empty redis_url disables rate limiting"
  contract. Without this, an Upstash hiccup at startup raises inside lifespan
  and Render treats the whole deploy as failed.
- Tests: `spoilerless/tests/test_rate_limit.py` — fake limiters
  (_RaisingLimiter/_DenyingLimiter/_AllowingLimiter), monkeypatched
  RedisBucket.init/get_redis. No live Redis needed.

## Test-writing trap: conftest patches RateLimiter.__call__
conftest's autouse `_disable_rate_limiter` fixture does
`monkeypatch.setattr(RateLimiter, "__call__", _noop)` — so a unit test that
calls `await limiter(request, response)` directly gets
`TypeError: _noop() got multiple values for argument 'response'` (the patched
function is a plain def, not a bound method). Workaround used:
```python
_ORIGINAL_CALL = RateLimiter.__call__   # capture at module import (fixture runs later)
await _ORIGINAL_CALL(limiter, _Request(), response=None)
```
Any future `__call__`-level unit test on a conftest-patched dependency needs
the same import-time capture.

## Full-suite hang diagnostic — usually SLOW, not hung
Full `pytest spoilerless/tests` (601 tests) takes **~43 min** against local
docker: per-test `setup_database` re-seeds (~12s each) in the
change-set/chat/candidate files plus a fresh TestClient + driver per test.
`pytest -q | tail` shows NOTHING until the very end → looks hung. Diagnose
before killing: run `-v > log` and tail the log (lines advancing = working),
sample `grep -c PASSED` twice 30s apart, and check the pytest python PID's
CPU (near-zero + log moving = slow-but-working; near-zero + log frozen =
truly hung on I/O — e.g. docker down → connection timeouts). Install
`pytest-timeout` (`uv pip install pytest-timeout`) and run with
`--timeout=120 --timeout-method=thread` to convert hangs into named
failures; note the thread method does NOT cover session/module fixtures.
Resolution of the 17th-pass "leftover hang": no hang existed — the full run
finished 599 passed / 1 skipped / 1 failed, and the single failure was stale
hotlink seed data on local docker (fixed by the self-healing upsert in
seventeenth-pass-reseed-sweep-env.md).

## Verification evidence
- Live before: `/api/auth/google` `{}` → 500 (should be 422);
  `{"credential":"x"}` → 500; logout → 204; /me → 401.
- Local before: 422 / 401 correct.
- Local with same Upstash URL: 422 / 401 correct (URL valid).
- Local with wrong password: app fails to start (AuthenticationError in
  RedisBucket init via lifespan).
- Live after user set REDIS_URL on Render: `[401]×7 [429]` burst = limiter
  live; login functional.
