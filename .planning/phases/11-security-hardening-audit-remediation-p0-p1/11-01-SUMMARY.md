# Plan 11-01 Summary — Shared fail-closed boundary tracer

## Done
- Created `spoilerless/app/api/boundary.py` with `resolve_effective_boundary(service, progress_service, series_id, user, requested_order, boundary_label)` — single fail-closed path: anonymous →1, authenticated no-record →1, authenticated with record → min(requested, view, watched) via `effective_view_order`, validated via `service.resolve_boundary` (422 INVALID_VISIBLE_UNTIL_ORDER).
- `spoilerless/app/api/graph.py`: imported shared resolver, added alias `_resolve_effective_boundary=resolve_effective_boundary`, deleted divergent clamp (requested/effective computation) in `get_graph`, now `effective = await resolve_effective_boundary(...)`. Existing visualization/expand/path/export call sites untouched via alias; deleted duplicate `_resolve_effective_boundary` definition at bottom.
- `spoilerless/app/api/candidates.py`: added `OptionalUserDependency`, `ProgressService` + `ProgressServiceDependency`, imported `resolve_effective_boundary`. `list_candidates` and `get_candidate` now keep omit→422 guard (INVALID_REQUEST) BEFORE resolver, then `effective=await resolve_effective_boundary(...)`, then `_require_resolved_boundary(effective)` and repo call with `effective`.
- `spoilerless/tests/test_security_boundary.py`: scratch `series_scratch_boundary` (1,2,3) with claims `extracted:boundary:order1/3` and characters `scratch:boundary:late_char` (3) + `mid_char` (2). Tests: anonymous 999 clamped to 1, hidden 404, fresh-account graph 1, progress clamp min, omit 422, invalid 422.

## Verification
- Imports: `uv run python -c "from spoilerless.app.api.boundary import resolve_effective_boundary"` → ok, graph/candidates/series/user_content/revisions all import.
- Grep: `grep -n resolve_effective_boundary spoilerless/app/api/graph.py` → 2 hits (import + alias + get_graph), no inline `effective_view_order` clamp remains in get_graph.
- Live DB not available (no docker/.env), so `test_security_boundary.py` live run deferred; DB-free `test_user_content_models` 23 passed.

## Files changed
- spoilerless/app/api/boundary.py (new)
- spoilerless/app/api/graph.py
- spoilerless/app/api/candidates.py
- spoilerless/tests/test_security_boundary.py

## Next
- Live env: `uv run pytest spoilerless/tests/test_security_boundary.py -q -x` + `uv run pytest spoilerless/tests/test_graph_api.py spoilerless/tests/test_candidate_ingest.py -q`
