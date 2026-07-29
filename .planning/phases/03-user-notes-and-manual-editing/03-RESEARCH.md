# Phase 03 Research: Backend User Notes, Manual Content, and Contract Hardening

**Phase:** 03 — User Notes and Manual Editing (backend slice only)  
**Researched:** 2026-07-29  
**Confidence:** High for the live-code findings and recommended shape; medium for the two write-boundary ambiguities called out below, which the planner must resolve conservatively without changing locked routes.

## Summary

Phase 03 should be planned as a small extension of the existing `api` → `domain` → `graph` layering, not as a service-framework rewrite. Add one user-content router, strict Pydantic models, and one user-content repository/query module; extend the existing graph projection and shared error/OpenAPI definitions. Preserve the lifespan-owned `Neo4jDatabase`, parameterized Cypher, manual seed path, graph response, and fail-closed filtering.

The safest minimal persistence design is:

1. Store notes as `(:UserNote)` nodes attached to exactly one `Character` or `Claim` through an existing `:REFERS_TO` relationship.
2. Store custom nodes under their existing ontology label (`Character`, `Event`, `Location`, `Organization`, or `Object`) with `origin = "user"` and a server-generated `user-node:` ID.
3. Store custom relationships as `(:Claim)` nodes with `claim_type = "user_authored"`, `origin = "user"`, stable `user-rel:` IDs, immutable subject/object/series ownership, and a predicate from the existing participation/character allowlist. Project these records into `GraphEdge`; do **not** require evidence for this explicitly user-authored branch.
4. Keep the existing canonical/candidate claim query evidence-mandatory. Add a separate user-relationship projection rather than weakening it with broad `OPTIONAL MATCH` clauses.
5. Derive every write's `visible_from_order` from persisted graph state: note target visibility for notes; persisted episode plus referenced endpoint visibility for custom content. Never accept `id`, `origin`, `series_id`, timestamps, or authoritative visibility from clients.
6. Use managed write transactions for validation plus mutation. Generate IDs/timestamps before the retryable transaction callback, match `origin = "user"` and the expected namespace on update/delete, and use `DETACH DELETE` only after dependency checks.
7. Stabilize OpenAPI with required `integer > 0` boundary parameters, strict enums/allowlists, `extra="forbid"`, typed success responses, a shared error envelope, declared `404/409/422/503` responses, health models, and contract tests over `app.openapi()`.

This completes only the backend half. It must not modify `frontend/` and must not mark Phase 03 complete while the separate frontend integration remains pending (`03-CONTEXT.md:19-22`; `.planning/ROADMAP.md:26-34`; `.planning/STATE.md:44-46`).

## Baseline Verified During Research

- `uv run pytest -q` returned **13 passed, 1 warning in 4.10s**. The warning is the already-known Starlette `httpx` deprecation.
- Live environment versions: FastAPI `0.140.7`, Pydantic `2.13.4`, Neo4j Python driver `6.2.0`; `pyproject.toml:4-12` requires Python `>=3.13` and carries no repository/service framework dependency.
- Live Neo4j is Community `2026.06.0` with Cypher 5. Current setup has uniqueness constraints for `Series`, `Episode`, `Character`, `Event`, `Location`, `Claim`, `Source`, and `EvidenceFragment`, but none for `UserNote`, `Organization`, or `Object`.
- Current OpenAPI proves the hardening gap: graph `visible_until_order` is optional `string | null`; graph only declares `200/422`; series detail only declares `200/422`; health `200` has an empty schema and no declared `503`.
- The orchestration workflow temporarily added `_auto_chain_active: false` to `.planning/config.json`; the orchestrator removed that ephemeral key before committing research.

## Existing Patterns and Exact Reuse Points

### Application and routing

- `backend/app/main.py:19-32` owns the async Neo4j driver in FastAPI lifespan and deliberately permits degraded startup. New routes must obtain this same instance, never create import-time or per-request drivers.
- `backend/app/main.py:35-51` is the router/error-handler registration point. Add one user-content router here and keep CORS unchanged.
- `backend/app/main.py:54-75` performs a real health check but returns unmodeled `JSONResponse` objects. Preserve runtime behavior while adding typed `200/503` OpenAPI shapes.
- `backend/app/api/series.py:10-72` establishes the `/api/series` prefix, `Annotated` dependency convention, persisted query style, ordered list response, and stable series 404 envelope.
- `backend/app/api/graph.py:28-37` repeats the dependency and `_error` helper. Move/reuse the helper from a shared contract/error module rather than duplicating it in the new router.
- `backend/app/api/graph.py:57-121` validates series/boundary before concurrent reads, constructs Pydantic response objects, and appends claim-projected edges. Extend this response assembly with a separately queried user-edge projection.

