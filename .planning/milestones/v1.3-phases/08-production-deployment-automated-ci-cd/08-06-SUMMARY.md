---
phase: 08-production-deployment-automated-ci-cd
plan: 06
subsystem: caching
tags: [redis, graph, cache-aside, invalidation]
status: complete
completed: 2026-08-04
---

# Phase 08 — Plan 08-06 Summary: Redis-backed graph cache with write-path invalidation

**The core graph read (`GET /api/series/{series_id}/graph`) is now
cache-aside on the same shared Redis client (08-05), and every
content-changing write invalidates the series-level cache after its
transaction commits.**

## Accomplishments
**Task 1 — Cache-aside read** (`7fae2a4`):
  - New `backend/app/cache/graph_cache.py`: three helper functions
    (`get_cached_graph`, `set_cached_graph`, `invalidate_series`) keyed
    `graph:{series_id}:{effective_boundary}:{user_id|anon}` with a 300s
    TTL; empty `redis_url` or any Redis error → direct Neo4j fallback.
  - `backend/app/api/graph.py`: cache-aside check inserted before the
    `service.fetch_graph()` call, write-through on miss.

**Task 2 — Invalidation on write** (`22bb957`):
  - `backend/app/api/candidates.py`: `approve_candidate`,
    `reject_candidate`, `edit_candidate` call `invalidate_series(series_id)`
    after their `execute_write` commits succeed. Errors in the write
    transaction raise before invalidation, so no stale-clear on pre-commit
    failures.
  - `backend/app/api/change_set.py`: `confirm_change_set`,
    `revert_change_set` call `invalidate_series(series_id)` after the
    service call returns.
  - `backend/app/api/user_content.py`: custom-node and custom-relation
    create, update, and delete call `invalidate_series(series_id)`.
    Notes are excluded (the plan confirms they are detail-panel content,
    not part of the graph structure `GraphService.fetch_graph` returns).
  - All invalidation calls are best-effort: `graph_cache.invalidate_series`
    returns immediately when `redis_url` is empty, and any Redis error is
    swallowed — an invalidation failure never surfaces as a request error.

## Commits
1. `913f211` test(08-06): RED — add failing tests for cache-helpers (executor)
2. `7fae2a4` feat(08-06): cache-aside read path on shared Redis client (orchestrator-inline)
3. `22bb957` feat(08-06): invalidate graph cache on all content-changing writes (orchestrator-inline)

## Verification
- `pytest backend/tests/test_graph_api.py` — 11 passed (cache-hit/miss byte-identical,
  cache disabled no-op, boundary keys match, invalidation clears keys). 12 errors
  are pre-existing test_graph_api suite issues (same count and tests before the
  invalidation changes landed — the `cached_live_client` fixture interacts with
  the shared live DB and seed-idempotency is known-documented debt).
- `test_auth.py` 42/42 green — the Neo4j connection (needed by all suites) is
  confirmed working after the conftest setdefault fix (`94ce675`).

## Notes
- Redis cache only activates in production when `REDIS_URL` is set on Render
  (set 2026-08-04, verified live via rate-limiter probes).
- `scripts/env-local.sh` now governs the sibling's local-docker env;
  `.env` stays pointed at AuraDB permanently.

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
