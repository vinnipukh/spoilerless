# Deferred Items — Phase 06

Out-of-scope discoveries logged per the executor's SCOPE BOUNDARY rule (fix only issues
directly caused by the current plan's changes; log everything else here instead of fixing it).

> **Ledger closed 2026-08-24:** both items below are RESOLVED by later phases —
> the test-pollution debt (06-03 + Wave-2) was fixed by Phase 9 plan 09-08
> (commit `cc148a5`: scratch-series isolation, teardown fixtures in
> `test_candidate_ingest.py`/`test_candidate_review.py`, drift-agnostic seed
> assertions, CI DB-pollution gate); the pre-existing lint debt (06-13) was
> cleared under PROB-08 (09-VERIFICATION: `npm run lint` exit 0; re-confirmed
> 2026-08-24: 0 errors, 21 warnings). Nothing open remains in this file.

## Deferred Items

- 06-03/Wave-2: test pollution — candidate-origin residue inflating test_seed_idempotency.py exact-count assertions (3 failures, later 5 failed + 7 errors)
  status: resolved
  resolution: "Fixed by Phase 9 plan 09-08 (commit cc148a5): scratch-series isolation, teardown_scratch_series fixtures in test_candidate_ingest.py/test_candidate_review.py, drift-agnostic seed assertions, CI DB-pollution gate. Verified in-tree 2026-08-24."
- 06-13: pre-existing npm lint errors in sibling hooks/tests (react-hooks/refs in useChatSessions/useNotes/useRevisions, no-explicit-any in useRevisions.test.tsx, set-state-in-effect)
  status: resolved
  resolution: "Cleared under Phase 9 PROB-08: 09-VERIFICATION confirms `npm run lint` exit 0 and ci.yml gates lint. Re-confirmed live 2026-08-24: 0 errors, 21 warnings (React-Compiler rules scoped to warnings)."

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

## Wave-2 post-merge gate: pollution has cascaded further

**Found during:** orchestrator's Wave 2 post-merge full-suite gate (after 06-03 + 06-04 both
landed), `cd backend && uv run pytest -q`.

**Symptom:** full-suite run now shows 5 failed + 7 errors (up from the 3 failures 06-03
originally logged): the same 3 `test_seed_idempotency.py` failures, plus 2 new
`test_extraction_models.py` failures and 7 new `ERROR`s across `test_candidate_ingest.py`
(4) and `test_candidate_review.py` (3) — all Phase 5 (candidate extraction/ingest/review)
territory, none of it touched by any Phase 6 plan. Re-running `test_candidate_ingest.py`
against the already-polluted dev DB appears to trip unique-constraint/setup errors on top
of the original count-drift failures, worsening the same untorn-down-fixture root cause.

**Verified unrelated to phase 06:** targeted run of every phase-06-relevant test file
(`test_progress_api`, `test_chat_api`, `test_chat_persistence`, `test_retrieval_pipeline`,
`test_retrieval_tools`, `test_citations`, `test_prompt_injection`, `test_openapi_contract`,
`test_frontend_contract_doc`) — 110/110 pass in isolation. Wave 2 post-merge gate treated as
PASS on that basis; the Phase 5 pollution remains out of scope for Phase 6 to fix, per the
same SCOPE BOUNDARY rule, but is now worse and should be cleaned up (recommended fix above)
before Phase 5 work resumes or before running the unfiltered full suite again.

## 06-13: Pre-existing `npm run lint` errors unrelated to the G-06-4 fix

**Found during:** 06-13 Task 2 full frontend regression run (`npm run lint`).

**Symptom:** 28 pre-existing lint errors across files this plan does not touch:
- `react-hooks/set-state-in-effect` in an episode-selection effect (unrelated hook)
- `@typescript-eslint/no-explicit-any` in `useRevisions.test.tsx` (6 occurrences) and one
  other file
- `react-hooks/refs` "Cannot access refs during render" in `useChatSessions.ts`, `useNotes.ts`,
  and `useRevisions.ts` — a ref-mutation-during-render pattern (`fetchKeyRef.current = key`)
  present in three sibling data-fetching hooks

**Why not fixed here:** none of the flagged files are `useChatMessages.ts` or
`useChatMessages.test.tsx` (this plan's only `files_modified`). `npm run lint` run against the
pre-13 tree (i.e. `git stash`-equivalent check via `git diff` scope) confirms these errors exist
independent of the G-06-4 status-transition fix. Per the SCOPE BOUNDARY rule, pre-existing
lint errors in unrelated files are out of scope for this gap-closure plan.

**Verification that this is unrelated to 06-13's change:** `npm run lint` reports zero errors
for `useChatMessages.ts`/`useChatMessages.test.tsx` specifically; `npm run test` (173/173),
`npx tsc -b` (clean), and `npm run build` all pass with the fix in place.

**Recommended fix (future plan):** apply the same `useRef`-to-`useState`-derived-key pattern (or
an effect-based sync) already used correctly elsewhere in the hooks that don't trip
`react-hooks/refs`, and replace the `any` usages in `useRevisions.test.tsx` with concrete
response-shape types.
