---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 07
subsystem: api
tags: [neo4j, fastapi, changeset, revert, revision, graph-editing]

# Dependency graph
requires:
  - phase: 06-06
    provides: ChangeSet Stage 2 (Confirm and Apply) — transactional apply, exactly one
      Revision per apply (resource_type='ChangeSet', action=Created), idempotency,
      staleness rejection
  - phase: 4
    provides: Revision domain model, RevisionRepository.log_revision, the
      api/revisions.py::revert_revision read-branch-apply-log pattern
provides:
  - "POST /api/series/{series_id}/change-sets/{change_set_id}/revert — reverts a
    previously applied, entirely create-shaped ChangeSet by deleting every resource
    it created, logging a new Reverted-action Revision, never editing the original"
  - Conflict detection guarding against overwriting a later, unrelated change to a
    created resource (fresh updated_at-vs-applied_at comparison, evaluated in Cypher)
  - "cannot_revert" rejection (422) for ChangeSets containing any update/delete-shaped
    operation, which has no stored per-operation prior state to restore
affects: [06-11]

# Actuals (#2632)
actuals:
  tokens: 12000
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Revert-eligibility gate: only ChangeSets whose applied operations are ALL
      create-shaped (create_node/create_relationship/create_claim/attach_evidence/
      create_note) support revert, derived from the ChangeSet's own apply-time
      Revision.after.operation_types — because Stage 2 (06-06) logs exactly ONE
      coarse Revision per apply with no per-operation 'before' snapshot, an
      update/delete-shaped operation has no recorded prior state to restore and
      raises ChangeSetRevertUnsupported (422), mirroring api/revisions.py::
      revert_revision's 'cannot revert a Creation revision' discipline: some
      shapes have no well-defined restore target and are rejected, never invented."
    - "In-Cypher freshness comparison instead of a Python-side value: the revert
      delete query MATCHes the ChangeSet node itself and compares
      `resource.updated_at = cs.applied_at` entirely inside one Cypher statement —
      never round-trips a driver-native Neo4j datetime through Python (which
      re-serializes it to a string via `_normalize` and would then never match a
      raw property in a WHERE clause). Zero rows back means the resource was
      touched by a later, unrelated change; the whole revert transaction aborts."
    - "Generic, label-agnostic single delete query for every create-shaped undo:
      MATCH (resource {id, series_id}) WHERE origin='user' AND
      updated_at=cs.applied_at, DETACH DELETE — works identically for a created
      node, Claim (relationship or claim), EvidenceFragment, or UserNote, since
      DETACH DELETE also removes the REFERS_TO/SUPPORTED_BY relationships those
      creates attached."

key-files:
  created:
    - backend/tests/test_change_set_revision.py
  modified:
    - backend/app/graph/change_set.py
    - backend/app/repository/change_set.py
    - backend/app/services/change_set.py
    - backend/app/api/change_set.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_frontend_contract_doc.py
    - docs/frontend-api-contract.md

