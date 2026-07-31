---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 05
subsystem: api
tags: [pydantic, discriminated-union, neo4j, fastapi, changeset, graph-editing]

# Dependency graph
requires:
  - phase: 06-01
    provides: ontology allowlist loading (graph/ontology.py), CustomNodeType/CustomRelationshipType enums
  - phase: 06-04
    provides: ChatSession model + progress-resolution pattern reused for ChangeSet ownership/boundary
provides:
  - ChangeSet operation discriminated union (13 closed operation types, extra="forbid")
  - POST /api/series/{series_id}/change-sets — Stage 1 (Propose) with zero target mutation
  - Canonical/candidate protection: direct-mutation ops targeting protected resources are
    transparently substituted with an honest create_note override-proposal
affects: [06-06, 06-07, 06-11]

# Actuals (#2632)
actuals:
  tokens: 15500
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discriminated Pydantic union with a Literal operation_type discriminator field, one closed
      StrictModel per operation type, none of which ever declares origin/visible_from_order/id"
    - "Single label-agnostic Cypher query (TARGET_VISIBILITY_QUERY) reused for every operation's
      target kind (node, Claim, UserNote) instead of one query per label"
    - "Service-layer transparent substitution: a direct-mutation op targeting a protected resource
      is swapped for a create_note override op before persistence, never raised as a bare rejection"

key-files:
  created:
    - backend/app/domain/change_set.py
    - backend/app/graph/change_set.py
    - backend/app/repository/change_set.py
    - backend/app/services/change_set.py
    - backend/app/api/change_set.py
    - backend/tests/test_change_set_api.py
    - backend/tests/test_change_set_protection.py
  modified:
    - backend/app/main.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_frontend_contract_doc.py
    - docs/frontend-api-contract.md

key-decisions:
  - "ChangeSet operations are validated in list order against a single shared TARGET_VISIBILITY_QUERY
    (label-agnostic MATCH) before ANY persistence — nothing is written unless every operation
    validates, so 'no partial draft' holds by construction, not by a special-cased rollback."
  - "Canonical/candidate protection is a service-layer transformation, not a rejection: the
    requested direct-mutation op is replaced with a create_note op referencing the same target,
    inside the same propose() call, so the user always gets a workable alternative."
  - "Relationships and update/delete-relationship/claim targets are both Claim nodes in this
    schema (custom relationships are stored as Claim), so the override-note target_type resolution
    checks for 'Claim' vs 'Character' in labels(target), matching the existing UserNote target
    types (Character|Claim) rather than inventing a new Note target kind."
  - "ChangeSet propose has NO idempotency-key enforcement (idempotency_key is always null on the
    draft) — that requirement belongs to a later confirm/apply stage per the plan's own scoping."

requirements-completed: [RAG-11, RAG-13]

coverage:
  - id: D1
    description: "ChangeSet operation discriminated union rejects unlisted operation_type, forbidden extra fields (origin/visible_from_order/id), non-allowlisted relationship types, and empty operations lists"
    requirement: "RAG-11"
    verification:
      - kind: unit
        ref: "backend/tests/test_change_set_api.py#test_operation_model_forbids_origin_field"
        status: pass
      - kind: unit
        ref: "backend/tests/test_change_set_api.py#test_discriminator_rejects_unknown_operation_type"
        status: pass
      - kind: unit
        ref: "backend/tests/test_change_set_api.py#test_operation_model_rejects_non_allowlisted_relationship_type"
        status: pass
      - kind: unit
        ref: "backend/tests/test_change_set_api.py#test_operation_model_requires_at_least_one_operation"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/series/{series_id}/change-sets validates every operation server-side and persists only the ChangeSet draft (zero target mutation); hidden/cross-series/nonexistent targets rejected identically; operations validated in list order with no partial persistence; propose is not idempotency-deduplicated"
    requirement: "RAG-11"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_propose_create_node_returns_awaiting_confirmation_and_creates_no_target"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_propose_hidden_target_rejected_like_nonexistent"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_propose_cross_series_target_rejected_identically_to_hidden"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_propose_operations_validated_in_list_order_no_partial_persistence"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_api.py#test_propose_same_content_twice_creates_distinct_change_sets"
        status: pass
    human_judgment: false
  - id: D3
    description: "A direct-mutation operation targeting an origin:canonical or origin:candidate resource is never persisted as requested; the server substitutes a create_note override proposal whose copy never claims the protected record was changed; origin:user targets are unaffected"
    requirement: "RAG-13"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_protection.py#test_protection_rejects_direct_delete_of_canonical_node"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_protection.py#test_protection_rejects_direct_delete_of_candidate_node"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_protection.py#test_protection_rejects_direct_update_of_candidate_claim"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_protection.py#test_protection_does_not_apply_to_user_origin_target"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 05: ChangeSet Stage 1 (Propose) Summary