### Domain and response closure

- `backend/app/domain/graph.py:10-26` defines the compatibility targets `GraphNode` and `GraphEdge`; custom graph content should serialize to these exact fields.
- `backend/app/domain/graph.py:29-44` assumes all returned `GraphClaim` records contain provenance. Do not force evidence-free user relationships through this response class unless it is deliberately split into another typed model.
- `backend/app/domain/graph.py:70-89` validates graph closure after serialization. Keep this defense in depth, but continue filtering endpoints in Cypher first.
- `backend/app/domain/series.py:4-18` demonstrates positive integer response constraints but currently has no enums, examples, or strict-extra policy.

### Database, ontology, setup, and spoiler filtering

- `backend/app/graph/database.py:11-52` is the only database boundary. `execute_query()` is appropriate for single-query reads and writes, but multi-step validate/classify/mutate work needs a repository callback executed by `session.execute_write()` in one retryable transaction.
- `backend/app/graph/database.py:55-60` provides the app-state dependency. Reuse it unchanged in route signatures.
- `backend/app/graph/ontology.py:34-74` loads versioned ontology values and provides allowlist validators. Extend it to preserve relationship groups or define a user-safe subset adjacent to this loader; do not scatter route-local strings.
- `ontology/node_types.yaml:10-23` already includes all five custom node labels and `UserNote`. No ontology expansion is needed.
- `ontology/relation_types.yaml:10-28` is the exact permitted custom relationship subset: participation (`PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`) plus character (`KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS`). Structural (`:4-8`), provenance (`:30-34`), and revision (`:36-39`) types are not public custom predicates.
- `ontology/claim_types.yaml:3-15` already provides `user_authored` and existing statuses. No new claim type/status is needed.
- `backend/app/graph/seed.py:16-33` currently omits `Organization`, `Object`, and `UserNote` from constraint/index setup. Add them without changing seed ingestion inputs.
- `backend/app/graph/seed.py:112-149` uses idempotent `IF NOT EXISTS` DDL and tolerates Community's lack of property-existence constraints. Follow this exact setup pattern.
- `backend/app/graph/seed.py:152-175` and `:177-246` are deterministic canonical upserts. Do not route user content through these loaders and do not let setup overwrite/delete `origin=user` records.
- `backend/app/spoiler/filter.py:8-13` validates that the boundary is an actually persisted episode in the requested series.
- `backend/app/spoiler/filter.py:15-27` filters nodes in Cypher before Pydantic. Add `Organization` and `Object` to the route's visible labels; `UserNote` should remain in note APIs unless product/UI explicitly needs notes as graph nodes.
- `backend/app/spoiler/filter.py:29-45` enforces source/target/edge visibility and same-series closure for structural edges.
- `backend/app/spoiler/filter.py:47-78`, `:80-100`, and `:102-126` require complete evidence/source paths and enforce claim validity independently from visibility. Preserve these queries as the evidence-backed branch.

### Tests and data

- `backend/tests/test_graph_api.py:34-49` seeds live Neo4j and exposes the current live `TestClient` fixture.
- `backend/tests/test_graph_api.py:52-70` proves sanitized database errors; reuse this failure-injection pattern for new endpoints.
- `backend/tests/test_graph_api.py:138-168` proves stable boundary/error behavior and database 503 sanitization.
- `backend/tests/test_graph_api.py:171-209` checks full serialized spoiler sentinels, exact counts, and closure at orders 1–3. Extend it with visible user-content cases without making all baseline canonical count assertions order-dependent.
- `backend/tests/test_seed_idempotency.py:25-71` snapshots nodes/relationships and proves exact 41/26 idempotency.
- `backend/tests/test_seed_idempotency.py:74-114` verifies uniqueness, visibility, and provenance. Extend canonical provenance assertions so user-authored relationships are exempt only through an explicit `origin=user AND claim_type=user_authored` condition.
- `data/dexter/metadata/episodes.json:2-30` is the persisted episode-order source for all write visibility.
- `data/dexter/seed/characters.json:2-10` and `data/dexter/seed/claims.json:2-10` show namespaced canonical IDs, series ownership, positive visibility, and `origin=canonical` conventions.

## Recommended Architecture and File Ownership

### Additions

