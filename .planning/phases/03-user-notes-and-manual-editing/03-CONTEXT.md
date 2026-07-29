# Phase 3: User Notes and Manual Editing - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

This worktree delivers the **backend slice** of Phase 3: stabilize the existing FastAPI/OpenAPI contract and implement backend CRUD for user notes, user-owned custom nodes, and user-owned custom relationships. It must preserve Phase 1 spoiler filtering, deterministic manual seed setup, canonical-data isolation, and ontology constraints.

No React/Cytoscape files may change. Overall Phase 3 remains incomplete until the separate `frontend-work` worktree integrates these APIs and verifies the UI requirements.

</domain>

<decisions>
## Implementation Decisions

### Worktree and Delivery Boundary
- **D-01:** Work only under backend, backend tests, backend-facing documentation, and planning artifacts in this `backend-work` worktree; do not modify `frontend/`.
- **D-02:** Manual curated JSON/YAML seed data remains the only ingestion path for this sprint. Do not add ingestion services, model clients, queues, vector stores, or extraction placeholders.
- **D-03:** Preserve all verified Phase 1 behavior: real Neo4j health, application-owned async driver, parameterized queries, fail-closed spoiler filtering, graph closure, sanitized errors, ontology validation, and idempotent setup.
- **D-04:** Backend completion does not mark the whole roadmap phase complete; frontend integration remains pending in `frontend-work`.

### Note Lifecycle and Attachments
- **D-05:** A `UserNote` attaches to exactly one target whose type is `Character` or `Claim`. Series, Season, Episode, generic edge, and multi-target attachments are outside this sprint.
- **D-06:** Notes support create, collection retrieval/filtering, direct retrieval, update, and hard deletion.
- **D-07:** The server generates a namespaced stable note ID. Requests cannot choose resource IDs.
- **D-08:** Note responses expose stable timestamps, `origin: "user"`, the attachment type/ID, derived `visible_from_order`, and plain-text content. No authentication identity or rich-text payload is introduced.
- **D-09:** Unsupported, ambiguous, missing, cross-series, or spoiler-hidden attachment targets are rejected; malformed references are never silently accepted.

### Custom-Content Boundaries
- **D-10:** User-created nodes are restricted to existing ontology types `Character`, `Event`, `Location`, `Organization`, and `Object`.
- **D-11:** User-created relationships are restricted to existing narrative and character predicates. Structural, provenance, and revision relationships cannot be created through the generic custom-content API.
- **D-12:** Public mutation models use explicit allowlisted fields. Arbitrary labels, arbitrary relationship types, raw Neo4j properties, and free-form property dictionaries are rejected.
- **D-13:** Custom-content resources use server-generated namespaced stable IDs and `origin: "user"`.
- **D-14:** Update and delete operations succeed only for resources created through the custom-content API. Canonical or candidate resources must never be overwritten or deleted by these routes.
- **D-15:** Custom nodes and relationships must appear through the existing spoiler-filtered graph contract when visible; do not create a second incompatible graph representation.

### Origin and Content Classification
- **D-16:** Keep the existing public field name `origin` and stabilize its values as `canonical | candidate | user`.
- **D-17:** Existing curated seed records remain `origin: "canonical"`; new note/custom content uses `origin: "user"`. Do not introduce a parallel `is_custom` or `source_type` discriminator.

### Spoiler Safety
- **D-18:** Every story-sensitive read requires an explicit `visible_until_order`, using the same persisted positive episode-order contract as `GET /api/series/{series_id}/graph`.
- **D-19:** Missing, malformed, non-positive, or non-persisted boundaries fail closed. The backend must never default to “watched everything.”
- **D-20:** Write visibility is derived server-side from the validated attachment target or selected persisted episode; clients do not submit authoritative `visible_from_order` values.
- **D-21:** Notes/custom content attached to or derived from hidden targets must not appear at earlier boundaries. Queries must filter before Pydantic response construction and preserve graph closure.
- **D-22:** Error messages, existence checks, collection counts, and direct lookups must not reveal hidden canonical or user content.

### REST and OpenAPI Contract
- **D-23:** Preserve existing route names and response fields unless a compatibility correction is explicitly documented for the frontend worktree.
- **D-24:** Use explicit Pydantic request/response models for every public endpoint. Never return raw Neo4j records or database-specific objects.
- **D-25:** Use one documented error envelope: `{"detail": {"code": "machine_code", "message": "Human-readable message."}}`.
- **D-26:** Status codes are: `200` reads/updates, `201` creates, `204` deletes, `404` missing or safely non-visible resources, `409` ownership/conflict cases, and `422` request/boundary/domain validation. Use `400` only if a failure is not representable as validation.
- **D-27:** OpenAPI is the frontend contract. Public operations require summaries, constrained schemas, declared success/error responses, and examples where shape or validation is ambiguous.
- **D-28:** Harden current OpenAPI so `visible_until_order` is documented as required positive episode order rather than nullable string; document graph/series `404`, database `503`, and health `200/503` response shapes.