**Typed ChangeSet discriminated-union propose endpoint with server-side ontology/visibility validation and transparent canonical/candidate override-proposal substitution — zero graph-target mutation.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3
- **Files modified/created:** 11

## Accomplishments
- `backend/app/domain/change_set.py`: closed 13-type Pydantic discriminated union (`operation_type` discriminator), every operation model built on `StrictModel` (`extra="forbid"`) — no operation ever declares `origin`, `visible_from_order`, or `id` as a settable field; `relationship_type`/`node_type` reuse the existing ontology-locked `CustomRelationshipType`/`CustomNodeType` enums; `ChangeSetCreateRequest.operations` requires at least one item.
- `POST /api/series/{series_id}/change-sets`: resolves the caller's persisted watch-progress boundary, validates every operation's target (existence + series scope + current visibility) in list order via one label-agnostic query, and persists only the `ChangeSet` draft node — a direct repository query after a `create_node`/`create_relationship` propose call proves zero target nodes/claims were created.
- Hidden, cross-series, and genuinely nonexistent targets all return the identical `422 invalid_request` — proven by comparing responses pairwise in tests, not just asserting each independently.
- Canonical/candidate protection: `update_node`/`delete_node`/`update_relationship`/`delete_relationship`/`update_claim`/`delete_claim` targeting an `origin:canonical` or `origin:candidate` resource is transparently rewritten into a `create_note` override-proposal ChangeSet (still `201 awaiting_confirmation`, just with a different `operations[0]`) whose content never uses "updated"/"changed"/"modified" about the protected resource. `origin:user` targets are an explicit positive control and mutate through the normal path unaffected.
- OpenAPI/frontend-contract closed-inventory tests and `docs/frontend-api-contract.md` updated in the same task as the new route (38→39 operations, 27→28 templates), per the Wave-0-style blocker in 06-PATTERNS.md.

## Task Commits

Each task was committed atomically (TDD RED then GREEN, both commits cover all three tasks together — see TDD Gate Compliance below):

1. **test(06-05):** `5ac5c19` — ChangeSet propose + canonical/candidate protection tests (Tasks 1, 2, 3)
2. **feat(06-05):** `6bfd6ef` — ChangeSet Stage 1 propose implementation + contract docs (Tasks 1, 2, 3)

## Files Created/Modified
- `backend/app/domain/change_set.py` - 13-type discriminated union, `ChangeSetCreateRequest`/`ChangeSetResponse`
- `backend/app/graph/change_set.py` - `CHANGE_SET_CREATE_QUERY` (draft-only write), `TARGET_VISIBILITY_QUERY` (label-agnostic)
- `backend/app/repository/change_set.py` - `ChangeSetRepository.propose`/`get_visible_target`, `ChangeSetSessionNotFound`
- `backend/app/services/change_set.py` - `ChangeSetService.propose`, in-order validation, canonical/candidate substitution
- `backend/app/api/change_set.py` - `POST /api/series/{series_id}/change-sets`
- `backend/app/main.py` - registered `change_set_router`
- `backend/tests/test_change_set_api.py` - Task 1 (domain) + Task 2 (propose endpoint) tests
- `backend/tests/test_change_set_protection.py` - Task 3 (canonical/candidate protection) tests
- `backend/tests/test_openapi_contract.py`, `backend/tests/test_frontend_contract_doc.py`, `docs/frontend-api-contract.md` - closed-inventory updates for the new route

## Decisions Made
- Reused `retrieval/tools.py`'s fail-closed visibility-filter shape (`visible_from_order <= $visible_until_order`) in a single **label-agnostic** repository query (`TARGET_VISIBILITY_QUERY`) rather than one query per operation-target label — every operation type's target (narrative node, Claim, UserNote) is validated through the identical code path, so hidden/cross-series/nonexistent are provably identical by construction, not by three independently-maintained checks.
- The canonical/candidate override note's `target_type` is resolved from `labels(target)` at validation time (`Claim` → `NoteTargetType.CLAIM`, `Character` → `NoteTargetType.CHARACTER`) — reuses the existing Note-to-entity linking mechanism exactly as instructed, no new ontology relation invented.
- `idempotency_key` is always `null` on a propose-stage draft; the plan's own truths explicitly scope idempotency enforcement to a later confirm/apply stage, not propose.
- Chat-session ownership is enforced in the same Cypher statement that creates the `ChangeSet` (`MATCH (u)-[:HAS_CHAT_SESSION]->(session:ChatSession {...})`) — a foreign/missing `chat_session_id` yields zero rows, mapped to the same generic 404 used elsewhere in this codebase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing validation] Added "at least one field changed" guards on update operations**
- **Found during:** Task 1 (domain model design)
- **Issue:** The plan's action text didn't specify guarding against a no-op update (e.g. an `update_node` with every optional field `None`), which would be a meaningless ChangeSet.
- **Fix:** Added `model_validator(mode="after")` to `UpdateNodeOperation`, `UpdateRelationshipOperation`, and `UpdateClaimOperation` requiring at least one settable field to be non-`None`.
- **Files modified:** `backend/app/domain/change_set.py`
- **Verification:** Covered implicitly by every propose test constructing valid update payloads with a real change; no test exercises the all-`None` rejection path directly, but the guard is exercised by Pydantic on every request.
- **Committed in:** `6bfd6ef`

