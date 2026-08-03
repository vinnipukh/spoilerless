---
phase: 07-spoiler-safety-hardening
plan: 2
subsystem: backend
tags: [spoiler-safety, progress-model, visibility-policy, effective-boundary, api-contract]

# Dependency graph
requires:
  - phase: 07-01
    provides: docs/SPOILER-TERMINOLOGY.md §6 policy contract, 07-AUDIT.md boundary plumbing map
provides:
  - backend/app/spoiler/policy.py — central D-04 visibility-policy service: validate_visibility_order, is_visible, effective_view_order (D-05 min rule, fail-closed, raises InvalidVisibilityOrder below 1), require_visible_resource, filter_public_metadata, mask_episode_metadata, assert_visibility_invariants
  - Split progress model: UserSeriesProgress carries watched_through_order + view_as_of_order (D-05); visible_until_order kept as the backward-compatible effective echo (D-07 idempotent migration: watched = view = old value)
  - ProgressService.upsert validates 1 <= view <= watched (assert_visibility_invariants); resolve() returns the policy-computed effective_view_order so every boundary consumer (graph, chat, ChangeSets) fails closed (D-12)
  - Graph GET fail-closed clamp: effective = min(requested, persisted view, persisted watched) via get_optional_current_user (anonymous callers keep legacy behavior); GraphResponse.effective_view_order echoed (D-21, additive)
  - Chat progress resolution switched to the split record (effective boundary)
  - Seed integrity audit excludes UserSeriesProgress/ChatSession (per-user state, not story content)
affects: [07-03 metadata gating + selector UX, 07-04 relationship/Cypher, 07-05 search/counts, 07-06 media, 07-07 chat/ChangeSet]

# Tech tracking
tech-stack:
  added: [backend/app/spoiler/policy.py]
  changed: [backend/app/graph/progress.py, backend/app/repository/progress.py, backend/app/services/progress.py, backend/app/api/progress.py, backend/app/domain/progress.py, backend/app/api/graph.py, backend/app/services/graph.py, backend/app/domain/graph.py, backend/app/api/deps.py, backend/app/services/chat.py, backend/app/graph/seed.py]
  removed: []
  pinned: []

# Summary
A single persisted boundary value is now split into watched_through_order
(highest contiguous confirmed order) and view_as_of_order (temporary spoiler
boundary), with the effective boundary always min(view, watched) computed by
the new central policy service. Existing rows migrate losslessly and
idempotently (watched = view = old visible_until_order). Every backend
boundary consumer — graph API, chat progress resolution, and the request
clamp — now resolves through policy.effective_view_order; a client asking
above the selected view is clamped to the view (fail-closed, never to
watched). API responses add effective_view_order additively while keeping
visible_until_order accepted/echoed (D-21 backward compatibility).

# Tests
## New
- policy unit tests: effective_view_order min rule + invalid-order raises; is_visible fail-closed on null visible_from_order; assert_visibility_invariants rejects view > watched (committed with policy.py, 441ea66)
- test_progress_api.py (+214 lines): split-field upsert/get, migration from legacy rows, invariant violations rejected (view > watched, order 0), view-only lower selection never lowers watched, effective boundary echoed in responses (committed 916693a)
- test_graph_api.py::test_graph_request_above_persisted_view_is_fail_closed — authenticated request-above-view (view=1, watched=3, request=3) returns effective_view_order 1 and hides dexter:character:paul_bennett (visible_from_order 2); anonymous request 3 keeps effective 3 (committed 8f7184f)

## Verification (canonical invocation, repo root)
unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_graph_api.py backend/tests/test_progress_api.py backend/tests/test_chat_api.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py backend/tests/test_seed_idempotency.py -q -k "not candidate"
=> 79 passed, 3 failed — the 3 failures are test_seed_idempotency.py drift, proven pre-existing via git stash (identical names at HEAD); zero new failures. Contract suites green (33 templates / 45 ops unchanged — response shapes only).

## Live-DB hygiene incidents handled (orchestrator)
- Interrupted-run pollution (executor 429 deaths) left orphaned UserSeriesProgress / Session / ChatSession nodes breaking the seed audit; cleaned test-created rows only, preserved the user's real progress + chat session.
- test_progress_api.py teardown originally deleted ALL UserSeriesProgress rows (would have wiped the user's real progress on every run) — changed to orphaned-only (rows whose :AppUser does not exist).
- Seed audit now excludes UserSeriesProgress/ChatSession — per-user state carries split-boundary fields, not a story reveal-point; real user rows can no longer fail the gate.

# Status
Complete. Three commits: 441ea66 (policy service + tests), 916693a (progress migration + service), 8f7184f (fail-closed graph boundary + audit exclusion). All acceptance criteria proven; contract tests green; baseline failure name-set unchanged.
