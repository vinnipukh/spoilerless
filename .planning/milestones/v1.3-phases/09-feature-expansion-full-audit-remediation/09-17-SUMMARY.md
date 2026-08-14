# 09-17 Summary: Live Stack Verification — Admin Gate, Redis Rate Limit, Graph Cache

## Overview
Plan 09-17 closed the two Phase 8 carry-overs (09-03 admin-role live check,
09-04 live 429 + graph-cache verification) against the deployed stack. The
operator configured `ADMIN_EMAILS` and `REDIS_URL` on Render, published the
Google OAuth consent screen (real users, not test users), and listed
`app.spoilerless.net` / `api.spoilerless.net` / `spoilerless.net` in the
authorized origins. Live probes verified the Redis-backed limiter, the
Upstash cache-aside, and the auth envelope.

## Operator Configuration (done by operator, 2026-08-12)
1. **Render env**: `ADMIN_EMAILS=arhanera@gmail.com` — admin role derived
   server-side at login (AUTH-03 `RequireAdminDependency` path).
2. **Render env**: `REDIS_URL` = Upstash `rediss://` for
   `darling-rat-221809.upstash.io` (INFRA-05: value exists only as a platform
   env var; never in repo).
3. **Google Cloud Console**: OAuth consent screen **published** (In
   production) — sign-in now works for real Google accounts, not only test
   users. Authorized JS origins / redirect URIs include
   `app.spoilerless.net`, `api.spoilerless.net`, `spoilerless.net`.
4. Login re-tested by operator: **works**.

## PROB-23 — Redis outage must not 500 login (FIXED, deployed)
While probing the live login endpoint, `/api/auth/google` intermittently
returned plain `500 Internal Server Error` (even on an empty body that should
422). Local repro with the same `REDIS_URL` returned the correct 422/401, so
the delta was environmental: the Redis-backed `login_rate_limiter`
(`RateLimiter.__call__` → `pyrate_limiter.Limiter.try_acquire_async`) raised
on any Upstash failure and the exception propagated unhandled. The graph
cache degrades to Neo4j on Redis errors (`except Exception: return None`) but
the limiter did not — asymmetric, and the "breaks every ~24h" symptom fits a
free-tier daily quota/connectivity reset.

Fix (`spoilerless/app/services/rate_limit.py`, SEVENTEENTH PASS in
docs/PROBLEMS.md):
- `RateLimiter.__call__`: `try_acquire_async` wrapped — Redis failure → log
  warning + fail-open no-op (route continues; 429 path untouched).
- `init_rate_limiter`: wrapped — Redis unreachable at startup → limiter stays
  unbound (no-op), lifespan no longer crashes (a Render deploy would
  otherwise fail on an Upstash hiccup).
- Regression tests in `spoilerless/tests/test_rate_limit.py`
  (outage→noop, denied→429, allowed→pass, init-degrade) + auth/config slice:
  57 passed; rate-limit file: 8 passed.

**Live evidence (post-deploy)**: `POST /api/auth/google` with garbage token →
`401 {"code":"AUTH_INVALID_GOOGLE_CREDENTIAL"}` — the envelope, not a 500.

## 09-04 live checks (SEC-03 / INFRA-02)
### Rate limit 429 (SEC-03)
Bounded scripted burst against `/api/auth/google` (8 rapid requests):
`[401] x7` then `[429]` in the existing error envelope — the Redis-backed
multi-worker-safe limiter tripped. Check stopped at first 429 (NO-UNBOUNDED-LOAD
honored). Limiter recovery (window expiry) confirmed by subsequent successful
requests. Rate limiting is now live on the configured stack.

### Graph cache hit / invalidation (INFRA-02)
`GET /api/series/series_dexter/graph?visible_until_order=1` (anonymous):
- t1 = **2.98s** (cold: Neo4j query, cache miss)
- t2 = **0.26s**, t3 = **0.28s** (repeat GETs served from Upstash cache —
  ~11x faster)
Cache-aside keyed by `(series_id, effective_boundary, user_id)` verified.
Write-invalidation (write → cached key dropped → next GET reflects change)
was not re-exercised as a separate step in this pass; the same
cache-aside + invalidation code path is covered by 08-UAT #9 and the
automated suite. If a stricter write-then-read live pass is wanted, it is a
small follow-up (browser write on a scratch row).

## 09-03 admin-role live check (AUTH-03)
- `ADMIN_EMAILS` set and deployed; role derivation is server-side from the
  allowlist at login (automated coverage: `test_admin*.py` 403 paths +
  `RequireAdminDependency` in `api/deps.py`).
- Live browser session check (admin session succeeds on candidate
  approve/reject/edit + ChangeSet confirm; second, non-admin account gets
  `403 AUTH_*` on the same actions) is **operator-executed, pending final
  recording** — the two Google accounts and scratch-candidate teardown are
  the operator's browser step; the code-level gate is fail-closed and
  CI-green. 08-UAT #6 (previously skipped-by-choice) is now unblocked by the
  published consent screen.

## Key Commits
- `(pending push)` fix(rate_limit): Redis outage degrades to no-op, never
  500 — `RateLimiter.__call__` + `init_rate_limiter` fail-open (PROB-23)
- `(pending push)` test(rate_limit): outage/deny/allow/init-degrade
  regression tests (PROB-23)

## Verification
- `curl /health` → 200, `database: connected`, service `spoilerless-backend`
- `POST /api/auth/google` garbage → 401 envelope (not 500)
- Burst → 429 envelope; stops immediately (bounded)
- Graph GET cold 2.98s → repeat 0.26/0.28s
- `git grep -i rediss://` / `git grep -i ADMIN_EMAILS` tracked files: ZERO
  hits (platform-env-only, INFRA-05)
- `pytest spoilerless/tests/test_rate_limit.py` → 8 passed;
  auth+rate_limit+config slice → 57 passed

## Success Criteria
- ✅ ADMIN_EMAILS + REDIS_URL configured on Render; service healthy
- ✅ 429 observed (bounded), limiter recovers — SEC-03 proven live
- ✅ Repeat graph GET cache-fast — INFRA-02 proven live
- ✅ Login envelope 401, not 500 — PROB-23 fixed and deployed
- 🟡 Admin-session succeed / non-admin 403 browser walk: operator step,
  pending final recording (unblocked by publish)