### Locked Endpoint List
Existing routes remain unchanged:
- `GET /health`
- `GET /api/series`
- `GET /api/series/{series_id}`
- `GET /api/series/{series_id}/episodes`
- `GET /api/series/{series_id}/graph?visible_until_order={order}`

New series-scoped note routes:
- `POST /api/series/{series_id}/notes`
- `GET /api/series/{series_id}/notes?visible_until_order={order}&target_type={type?}&target_id={id?}`
- `GET /api/series/{series_id}/notes/{note_id}?visible_until_order={order}`
- `PATCH /api/series/{series_id}/notes/{note_id}`
- `DELETE /api/series/{series_id}/notes/{note_id}`

New series-scoped custom-node routes:
- `POST /api/series/{series_id}/custom-nodes`
- `GET /api/series/{series_id}/custom-nodes/{node_id}?visible_until_order={order}`
- `PATCH /api/series/{series_id}/custom-nodes/{node_id}`
- `DELETE /api/series/{series_id}/custom-nodes/{node_id}`

New series-scoped custom-relationship routes:
- `POST /api/series/{series_id}/custom-relationships`
- `GET /api/series/{series_id}/custom-relationships/{relationship_id}?visible_until_order={order}`
- `PATCH /api/series/{series_id}/custom-relationships/{relationship_id}`
- `DELETE /api/series/{series_id}/custom-relationships/{relationship_id}`

### Request and Response Schema Summary
- **Note create:** target type (`Character | Claim`), canonical target ID, and non-empty plain-text content. The server derives ID, series, origin, visibility, and timestamps.
- **Note update:** mutable note content only. Attachment identity, origin, and server-owned ID are immutable in this sprint.
- **Note response:** ID, series ID, target type, target ID, content, `origin: "user"`, derived `visible_from_order`, `created_at`, and `updated_at`.
- **Custom node create:** allowlisted node type, label, persisted episode reference used for visibility, and only type-specific allowlisted fields. No arbitrary property map.
- **Custom node update:** allowlisted mutable presentation/domain fields only; ID, series, origin, type, and ownership are immutable.
- **Custom node response:** GraphNode-compatible identity/type/label/visibility/origin fields plus only explicitly modeled custom-content metadata.
- **Custom relationship create:** source ID, target ID, allowlisted narrative/character predicate, and persisted episode reference when required to derive conservative visibility.
- **Custom relationship update:** allowlisted mutable relationship fields only; endpoints, ID, series, and ownership are immutable unless planning proves a safe explicit replacement contract.
- **Custom relationship response:** GraphEdge-compatible ID/source/target/type/visibility/origin fields.
- **List responses:** typed arrays, deterministic ordering, no hidden total/count metadata, and filters that reject partial or contradictory target selectors.

### Validation and Error Rules
- Validate series, persisted episode order, attachment/resource existence, same-series membership, allowed ontology subset, ownership, and visibility before mutation or serialization.
- Reject client-supplied IDs, client-authoritative visibility, arbitrary Neo4j labels/types/properties, canonical mutation, cross-series links, dangling endpoints, and contradictory note filters.
- Keep database exceptions sanitized and declare the stable `503 database_unavailable` envelope in OpenAPI.
- Preserve `series_not_found` and `invalid_visible_until_order`; add stable machine codes for unsupported target/type, resource not found, immutable field, canonical mutation, cross-series reference, and conflict cases.

### Expected Files to Change
Likely existing files:
- `backend/app/main.py`
- `backend/app/api/series.py`
- `backend/app/api/graph.py`
- `backend/app/domain/series.py`
- `backend/app/domain/graph.py`
- `backend/app/core/errors.py`
- `backend/app/graph/seed.py` (validation/idempotency changes only if required)
- `backend/app/spoiler/filter.py`
- `backend/tests/test_graph_api.py`
- `backend/tests/test_seed_idempotency.py`

Expected focused additions, with exact names finalized by the planner to match neighboring conventions:
- user-content API module under `backend/app/api/`
- user-content Pydantic models under `backend/app/domain/`
- user-content Neo4j query/repository module under `backend/app/graph/`
- focused contract/integration tests under `backend/tests/`
- `docs/frontend-api-contract.md`

### Required Subagent Skill Map
- `gsd-planner`: `architecture/backend`, `fastapi`, `neo4j`
- `gsd-executor`: `fastapi`, `neo4j`, `testing`
- `gsd-verifier`: `testing`, `api-review`

### Claude's Discretion
- Exact Pydantic class/module names and internal query organization, while matching established `api` / `domain` / `graph` boundaries.
- Conservative field length constraints and deterministic collection ordering.
- Transaction grouping and query decomposition, provided queries stay parameterized and behavior remains atomic and testable.
- Whether custom relationships are persisted directly or represented through an existing user-authored claim pattern, provided the public GraphEdge-compatible contract and canonical isolation remain unchanged.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Agent Contract
- `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md` §1.1, §3, §4, §5, §7, §8 — one-week manual-seed boundary, invariants, ontology, temporal model, Neo4j identifiers, and recommended REST contract.
- `ROADMAP.md` — canonical Prototype v0 scope; planning artifacts must not narrow it.
- `.planning/PROJECT.md` — project constraints, qualified brownfield facts, and active Prototype v0 boundary.
- `.planning/ROADMAP.md` — dependency-ordered five-phase delivery roadmap; Phase 3 remains UI-incomplete in this worktree.
- `.planning/REQUIREMENTS.md` §Phase 3 — NOTE-01 through NOTE-03 acceptance scope.
- `.planning/STATE.md` — Phase 1 verified baseline and current project position.

