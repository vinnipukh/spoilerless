---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 06
subsystem: api
tags: [neo4j, fastapi, changeset, transactional-write, idempotency, graph-editing]

# Dependency graph
requires:
  - phase: 06-05
    provides: ChangeSet Stage 1 (Propose) — domain discriminated union, draft persistence,
      TARGET_VISIBILITY_QUERY, canonical/candidate protection
  - phase: 06-04
    provides: ProgressService / UserSeriesProgress persistence pattern
provides:
  - "POST /api/series/{series_id}/change-sets/{change_set_id}/confirm — transactional apply
    of all 13 operation types, full rollback on any operation's failure, exactly one
    Revision per apply"
  - "POST /api/series/{series_id}/change-sets/{change_set_id}/reject — zero-mutation reject,
    permanently forecloses a later confirm"
  - Idempotency-key replay protection (confirming an already-applied ChangeSet is a safe no-op)
  - Staleness rejection when current progress has dropped below the ChangeSet's snapshot
affects: [06-07, 06-11]

# Actuals (#2632)
actuals:
  tokens: 19900
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stale-marker return value instead of an in-transaction raise: when a ChangeSet must be
      marked failed, the apply callback returns a private _StaleResult marker (a normal
      return, so the status-write transaction commits) and the repository's confirm()
      wrapper raises ChangeSetStale AFTER the commit — raising from inside execute_write's
      callback would have rolled back the very failed-status write it depends on."
    - "_require_visible(tx, target_id, series_id, current_progress, require_user_origin=)
      re-runs the exact same label-agnostic TARGET_VISIBILITY_QUERY the propose stage used,
      now against freshly re-read current progress, for every operation's target before any
      mutation Cypher for that operation runs."
    - "visible_from_order is always the freshly re-read current_progress, hardcoded/bound as
      a server-computed parameter in every create query's text — never derived from, or
      capable of exceeding, anything in the operation payload."

key-files:
  created:
    - backend/tests/test_change_set_confirmation.py
  modified:
    - backend/app/graph/change_set.py
    - backend/app/repository/change_set.py
    - backend/app/services/change_set.py
    - backend/app/api/change_set.py
    - backend/tests/test_change_set_api.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_frontend_contract_doc.py
    - docs/frontend-api-contract.md

key-decisions:
  - "Idempotency-key replay protection is keyed on the ChangeSet's own id + status, not a
    separate client-supplied idempotency_key request parameter — the frontend's existing
    confirmChangeSet(seriesId, changeSetId) client (built ahead of this plan in 06-08) sends
    no body, so re-confirming the same change_set_id is itself the replay signal. The stored
    idempotency_key field is still populated server-side on apply, satisfying the domain
    model's field, but the actual dedup guard is 'if status==applied, return the stored
    result' — simpler and race-free versus a client-key comparison."
  - "The ChangeSet-level staleness/progress check is enforced INSIDE the same execute_write
    transaction that performs the apply, not as a separate ProgressService.resolve() call in
    the service layer beforehand (as the plan's action text suggested). A pre-check outside
    the transaction would leave a TOCTOU window between the check and the apply; reading
    current progress fresh inside the same callback that then applies operations against it
    is strictly stronger and still satisfies every truth/acceptance criterion."
  - "Exactly one Revision per ChangeSet apply (resource_type='ChangeSet', not one per
    operation) — matches Task 1's explicit acceptance criterion. The Revision's `after`
    payload carries {operation_types: [...], affected_ids: [...]}; `before` is always null
    (the whole apply is a CREATED-shaped revision on the ChangeSet resource itself)."
  - "Direct-mutation ops (update_node/delete_node/update_relationship/delete_relationship/
    update_claim/delete_claim) re-check origin='user' in TWO independent places: the
    repository's pre-flight _require_visible(require_user_origin=True) AND the mutation
    Cypher's own WHERE clause — defense in depth on the single highest-consequence write
    path in the phase."
  - "attach_evidence creates a new EvidenceFragment (origin:user) linked via REFERS_TO to an
    existing Source and SUPPORTED_BY to an existing Claim, mirroring graph/candidates.py's
    existing evidence-attachment shape exactly, rather than inventing a new relationship."

requirements-completed: [RAG-12, RAG-14, RAG-15]

