# Phase 9 Verification Runbook (2026-08-13, gsd-verifier)

Goal-backward verification of `.planning/phases/09-feature-expansion-full-audit-remediation`
against live code + targeted tests. Outcome: `status: passed`, score 40/42, 0 BLOCKERs,
2 UNCERTAIN (behavioral) routed to human verification. `09-VERIFICATION.md` written
(287 lines, frontmatter must_haves = all 42 requirement-level truths).

## Method notes

- **Must-have count**: 42 requirement-level truths (REBRAND-01, PROB-01..05, PROB-09..21,
  PROB-22..32, FEAT-01..10, FEAT-11, DOCS-04). PROB-06/07/08 are test-infra truths:
  PROB-08 verifiable live (`npm run lint` → 0), PROB-07 is behavioral (two full vitest
  runs needed) → human item, PROB-06 verified-with-warning (pollution sensitivity).
- **Commit-SHA existence proof**: `for sha in <all claimed SHAs>; do git cat-file -e
  "$sha^{commit}" && echo OK || echo MISSING; done` — all 34 Phase-9 SHAs exist on main.
- **REBRAND gate interpretation** (see SKILL.md): `git grep -il hdgrafcehennemi` hits in
  README/CONTRIBUTING/DEVELOPMENT/GETTING-STARTED are clone URLs + `cd hdgrafcehennemi`
  dir names; DEPLOYMENT.md:491-497 references `hdgrafcehennemi-backend` as the stale-build
  detection string. All intentional — the GitHub remote rename was NOT executed.

## Targeted test batches (total 258 passed / 1 skipped / 1 failed; ~11 min)

| Batch | Files | Result |
|---|---|---|
| DB-free core+contract | test_user_content_models, test_google_verifier, test_spoiler_policy, test_database, test_ontology, test_series_service, test_api_series, test_deps, test_config, test_main_lifespan, test_frontend_contract_doc, test_rate_limit, test_visibility | 98 passed, 1 skipped (documented live-JWKS happy-path skip) |
| Live auth/ownership/share | test_share_api, test_session_repository, test_user_content_api, test_revisions | 57 passed (7:35) |
| Live graph path/export | test_graph_api `-k "path or export"` | 10 passed (91 deselected) |
| Stub-DB pipeline+auth | test_retrieval_pipeline, test_auth | 61 passed (0.73s) |
| Live candidate/seed/schema | test_candidate_ingest, test_candidate_review, test_seed_idempotency, test_setup_schema_check | 32 passed, 1 FAILED |

Live runs used env overrides (root `.env` points at AuraDB — shell env beats it):
`NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j`.

## The 1 failure — baseline pollution classification (reusable technique)

`test_seed_idempotency.py::test_constraints_visibility_and_provenance` asserts
`missing_visibility == [{"count": 0}]` under `series_dexter` (excluding
UserSeriesProgress/ChatSession/ChatMessage). It failed with count=2. Classification
procedure that worked:

1. Ad-hoc query the live DB for the offending nodes (labels/id/origin) instead of guessing.
2. Result: two `:ChangeSet` nodes, `origin: null`, no visible_from_order — app system
   nodes, same documented class as `UserSeriesProgress`.
3. Check whether the creating tests clean up: `test_change_set_*.py` DO have
   `module_cleanup_fixture` deleting all ChangeSets → residue = orphans from a crashed
   earlier run on the shared docker volume, NOT a Phase-9 regression (matches the known
   ~12 baseline failures).
4. Verdict: WARNING gap (test remains order/state-sensitive), not a BLOCKER. Suggested
   fix: `AND NOT node:ChangeSet` in the assert or sweep orphans in module setup.

## Invocation traps (all hit this session)

- `pytest-timeout` NOT installed in the venv — `--timeout=120` is a usage error; drop it.
- `-k` must be a separate argv entry. `"file.py -k 'a or b'"` as ONE quoted argument is
  parsed as a single file path → collection error EXIT=4. A bare `-k` applies to ALL
  files in the invocation (deselects tests in the others) — run filtered and unfiltered
  files in separate invocations.
- Ad-hoc scripts using the in-app `Neo4jDatabase` need BOTH:
  `PYTHONPATH=<repo root>` (pytest works via conftest sys.path; plain `.venv/Scripts/python.exe`
  gets `ModuleNotFoundError: No module named 'spoilerless'`) AND
  `database.open()` + `await database.verify_connection()` before `execute_query`
  (else `RuntimeError: Neo4j driver has not been initialized`). Fixture pattern:
  `spoilerless/tests/test_seed_idempotency.py:20-27`. Write the script via write_file to
  `%TEMP%` (hermes-verify-*.py) and `rm` after.

## Repo-state facts refreshed

- Docker container `spoilerless-neo4j` (neo4j:2026.06.0-community) is the local test DB.
- `.planning/ROADMAP.md` tracking doc is STALE: still "Plans: 10/18 plans executed" with
  09-11..09-18 unchecked although all 18 SUMMARY.md exist on disk (through 08-12) —
  flag for orchestrator closeout, never "fix" it yourself.
- FE coverage gap: FEAT-09 share frontend (ShareDialog/ShareView) has NO automated FE
  tests (no ShareDialog.test.tsx; App.test.tsx has 0 share refs) — backend
  `test_share_api.py` (5 tests) covers the API; FEAT-11 BacklinksTab likewise untested
  at FE level. Route FE UX to human/browser verification.
- `docs/API.md` is locked by `test_frontend_contract_doc.py` at 50 ops / 37 templates
  (passed) — matches the 08-10 snapshot.
