# Plan 12-10 Summary — Consolidate share boundary clamping into resolve_effective_boundary

Consolidated share link creation boundary resolution into `resolve_effective_boundary` and extracted candidate omitted-boundary validation into `require_boundary`.

## What Landed

**Task 1 — Replace inline share clamp with resolve_effective_boundary**
- Updated `spoilerless/app/api/share.py`:
  - Replaced inline clamp logic (progress lookup + min + `effective_view_order` + `resolve_boundary` + 422) in `create_share_link` with a single call to `resolve_effective_boundary(service, progress_service, payload.series_id, user, payload.visible_until_order)`.
  - Removed unused import `from spoilerless.app.spoiler.policy import effective_view_order`.
- Updated `spoilerless/app/api/boundary.py`:
  - Updated module docstring to explicitly include `share (create_share_link)` in the D-01 gated-route set.

**Task 2 — Extract require_boundary and deduplicate candidates guards**
- Added `require_boundary(visible_until_order: int | None) -> int` to `spoilerless/app/api/boundary.py` raising 422 `INVALID_REQUEST` when `visible_until_order` is missing.
- Updated `spoilerless/app/api/candidates.py`:
  - Replaced inline missing-boundary check blocks with `visible_until_order = require_boundary(visible_until_order)`.

**Task 3 — Pin clamp/422 behavior with tests and update wave inventory**
- Added scratch-series backed unit tests in `spoilerless/tests/test_share_api.py`:
  - `test_create_share_clamps_to_persisted_progress` (clamps order past progress to effective view order 2).
  - `test_create_share_no_progress_fails_closed_to_one` (fails closed to order 1 without progress record).
  - `test_create_share_non_persisted_order_422` (returns 422 `INVALID_VISIBLE_UNTIL_ORDER` if clamped order is not a persisted episode).
- Updated `.planning/STATE.md` D-01 gated-route decision log entry to append `share`.

## Verification
- Ran backend test suite across share, boundary, candidates, and OpenAPI contract tests:
  - `pytest spoilerless/tests/test_share_api.py spoilerless/tests/test_security_boundary.py spoilerless/tests/test_openapi_contract.py spoilerless/tests/test_candidate_ingest.py spoilerless/tests/test_candidate_review.py` → **48 passed in 238.32s**

## Self-Check: PASSED
- `spoilerless/app/api/share.py`
- `spoilerless/app/api/boundary.py`
- `spoilerless/app/api/candidates.py`
- `spoilerless/tests/test_share_api.py`
- `.planning/STATE.md`
