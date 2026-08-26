# Phase 12 Plan 15: Structural Cache Invalidation Summary

## Executed Tasks

### Task 1: Add the deep invalidate_series_cache facade
- Added `async def invalidate_series_cache(self, series_id: str) -> None:` facade to `GraphService` in `spoilerless/app/services/graph.py` delegating to `invalidate_series(series_id)`.
- Updated `spoilerless/app/cache/graph_cache.py` module docstring with the comprehensive call-site inventory for invalidation across API endpoints and noted the deliberate boundary (no write coordinator).

### Task 2: Replace the 12 call sites and fix the revert omission
- Removed direct imports of `invalidate_series` from `spoilerless.app.cache.graph_cache` across `spoilerless/app/api/candidates.py`, `spoilerless/app/api/change_set.py`, and `spoilerless/app/api/user_content.py`.
- Replaced all 12 existing invalidation call sites in `candidates.py` (4), `change_set.py` (2), and `user_content.py` (6) with `service.invalidate_series_cache(series_id)`.
- Fixed the LIVE staleness omission in `spoilerless/app/api/revisions.py`: `revert_revision` now invokes `service.invalidate_series_cache(series_id)` immediately after `execute_write`.

### Task 3: Pin invalidation semantics and the revert regression
- Added `test_invalidate_series_facade_epoch_bump_and_delete` and `test_invalidate_series_cache_swallows_redis_errors` in `spoilerless/tests/test_visualization_cache.py`.
- Added `test_revert_invalidates_series_cache` in `spoilerless/tests/test_revisions.py` asserting that reverting a revision triggers invalidation for the scratch series ID.

## Verification Results

- `from spoilerless.app.main import app` imports cleanly (exit 0).
- `grep -rn "from spoilerless.app.cache.graph_cache import invalidate_series" spoilerless/app/api` returns 0 results.
- `grep -rn "invalidate_series_cache" spoilerless/app/api` returns 13 total call sites (12 migrated + 1 revert).
- `test_visualization_cache.py` (14 passed).
