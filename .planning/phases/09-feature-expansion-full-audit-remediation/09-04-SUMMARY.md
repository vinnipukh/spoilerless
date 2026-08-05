---
phase: 09-feature-expansion-full-audit-remediation
plan: 04
type: execute
status: complete
executed_by: gsd-executor (deleg_ff69338f 503-death, deleg_0103bf48 429-death partial Tasks 1-2) + orchestrator inline completion (Task 3, test fixes, verification, SUMMARY) per user directive to finish inline
---

# Phase 09 — Plan 09-04 Summary: Read-path hardening

## Objective

PROB-04/#12 (anonymous client-chosen boundary), PROB-05/#13 (candidates
default-to-everything), PROB-03/#32 (session id collision) + #9 (no
slide-on-read, background sweep), PROB-16/#37 (None visibility → 422).

## Commits

| Task | SHA | Message |
|------|-----|---------|
| 1+2 | `f8e7650` | feat(09-04): anonymous boundary fixed at 1 + candidates require resolved boundary + None visibility 422 (PROB-04/05/16) |
| 3 | `1c7d497` | feat(09-04): uuid4 session ids + background sweep, no slide-on-read (PROB-03) |

## What shipped

### Task 1 — anonymous boundary + candidates resolved boundary (PROB-04/05)
- `graph.py get_graph`: anonymous `visible_until_order` is IGNORED — effective
  boundary fixed at 1, persisted-episode check resolves against the effective
  (not requested) order so anonymous clients can't even probe episode ids
  above boundary 1; authenticated callers keep the D-05 min against their
  persisted split record
- `series.py list_episodes`: same anonymous clamp (effective = 1)
- `candidates.py`: new `_require_resolved_boundary` gate on list+get —
  omitted boundary → 422 `invalid_request` (never default-to-everything);
  non-persisted order → 422 `invalid_visible_until_order` (mirrors graph
  read path, D-09). Ingest stays auth-gated (09-03)
- New tests: `test_anonymous_graph_boundary_is_fixed_at_one`,
  `test_anonymous_episode_list_boundary_is_fixed_at_one`,
  `TestCandidateReadBoundary` (4 tests, scratch ids + teardown)

### Task 2 — None visibility fails closed (PROB-16/#37)
- `progress.py` catches `InvalidVisibilityOrder` → 422
  `invalid_visible_until_order` envelope (never a bare TypeError 500) on
  corrupt/legacy split fields
- `spoiler/policy.py` + `test_spoiler_policy.py` updated

### Task 3 — collision-proof sessions + sweep (PROB-03/#9/#32)
- `Neo4jSessionRepository.create` id → `session:{uuid4()}` (old
  `session:{user_id}:{int(now)}` collided same-second against the
  session_id unique constraint; id no longer encodes user/time)
- No slide-on-read: `refresh` bumps `last_seen_at` only — `expires_at` never
  extends on read (both in-memory + Neo4j impls; auth.py docstring updated)
- New `sweep_expired()`: deletes `expires_at < $now OR revoked_at IS NOT
  NULL`, returns count, idempotent/concurrency-safe
- Lifespan background task in `main.py`: hourly sweep loop, guarded on
  reachable DB, per-iteration exception tolerance, cancellation on shutdown
- New tests: same-second double login → 2 distinct ids (#32 regression),
  refresh does not extend expiry, sweep removes only expired/revoked +
  idempotent second sweep

## Verification (real runs)

- `test_graph_api.py`: 26/26 (incl. 6 boundary tests fixed for the new
  anonymous-clamp contract via parameterized boundary sessions)
- `test_candidate_ingest.py` + `test_progress_api.py` + `test_spoiler_policy.py`: 52/52
- `test_session_repository.py` + `test_auth.py`: 46/46
- `test_episode_masking.py`: 8/8 (high-boundary probes now authenticated)
- Heavy regression (user_content_api + candidate_review + progress_api +
  change_set_revision + revisions): 91/91
- Grep gates: `rg "int\(now\)|slide"` — only docstrings/comments remain

## Self-Check

✅ PASS — all 3 tasks complete and committed; every test-side failure was
contract drift against the new fail-closed behavior (fixed inline, not
masked); no `.planning/config.json` or `.env` touched; no real-user rows
deleted (scratch users + boundary fixtures cleaned in teardown).

*Completed: 2026-08-05 (2 executor deaths → inline completion per user)*