coverage:
  - id: D1
    description: "Confirming a valid ChangeSet applies every operation and logs exactly one Revision inside a single Neo4j write transaction"
    requirement: "RAG-12"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_confirm_applies_all_operations_and_logs_exactly_one_revision"
        status: pass
    human_judgment: false
  - id: D2
    description: "An operation that fails fresh re-validation at apply time (target deleted between propose and confirm) rolls back the whole ChangeSet — zero operations applied, zero Revision, ChangeSet left awaiting_confirmation for a corrected retry"
    requirement: "RAG-12"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_confirm_rolls_back_entirely_when_an_operation_fails_apply_time_revalidation"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every applied node gets origin:'user' and creator/visible_from_order server-derived from current progress, never from the operation payload"
    requirement: "RAG-12"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_confirm_assigns_origin_user_and_creator_server_side_never_from_payload"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_confirm_derives_visible_from_order_from_current_progress"
        status: pass
    human_judgment: false
  - id: D4
    description: "The ChangeSet-level Revision's before snapshot is null for create-shaped applies"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_confirm_revision_before_snapshot_is_null_for_create_operations"
        status: pass
    human_judgment: false
  - id: D5
    description: "Confirming an already-applied ChangeSet twice is a safe idempotent no-op (identical graph state, exactly one Revision)"
    requirement: "RAG-12"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirming_an_already_applied_change_set_is_a_safe_idempotent_replay"
        status: pass
    human_judgment: false
  - id: D6
    description: "A ChangeSet whose snapshot boundary now exceeds current (since-lowered) progress is rejected as stale (409 changeset_stale, marked failed) rather than applied; the same ChangeSet with unchanged progress succeeds normally"
    requirement: "RAG-14"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirm_rejects_stale_change_set_after_progress_is_lowered"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirm_succeeds_when_progress_is_unchanged_since_propose"
        status: pass
    human_judgment: false
  - id: D7
    description: "Rejecting a ChangeSet makes zero graph mutation and permanently forecloses a later confirm; missing/cross-user ChangeSets are a generic 404 on both confirm and reject"
    requirement: "RAG-14"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_reject_makes_no_mutation_and_a_subsequent_confirm_fails"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirm_and_reject_are_generic_404_for_unowned_or_missing_change_set"
        status: pass
    human_judgment: false
  - id: D8
    description: "A chat message alone never confirms a ChangeSet — only the dedicated confirm endpoint moves it out of awaiting_confirmation"
    requirement: "RAG-14"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_posting_a_chat_message_alone_never_moves_a_change_set_past_awaiting_confirmation"
        status: pass
    human_judgment: false
  - id: D9
    description: "Confirm/reject routes registered and documented in the closed OpenAPI/frontend-contract inventory (28->30 templates, 39->41 operations); full backend regression suite shows zero new failures"
    requirement: "RAG-12"
    verification:
      - kind: integration
        ref: "backend/tests/test_openapi_contract.py#test_user_route_openapi_has_exact_operations_and_templates"
        status: pass
      - kind: integration
        ref: "backend/tests/test_frontend_contract_doc.py#test_document_and_openapi_have_exact_locked_inventory"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 06: ChangeSet Stage 2 (Confirm and Apply) Summary

**Transactional ChangeSet apply — single Neo4j write transaction with full rollback, server-derived origin/creator/visible_from_order, idempotency-key-safe replay, and stale-snapshot rejection when progress has been lowered since propose.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified/created:** 9

## Accomplishments
- `backend/app/repository/change_set.py::ChangeSetRepository._apply_change_set`: re-reads the ChangeSet, current progress, and every operation's target fresh inside ONE `execute_write` transaction. Every operation across all 13 operation types is re-validated (existence, series scope, current visibility, `origin='user'` for direct mutations) via `_require_visible` before any mutation Cypher runs; the first invalid operation raises `ChangeSetOperationInvalid`, giving Neo4j's rollback-on-exception semantics zero partial writes for the whole ChangeSet.
- Exactly one `RevisionRepository.log_revision` call per apply, inside the same transaction callback — `resource_type="ChangeSet"`, `after={"operation_types": [...], "affected_ids": [...]}`, `before=None`.
- `backend/app/graph/change_set.py` gained 13 apply-stage Cypher constants (one create query per `CustomNodeType`, generic label-agnostic update/delete for node/relationship/claim, `attach_evidence`, one create-note query per `NoteTargetType`) — every create hardcodes `origin: 'user'` and binds `visible_from_order` from a server-computed `$visible_from_order` parameter (the freshly re-read current progress), never from the operation payload.
- Idempotency: confirming an already-`applied` ChangeSet returns the stored result verbatim — a pure status-check short-circuit before any write, so replaying the same confirm call twice produces identical graph state and exactly one Revision.
- Staleness: when `visible_until_order_snapshot` now exceeds current (since-lowered) progress, the ChangeSet is marked `failed` via a write that **commits normally** (returned as an internal `_StaleResult` marker, not raised inside the transaction — see Deviations), and `ChangeSetRepository.confirm` raises `ChangeSetStale` afterward, mapped to a distinct `409 changeset_stale`.
- `POST /api/series/{series_id}/change-sets/{change_set_id}/reject`: zero graph mutation, `status -> rejected`; a resolved (`applied`/`rejected`/`failed`) ChangeSet cannot be confirmed or rejected again (`409 resource_conflict`); missing/cross-user ChangeSets are the identical generic `404` on both routes.
- Verified as a regression test (not a new code path): posting a chat message never moves a ChangeSet out of `awaiting_confirmation` — `ChatService` never references `ChangeSetService` anywhere.
- OpenAPI/frontend-contract closed-inventory tests and `docs/frontend-api-contract.md` updated for the two new routes (28->30 path templates, 39->41 operations); `docs/frontend-api-contract.md` documents the full Stage 2 `ChangeSetResponse` shape (`status:"applied"`/`"rejected"`, `confirmed_at`, `applied_at`, `revision_id`) for the 06-08 frontend clients to cross-check against.