key-decisions:
  - "Revert semantics deviate from a literal per-resource field-level restore
    (what api/revisions.py::revert_revision does for a single UPDATED/DELETED
    resource) because Stage 2 (06-06) never recorded a per-operation 'before'
    snapshot — only one coarse ChangeSet-level Revision with
    {operation_types, affected_ids}. The minimal-revert allowance RAG-15
    explicitly grants ('a minimal revert implementation is acceptable... but
    applied changes must still be auditable') is resolved as: revert deletes
    every resource a create-shaped ChangeSet created (a well-defined pre-apply
    state — 'it did not exist'), and rejects (422) any ChangeSet containing an
    update/delete-shaped operation, since restoring those would require
    inventing state that was never recorded. This is disclosed here as planner
    discretion, not a literal fork/copy of revisions.py's field-restore code."
  - "The ChangeSet's own `revision_id` is repointed to the new Reverted Revision
    on successful revert (status: applied -> reverted). This does not violate
    'never edits the original Revision' (that invariant is about the Revision
    node's own fields, verified byte-identical before/after) — it is a
    ChangeSet-node property update to the SAME field 'applied' already used to
    point at its own resolving Revision, now pointing at reverted's."
  - "Conflict detection compares `resource.updated_at` against the ChangeSet's
    own `applied_at`, both read fresh from Neo4j inside the same Cypher
    statement — not a Python-side value passed as a query parameter, which
    would compare a driver-native datetime property against a re-serialized
    ISO string and never match (caught before any test run, by reasoning about
    `_normalize`'s `iso_format()` conversion, not via a failing test)."
  - "Truth 5 ('only user-origin changes support revert... consistent with the
    canonical/candidate protection invariant') is verified via the real
    transparent-substitution path (an update_node targeting a canonical
    resource becomes a create_note override at propose time, per 06-05):
    reverting that override deletes only the user-origin note, never the
    canonical target — proven end-to-end rather than via a repository-level
    unit test bypassing the substitution."

requirements-completed: [RAG-15]

coverage:
  - id: D1
    description: "Reverting a ChangeSet with exactly one applied (create-shaped) Revision succeeds, deletes every resource it created, and logs a new Reverted-action Revision"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_after_single_applied_change_set_deletes_created_resource"
        status: pass
    human_judgment: false
  - id: D2
    description: "Reverting a ChangeSet with no applied Revision (never confirmed, or already resolved) is rejected; reverting an already-reverted ChangeSet is rejected"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_rejected_when_change_set_was_never_applied"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_reverting_an_already_reverted_change_set_is_rejected"
        status: pass
    human_judgment: false
  - id: D3
    description: "Revert never edits or deletes the original apply-time Revision — its fields are byte-identical before and after, with the new Reverted Revision appended after it"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_never_edits_the_original_apply_revision"
        status: pass
    human_judgment: false
  - id: D4
    description: "A resource modified by a later, unrelated ChangeSet after this one applied causes revert to fail with a conflict, leaving the later change's state untouched"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_conflicts_when_resource_modified_by_later_unrelated_change"
        status: pass
    human_judgment: false
  - id: D5
    description: "Revert requires its own explicit call — a chat message alone never triggers it"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_requires_explicit_call_never_triggered_by_a_chat_message"
        status: pass
    human_judgment: false
  - id: D6
    description: "A ChangeSet containing any update/delete-shaped operation has no stored prior state to restore and is rejected with 422, leaving its applied state untouched"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_rejected_for_change_set_with_no_stored_prior_state"
        status: pass
    human_judgment: false
  - id: D7
    description: "Missing or cross-user change_set_id is a generic 404, matching confirm/reject's discipline"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_generic_404_for_missing_or_cross_user_change_set"
        status: pass
    human_judgment: false
  - id: D8
    description: "Reverting a canonical/candidate-protection override note leaves the canonical resource itself completely untouched, consistent with RAG-13's protection invariant"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_revision.py#test_revert_of_canonical_override_note_leaves_canonical_resource_untouched"
        status: pass
    human_judgment: false
  - id: D9
    description: "Revert route registered in the closed OpenAPI/frontend-contract inventory (30->31 templates, 41->42 operations); full backend regression suite shows zero new failures, including Phase 4's own revision/revert tests unmodified"
    requirement: "RAG-15"
    verification:
      - kind: integration
        ref: "backend/tests/test_openapi_contract.py#test_user_route_openapi_has_exact_operations_and_templates"
        status: pass
      - kind: integration
        ref: "backend/tests/test_frontend_contract_doc.py#test_document_and_openapi_have_exact_locked_inventory"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 07: ChangeSet Revert Summary

**Minimal, safe revert for ChangeSet-originated changes — deletes every resource a create-shaped ChangeSet applied, logs a new Reverted Revision without ever editing the original, and conflicts (409) rather than silently overwrites a later, unrelated change.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files modified/created:** 8

## Accomplishments
- `backend/app/repository/change_set.py::ChangeSetRepository.revert` follows `api/revisions.py::revert_revision`'s read-branch-apply-log shape inside one `execute_write` transaction: reads the ChangeSet (user-scoped), rejects (409) if `status != "applied"` (nothing to revert), reads its own apply-time Revision to recover `{operation_types, affected_ids}`, rejects (422) if any operation is update/delete-shaped (no stored prior state to restore), deletes every affected resource with a fresh Cypher-side `updated_at = cs.applied_at` conflict guard, logs a new `Reverted`-action Revision, and marks the ChangeSet `reverted`.
- `backend/app/graph/change_set.py` gained `CHANGE_SET_REVISION_GET_QUERY` (server-internal Revision read by id, unfiltered by visibility — distinct from the user-facing `REVISION_GET_QUERY`), `CHANGE_SET_REVERT_DELETE_QUERY` (one generic, label-agnostic delete usable for every create-shaped resource type — node, Claim, EvidenceFragment, UserNote), and `MARK_CHANGE_SET_REVERTED_QUERY` (only transitions from `status='applied'`, ownership-scoped via the `(:AppUser)-[:PROPOSED_CHANGE_SET]->` pattern).
- `POST /api/series/{series_id}/change-sets/{change_set_id}/revert` added to `backend/app/api/change_set.py`, mapping `ChangeSetNotFound`->404, `ChangeSetNotRevertible`->409, `ChangeSetRevertConflict`->409, `ChangeSetRevertUnsupported`->422 — same generic-404/ownership discipline as confirm/reject.
- 9 new integration tests in `backend/tests/test_change_set_revision.py` covering the full behavior matrix: successful revert, zero-Revision rejection, double-revert rejection, original-Revision byte-identity, later-unrelated-change conflict (leaving that later state untouched), explicit-call-only (chat-message regression), unsupported update/delete-shaped ChangeSets, generic 404 for missing/cross-user, and canonical-resource protection consistency via the real transparent-substitution path.
- Contract inventory updated: `test_openapi_contract.py`/`test_frontend_contract_doc.py` (30->31 path templates, 41->42 operations) and `docs/frontend-api-contract.md` gained a "Stage 3 — revert" section documenting the eligibility gate, conflict semantics, and error codes for the 06-11 frontend integration.
- Full backend suite: **311 passed** (302 pre-existing baseline + 9 new), **5 failed / 7 errors** — identical pre-existing Phase-5 test-pollution failures already logged in `deferred-items.md` (same test names as the known_deferred_item baseline). Zero regressions, and Phase 4's own `/api/revisions/{id}/revert` tests pass unmodified.

## Task Commits

1. **feat(06-07):** `b1b32c1` — revert endpoint, repository/service/API wiring, and 9 tests (Task 1; test+implementation combined in one commit — see TDD Gate Compliance below)
2. **docs(06-07):** `878f3e2` — register revert route in closed contract inventory, full-suite regression confirmation (Task 2)

## Files Created/Modified
- `backend/app/graph/change_set.py` - `CHANGE_SET_REVISION_GET_QUERY`, `CHANGE_SET_REVERT_DELETE_QUERY`, `MARK_CHANGE_SET_REVERTED_QUERY`
- `backend/app/repository/change_set.py` - `RevertChangeSetCommand`, `ChangeSetNotRevertible`/`ChangeSetRevertUnsupported`/`ChangeSetRevertConflict` exceptions, `_CREATE_OPERATION_TYPES`, `ChangeSetRepository.revert`/`_revert_change_set`
- `backend/app/services/change_set.py` - `ChangeSetService.revert` orchestration, re-exported exceptions
- `backend/app/api/change_set.py` - `POST .../{change_set_id}/revert`, error mapping (404/409/409/422)
- `backend/tests/test_change_set_revision.py` - 9 tests covering the full must-haves matrix
- `backend/tests/test_openapi_contract.py`, `backend/tests/test_frontend_contract_doc.py`, `docs/frontend-api-contract.md` - closed-inventory + documentation updates for the revert route

## Decisions Made
- Revert semantics are scoped to create-shaped ChangeSets only, deviating from a literal field-level restore, because Stage 2 (06-06) records exactly one coarse ChangeSet-level Revision (`{operation_types, affected_ids}`, `before: null`) with no per-operation prior-state snapshot to restore an update/delete from. This is the RAG-15 "minimal revert implementation is acceptable" allowance, resolved as: create-shaped ChangeSets are fully revertible (delete what was created — a well-defined pre-apply state); update/delete-shaped ChangeSets are rejected (422) rather than silently mishandled, mirroring `api/revisions.py::revert_revision`'s existing "cannot revert a Creation revision" discipline for the analogous "no well-defined restore target" case.
- The ChangeSet's `revision_id` field is repointed to the new Reverted Revision on successful revert — this updates the ChangeSet node's own property (already repointed at each resolving Revision, exactly as `confirm` does), never the original Revision node's own fields (verified byte-identical by test).
- Conflict detection compares `resource.updated_at` against the ChangeSet's own `applied_at`, both read from the same Neo4j node inside one Cypher statement — never a Python-side value, which would compare a driver-native datetime against a re-serialized ISO string (via `_normalize`'s `iso_format()`) and never match. Caught by design review before any test run, not via a failing test.
- Truth 5's canonical-protection consistency is verified via the real transparent-substitution path (an `update_node` on a canonical target becomes a `create_note` override at propose time per 06-05) rather than a synthetic repository-level bypass — proving end-to-end that revert never touches the canonical resource itself.

## Deviations from Plan

### Auto-fixed Issues

None — the datetime-comparison design flaw described above was caught during design/implementation (before any test was written or run), not discovered via a failing test or post-hoc bug, so it is documented as a key decision rather than a Rule 1 auto-fix.

**Total deviations:** 0 auto-fixed. One documented design decision (revert scope limited to create-shaped ChangeSets) required by the actual data model Stage 2 (06-06) persisted, disclosed above as planner discretion per the plan's own "planner discretion resolved in favor of..." framing.
**Impact on plan:** None — every must-have truth in the plan's frontmatter is satisfied; the scope decision is the only viable reading given what 06-06 actually recorded, and is fully tested.

## TDD Gate Compliance

Task 1 was authored `tdd="true"`. Test and implementation were written together and committed in a single `feat(06-07)` commit (`b1b32c1`) rather than a separate `test(...)` (RED) commit followed by `feat(...)` (GREEN) — all 9 tests passed on the first run against the already-complete implementation, so there was no genuinely-failing RED state to commit separately. This follows the same disclosed precedent as 06-06's SUMMARY ("RED and GREEN executed as one combined cycle... disclosed here rather than a false RED claim"). No separate `test(...)` commit exists in git log for this plan; this is recorded here as a known gate-sequence gap rather than silently claimed as satisfied.

## Issues Encountered
- Full backend suite (`uv run pytest`) shows `311 passed / 5 failed / 7 errors` — the failures/errors are the exact same pre-existing Phase-5 test-pollution issue already logged in `.planning/phases/06-.../deferred-items.md` and confirmed present at the start of this plan's execution (`test_seed_idempotency.py` x3, `test_extraction_models.py` x2, `test_candidate_ingest.py` x4 errors, `test_candidate_review.py` x3 errors). 302 pre-existing baseline + 9 new tests from this plan = 311; identical failing test names, zero new failures.

## Next Phase Readiness
- RAG-15 is now fully satisfied: ChangeSet-originated changes can be safely undone (create-shaped) or explicitly rejected as unsupported (update/delete-shaped), with full auditability via the Revision log.
- 06-11 (frontend `ChangeSetCard` confirm/reject/revert wiring) can build directly against the real revert response shape (`status:"reverted"`, `revision_id` repointed) and error codes documented in `docs/frontend-api-contract.md`'s new "Stage 3 — revert" section.
- No blockers.

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*

## Self-Check: PASSED

All 8 created/modified files found on disk; both commit hashes (`b1b32c1`, `878f3e2`) found in `git log`.
