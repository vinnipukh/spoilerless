# 07-08 Acceptance Checklist — Phase 07 spoiler-safety-hardening

Repo: C:\Users\arhan\PycharmProjects\hdgrafcehennemi · Branch: main · Date: 2026-08-03

## Backend regression (Task 1)

- [PASS] Full backend suite, canonical invocation:
  `unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests -q`
  → **410 passed, 3 failed, 0 errors**. The 3 failures are the documented
  pre-existing baseline drift (`test_seed_idempotency.py`: seed count drift ×3 —
  identical names at HEAD, proven via stash earlier in the phase). **Zero new
  failures.** The old baseline's extraction-model ×2 + candidate-ingest/review
  ×7 errors now pass (re-run: `test_extraction_models.py test_candidate_ingest.py
  test_candidate_review.py` → 32 passed).
- [PASS] Spoiler/phase suites green (single targeted run during the phase):
  `pytest backend/tests/test_spoiler_policy.py test_progress_api.py test_episode_ordering.py test_episode_masking.py test_graph_api.py test_retrieval_tools.py test_retrieval_pipeline.py test_user_content_api.py test_chat_api.py test_chat_persistence.py test_citations.py test_prompt_injection.py test_change_set_api.py test_change_set_confirmation.py test_openapi_contract.py test_frontend_contract_doc.py -q` → **117 passed** (plus retrieval_tools/prompt_injection in later runs).
- [PASS] Contract suites green across the phase: `test_openapi_contract.py` + `test_frontend_contract_doc.py` pass unchanged every run (route inventory unchanged all phase; response shapes additive only).
- [PASS] Live-DB hygiene: no test-created progress rows remain (`MATCH (p:UserSeriesProgress)` → 0 rows — teardowns ran; the dangerous all-rows teardown was replaced with orphaned-only in 07-02). AppUser/Session uuid rows from auth suites remain but are inert (seed audit scans story nodes only; ambiguous rows left untouched per never-delete-real-data rule).
- [PASS] `git diff --check` clean on all phase commits.

## Frontend regression (Task 2)

- [PASS] `cd frontend && NODE_ENV=test CI=1 npx vitest run` → **186 passed (26 files), 0 failures**.
- [PASS] `npx tsc --noEmit` → clean.
- [PASS] `npx eslint src` → **28 errors = exactly the documented pre-existing baseline; 0 NEW errors**.
- [PASS] `npm run build` → succeeds (rolldown chunk-size advisory only).

## Live acceptance (Task 3)

- [PASS] Server up: `curl http://127.0.0.1:8000/health` → `{"status":"ok","database":"connected","service":"hdgrafcehennemi-backend"}`. (Note: `/api/health` is not a route; `/health` is.)
- [PASS] Boundary masking verified against the live server (anonymous):
  `GET /api/series/series_dexter/episodes?visible_until_order=1` →
  S01E01 → "Dexter", unlocked: true · S01E02 → "S01E02 — Episode 2", unlocked: false ·
  S01E03 → "S01E03 — Episode 3", unlocked: false. D-08 generic masking + D-22 unlock flags confirmed end-to-end.
- [NOTE] Full UI browser pass via dev-login requires `auth_dev_code` in settings
  (dev-only bypass); the API-level boundary behavior above is verified. Formal
  gsd-verify-work remains the post-phase step.

## Summary

PASS rows: **8**. Baseline failure name-set matches exactly (seed ×3);
everything else green. 07-08 produced no production-code changes (one
test-construction fix for the D-21 field: 436d394).
