# Plan 05-02 SUMMARY — Candidate ingest API + candidate storage

**Phase:** 05-future-extraction-preparation  
**Plan:** 05-02  
**Status:** ✅ Complete  
**Date:** 2026-07-30

## Deliverables

1. **`backend/app/graph/candidates.py`** (new) — CandidateRepository with async Neo4j persistence:
   - `ingest_batch()` — atomic batch ingest via `execute_write`, deterministic SHA256-derived IDs, MERGE-based upsert
   - `get_candidate_claim()` — single candidate with linked sources and evidence
   - `list_candidate_claims()` — all candidates with optional spoiler filtering

2. **`backend/app/api/candidates.py`** (new) — Three routes:
   - `POST /api/series/{series_id}/candidates/ingest` — batch ingest with partial success
   - `GET /api/series/{series_id}/candidates` — list with optional `visible_until_order`
   - `GET /api/series/{series_id}/candidates/{claim_id}` — single candidate detail

3. **`backend/app/main.py`** (modified) — Wired candidate router

4. **`data/dexter/test/extraction_fixture.json`** (new) — 3 Dexter claims:
   - 2 S01E01-visible claims (vfo=1): Dexter conceals blood slides, Debra works with Dexter
   - 1 S01E02-invisible claim (vfo=2): Rudy dates Debra

## Verification Results

| Check | Status |
|-------|--------|
| CandidateRepository imports | ✅ |
| Router has 3 routes | ✅ |
| Router wire-in (app.include_router) | ✅ |
| OpenAPI schema loads with new routes | ✅ |
| Fixture parses as valid ExtractionBatchEnvelope (3 claims) | ✅ |
| Fixture has 2 claims at vfo=1, 1 at vfo=2 | ✅ |
| Deterministic IDs derived correctly | ✅ |

## Async Adaptation
All code adapted from plan's sync style to the existing codebase's async patterns:
- Routes are `async def`
- Database operations use `await`
- `execute_write` work function uses `async def work(tx, cmd)` pattern

## No Frontend Changes
No frontend files modified. ✅
