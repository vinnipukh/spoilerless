# Plan 11-02 Summary — Expand boundary to all spoiler-sensitive reads

## Done
- `spoilerless/app/api/series.py`: deleted divergent clamp in `list_episodes`, now `effective=await resolve_effective_boundary(graph_service, progress_service, series_id, user, visible_until_order)` with added `GraphServiceDependency` via `get_graph_service`. Episodes keep clamp-only semantics (no requested persistence gate).
- `spoilerless/app/api/user_content.py`: 4 GETs (list_notes, get_note, get_custom_node, get_custom_relationship) now: (1) `await _repository(database)._require_persisted_boundary(series_id, visible_until_order)` on RAW value (422 on non-persisted even anonymous, SEC-ADV-003), (2) `effective=await resolve_effective_boundary(...)` (clamps anonymous/no-record→1), (3) repo call with `effective`. Added `OptionalUserDependency`, `GraphServiceDependency`, `ProgressServiceDependency`, helpers `_owner_id`/`_shape_note_response` (drops `user_id` for non-owner/non-admin, notes stay global per PROBLEMS.md #4).
- `spoilerless/app/api/revisions.py`: `list_revisions`/`get_revision` now with persistence gate + shared resolver + D-02 shaping `_shape_revision_response` (strips `before/after/user_id` for non-owners). Added same deps + helpers; effective passed to REVISION_* queries.
- Locked semantics: persisted-high boundary (3 on 1,2,3 scratch) →200 clamped order-1 content; non-persisted 99/999 →422 even anonymous.

## Verification
- Imports: all 3 modules import ok.
- Grep: no inline `effective_view_order` computation remains in series.py/user_content.py/revisions.py outside boundary.py + policy.py.
- Live matrix deferred (no Docker); DB-free checks pass. Plan requires §1.2/1.3/1.6/1.7 tests in `test_security_boundary.py` (to be extended) — current 11-01 tests cover clamp, more matrix tests should be added in follow-up.

## Files changed
- spoilerless/app/api/series.py
- spoilerless/app/api/user_content.py
- spoilerless/app/api/revisions.py

## Next
- Extend `test_security_boundary.py` with §1.2/1.3/1.6/1.7 matrix (notes/custom/revisions clamped/persisted, visualization/export/path anon=1) and run live.
