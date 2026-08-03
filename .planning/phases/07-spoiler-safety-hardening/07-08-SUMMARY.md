---
phase: 07-spoiler-safety-hardening
plan: 8
subsystem: verification
tags: [spoiler-safety, regression, acceptance]

# Dependency graph
requires:
  - phases: 07-01..07-07 (all complete)
provides:
  - 07-08-ACCEPTANCE.md — 8 PASS rows: full backend suite name-set match (410 passed / 3 failed = documented seed-drift baseline, zero new failures; old extraction/candidate errors now pass), spoiler suites green, contract suites green, live-DB hygiene clean, vitest 186/186, tsc clean, eslint exactly the 28-error baseline (0 new), production build OK, /health ok + database connected, live boundary masking verified (S01E02/03 generic titles + locked at boundary 1) against the user's running instance
  - One test-construction fix: GraphResponse model constructions gain effective_view_order (436d394) — D-21 field gap in test_user_content_models.py

# Tech tracking
tech-stack:
  added: [.planning/phases/07-spoiler-safety-hardening/07-08-ACCEPTANCE.md]
  changed: [backend/tests/test_user_content_models.py]
  removed: []
  pinned: []

# Summary
Phase-wide regression confirms the spoiler-safety hardening holds end-to-end.
The full backend suite (410 tests) matches the documented baseline failure
name-set exactly with zero new failures; every phase-specific suite (policy,
progress, ordering, masking, graph, retrieval, chat, citations, prompt
injection, change sets, contracts) is green; the frontend passes vitest,
typecheck, the lint gate (0 new over the 28-error baseline), and the
production build. Live acceptance against the running instance verified the
D-08 generic masking and D-22 unlock flags at boundary 1. No production code
changed in this plan.

# Tests
## Verification commands (all recorded in 07-08-ACCEPTANCE.md)
- pytest backend/tests -q → 410 passed, 3 failed (seed drift baseline), 0 errors
- pytest test_extraction_models.py test_candidate_ingest.py test_candidate_review.py -q → 32 passed
- cd frontend && NODE_ENV=test CI=1 npx vitest run → 186 passed
- npx tsc --noEmit → clean; npx eslint src → 28 (baseline, 0 new); npm run build → OK
- curl /health → {"status":"ok","database":"connected",...}
- GET /api/series/series_dexter/episodes?visible_until_order=1 → S01E02/03 generic masked titles, is_unlocked false

# Status
Complete. Commit 436d394 (test fix). 07-08-ACCEPTANCE.md (8 PASS rows) + this summary committed. Phase execution complete — 8/8 plans; formal gsd-verify-work is the remaining post-phase step.
