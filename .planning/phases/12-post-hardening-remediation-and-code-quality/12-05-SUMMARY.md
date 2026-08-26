---
phase: 12-post-hardening-remediation-and-code-quality
plan: 05
subagent: executor (died at 50-call cap post-verification; orchestrator committed remaining tests + summary)
---

# Plan 12-05 Summary — Runtime resilience + error-code compliance

## What was built

1. **THERMO-P2-02** (commit `6303a2c`): `spoilerless/app/domain/settings.py::_host_is_blocked` now resolves DNS via `_resolve_host_with_timeout` — ThreadPoolExecutor, 1.0s budget; unresolvable/timed-out host fails closed (blocked). IP-literal blocking untouched.
2. **THERMO-P2-04 + P3-03** (commit `16c0307`): `RateLimiter` lazily re-attempts binding on every request when unbound (`_lazy_init()` via get_redis) — a startup Redis blip no longer latches 503 forever. Extracted `_handle_unavailable_redis(settings)` policy: no redis_url → silent off; non-production or fail_open → warn + allow; production fail-closed → 503 `RATE_LIMIT_UNAVAILABLE`. Code registered in `core/errors.py`; BodySizeLimitMiddleware emits uppercase `PAYLOAD_TOO_LARGE`.
3. **Tests** (commit `test(12-05)`): +112 lines in `spoilerless/tests/test_rate_limit.py` covering the lazy re-init retry path after outage (fake limiter binds on first request).

## Verification

- `pytest spoilerless/tests/test_rate_limit.py -q` → 11 passed
- `pytest spoilerless/tests/test_visualization_cache.py spoilerless/tests/test_security_boundary.py -q` → 21 passed
- Working tree clean for `spoilerless/app` at commit time.

## Deviations

None material. Executor hit the tool-call cap after its final verification run; orchestrator committed the already-green test file and wrote this SUMMARY.

## Self-Check: PASSED

Key files:
- spoilerless/app/domain/settings.py · spoilerless/app/services/rate_limit.py · spoilerless/app/core/errors.py · spoilerless/app/main.py
- spoilerless/tests/test_rate_limit.py
