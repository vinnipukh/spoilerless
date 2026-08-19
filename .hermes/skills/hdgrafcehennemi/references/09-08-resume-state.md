# 09-08 Resume State — test isolation + deterministic suite (budget-handoff mid-Task-1)

Plan 09-08 (wave 3, PROB-06/18/20/22: scratch-series isolation, seed-drift fixes,
zombie sweep script, CI pollution gate, core-module unit tests, startup schema
check) executor died at the tool-iteration budget with Task 1 fully edited but
UNCOMMITTED (zero commits landed). HEAD `075a222` on main.

## Repo state at handoff
- Pre-existing dirty/untracked (do NOT touch/stage): `.planning/config.json`,
  `.hermes/`, `docs/FEATURE-IDEAS.md`, `docs/FEATURE-RESEARCH.md`,
  `scripts/sweep_error_codes_09_05.sh`.
- Uncommitted Task-1 edits (stage explicitly; commit
  `test(09-08): scratch-series isolation + state-independent seed assertions (PROB-06/22)`):
  1. `spoilerless/tests/conftest.py` — added `CANDIDATE_SCRATCH_SERIES = "series_scratch_candidates"`,
     `REVIEW_SCRATCH_SERIES = "series_scratch_review"`,
     `bootstrap_scratch_series(series_id, episode_orders=(1,2,3))`
     (MERGE Series + Episode nodes + PART_OF rels so D-09 boundary validation resolves),
     `teardown_scratch_series(series_id)` (series-scoped delete + origin='candidate'
     residue + UserSeriesProgress rows; fresh driver/loop via `asyncio.run`).
  2. `spoilerless/tests/test_candidate_ingest.py` — `TestCandidateIngest.SERIES_ID` +
     `TestCandidateReadBoundary.SERIES_ID` → `CANDIDATE_SCRATCH_SERIES`; module-scoped
     `live_client` bootstraps scratch before TestClient and tears down in `finally`.
     Parse OK; `rg 'series_dexter'` = 0.
  3. `spoilerless/tests/test_candidate_review.py` — same with `REVIEW_SCRATCH_SERIES`;
     both `/ingest` call sites f-string'd to the scratch id. Parse OK; `rg 'series_dexter'` = 0.
  4. `spoilerless/tests/test_seed_idempotency.py` — (a) `test_seed_is_idempotent_and_complete`:
     `first_counts == second_counts` + full snapshot equality + per-label superset vs
     `load_seed_data()` counts + PART_OF/PRECEDES/SUPPORTED_BY/REFERS_TO invariants
     (exact 290/308 gone); (b) both constraint-set asserts → `expected_labels <= unique_labels`;
     (c) `create_note`/`create_custom_node` called with `"user:seed-test"` as user_id
     (3-arg 09-03 signature); (d) `test_setup_preserves_user_layer...`: canonical-layer
     superset checks + `second_report == first_report` + tolerant incomplete-claims assert.

## Verified baseline (pre-edit runs; local docker `hdgrafcehennemi-neo4j`,
`unset PYTHONPATH` + NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j)
- `test_retrieval_tools.py`: 10 failed / 29 passed — all the stale-visibility class:
  - `test_search_entities_returns_visible_matches_in_stable_order` — "morgan" now matches 4
    (dexter/debra/doris/harry, all vfo=1)
  - `test_search_entities_hides_future_matches`, `test_search_entities_mixed_query_returns_only_visible_matches`,
    `test_search_entities_fuzzy_partial_match_cannot_reveal_hidden_entity` — harry/doris visible at 1 now
  - `test_find_path_returns_visible_path`, `test_find_path_clamps_requested_hops_to_server_ceiling` —
    BFS edge is now `dexter:claim:s01e01:debra_trusts_dexter`, not `dexter_debra_family`
  - `test_get_claims_hidden_and_missing_ids_identical`, `test_get_entity_hidden_character_behaves_as_nonexistent`,
    `test_get_neighborhood_excludes_hidden_claims`, `test_get_neighborhood_hidden_entity_fails_closed` — HARRY probes
- `test_seed_idempotency.py`: 4 failed / 6 passed — 2 count-drift (290/308 and 573/297/309)
  + 2 TypeError from 2-arg `create_note`/`create_custom_node` calls.

## Verified seed facts (do NOT re-derive)
- Characters: `paul_bennett` vfo=2, `rudy_cooper` vfo=3 are the only characters hidden at
  boundary 1. All Morgans incl. harry/doris vfo=1; rita/astor/cody/batista/doakes vfo=1.
- Claims: the only paul claim is `dexter:claim:s01e02:rita_paul_family` vfo=2.
  `dexter:claim:s01e01:debra_trusts_dexter` vfo=1 exists (broke the old find_path edge assert).
- Search-query probes (labels): "bennett" → rita(1)/paul(2)/astor(1)/cody(1); "aul" → only paul;
  "paul" → only paul; "morgan" → 4 (all vfo=1). SEARCH_ENTITIES_QUERY returns `visible_from_order`
  so ordering asserts can key on `(visible_from_order, id)`.
- `api/candidates.py` list/get 422 any boundary that isn't a persisted episode order of THAT
  series (D-09 `_require_resolved_boundary` via `GraphService.resolve_boundary`); approve/reject/edit
  and the revisions routes do NOT validate the boundary.
- Ingest-created nodes (Source/EvidenceFragment/Claim) and Revision nodes all carry `series_id`,
  so a series-scoped DETACH DELETE covers everything a candidate test creates.

## Design decisions already made (for continuation)
- Scratch bootstrap + teardown live in conftest.py as plain functions; candidate files'
  module-scoped `live_client` fixture calls them in try/finally. Function-scoped
  user/admin/ingest_session fixtures unchanged (they already delete their own AppUser+Session
  via google_sub).
- Task 2: `spoilerless/scripts/zombie_sweep.py` (dry-run default, `--execute` flag, module
  constant `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11` + optional env override, delete only degree-0
  AppUsers / expired-or-revoked-or-orphaned Sessions, print before/after counts, TLS
  normalization per `database.py`), ci.yml pollution gate (post-suite Cypher residue check) +
  pip-audit/npm audit + upload-artifact, release.yml staged-promotion skeleton,
  docs/RUNBOOK.md, DEPLOYMENT.md branch-protection checklist.
- Task 3: seven unit test files (test_database/test_ontology/test_series_service/test_api_series/
  test_deps/test_config/test_main_lifespan) + `check_seed_schema` in seed.py wired into
  setup_database (episode props `synopsis_visible_from_order`/`image_visible_from_order`
  key-presence — the 01N52 drift class) + `--check` mode in setup.py + schema-check test in
  test_seed_idempotency.py. test_deps uses starlette `Request(scope)` + stub service (no live DB);
  test_config uses `Settings(_env_file=None, ...)`; test_main_lifespan monkeypatches
  `main.Neo4jSessionRepository` with a fake sweep counter.

## Remaining steps
1. Verify Task 1: `uv run pytest spoilerless/tests/test_candidate_ingest.py
   spoilerless/tests/test_candidate_review.py spoilerless/tests/test_seed_idempotency.py -x -q`
   (background it; modules take minutes) → commit Task 1.
2. Fix the 10 test_retrieval_tools.py tests (HARRY→PAUL/RUDY probes, find_path edge set,
   bennett/aul query terms) → same or follow-up test commit.
3. Task 2 commit, Task 3 commit, full backend suite (deterministic, 0 unexpected), targeted
   vitest + `npm run build`, 09-08-SUMMARY.md + STATE/ROADMAP tracking + final docs commit.
   Never commit `.planning/config.json`; stage explicit paths only.