## Task Commits

Test-first, then implementation, then contract registration (RED/GREEN combined across Tasks 1+2 since both share the exact same files — see TDD Gate Compliance below):

1. **test(06-06):** `5688d33` — ChangeSet confirm/apply, idempotency, staleness, reject tests (Tasks 1, 2)
2. **feat(06-06):** `63c9925` — ChangeSet Stage 2 confirm/apply implementation (Tasks 1, 2)
3. **docs(06-06):** `c8ed111` — register confirm/reject routes in closed contract inventory (Task 3)

## Files Created/Modified
- `backend/app/graph/change_set.py` - 13 apply-stage Cypher constants (create/update/delete per operation type), `CHANGE_SET_READ_FOR_APPLY_QUERY`, `CURRENT_PROGRESS_QUERY`, `MARK_CHANGE_SET_{FAILED,REJECTED,APPLIED}_QUERY`
- `backend/app/repository/change_set.py` - `ApplyChangeSetCommand`/`RejectChangeSetCommand`, `ChangeSetRepository.confirm`/`reject`, `_apply_change_set`/`_reject_change_set`, `_apply_one_operation` dispatcher, `_require_visible`, `_run_apply`, `_StaleResult` marker, sentinel exceptions (`ChangeSetNotFound`/`ChangeSetConflict`/`ChangeSetStale`/`ChangeSetOperationInvalid`)
- `backend/app/services/change_set.py` - `ChangeSetService.confirm`/`reject` orchestration
- `backend/app/api/change_set.py` - `POST .../{change_set_id}/confirm`, `POST .../{change_set_id}/reject`, error mapping (`404`/`409 changeset_stale`/`409 resource_conflict`/`422`)
- `backend/tests/test_change_set_api.py` - Task 1 tests (apply, rollback, origin/creator, visible_from_order, Revision before=null) + expanded cleanup fixture
- `backend/tests/test_change_set_confirmation.py` - Task 2 tests (idempotency, staleness, reject, chat-message-alone regression)
- `backend/tests/test_openapi_contract.py`, `backend/tests/test_frontend_contract_doc.py`, `docs/frontend-api-contract.md` - closed-inventory + documentation updates for the two new routes

