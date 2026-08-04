# Deferred Items — Phase 08

Out-of-scope discoveries logged per the GSD executor scope boundary (do not fix;
tracked here for the phase owner).

## 2026-08-04 — test_seed_idempotency.py hardcoded seed count vs live-DB residue

- **Symptom:** `test_seed_is_idempotent_and_complete` asserts
  `first_counts == second_counts == {"nodes": 41, "relationships": 26}` but the
  shared live Neo4j returns `{"nodes": 49, "relationships": 32}` — 8 nodes /
  6 relationships of residue. Fails both in full-suite order AND standalone.
- **Cause:** Pre-existing, already documented in `.planning/STATE.md`
  Blockers ("test-pollution debt in test_seed_idempotency.py (untorn-down
  candidate-origin fixture from test_candidate_ingest.py)") and the
  `hdgrafcehennemi` skill. Candidate-ingestion tests
  (`test_candidate_ingest.py`, `test_candidate_review.py` — whose
  `ingested_claim_id` fixture predates 08-03) leave `origin='candidate'`
  Claim/evidence/source rows in `series_dexter`; `setup_database()` counts
  them, breaking the exact-count assertions. NOT caused by the 08-03 code
  changes (the same ingestion + non-cleanup pattern existed before 08-03).
- **Fix path (not taken — out of 08-03 scope):** either make
  `test_seed_idempotency.py` count only seed-owned nodes (e.g. filter by the
  seeded series + origin='canonical'), or add teardown that deletes
  test-ingested candidate claims in `test_candidate_ingest.py` /
  `test_candidate_review.py`.
- **Status:** Open technical debt — mapped to no v1.3 requirement (STATE.md).
