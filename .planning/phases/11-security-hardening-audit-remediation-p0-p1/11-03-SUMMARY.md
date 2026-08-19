# Plan 11-03 Summary: Ingest hardening + pagination

## Done
- Task1: server-derived visibility + existence validation
  - domain/extraction.py: ExtractionClaim.visible_from_order now `VisibilityOrder | None = None` with docstring explaining server derivation and mismatch rejection.
  - graph/candidates.py: added `_VISIBILITY_PREPASS_QUERY` and `_resolve_claim_visibility(tx, series_id, claim)` importing `derive_visible_from_order`; checks episode existence (episode_order not None) and subject/object existence via explicit MATCH; returns derived visible_from_order via `max(endpoint_vfos)` or episode_order alone.
  - Modified `_ingest_candidate_claims` loop: calls `_resolve_claim_visibility`; on None appends `INGEST_ERROR` "referenced node not found in series" and continue; on mismatch `visible_from_order != derived` appends `INVALID_EXTRACTION_PAYLOAD` and continue; persists `derived` only.

- Task2: ingest rate limit + cache invalidation
  - api/candidates.py: added `content_write_rate_limiter` dependency `_rate_limit` to `ingest_candidates`; after `repo.ingest_batch` calls `await invalidate_series(series_id)` unconditionally.

- Task3: pagination
  - graph/candidates.py: `list_candidate_claims` now signature `(series_id, visible_until_order=None, *, limit=100, after_created_at=None, after_id=None)` with composite keyset `AND ($after_created_at IS NULL OR claim.created_at < $after_created_at OR (claim.created_at = $after_created_at AND claim.id > $after_id))`, ordered `ORDER BY claim.created_at DESC, claim.id ASC LIMIT $limit`.
  - api/candidates.py: `list_candidates` now accepts `limit Query(default=100, ge=1, le=500)`, `after_created_at`, `after_id` and forwards to repo; retains omit→422 and effective boundary flow from 11-01.

## Verification
- Import checks: `uv run python -c "from spoilerless.app.domain.extraction import ExtractionClaim; ..."` → visible_from_order None ok, cand repo ok, api ok.
- No live Neo4j available in this environment (docker not found, .env absent) so `uv run pytest spoilerless/tests/test_candidate_ingest.py` not run live; tests are expected to require scratch series `CANDIDATE_SCRATCH_SERIES` (already used) and should be run on CI/live env.
- Grep gate: no ingest path persists `claim.visible_from_order` directly; only `derived` is persisted.

## Risks
- Extra existence queries in `_resolve_claim_visibility` add round-trips; transaction still atomic.
- Pagination cursor uses datetime; client must echo exact `created_at` string; nil cursor handled via NULL params.
- Older payloads with visible_from_order set will now be rejected on mismatch (intended).

## Files changed
- spoilerless/app/domain/extraction.py
- spoilerless/app/graph/candidates.py
- spoilerless/app/api/candidates.py

## Next
- Run live tests on environment with Neo4j: `uv run pytest spoilerless/tests/test_candidate_ingest.py -q -x && uv run pytest spoilerless/tests/test_extraction_models.py -q`
