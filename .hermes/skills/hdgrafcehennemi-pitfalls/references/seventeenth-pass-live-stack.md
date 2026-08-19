# SEVENTEENTH PASS — Live-Stack Verification Lessons (2026-08-12)

Phase 09 close-out (plans 09-17/09-18) surfaced durable, reusable pitfalls.
All verified live; all fixed in commit 51d69c5.

## 1. Redis-backed features must degrade to no-op, never 500 (PROB-23)

`RateLimiter.__call__` called `limiter.try_acquire_async()` with NO error
handling. Any Upstash failure (free-tier daily quota exhaustion, connectivity
blip) raised unhandled → plain `500 Internal Server Error` on
`/api/auth/google` — even for an empty body that should 422. The graph cache
(`cache/graph_cache.py`) already degraded (`except Exception: return None` →
Neo4j); the limiter did NOT. Symptom: "Google OAuth breaks every ~24 hours" =
Upstash free-tier daily quota/connectivity reset cycle, NOT a Google problem.

**Rule:** every Redis-touching path must fail-open (log + continue) exactly
like the cache. That includes `init_rate_limiter()`: an unreachable Redis at
startup previously raised inside `lifespan()` → Render marks the whole deploy
failed.

**Live-probe signature:** `POST /api/auth/google` with `{}` returning 500
(should 422) = exception in a dependency BEFORE body validation. Route deps
order matters: logout (service+CSRF only) works while login (adds
`login_rate_limiter`) 500s → the limiter is the delta.

## 2. Neo4j driver drops None properties — seed nulls never create keys (01N52)

`episodes.json` carries `synopsis_visible_from_order: null` /
`image_visible_from_order: null` for S01E02/E03. The driver omits None
properties on write, so the KEY was never created on those nodes. Querying a
key that exists on NO node in the DB emits the 01N52 "property key does not
exist" warning class — and a reseed with the same data CANNOT fix it.

**Fix:** `load_seed_data()` materializes a null reveal-point as the episode's
own `visible_from_order` (null semantics = "reveal with the episode itself"),
so the keys always exist. Verify presence, not value:
`e.synopsis_visible_from_order IS NOT NULL` — note the old
`exists(variable.property)` syntax is REMOVED in Neo4j 2026 (42I52 error).

**Probe notifications:** `driver.execute_query(...)` then
`res.summary.gql_status_objects` (`.notifications` is deprecated). A benign
"successful completion" note is NOT an 01N52.

## 3. neo4j 6.2.0 removed the legacy `trust=` config key

`GraphDatabase.driver(uri, trust=TrustCustomCAs(...))` →
`ConfigurationError: Unexpected config keys: trust`. Use
`trusted_certificates=TrustCustomCAs(certifi.where())` — matches
`spoilerless/app/graph/database.py`'s Aura path. Check scripts for the old
key whenever the driver version bumps.

## 4. Live probing through the CSRF origin guard

Every cookie-authenticated state-changing route runs `verify_origin`. Plain
`curl` without Origin/Referer → `403 AUTH_ORIGIN_NOT_ALLOWED` (expected, not
the bug). For real probes always send
`-H "Origin: https://app.spoilerless.net"`. CORS preflight (OPTIONS) works
without the guard and confirms allowed origins.

Deployed-build awareness: `git ls-remote origin main` vs local HEAD — local
can be many commits ahead (unpushed) while Render serves origin. `/health`
`service` field = build marker (`hdgrafcehennemi-backend` old /
`spoilerless-backend` new), not a version.

## 5. Testing a class method that conftest patches (autouse fixture)

`conftest.py`'s autouse `_disable_rate_limiter` replaces
`RateLimiter.__call__` with a no-op for the whole suite. Calling
`await limiter(request, response=None)` in a unit test then hits the patched
no-op (`TypeError: got multiple values for argument 'response'`).

**Pattern:** capture the original at module import — fixtures run later —
then invoke it directly, bypassing the class-attribute patch:

```python
_ORIGINAL_CALL = RateLimiter.__call__   # module level, before fixtures
await _ORIGINAL_CALL(limiter, _Request(), response=None)
```

## 6. Sweep/audit fallbacks

`scripts/aura_graph_integrity.sh` and `docs/RUNBOOK.md` are referenced by
plans but may be ABSENT from the tree — fall back to the sweep's own
`--dry-run` + direct read-only Cypher via `execute_query`. Sweep count
REALITY vs RESEARCH estimate: live DB had 65 zombies / 8 sessions (not the
~3,855 predicted) — earlier sweeps had partially run; always trust the live
dry-run numbers, and verify the real admin user (ties = never a candidate)
plus the NEVER_DELETE constant separately.