- `backend/app/api/user_content.py` — all locked series-scoped note/custom-node/custom-relationship routes; thin validation/orchestration only.
- `backend/app/domain/user_content.py` — enums, create/patch/response models, discriminated custom-node request union, shared examples.
- `backend/app/graph/user_content.py` — Cypher constants and transaction/repository operations; no FastAPI imports.
- `backend/tests/test_user_content_models.py` — pure Pydantic/enum/schema tests.
- `backend/tests/test_user_content_api.py` — live CRUD, ownership, isolation, spoiler, deletion, and 503 tests.
- `backend/tests/test_openapi_contract.py` — no-database OpenAPI assertions.
- `docs/frontend-api-contract.md` — locked endpoints, schemas, examples, stable errors, visibility rules, and frontend compatibility notes required by `03-CONTEXT.md:206-213`.

### Focused modifications

- `backend/app/main.py` — router registration, modeled health responses, request-validation handler registration.
- `backend/app/core/errors.py` — `ErrorDetail`/`ErrorResponse`, shared exception helper, sanitized RequestValidationError handler, response declaration helpers/constants if useful.
- `backend/app/domain/graph.py` — `Origin` enum and stronger GraphNode/GraphEdge typing only if compatible with existing output.
- `backend/app/api/graph.py` — required positive boundary, declared responses, summaries, custom-edge query/assembly, expanded visible custom node labels.
- `backend/app/api/series.py` — summaries and declared `404/503` responses; preserve fields/routes.
- `backend/app/graph/database.py` — small `execute_write` transaction hook, not a repository framework.
- `backend/app/graph/ontology.py` — expose/test the safe relationship categories rather than duplicate unverified constants.
- `backend/app/graph/seed.py` — idempotent constraints/indexes only; no user-content ingestion.
- `backend/app/spoiler/filter.py` — separate visible user-edge query and any shared fail-closed predicates.
- Existing graph/idempotency tests — regression coverage and setup behavior with user content present.

Keep route, domain, and persistence work in separate plan tasks or clearly assigned files to reduce merge conflicts. Assign `main.py`, `core/errors.py`, `domain/graph.py`, and `spoiler/filter.py` to the contract/integration task rather than allowing all CRUD tasks to edit them concurrently.

## Persistence and Data Model

### Stable IDs and immutable ownership

Generate IDs server-side once before entering a retryable transaction:

- note: `user-note:<uuid>`
- custom node: `user-node:<uuid>`
- custom relationship: `user-rel:<uuid>`

UUID4 from the standard library is sufficient; no dependency is needed. Never use Neo4j `elementId()` publicly. Match updates/deletes on **all** of: expected label/resource representation, `id`, `series_id`, `origin = "user"`, and correct namespace. Requests must not define `id`, `series_id`, `origin`, `visible_from_order`, timestamps, type/label ownership, or relationship endpoints on PATCH.

A namespace is defense in depth, not the sole ownership check. `origin=user` means API-owned content in this no-auth prototype; it is not a user/account identifier.

### `UserNote`

Recommended node properties:

| Property | Type/rule |
|---|---|
| `id` | server-generated `user-note:` stable string |
| `series_id` | immutable path series |
| `target_type` | `Character | Claim` |
| `target_id` | immutable stable target ID |
| `content` | stripped non-empty plain text with a conservative maximum |
| `origin` | literal `user` |
| `visible_from_order` | copied/derived from the validated target's positive persisted value |
| `created_at`, `updated_at` | server UTC datetimes; create sets both, patch changes only `updated_at` |

Persist `(note:UserNote)-[ref:REFERS_TO]->(target)` with stable relationship metadata (`id`, `series_id`, `visible_from_order`, `origin=user`) or at minimum keep the target properties and relationship atomically consistent. The relationship uses an existing ontology type; no `HAS_NOTE` expansion is needed. Direct/list reads must re-match the target and filter both note and target visibility. Hard delete uses `DETACH DELETE note` and must not touch the target.

Deterministic note list ordering should be `updated_at DESC, id ASC` (or `created_at ASC, id ASC` if chosen once and documented). Return arrays only—no total/count metadata.

### Custom nodes

Persist each node with one existing ontology label and these common properties:

- `id`, `node_type`, `series_id`, `label`, `episode_id`, `visible_from_order`, `origin=user`, `created_at`, `updated_at`.