### Existing Backend Contract and Safety Baseline
- `backend/app/main.py` — app lifespan, router integration, CORS, and health behavior.
- `backend/app/api/series.py` — existing series/episode route conventions.
- `backend/app/api/graph.py` — existing graph route, boundary parsing, query composition, and response construction.
- `backend/app/domain/graph.py` — current public graph models and closure validation.
- `backend/app/domain/series.py` — current metadata response models.
- `backend/app/core/errors.py` — sanitized Neo4j error envelope.
- `backend/app/graph/database.py` — application-owned async driver and parameterized query execution.
- `backend/app/graph/ontology.py` — ontology allowlist loading and validation.
- `backend/app/graph/seed.py` — manual seed loading, validation, constraints, and idempotent upserts.
- `backend/app/spoiler/filter.py` — fail-closed node/edge/claim/source/evidence Cypher.
- `backend/tests/test_graph_api.py` — verified boundary, error, validity, and graph-closure behavior.
- `backend/tests/test_seed_idempotency.py` — verified 41-node/26-relationship idempotent setup and provenance checks.
- `ontology/node_types.yaml` — existing node types, including `UserNote`; no unrelated expansion permitted.
- `ontology/relation_types.yaml` — relationship allowlist from which the user-safe subset must be selected.
- `ontology/claim_types.yaml` — existing user-authored claim and status vocabulary.
- `data/dexter/metadata/*.json` and `data/dexter/seed/*.json` — sole curated ingestion fixtures for this sprint.

</canonical_refs>

<code_context>
## Existing Code Insights

### Current Verified State
- `uv run pytest -q` passed **13 tests** on 2026-07-29; one third-party Starlette deprecation warning remains.
- Live idempotency tests prove repeated setup yields the same **41 nodes and 26 relationships**.
- The generated OpenAPI currently exposes `visible_until_order` as nullable string and omits several runtime `404`/`503` response contracts; this is a concrete hardening target.

### Reusable Assets
- `Neo4jDatabase.execute_query`: async parameterized query boundary for all new persistence operations.
- `_error` pattern in `backend/app/api/graph.py`: starting point for the shared documented error contract.
- `GraphNode`, `GraphEdge`, and `GraphResponse`: public graph compatibility target for custom content.
- `load_ontology` and validation methods: authoritative allowlists; do not duplicate ontology constants in route handlers.
- Existing setup/idempotency fixtures: baseline for proving new schema/setup behavior remains rerunnable.

### Established Patterns
- FastAPI dependencies resolve the lifespan-owned database from `app.state`.
- Cypher performs spoiler filtering before response construction.
- Pydantic validates public serialization and graph closure.
- Deterministic seed IDs use namespaced strings; user-resource IDs must be server-generated and namespaced separately.
- Database startup may degrade safely while docs remain available.

### Integration Points
- Register new routers in `backend/app/main.py`.
- Extend spoiler-filtered graph queries so visible user content participates without bypassing canonical safety checks.
- Use ontology-approved allowlists in request validation and persistence.
- Expand tests without modifying frontend fixtures or introducing an external ingestion path.
- Publish final response/error examples in `docs/frontend-api-contract.md` for the `frontend-work` agent.

### Codebase Map Warning
- `.planning/codebase/STACK.md`, `ARCHITECTURE.md`, and `INTEGRATIONS.md` were mapped before Phase 1 and contain stale claims (for example, missing tests and import-time driver ownership). Downstream agents must trust the live files and Phase 1 verification over those stale map statements.

</code_context>

<specifics>
## Specific Ideas

### Frontend Handoff Requirements
The final backend contract document must contain:
1. locked endpoint list;
2. request and response schema summaries;
3. validation and stable error rules;
4. spoiler-filtering and boundary rules;
5. compatibility changes the frontend worktree must account for;
6. examples for ambiguous create/read/error cases.

### Unresolved Decisions Requiring User Approval
None at discussion close. Any planner proposal that changes the locked endpoint paths, broadens attachment targets, permits canonical mutation, adds ontology types, changes `origin` values, weakens explicit boundary requirements, or expands beyond backend scope must return for user approval.

</specifics>

<deferred>
## Deferred Ideas

- React/Cytoscape note and custom-content UI — separate `frontend-work` worktree; required before overall Phase 3 completion.
- Revision history, restoration, and soft deletion — Phase 4.
- Candidate review/moderation and extraction contracts — Phase 5.
- Authentication, permissions, per-user identity, collaboration, file uploads, rich-text editing, automatic ingestion, LLM extraction/chat, and ontology expansion — post-v0 or separate future phases.

</deferred>

---

*Phase: 3-user-notes-and-manual-editing*
*Context gathered: 2026-07-29*