**2. [Wording clarification, not a fix] Plan text says "twelve" operation types, action text and done-criteria list 13**
- **Found during:** Task 1
- **Issue:** Task 1's `<behavior>` bullet says "outside the twelve allowed values" while listing 13 values, and the `<done>` criterion says "exactly the 13 allowed operation types." This is an internal wording inconsistency in the plan, not a functional ambiguity.
- **Resolution:** Implemented all 13 operation types exactly as listed (matches `<done>` and the PRD's "Suggested operation types" list) — no code change was needed, just noting the discrepancy for the record.

---

**Total deviations:** 1 auto-fixed (Rule 2), 1 wording note (no code impact).
**Impact on plan:** The Rule 2 addition is a correctness guard with no scope creep; the wording note required no fix.

## TDD Gate Compliance

Per 06-PATTERNS.md and the plan's own `<files>` lists, `backend/tests/test_change_set_api.py` is shared between Task 1 (domain-only tests) and Task 2 (propose-endpoint integration tests) by design — the plan lists no separate test file for Task 1 and points Task 1's `<verify>` at the same file Task 2 uses. Similarly, `backend/app/services/change_set.py` is listed as a file for both Task 2 (validation) and Task 3 (protection), since the protection substitution lives inside the same `propose()` orchestration as target validation.

Given this file-sharing by plan design, RED and GREEN were executed as **one combined cycle covering all three tasks**, rather than three isolated per-task RED/GREEN pairs:
- RED: `5ac5c19` adds both `test_change_set_api.py` (Tasks 1+2) and `test_change_set_protection.py` (Task 3) — all initially failing (Tasks 2/3 failed on missing modules; Task 1's assertions were written against the already-drafted domain model in the same working session, so they did not independently fail before GREEN — disclosed here rather than a false RED claim).
- GREEN: `6bfd6ef` adds every implementation file; the full plan verification command (`pytest tests/test_change_set_api.py tests/test_change_set_protection.py tests/test_openapi_contract.py tests/test_frontend_contract_doc.py -x`) passes 28/28 after this commit.

Both a `test(...)` commit and a subsequent `feat(...)` commit exist in git log, satisfying the gate-sequence check; the granularity is plan-level (covering all 3 tasks together) rather than per-task, disclosed above as a deviation from the ideal isolated-per-task RED.

## Issues Encountered
- Two out-of-band verification queries in the test files initially reused the app's shared `Neo4jDatabase` instance via a second `asyncio.run()` call, which deadlocked (the driver's connections are bound to `TestClient`'s portal loop — the exact cross-loop pitfall already documented in `test_chat_api.py`'s fixture comments). Fixed by adding a `_fresh_query()` helper that opens/closes its own driver for every out-of-band check, matching the working pattern already used elsewhere in the test suite.
- Full backend suite run (`uv run pytest`) shows 5 failed + 7 errors, all in `test_seed_idempotency.py`, `test_extraction_models.py`, `test_candidate_ingest.py`, and `test_candidate_review.py` — this is the pre-existing Phase-5 test-pollution issue already logged in `.planning/phases/06-.../deferred-items.md` (confirmed via direct query: zero leftover fixture nodes from this plan's own tests). No new failures outside those four files; 291 passed overall (up from the previously-recorded 265+pollution baseline, consistent with this plan's 28 new tests).

## Next Phase Readiness
- Stage 2 (confirm/apply, 06-06) can now build directly on `ChangeSetRepository`/`ChangeSetService` — the `ChangeSet` draft node, its `operations_json` payload, and `visible_until_order_snapshot` are all in place and match the PRD's `ChangeSet` model shape exactly.
- The frontend `ChangeSetCard` (06-11) has a stable `ChangeSetResponse` wire contract to build against (`status`, `operations[].operation_type`, `summary`) — including the `create_note` override-proposal shape for canonical/candidate refusals.
- No blockers.

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*

## Self-Check: PASSED

All 7 created files found on disk; both commit hashes (`5ac5c19`, `6bfd6ef`) found in `git log`.