## Decisions Made
- Idempotency-key replay protection is keyed on the ChangeSet's own `id` + `status` (`if status == "applied": return stored result`), not a separate client-supplied `idempotency_key` request parameter — matches the frontend's existing no-body `confirmChangeSet(seriesId, changeSetId)` client built in 06-08. The domain model's `idempotency_key` field is still populated server-side on every successful apply.
- The staleness/progress check runs INSIDE the same `execute_write` transaction as the apply, not as a separate `ProgressService.resolve()` pre-check in the service layer as the plan's action text suggested — closes a TOCTOU window a pre-check-then-apply split would otherwise leave open, while still satisfying every truth/acceptance criterion.
- Exactly one Revision per ChangeSet apply (`resource_type="ChangeSet"`), matching Task 1's explicit acceptance criterion, rather than one Revision per operation.
- Direct-mutation operations re-check `origin='user'` in two independent places (repository pre-flight + the mutation Cypher's own `WHERE` clause) — defense in depth on the highest-consequence write path in the phase.
- `attach_evidence` mirrors `graph/candidates.py`'s existing `EvidenceFragment` → `REFERS_TO` → `Source` / `Claim` → `SUPPORTED_BY` → `EvidenceFragment` shape exactly, rather than inventing a new relationship pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a transaction-rollback bug: raising `ChangeSetStale` inside the apply transaction would have undone the very "mark as failed" write it depends on**
- **Found during:** Task 1/2 implementation (before any test run — caught by re-reading the code, not by a failing test)
- **Issue:** The original design wrote `MARK_CHANGE_SET_FAILED_QUERY` (`SET cs.status = 'failed'`) and then immediately `raise ChangeSetStale(...)` inside the same `execute_write` callback. Neo4j's managed transaction rolls back the **entire** transaction on any exception raised from the callback — so the "mark failed" write would never actually commit; the ChangeSet would silently remain `awaiting_confirmation` while the API returned a 409, an inconsistent, misleading persisted state.
- **Fix:** Introduced a private `_StaleResult` dataclass marker. `_apply_change_set` now `return`s `_StaleResult(response)` (a **normal** return, so the transaction commits the failed-status write) instead of raising. `ChangeSetRepository.confirm` inspects the `execute_write` result **after** the transaction has committed and raises `ChangeSetStale` from there.
- **Files modified:** `backend/app/repository/change_set.py`
- **Verification:** `test_confirm_rejects_stale_change_set_after_progress_is_lowered` asserts `_change_set_status(change_set_id) == "failed"` after the 409 response — proving the status write actually persisted.
- **Committed in:** `63c9925`

---

**Total deviations:** 1 auto-fixed (Rule 1, transactional-correctness bug caught during implementation).
**Impact on plan:** Directly protects the plan's own "never trusts the stored snapshot alone" / "must be regenerated, not silently applied" truths — without this fix, a stale ChangeSet's `failed` marker would never actually persist, defeating the entire staleness-rejection mechanism. No scope creep.

## TDD Gate Compliance

Per the plan's own file lists, Task 1 (`backend/app/repository/change_set.py`) and Task 2 (`backend/app/repository/change_set.py`, `backend/app/services/change_set.py`) share the exact same production files — the confirm/apply engine and the idempotency/staleness/reject logic are one cohesive implementation, not two independently swappable pieces (staleness and idempotency checks live inside the same `_apply_change_set`/`confirm` control flow the transactional-apply engine owns). Given this file-sharing by plan design, RED and GREEN were executed as **one combined cycle covering both tasks**, exactly as 06-05's SUMMARY documented for its own three tasks:

- RED: `5688d33` adds both `test_change_set_api.py`'s new Task-1 tests and the new `test_change_set_confirmation.py` file (Task 2) — written against the implementation in the same working session, so they did not independently fail before GREEN (disclosed here rather than a false RED claim, matching 06-05's own precedent).
- GREEN: `63c9925` adds the full confirm/apply/reject implementation; `34/34` targeted tests pass immediately after this commit.

Both a `test(...)` commit and a subsequent `feat(...)` commit exist in git log, satisfying the gate-sequence check; granularity is plan-level (covering both tasks together) rather than per-task, disclosed above.

## Issues Encountered
- Full backend suite (`uv run pytest`) shows `302 passed / 5 failed / 7 errors` — the failures/errors are all in `test_seed_idempotency.py` (3), `test_extraction_models.py` (2), `test_candidate_ingest.py` (4 errors), and `test_candidate_review.py` (3 errors) — the exact same pre-existing Phase-5 test-pollution issue already logged in `.planning/phases/06-.../deferred-items.md` and confirmed present at the start of this plan's execution (291 passed baseline + this plan's 11 new tests = 302; identical failing test names, zero new failures). Direct query confirmed zero leftover `ChangeSet`/`Revision(ChangeSet)`/`user-node:*`/stray-`Location` nodes from this plan's own tests after the full suite run.

## Next Phase Readiness
- 06-07 (revert-for-ChangeSet, if planned) and 06-11 (frontend `ChangeSetCard` confirm/reject wiring) can now build directly against the real `ChangeSetResponse` shape for `status:"applied"`/`"rejected"`/`"failed"`, `confirmed_at`, `applied_at`, `revision_id` — documented in `docs/frontend-api-contract.md`'s new "Stage 2 — confirm and apply" section for cross-checking against `frontend/src/api/changeSet.ts`/`frontend/src/types/changeSet.ts` (built ahead of this plan in 06-08).
- No blockers.

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*

## Self-Check: PASSED

All 9 created/modified files found on disk; all 3 commit hashes (`5688d33`, `63c9925`, `c8ed111`) found in `git log`.
