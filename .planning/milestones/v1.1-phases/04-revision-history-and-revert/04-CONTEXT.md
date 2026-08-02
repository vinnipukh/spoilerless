# Phase 4: Revision History and Revert — Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **backend slice** of Phase 4: append-only Revision model, API endpoints for listing/inspecting/reverting revisions, and automatic revision logging of all existing user-content mutations (notes, custom nodes, custom relationships). It also logs claim mutations if claim-editing endpoints are present.

No React/Cytoscape files may change. Overall Phase 4 requires frontend history-panel integration to be fully complete, but this context delivers the complete backend.

</domain>

<decisions>
## Implementation Decisions

### Domain Model
- **D-01:** `Revision` Neo4j node with properties: `id` (namespaced `revision:{uuid4}`), `series_id`, `resource_type` (neolabel like UserNote/Claim/Character), `resource_id`, `action` (Created/Updated/Deleted/Reverted), `before` (JSON string of prior state or null), `after` (JSON string of new state or null), `created_at` (UTC datetime).
- **D-02:** Use `REVISES` relationship from Revision to the modified resource. Link is important for future graph traversal, but not exposed in initial API.
- **D-03:** Every user-content mutation (note create/update/delete, custom-node create/update/delete, custom-relationship create/update/delete) must create a Revision in the **same Neo4j transaction** as the mutation.

### Action Semantics
- **D-04:** `Created`: before=null, after=resource state after creation.
- **D-05:** `Updated`: before=resource state before mutation, after=resource state after mutation.
- **D-06:** `Deleted`: before=resource state before deletion, after=null.
- **D-07:** `Reverted`: before=resource state before revert mutation, after=resource state after revert. Revert always creates a new revision (never mutates existing ones).

### Revert Behavior
- **D-08:** Revert for notes: restore content from the revision's "before" snapshot. Revert for custom nodes: restore label from "before". Revert for custom relationships: restore predicate from "before".
- **D-09:** Revert is only supported for `Updated` and `Deleted` actions (you can't revert a create — the resource would be deleted; you can't revert a revert — use the original revision's after state).
- **D-10:** Reverting a deleted resource: the action is `Created` — the resource is re-created from the revision's before snapshot. This creates a new revision with action=Reverted, showing before=null, after=restored state.
- **D-11:** Revert must verify that the target resource still exists and belongs to origin='user'. Canonical/candidate resources are never revertable through this API.

### REST API
- **D-12:** New routes:
  - `GET /api/series/{series_id}/revisions?visible_until_order={order}&resource_type={type?}&resource_id={id?}` — list revisions
  - `GET /api/series/{series_id}/revisions/{revision_id}?visible_until_order={order}` — get single revision
  - `POST /api/series/{series_id}/revisions/{revision_id}/revert` — revert to revision
- **D-13:** List returns most recent first (order by `created_at DESC`). Supports optional resource_type and resource_id filters.
- **D-14:** Revert is idempotent: calling revert twice on the same revision creates two revert revisions. The first reverts to the old state; the second reverts back to the prior state.
- **D-15:** All revision routes require the standard `visible_until_order` spoiler boundary. Revisions attached to hidden resources are filtered out.

### Integration Points
- **D-16:** Modify `backend/app/repository/user_content.py` to create Revision records inside every write transaction. Use a shared helper `_log_revision(tx, ...)` that creates a Revision node and REVISES relationship.
- **D-17:** Add Revision constraint and index to `backend/app/graph/seed.py` `create_constraints()`.
- **D-18:** Wire the revision router in `backend/app/main.py`.
- **D-19:** The `backend/app/revisions/` package becomes the home for the revision API and repository. Move revision-specific code there, not into user_content.py.

</decisions>

<canonical_refs>
## Canonical References

- ROADMAP.md §Phase 4 — Revision History and Revert requirements
- `.planning/REQUIREMENTS.md` — REV-01, REV-02, REV-03
- `.planning/STATE.md` — current project position
- `backend/app/domain/user_content.py` — existing user-content Pydantic models
- `backend/app/repository/user_content.py` — existing Neo4j persistence for user content
- `backend/app/api/user_content.py` — existing user-content API routes (pattern for revision routes)
- `backend/app/graph/seed.py` — constraint/index creation patterns
- `backend/app/core/errors.py` — shared error contract
- `backend/app/main.py` — router registration

</canonical_refs>

<code_context>
## Existing Code Insights

### Patterns to Follow
- Error handling: `error_responses(404, 422, 503)` + `http_error(...)` from `backend/app/core/errors.py`
- Router pattern: `APIRouter(prefix="/api/series", tags=["revisions"])` 
- Parameterized Cypher via `Neo4jDatabase.execute_query`
- Managed write transactions via `Neo4jDatabase.execute_write`
- Test pattern: module-scoped `live_client` fixture, `user_content_client` fixture, `second_series` fixture
- Revision logging must happen inside the same `execute_write` callback as the mutation

### State to Preserve
- All existing tests must remain green
- No frontend changes
- No new dependencies
- Canonical data isolation (revert must not touch canonical resources)
- Fail-closed spoiler filtering for revision visibility

</code_context>

<specifics>
## Implementation Strategy

### Plan 04-01: Revision domain model + Neo4j persistence
Files:
- `backend/app/domain/revision.py` — new: Action enum (StrEnum), RevisionResponse, RevertResponse models
- `backend/app/revisions/__init__.py` — implement: RevisionRepository class
- `backend/app/graph/seed.py` — add: Revision constraint, REVISES index
- `backend/app/repository/user_content.py` — modify: add _log_revision and call it in each write callback

### Plan 04-02: Revision API + revert endpoint
Files:
- `backend/app/api/revisions.py` — new: list/get/revert routes
- `backend/app/main.py` — modify: register revision router
- `backend/tests/test_revisions.py` — new: API tests

### Plan 04-03: Tests + verification
- Full test suite for revision model, repository, API, revert
- Verify all existing tests still pass
- Verify no frontend contamination

</specifics>

<deferred>
- Frontend history panel (UI rendering of revisions and revert button)
- Revision tracking for canonical/seed data changes
- Revision diff view (structured before/after comparison)
- Revert on claims (deferred until claim-editing UI exists)
- Batch revert/multi-revision operations

</deferred>

---

*Phase: 04-revision-history-and-revert*
*Context gathered: 2026-07-30*
