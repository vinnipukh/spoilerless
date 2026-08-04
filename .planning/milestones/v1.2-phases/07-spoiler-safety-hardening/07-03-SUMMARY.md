---
phase: 07-spoiler-safety-hardening
plan: 3
subsystem: full-stack
tags: [spoiler-safety, episode-metadata, masking, view-as-of, selector-ux]

# Dependency graph
requires:
  - phase: 07-02
    provides: policy.mask_episode_metadata / effective_view_order, split progress record (watched_through_order/view_as_of_order)
provides:
  - data/dexter/metadata/episodes.json title_is_spoiler + title_visible_from_order (all 3 seeded episodes), written via parameterized Cypher, no new constraints
  - EpisodeResponse display_title / is_unlocked / is_current_view (additive, D-21); episodes route optional visible_until_order param resolved through the D-05 fail-closed formula (requested_view = min(requested, persisted view) then policy.effective_view_order)
  - Server-side masking (D-08): services/series.py -> policy.mask_episode_metadata — spoiler titles become "<code> — Episode N" above the boundary, synopsis/runtime/image never synthesized, missing title-safety metadata fails conservatively (META-03)
  - Frontend: useWatchProgress watchedThroughOrder/viewAsOfOrder split; view-only selection (PROG-01) never opens the modal and never lowers watched; forward unlock copy "Episodes 1 through N will be considered watched" (D-06); EpisodeSelector 3-state rendering with Lock affordance + sr-only text (D-22), locked items stay selectable; api/progress.ts + api/series.ts extensions
affects: [07-06 media (masking path), 07-07 chat boundary, 07-08 regression]

# Tech tracking
tech-stack:
  added: [frontend/src/components/episode/EpisodeSelector.test.tsx, backend/tests/test_episode_masking.py, backend/tests/test_episode_ordering.py]
  changed: [data/dexter/metadata/episodes.json, backend/app/graph/seed.py, backend/app/domain/series.py, backend/app/services/series.py, backend/app/api/series.py, frontend/src/types/series.ts, frontend/src/api/series.ts, frontend/src/api/progress.ts, frontend/src/hooks/useWatchProgress.ts, frontend/src/hooks/useEpisodes.ts, frontend/src/components/episode/EpisodeSelector.tsx, frontend/src/components/episode/ConfirmAdvanceModal.tsx, frontend/src/App.tsx]
  removed: []
  pinned: []

# Summary
Future episode titles are now masked server-side at the effective boundary:
the episodes API accepts an optional visible_until_order, resolves it through
the 07-02 fail-closed formula, and returns an already-masked display_title
("S01E02 — Episode 2") plus is_unlocked/is_current_view. Title-safety
metadata is seed-driven (title_is_spoiler/title_visible_from_order), and
publication-order semantics are locked by tests (S01E09 < S01E10,
season-end < next-season start, flashback reveal, fictional-chronology
irrelevance). The frontend splits watched progress from the view boundary:
selecting an earlier already-watched episode moves only the view (no modal,
watched untouched — PROG-01), selecting above watched opens the unlock
confirmation stating Episodes 1 through N will be considered watched (D-06),
and the selector shows watched/current/locked states with an explicit Lock
affordance + accessible text, never color alone (D-22). Masked episodes
remain selectable so the unlock flow is reachable.

# Tests
## New
- backend/tests/test_episode_ordering.py — S01E09 < S01E10, season boundary, flashback reveal, fictional-chronology irrelevance (D-09); title-safety metadata present in seed (META-03)
- backend/tests/test_episode_masking.py — generic label above boundary, real title below, is_unlocked/is_current_view correct, missing-metadata conservative fallback, no synopsis/runtime/image above boundary, request-below-view and request-above-view min cases
- frontend/src/components/episode/EpisodeSelector.test.tsx — masked display_title rendering, Locked accessible text, locked items still selectable, current-view selection
- useWatchProgress.test.ts — view-only selection (no modal, watched unchanged, view-only POST), forward confirm POSTs both orders, above-watched opens confirmation

## Verification
- Backend: unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_episode_masking.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py -q => 18 passed (contract inventory unchanged — optional param on existing route)
- Frontend full suite: NODE_ENV=test CI=1 npx vitest run => 182 passed (26 files)
- npx tsc -b clean; eslint on all touched files: 0 errors, 0 warnings
- Baseline unchanged: 3 pre-existing test_seed_idempotency failures verified identical at HEAD (stash technique)

# Status
Complete. Commits: 95f62a6 (seed metadata), 38c6f0e (ordering/title-safety tests), 6aeb4f9 (server-side masking), 9c3ec7e (frontend view-as-of UX). Companion user-requested fix committed separately: b043b41 (chat bubble min-w scaling).