For this one-week prototype, the minimal public create contract can expose only `node_type`, `label`, and required persisted `episode_id`. This satisfies the allowlist without inventing unsupported property maps. If type-specific fields are needed, model them as a discriminated union and add only fields justified by live data (for example an Event's `location_id`), including same-series/visibility validation. Do not expose `properties: dict`.

The type/Neo4j label is immutable after creation. PATCH should minimally allow `label`; any extra type-specific mutable fields must be explicit. Use one static query per allowlisted label or a proven, allowlisted dynamic-label mechanism. Never interpolate an unchecked request value into Cypher.

### Custom relationships

Recommended representation: a `Claim` node used as an explicit user-authored relationship record:

| Property | Type/rule |
|---|---|
| `id` | server `user-rel:` ID; also the custom relationship resource ID |
| `series_id` | immutable path series |
| `subject_id`, `object_id` | immutable endpoint IDs |
| `predicate` | safe participation/character enum |
| `claim_type` | literal `user_authored` |
| `origin` | literal `user` |
| `episode_id` | validated persisted episode selected for write visibility |
| `visible_from_order` | conservative maximum of selected episode order and both endpoint visibilities |
| `created_at`, `updated_at` | server UTC datetimes |

This avoids unchecked dynamic relationship-type Cypher and reuses the existing global `Claim.id` uniqueness constraint. PATCH may allow only `predicate` (and future explicit presentation metadata); endpoints, ID, series, origin, claim type, and visibility basis remain immutable. This gives “editing relationships” a meaningful, bounded operation without endpoint replacement.

Graph projection should return:

- `id = user-rel:<uuid>`
- `source = subject_id`
- `target = object_id`
- `type = predicate`
- `visible_from_order`
- `origin = user`
- `claim_id = null` unless the frontend contract deliberately treats this same ID as fetchable claim detail

Do not include user relationship records in evidence-backed `GraphClaim`, `GraphSource`, or `GraphEvidence` collections unless a separate optional-provenance model is explicitly introduced. The existing frontend-compatible edge is sufficient for D-15/D-94.

### Constraints and indexes

Extend idempotent setup with:

- uniqueness on `UserNote.id`, `Organization.id`, and `Object.id`;
- visibility indexes on those three labels;
- series indexes on those three labels;
- a composite note lookup index on `UserNote(series_id, target_type, target_id)` if Neo4j's planner benefits in the live query plan;
- optionally composite `(series_id, visible_from_order)` indexes for `UserNote` and frequently filtered custom labels after `EXPLAIN`/test evidence, rather than speculative broad indexing.

`Claim.id` already protects custom relationship IDs. Existing concrete-label constraints protect custom nodes once `Organization`/`Object` are added. Neo4j Community does not enforce property existence here (`seed.py:143-149`), so request validation, transactional write predicates, and integration acceptance queries remain mandatory.

### Transaction pattern

Do not perform “check target → return to route → create” as separate `execute_query()` calls. That introduces time-of-check/time-of-use races and partial classification. Add a narrowly typed helper roughly equivalent to:

```python
async with database.driver.session(database=database.database) as session:
    return await session.execute_write(work, command)
```

Inside `work(tx, command)`, validate series/episode/targets/ownership and mutate in the same managed transaction. The callback must have no external side effects because Neo4j may retry it. Generate the resource ID and timestamps before `execute_write` so retries remain stable. Use `CREATE`, rely on uniqueness, and map a collision to `409 resource_conflict` without returning database internals.

Updates set only mutable fields and `updated_at`; never `SET node += $request` with a public dictionary. Deletes use exact ownership matches. For custom-node deletion, prefer `409 resource_in_use` when notes or custom relationships refer to the node, rather than silently cascading unrelated resources; after dependencies are removed, hard-delete it. Notes and custom-relationship records can be hard-deleted directly.

## REST, Pydantic, and OpenAPI Contract

### Required positive boundary

Replace manual `str | None` parsing at `backend/app/api/graph.py:40-67` with a required integer query parameter:

```python
VisibleUntilOrder = Annotated[
    int,
    Query(gt=0, description="Persisted positive episode order.", examples=[1]),
]
```

No default means OpenAPI emits `required: true`; `int` emits `type: integer`; `gt=0` emits `exclusiveMinimum: 0`. Keep the persisted `BOUNDARY_QUERY` check because schema positivity alone cannot prove the order belongs to the series. The locally installed FastAPI/Pydantic versions were verified to generate this exact shape.

Use the same alias for every story-sensitive GET in D-18. Missing/malformed/non-positive values pass through the shared validation handler as the stable envelope; positive but non-persisted values return `422 invalid_visible_until_order`.

### Strict request models

- `ConfigDict(extra="forbid", str_strip_whitespace=True)` on all mutation requests.
- `Field(min_length=1, max_length=...)` for content/labels; use conservative documented limits.
- `StrEnum`/`Literal` for `Origin`, note target type, custom node type, and safe predicate.
- `Literal["user"]` in user-content responses, or a shared `Origin` enum whose values are exactly `canonical | candidate | user`.
- Custom-node create should be a discriminated union on `node_type` if variants have different fields.
- PATCH models need a model validator requiring at least one mutable field; fields explicitly set to `null` should be rejected unless null is a documented domain value.
- IDs should have examples and, where useful, namespace patterns in response schemas. Requests contain only reference IDs, never new resource IDs.
- Response timestamps use Pydantic `datetime` so OpenAPI emits `string/date-time`; normalize to UTC.

Because the ontology is file-backed while OpenAPI enums are static, add a test asserting the public safe predicate enum equals exactly the participation + character values from ontology. This catches drift without generating unstable schemas at request time.

### Error model and validation handler

Define:

```python
class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    detail: ErrorDetail
```

Register a `RequestValidationError` handler so FastAPI's default list-shaped 422 does not violate D-25. Return a sanitized code such as `invalid_request`, with specific stable mappings for boundary and forbidden immutable fields where the input location is unambiguous. Never echo rejected values, Neo4j text, hidden labels, or target details.

Declare, per operation, applicable responses with `responses={404: {"model": ErrorResponse, ...}, 409: ..., 422: ..., 503: ...}`. The local FastAPI version generates the referenced component schemas correctly. Include examples in `content.application/json.examples` for ambiguous errors and model-level `json_schema_extra` examples for request/response shapes.

Suggested stable codes (the planner should centralize names once):

- `series_not_found`
- `invalid_visible_until_order`
- `invalid_request`
- `unsupported_target_type`
- `unsupported_node_type`
- `unsupported_relationship_type`
- `resource_not_found` / `note_not_found` where distinction is safe
- `immutable_field`
- `cross_series_reference`
- `resource_conflict`
- `resource_in_use`
- `database_unavailable` / sanitized `database_error`

Use `404` for missing and safely non-visible resources with the same message. Use `409` for attempts to mutate canonical/candidate content or dependent/in-use resources, but do not reveal a hidden resource merely to give a more precise ownership error. Use `422` for schema, boundary, ontology, contradictory filter, and safe cross-series domain validation.

### Health and existing route hardening

Create explicit health models, for example `HealthOk(status="ok", database="connected", service=...)` and `HealthDegraded(status="degraded", database="unavailable", service=...)`. Annotate `/health` with the 200 response model and a declared modeled 503 response. Health remains the intentional exception to the normal `detail` envelope because D-28 locks its operational shape.

Add explicit summaries and response declarations to all existing series/graph operations. Preserve paths and response fields. Do not rename the series-scoped graph endpoint or reintroduce the obsolete root `/api/graph` wording from older requirements prose.

### Locked endpoints

Plan exactly the existing five routes and the 13 new series-scoped routes in `03-CONTEXT.md:58-83`. Creates return `201`, reads/patches `200`, deletes `204` with no response body. Note collection filters must enforce either both `target_type` and `target_id` or neither; a partial/contradictory selector is `422`. Collection ordering is deterministic and carries no hidden totals.

## Spoiler-Safe Query Strategy

### Reads

Every note/custom direct or collection GET must execute this order:

1. Validate the path series without leaking other data.
2. Validate `visible_until_order` as positive and as a persisted episode order in that series.
3. Match the resource by `series_id`, expected ownership/representation, and ID.
4. Match its target/endpoints.
5. Require resource and target/endpoints `visible_from_order <= $visible_until_order` in Cypher.
6. Return only explicitly projected fields.
7. If zero rows, return the same sanitized 404 for absent and hidden.

Never fetch a resource and then let Pydantic/front-end filtering decide visibility. Never run a separate count that includes hidden rows. List query count is simply the length of already-filtered returned rows and is not exposed as metadata.

### Graph

Keep the evidence-backed query unchanged in principle. Add a separate `VISIBLE_USER_RELATIONSHIPS_QUERY` that matches only:

```text
relationship_record:Claim
origin = user
claim_type = user_authored
series_id = requested series
positive resource visibility <= boundary
same-series source and target
source and target visibility <= boundary
predicate in the server safe allowlist
```

Project directly to `GraphEdge` and append before `GraphResponse` construction. Do not change canonical claim provenance matches to optional. Add `Organization` and `Object` to visible graph node labels so user edges can achieve closure. Any user edge whose endpoint is hidden is omitted, not returned dangling.

### Write visibility

- Note: derive from the validated target (`visible_from_order = target.visible_from_order`).
- Custom node: require a persisted `episode_id`; derive its order and use it as visibility.
- Custom relationship: require a persisted `episode_id` and conservatively derive `max(episode_order, source.visible_from_order, target.visible_from_order)`.

The request never carries authoritative `visible_from_order`. A persisted positive episode relation/order must exist; `coalesce(..., 1)` is forbidden because missing visibility must fail closed.

### Threat cases the plan must test

- A note on an order-3 Claim is absent at order 1/2, including from response text and list length.
- Direct GET for a hidden note/custom node/relationship returns the same 404 shape as a random ID.
- A user relationship is hidden if its own derived visibility or either endpoint is hidden.
- A custom node label cannot be discovered through counts before its episode boundary.
- Cross-series target/endpoints cannot be attached; error bodies contain no labels or hidden metadata.
- Canonical/candidate IDs supplied to PATCH/DELETE are never mutated and do not produce detailed hidden facts.
- A malformed persisted record with missing visibility is excluded rather than defaulted visible.
- User-authored evidence exemption cannot admit an evidence-free canonical/candidate claim.
- Deleting a resource removes it and its API-owned attachment relationship; rerunning setup does not resurrect it.
- Setup after user content exists preserves user content and canonical counts/idempotency.

### Contract ambiguity the planner must handle explicitly

There are two tensions in the locked decisions, not reasons to broaden scope:

1. D-09 says spoiler-hidden note targets are rejected, but note POST has no boundary or episode input (`03-CONTEXT.md:67`, `:85-88`). The conservative compatible interpretation is: validate a same-series target with persisted positive visibility, derive the note visibility from it, and guarantee earlier reads cannot expose the note. Do not invent client-authoritative visibility. If product intent truly requires rejection relative to the caller's current boundary, the planner must add a non-authoritative boundary parameter through an explicit contract correction rather than guessing.
2. PATCH returns can contain story-sensitive fields, yet locked PATCH routes have no boundary parameter (`03-CONTEXT.md:70-71`, `:76-77`, `:82-83`). Keep mutation responses limited to the requested/API-owned resource, use unguessable namespaced IDs and generic errors, and document this limitation. Do not perform global existence probes to classify hidden IDs. If strict D-22 protection is required for mutation responses too, a boundary parameter needs explicit approval/contract documentation.

These should be surfaced in the plan's must-haves and frontend contract rather than silently resolved in a way that changes locked paths or trusts client visibility.

## Testing Strategy

### Unit/contract tests (no live Neo4j)

1. Pydantic accepts each legal enum and rejects arbitrary labels/types/predicates/properties, client IDs, origin, series, visibility, timestamps, immutable PATCH fields, blank/oversized text, and empty PATCH bodies.
2. Public `Origin` emits exactly `canonical | candidate | user`.
3. Safe custom predicate enum equals ontology participation + character groups and excludes structural/provenance/revision groups.
4. GraphResponse still rejects dangling custom edges.
5. RequestValidationError emits the documented envelope, not FastAPI's list-shaped default.
6. `app.openapi()` assertions for every public operation:
   - summaries exist;
   - success schema/status is declared;
   - `visible_until_order` is required integer with `exclusiveMinimum: 0`;
   - required `404/409/422/503` schemas reference `ErrorResponse`;
   - health declares typed 200 and 503;
   - mutation requests forbid extra fields and expose enums/examples;
   - delete has 204/no body.
7. Repository query tests/fakes assert all values are passed as parameters and unsafe types cannot reach dynamic Cypher selection.

### Live Neo4j integration tests

Use a fixture that deletes only `origin=user` resources before and after each user-content test. Never wipe canonical seed data. Tests should cover:

- Full note create/list/filter/direct-get/content-only-patch/hard-delete lifecycle and stable timestamps/ID/origin/derived visibility.
- All five custom node types create/read/label-patch/delete, at least one graph projection for each label family, and no arbitrary fields.
- Custom relationship create/read/predicate-patch/delete with GraphEdge-compatible graph output.
- Same-series and persisted-episode validation; test-only second-series fixture for cross-series attempts, cleaned transactionally.
- Hidden target/endpoint rejection or fail-closed derivation and zero early-boundary leaks.
- Canonical/candidate isolation for PATCH/DELETE; compare database snapshots before/after failed requests.
- Direct hidden-vs-missing response equivalence and absence of labels/count hints.
- Graph closure and order 1/2/3 sentinels with user nodes/edges present.
- Evidence-free user relationship is visible as an edge, while an injected malformed evidence-free canonical/candidate claim remains invisible.
- Hard deletion verified by direct database query; no soft-delete properties/tombstones.
- ID uniqueness/conflict maps to sanitized 409.
- Database-unavailable dependency override returns declared sanitized 503 for every route family.
- Setup reruns with user content present: canonical 41/26 baseline remains idempotent, user records survive, and new constraints/indexes remain singletons.

Avoid relying on pytest file order. Existing `setup_database()` reports all series-owned nodes/relationships (`seed.py:249-265`), so user content can change its total. Either isolate cleanup or update setup/idempotency assertions to distinguish canonical seeded counts from preserved user content; production setup must never delete user records to restore 41/26.

### Concrete verification commands

```bash
uv run pytest -q backend/tests/test_user_content_models.py
uv run pytest -q backend/tests/test_openapi_contract.py
uv run pytest -q backend/tests/test_user_content_api.py
uv run pytest -q backend/tests/test_graph_api.py backend/tests/test_seed_idempotency.py
uv run pytest -q
uv run python -m backend.app.graph.setup
uv run python -c "from backend.app.main import app; app.openapi(); print('openapi-ok')"
git diff --check
```

The live suite assumes local Neo4j credentials from `backend/tests/conftest.py:15-18`. Keep the final full-suite baseline explicit; targeted passes are not enough.

## Planning Decomposition

A good backend-only plan can be four dependency-ordered slices:

1. **Contract foundation and OpenAPI hardening** — shared errors/validation handler, origin and public enums, strict schemas, required positive boundary, health/series/graph response declarations, OpenAPI tests. This creates the stable contract before CRUD.
2. **Persistence and setup** — managed transaction hook, user-content repository, IDs/timestamps, `UserNote`/Organization/Object constraints and indexes, canonical-preserving setup tests.
3. **Notes and custom-node CRUD** — locked routes, same-series/persisted visibility checks, immutable ownership, hard deletion/dependency conflict behavior, live tests.
4. **Custom relationships and graph integration** — user-authored Claim persistence, safe predicate allowlist, evidence-exempt user projection, expanded custom node labels, graph closure/spoiler regression tests, frontend API contract document.

Each plan task should list exact routes/models/queries/tests and end with executable verification. Keep `frontend/` out of every file list. Do not mark `.planning/ROADMAP.md` Phase 03 complete from this backend worktree.

## Risks and Pitfalls

| Risk | Control |
|---|---|
| Broad `OPTIONAL MATCH` makes evidence-free canonical claims visible | Separate evidence-backed and explicit user-authored queries; test malformed canonical claim exclusion. |
| Client controls label/type or Cypher text | Strict enums, `extra=forbid`, ontology drift test, static query selection after validation. |
| Canonical resource mutation | Match label + namespaced ID + path series + `origin=user` + user representation in one write transaction. |
| TOCTOU between validation and mutation | Managed `execute_write` transaction; no route-level check-then-write sequence. |
| Retry duplicates or timestamp drift | Generate ID/timestamps before retryable transaction callback; callback has no external side effects. |
| Hidden existence leaks through direct lookup, errors, or counts | Filter before projection, normalize absent/hidden to 404, no total metadata, no global classification probes. |
| Custom edge breaks graph closure | Filter edge and both endpoints in Cypher; include Organization/Object nodes; retain GraphResponse validator. |
| Evidence requirement accidentally applies to user content or is weakened globally | Explicit branch on `origin=user AND claim_type=user_authored`; retain mandatory canonical/candidate provenance query. |
| Setup tests delete or overwrite user content | Seed remains canonical-only; cleanup fixture deletes user records only around tests; add preservation test. |
| `SET += request` overwrites ownership fields | Explicit property SET clauses for create and PATCH. |
| Hard-delete cascades silently | Reject custom-node deletion with 409 while dependent notes/relationships exist; delete dependents explicitly. |
| Static API enum drifts from YAML | Unit test public safe enums against ontology groups/version. |
| Default FastAPI 422 violates stable envelope | Install and test RequestValidationError handler; declare ErrorResponse everywhere. |
| Existing exact graph counts become brittle after CRUD tests | Isolate user fixtures and distinguish canonical baseline counts from temporary user content. |
| Phase 4 revision requirements leak into Phase 3 | Hard delete and direct updates only; no revision/tombstone scaffolding in this phase. |

## Explicit Non-Goals

- No `frontend/` changes and no Phase 03 completion claim.
- No auth, accounts, permissions, ownership identities, collaboration, or multi-user semantics.
- No rich text, uploads, comments, multi-target notes, edge notes, series/season/episode notes, or note history.
- No soft delete, tombstones, revisions, restore, revert, or audit event framework (Phase 04).
- No LLM, extraction, moderation/review, candidate ingestion, queues, vector stores, connectors, or new ingestion paths.
- No automatic relationship publication, no evidence generation for user content, and no weakening of evidence rules for canonical/candidate content.
- No arbitrary Neo4j labels/types/properties, no GraphQL, no ORM/repository framework, and no ontology expansion.
- No changes to curated JSON/YAML beyond tests if fixtures are truly required; manual curated files remain the only seed ingestion source.

## Decision and Requirement Traceability

| Decision / requirement | Research recommendation / planned evidence |
|---|---|
| D-01 | Backend/domain/graph/tests/docs only; explicit no-frontend file ownership. |
| D-02 | User CRUD is direct API persistence; `seed.py` remains the sole curated JSON path; no ingestion modules. |
| D-03 | Reuse lifespan driver, parameterized/managed transactions, fail-closed Cypher, closure validator, sanitized errors, ontology loader, idempotent setup; full regression suite. |
| D-04 | Backend artifact and docs only; do not advance overall Phase 03 completion. |
| D-05 | `UserNote` has exactly one immutable `Character | Claim` target and one `REFERS_TO` link. |
| D-06 | Five note operations, content-only PATCH, and `DETACH DELETE` lifecycle integration test. |
| D-07 | Server `user-note:<uuid>` IDs; request models forbid IDs. |
| D-08 | Typed note response with user origin, target identity, derived visibility, UTC timestamps, plain text. |
| D-09 | Atomic same-series/type/existence/positive-visibility target validation; earlier reads hidden; ambiguity documented. |
| D-10 | Exact five-label enum and constraints for missing Organization/Object labels. |
| D-11 | Exact participation + character predicate enum; structural/provenance/revision excluded. |
| D-12 | Explicit strict request models/discriminated union; no dict properties or unchecked Cypher names. |
| D-13 | Server `user-node:` / `user-rel:` IDs and literal user origin. |
| D-14 | Mutation matches user origin, namespace, series, representation; canonical/candidate before/after snapshots. |
| D-15 | Extend existing GraphNode/GraphEdge response and closure; no second graph endpoint/model. |
| D-16 | Shared Origin enum exactly `canonical | candidate | user`, asserted in OpenAPI. |
| D-17 | Curated seed untouched; new records user; no `is_custom`/`source_type` discriminator. |
| D-18 | One required positive integer query alias on every story-sensitive GET plus persisted boundary query. |
| D-19 | No default/coalesce; malformed, non-positive, missing, and non-persisted tests fail closed. |
| D-20 | Note target / episode / endpoint-derived write visibility; client visibility fields forbidden. |
| D-21 | Resource and target/endpoint visibility predicates before projection; graph closure regression tests. |
| D-22 | Hidden/missing equivalence, no count metadata, no labels/values in errors, no global classification probes. |
| D-23 | Preserve all paths and response fields; compatibility corrections isolated in frontend contract doc. |
| D-24 | Pydantic request/response/error/health models everywhere; explicit field projections from Neo4j. |
| D-25 | Shared `ErrorResponse` and RequestValidationError handler; exact-envelope tests. |
| D-26 | 200/201/204 and declared 404/409/422/503 mapping per operation. |
| D-27 | Summaries, enums/constraints, examples, typed responses, and comprehensive `app.openapi()` assertions. |
| D-28 | Graph boundary becomes required positive integer; graph/series 404, DB 503, and health 200/503 are modeled. |
| NOTE-01 | Live note CRUD and character/claim attachment tests provide backend acceptance evidence; UI remains pending. |
| NOTE-02 | Live custom-node/relationship create/edit/delete plus canonical-isolation tests provide backend acceptance evidence; UI remains pending. |
| NOTE-03 | Persisted/API `origin=user`, canonical/candidate/user enum, and graph-compatible response distinction; visual treatment remains frontend work. |
| Phase 1 INFRA/API/META/SEED | Preserve real health, driver lifecycle, parameterized transactions, setup idempotency, spoiler boundaries, graph closure, canonical evidence/provenance, and 13-test baseline through explicit regression commands. |

## Planner Checklist

- Treat `03-CONTEXT.md` decisions as locked and mention D-01 through D-28 in plan must-haves/tasks.
- Use the live files/line ranges above, not stale `.planning/codebase` maps.
- Decide and document the minimal custom-node mutable field set and custom-node dependency-delete behavior.
- Explicitly address the write-boundary ambiguity without adding client-authoritative visibility or changing locked paths silently.
- Keep canonical evidence filtering and user-edge filtering separate.
- Include OpenAPI assertions as deliverables, not manual Swagger inspection only.
- Include setup preservation with existing user content, not merely rerun counts on an empty user layer.
- End every implementation plan with targeted tests, full `uv run pytest -q`, setup smoke, OpenAPI generation, and `git diff --check`.
- Keep `.planning/config.json` free of ephemeral orchestration keys in Phase 03 implementation commits.

## RESEARCH COMPLETE