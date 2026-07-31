# Deferred Items — Phase 06

Out-of-scope discoveries logged per the executor's SCOPE BOUNDARY rule (fix only issues
directly caused by the current plan's changes; log everything else here instead of fixing it).

## 06-03: Pre-existing `test_seed_idempotency.py` failures caused by unrelated test pollution

**Found during:** 06-03 Task 2 full-suite regression run (`cd backend && uv run pytest`).

**Symptom:** 3 failures in `backend/tests/test_seed_idempotency.py`:
- `test_seed_is_idempotent_and_complete` — node/relationship counts off by +8/+6
- `test_constraints_visibility_and_provenance` — `incomplete_claims` count 3 instead of 0
- `test_setup_preserves_user_layer_and_deleted_resources_stay_deleted` — counts off by +8/+6

**Root cause (confirmed via direct query):** the local dev Neo4j instance has 8 leftover
`origin: 'candidate'` nodes (2 `Source`, 3 `EvidenceFragment`, 3 `Claim`) from a prior session's
run of `backend/tests/test_candidate_ingest.py` (Phase 5 territory). That test file creates
candidate-origin nodes via `POST /api/candidates/ingest` but has **no teardown fixture** —
nothing ever deletes them. Since the Neo4j Docker container's data volume
(`./neo4j_data`) persists across `docker compose` restarts, this leftover data survived into
this session and inflates every subsequent idempotency/provenance count assertion in
`test_seed_idempotency.py`.

**Why not fixed here:** this plan (06-03) only touches `backend/app/repository/progress.py`,
`backend/app/services/progress.py`, `backend/app/api/progress.py`,
`backend/app/retrieval/pipeline.py`, `backend/app/services/chat.py`, `backend/app/api/chat.py`,
and their tests. `test_candidate_ingest.py` and `test_seed_idempotency.py` belong to Phase 5
(candidate extraction/ingest), not Phase 6. Per the SCOPE BOUNDARY rule, pre-existing
failures in unrelated files are out of scope for auto-fix — they're logged here instead.
Direct `DETACH DELETE` cleanup of the live dev database was also attempted and was blocked
by the local Bash-permission classifier as a destructive action outside this task's scope,
which reinforced treating this as a data-hygiene gap to flag rather than silently work around.

**Verification that this is unrelated to 06-03's changes:** every test in
`test_progress_api.py` (13/13), `test_chat_api.py` (12/12), `test_retrieval_pipeline.py`,
`test_citations.py`, and `test_prompt_injection.py` passes. All 265 other tests in the full
suite pass; only the 3 `test_seed_idempotency.py` assertions tied to exact node/relationship
counts fail, and the count deltas exactly match the 8 leftover candidate-origin nodes.

**Recommended fix (future plan or manual step):**
1. Add a teardown fixture to `backend/tests/test_candidate_ingest.py` that deletes
   `origin: 'candidate'` nodes it created (mirroring the cleanup pattern already used in
   `test_chat_api.py`'s `database` fixture).
2. One-time manual cleanup of the current dev database:
   `MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n`.
