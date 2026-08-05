---
phase: 09-feature-expansion-full-audit-remediation
plan: 03
type: execute
status: complete
executed_by: gsd-executor (Task 1 partial) + sibling agent (Tasks 2-3) + orchestrator closeout (Task 1 fixes, Task 3 verification, Task 4)
---

# Phase 09 — Plan 09-03 Summary: Write-path auth & ownership hardening

## Objective

PROB-01/02/12/25/26/27/33/34: every mutation endpoint requires an
authenticated, correctly-scoped owner; user-content records carry owner
`user_id`; one visibility-derivation rule shared by both create paths; real
persisted revision ids; actor attribution on every revision; dual revert
links on ChangeSets.

## Commits

| Task | SHA | Message | Author |
|------|-----|---------|--------|
| 1 | `0f3c388` | feat(09-03): auth-gate all mutation routes + owner-bound user content | executor partial + orchestrator test fixes |
| 2 | `4c40651` | feat(09-03): created_by attribution + single visibility-derivation rule (PROB-25/26) | sibling agent |
| 3 | `f6c4d43` | feat(09-03): real persisted revision ids + user_id actor attribution + dual revert links (PROB-12/33/34/27) | sibling agent + orchestrator verification |

## What shipped

### Task 1 — auth-gate + owner binding (`0f3c388`, +550/-114)
- `CurrentUserDependency` on all 9 user-content mutation routes + candidate
  ingest + revision revert (closes PROBLEMS #1/#2/#3 anonymous-write class)
- `user_id` (required) added to `NoteResponse`/`CustomNodeResponse`/
  `CustomRelationshipResponse` + examples
- Owner-scope WHERE clauses (`$is_admin = true OR node.user_id = $user_id`)
  on note/node/relationship UPDATE+DELETE; `UserContentForbidden` → 403;
  `_raise_on_ownership_conflict()` (403 cross-owner / 409 non-user / 404
  missing); `user_id` on all CREATE nodes; `take_snapshot` includes user_id
- Candidate approve/reject/edit admin gates preserved; ingest gated (actor
  unused, documented)
- Revert: owner check on UPDATED (live `user_id`) and DELETED (snapshot
  `user_id`, fail-closed legacy = admin-only) resources
- New tests: `test_anonymous_mutations_are_rejected_with_401`,
  `test_user_content_is_owner_bound_and_cross_owner_mutations_rejected`
  (scratch series `test-series:user-content`), `test_ingest_anonymous_returns_401`,
  `test_revert_anonymous_returns_401`
- Executor budget-death during verification; orchestrator fixed 2 test call
  sites (create_note 3-arg signature, `user_id` on response-model fixtures)

### Task 2 — created_by + single visibility rule (`4c40651`, sibling)
- NEW `spoilerless/app/spoiler/visibility.py`: `derive_visible_from_order(
  episode_order, current_progress) = max(...)` fail-closed (>=1) — the ONE
  rule (PROB-25, #49)
- Direct-API creates stamp `created_by: $user_id` on notes, custom nodes,
  custom relationships (PROB-26, #50); ChangeSet path already stamped it
- Custom-node direct create derives visibility via the shared helper instead
  of inline Cypher `episode.episode_order`
- ChangeSet apply routes all five create ops through the same helper
  (removes silent discard of operation episode order; provably identical
  since apply requires `episode.visible_from_order <= current_progress`)
- `TARGET_VISIBILITY_QUERY` additively returns `visible_from_order`; new
  `test_visibility.py` pins the rule

### Task 3 — real revision ids + actor + dual revert links (`f6c4d43`, sibling, verified by orchestrator)
- `RevisionRepository.log_revision` gains `user_id` param; `RevisionResponse`
  gains `user_id` field (PROB-33, #33)
- Candidate approve/reject return the REAL persisted `log_revision` id, not
  the fabricated sha256 (PROB-12/34)
- ChangeSet revert keeps BOTH ids: `apply_revision_id` + `revert_revision_id`
  instead of overwriting (PROB-27, #51)
- Orchestrator verified the uncommitted sibling partial: 43/43 targeted tests
  green against live docker Neo4j before committing

## Verification

- `test_user_content_repository.py` + `test_user_content_models.py` +
  `test_revision_models.py`: 39/39 (unit, post-Task-1 fixes)
- Live auth-gate subset (user_content_api + candidate_review,
  `-k "ingest or anonymous or owner or 401 or 403"`): 3/3
- `test_candidate_review.py` + `test_change_set_revision.py` +
  `test_revisions.py` + `test_revision_models.py`: 43/43 (post-Task-3, live)
- Known baseline failures (seed-drift/pollution) untouched — planned 09-08/09-18

## Self-Check

✅ PASS — all 3 tasks executed, commits landed, owner/auth invariants tested,
no `.planning/config.json` or `.env` touched, no real-user data deleted
(scratch series used for new 401/403 tests).

*Completed: 2026-08-05 (multi-agent: executor partial + sibling + orchestrator)*
