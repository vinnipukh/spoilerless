# Phase 03 Live Backend Pattern Map

**Scope:** backend-only pattern map for user notes, user-owned custom content, graph integration, and API contract hardening.  
**Source of truth:** live files read on 2026-07-29, plus `03-CONTEXT.md`, `03-RESEARCH.md`, and `03-VALIDATION.md`. Line ranges below refer to the current pre-Phase-03 files.  
**Boundary:** no `frontend/` file belongs to this map (D-01, D-04).

## Artifact/File Map

### Planned additions

| Planned file | Role | Data flow / responsibility | Closest live analog |
|---|---|---|---|
| `backend/app/api/user_content.py` | FastAPI transport/orchestration | Own all 13 locked series-scoped note, custom-node, and custom-relationship routes; parse path/query/body, call repository, construct typed responses, map safe domain outcomes to the shared error envelope. No Cypher and no raw Neo4j records. | Router/dependency/error style in `backend/app/api/series.py:10-72` and `backend/app/api/graph.py:28-121`. |
| `backend/app/domain/user_content.py` | Public contract | Strict enums and create/PATCH/response models for notes, five custom-node types, safe predicates, timestamps, immutable/server-owned fields, and deterministic list shapes. Use `extra="forbid"`; responses remain GraphNode/GraphEdge-compatible. | Positive field constraints in `backend/app/domain/series.py:4-18`; graph compatibility and closure in `backend/app/domain/graph.py:10-89`. |
| `backend/app/graph/user_content.py` | Repository/query layer | Parameterized read queries and managed-write callbacks for atomic validate/classify/mutate operations. Derive IDs/timestamps before retries; derive visibility from matched target/episode/endpoints; project explicit fields only. No FastAPI imports. | `Neo4jDatabase.execute_query()` in `backend/app/graph/database.py:46-52`; Cypher constants in `backend/app/spoiler/filter.py:3-126`; setup query functions in `backend/app/graph/seed.py:112-246`. |
| `backend/tests/test_user_content_models.py` | Pure unit/schema tests (Wave 0) | Reject arbitrary labels/types/properties, server-owned inputs, blank/oversized content, immutable PATCH fields, null/empty PATCHes; verify exact enums and ontology drift. No live database. | `GraphResponse` validation test in `backend/tests/test_graph_api.py:106-135`; ontology rejection in `backend/tests/test_seed_idempotency.py:117-122`. |
| `backend/tests/test_user_content_api.py` | Live Neo4j integration tests (Wave 0) | CRUD, same-series ownership, hidden/missing equivalence, derived visibility, hard deletion, dependency conflicts, canonical isolation, graph visibility, setup preservation, and sanitized 503 behavior. Cleanup must target only `origin = 'user'`. | Live `TestClient` fixture in `backend/tests/test_graph_api.py:34-49`; async live DB fixture in `backend/tests/test_seed_idempotency.py:14-22`; dependency override in `backend/tests/test_graph_api.py:155-168`. |
| `backend/tests/test_openapi_contract.py` | No-database contract tests (Wave 0) | Assert all 18 routes, summaries, success/error models, strict enums/examples, required positive integer boundaries, typed health 200/503, and 204-without-body deletes via `app.openapi()`. | App import/docs startup in `backend/tests/test_graph_api.py:73-87`; live generation entry point is `backend.app.main:app` (`backend/app/main.py:35-54`). |
| `docs/frontend-api-contract.md` | Backend-to-frontend handoff | Locked endpoint inventory, request/response examples, stable errors, spoiler-boundary rules, compatibility corrections, and explicit statement that frontend integration remains pending. | No current tracked `docs/` artifact is an equivalent; content requirements are locked in `03-CONTEXT.md:206-213`. |

### Focused modifications

| Existing file | Planned responsibility | Current integration point / range | Primary trace |
|---|---|---|---|
| `backend/app/main.py` | Include user-content router; model health 200/503; install shared request-validation handling while preserving lifespan and CORS. | Lifespan `19-32`; app/router wiring `35-51`; health `54-75`. | D-03, D-25, D-27, D-28. |
| `backend/app/api/series.py` | Add summaries and declared 404/503 response schemas without changing paths or fields. | Router and dependency `10-11`; operations `14-72`. | D-23, D-27, D-28. |
| `backend/app/api/graph.py` | Replace nullable-string boundary with required positive integer schema; declare errors; include Organization/Object nodes and a separately queried user-edge projection. | Dependency/error helper `28-37`; parser `40-54`; route/read orchestration `57-121`. | D-15, D-18..D-28, NOTE-02/03. |
| `backend/app/domain/series.py` | Add health/contract models only if planner locates them here; preserve existing response fields. | Current response models `4-18`. | D-23, D-24, D-28. |
| `backend/app/domain/graph.py` | Stabilize `origin` (`canonical | candidate | user`) and retain exact GraphNode/GraphEdge compatibility and closure. Do not force evidence-free user relationships into `GraphClaim`. | Nodes/edges `10-26`; provenance-required claim `29-44`; closure `70-89`. | D-15..D-17, D-21, D-24, NOTE-03. |
| `backend/app/core/errors.py` | Add typed `ErrorDetail`/`ErrorResponse`, shared HTTP error helper, sanitized request-validation handler, and reusable OpenAPI response declarations; preserve Neo4j sanitization. | Safe exception set `8-13`; sanitized response `16-27`; handler installer `30-35`. | D-22, D-25..D-28. |
| `backend/app/graph/database.py` | Add a narrow managed-write extension point using `session.execute_write`; keep the app-owned driver and current read helper. | Driver lifecycle `11-44`; `execute_query` `46-52`; app-state dependency `55-60`. | D-03, D-14, D-20. |
| `backend/app/graph/ontology.py` | Preserve relation groups or expose a user-safe participation+character subset so route/domain constants do not drift from YAML. | Loader/flattening `18-31`; current flattened dataclass and validators `34-61`; load `64-74`. | D-10..D-12. |
| `backend/app/graph/seed.py` | Add idempotent uniqueness/index setup for UserNote, Organization, and Object; do not add user ingestion or overwrite/delete user records. | Current labels omit them at `16-26`; DDL `112-149`; canonical upserts `152-246`; total report `249-265`. | D-02, D-03, D-14, D-17, NOTE-01/02. |
| `backend/app/spoiler/filter.py` | Add a separate fail-closed user-relationship projection and reusable visibility predicates; preserve evidence-backed claim/source/evidence queries. | Boundary `8-13`; nodes `15-27`; structural edges `29-45`; evidence-backed branch `47-126`. | D-15, D-18..D-22. |
| `backend/tests/test_graph_api.py` | Extend graph/closure/spoiler regressions for visible user nodes/edges and ensure evidence-free canonical/candidate claims remain excluded. Keep canonical baseline assertions isolated. | Error tests `52-70`, `138-168`; closure `106-135`; boundary/count/sentinel checks `171-209`; validity `212-223`. | D-03, D-15, D-21/22, NOTE-02/03. |
| `backend/tests/test_seed_idempotency.py` | Prove setup preserves user content; add missing constraints/index expectations; exempt only explicit user-authored relationships from evidence requirements. | Snapshot/idempotency `25-71`; constraints/visibility/provenance `74-114`. | D-02/03, D-14/17, NOTE-01/02. |

### Read-only authorities and fixtures

| File(s) | Planner use | Do not do |
|---|---|---|
| `ontology/node_types.yaml:3-23` | Select exactly Character, Event, Location, Organization, Object for custom nodes and Character/Claim for note targets; UserNote already exists. | Do not expand ontology (D-10). |
| `ontology/relation_types.yaml:3-39` | Public predicate subset is participation `10-16` plus character `18-28`. | Never expose structural `4-8`, provenance `30-34`, or revision `36-39` as generic custom predicates (D-11). |
| `ontology/claim_types.yaml:3-20` | Reuse `user_authored` (`8`) and existing status/confidence vocabulary. | Do not invent a parallel claim type. |
| `data/dexter/metadata/episodes.json:2-30` | Persisted order/episode source for write visibility and boundary tests. | Do not accept client-authoritative order or add an ingestion path (D-02, D-20). |
| `data/dexter/seed/characters.json:2-10` | Canonical namespaced IDs, `series_id`, positive visibility, `origin=canonical`. | Do not mutate canonical fixtures for user CRUD. |
| `data/dexter/seed/claims.json:2-10` | Canonical Claim shape and evidence/source provenance conventions. | Do not weaken provenance to accommodate user-authored relationships. |
| Remaining `data/dexter/metadata/*.json`, `data/dexter/seed/*.json` | Existing canonical-only seed input. | Do not route user content through seed files or make setup restore deleted user resources. |
| `pyproject.toml:1-22` | Existing FastAPI/Pydantic/Neo4j/pytest toolchain; use `uv`. | Add no ORM, repository framework, ingestion, queue, or model dependency. |

## End-to-End Data Flow

### Existing read path to preserve

1. `backend/app/main.py:19-32` creates one `Neo4jDatabase`, opens it during lifespan, stores it at `app.state.neo4j`, tolerates degraded startup, and closes it at shutdown.
2. Route signatures use `Annotated[Neo4jDatabase, Depends(get_database)]` (`api/series.py:10-11`, `api/graph.py:28-29`). `get_database()` returns the lifespan instance (`graph/database.py:55-56`).
3. Routes call `execute_query(query, **parameters)`; the database boundary forwards values through Neo4j's `parameters_` argument (`graph/database.py:46-52`).
4. Graph reads validate series, parse/validate boundary, then run node/edge/claim/source/evidence queries (`api/graph.py:57-96`).
5. Cypher filters visibility and closure before records leave Neo4j (`spoiler/filter.py:8-126`).
6. Routes explicitly construct Pydantic models (`api/graph.py:98-121`), and `GraphResponse` rejects dangling edges (`domain/graph.py:79-89`).
7. Neo4j exceptions are converted to a sanitized stable 503 envelope (`core/errors.py:16-35`).

### Planned note flow (D-05..D-09, D-18..D-22, NOTE-01)

`POST body -> strict NoteCreate -> repository managed write -> match path series and exactly one Character|Claim target -> require same series and positive persisted target visibility -> generate user-note UUID/timestamps outside retry callback -> CREATE UserNote + REFERS_TO atomically -> explicit NoteResponse (201)`.

Reads must validate the persisted `visible_until_order`, re-match both note and target, and apply note+target visibility predicates before projection. List filters accept both `target_type` and `target_id`, or neither; partial selectors are 422. Hidden and absent direct IDs return the same safe 404. PATCH changes content and `updated_at` only. DELETE hard-deletes only the API-owned UserNote and its attachment, never the target.

### Planned custom-node flow (D-10, D-12..D-15, D-18..D-22, NOTE-02/03)

`POST body -> strict five-type model -> managed write -> validate series + persisted episode -> choose a static query by validated allowlisted label -> derive episode order -> CREATE origin=user node -> custom response / existing graph projection`.

The request supplies only explicit presentation/domain fields (minimally `node_type`, `label`, `episode_id`), never a properties dictionary. PATCH permits explicit mutable fields only (minimally label). Direct reads filter resource visibility in Cypher. Delete first checks API-owned dependent notes/user relationships and returns 409 when in use; an allowed delete matches label + ID namespace + series + `origin=user` in the transaction.

### Planned custom-relationship flow (D-11..D-15, D-18..D-22, NOTE-02/03)

Use an explicit `Claim` record with `id=user-rel:<uuid>`, `claim_type=user_authored`, `origin=user`, immutable endpoint/series ownership, and an allowlisted participation/character predicate. In one managed transaction, validate the persisted episode and both same-series endpoints, then derive `max(episode_order, source.visible_from_order, target.visible_from_order)`. PATCH may change only an explicitly modeled predicate. Direct responses are GraphEdge-compatible.

Graph integration is a **separate** user-relationship query. It filters record, endpoints, series, boundary, origin, claim type, and predicate before returning GraphEdge fields. It does not populate GraphClaim/Source/Evidence collections and does not loosen canonical evidence matches.

### Contract flow (D-23..D-28)

`domain models + route metadata -> FastAPI app -> app.openapi() -> test_openapi_contract.py -> docs/frontend-api-contract.md -> separate frontend-work consumer`.

Current live generation exposes only five paths. The graph boundary is currently `required: false`, `string|null`; graph responses are only 200/422, series detail only 200/422, and health 200 has an empty schema. Contract work must turn `visible_until_order` into a no-default `int` with `Query(gt=0, ...)`, retain persisted-boundary Cypher validation, and declare typed success/errors and examples.

## Existing Analogs and Code Excerpts

### FastAPI router and dependency

From `backend/app/api/series.py:10-16`:

```python
router = APIRouter(prefix="/api/series", tags=["series"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]

@router.get("", response_model=list[SeriesResponse])
async def list_series(database: DatabaseDependency) -> list[SeriesResponse]:
    records = await database.execute_query(...)
```

Reuse the series prefix and typed dependency. New public operations add summaries, explicit status codes, typed responses, and declared error models rather than copying the current minimal decorator.

### Existing HTTP/domain error and database sanitization

Route-local helper at `backend/app/api/graph.py:33-37`:

```python
def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code,
                         detail={"code": code, "message": message})
```

Database envelope at `backend/app/core/errors.py:16-27`:

```python
def database_error_response(exc: BaseException) -> JSONResponse:
    unavailable = isinstance(exc, (ServiceUnavailable, AuthError, OSError))
    code = "database_unavailable" if unavailable else "database_error"
    ...
    return JSONResponse(
        status_code=503,
        content={"detail": {"code": code, "message": message}},
    )
```

Centralize the route helper and model the envelope as `ErrorResponse(detail=ErrorDetail(code, message))`. Add a `RequestValidationError` handler so framework 422 responses do not revert to FastAPI's list-shaped default. Do not echo request values, labels, Cypher, credentials, or hidden-resource facts (D-22, D-25).

### Current boundary pattern and required replacement

Current manual parser/route at `backend/app/api/graph.py:40-67` accepts `str | None = Query(default=None)`, then rejects absent/non-ASCII/non-digit/non-positive values itself. The reusable target is:

```python
VisibleUntilOrder = Annotated[
    int,
    Query(gt=0, description="Persisted positive episode order.", examples=[1]),
]
```

No default makes OpenAPI required; `int` and `gt=0` produce integer and exclusive minimum. This schema check does **not** replace `BOUNDARY_QUERY` (`spoiler/filter.py:8-13`), which proves the order is persisted for the path series.

### Pydantic compatibility and closure

`backend/app/domain/graph.py:10-26` is the public compatibility target:

```python
class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    visible_from_order: int = Field(ge=1)
    origin: str
    episode_id: str | None = None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    visible_from_order: int = Field(ge=1)
    origin: str
    claim_id: str | None = None
```

Closure defense at `backend/app/domain/graph.py:79-89` builds the returned node-ID set and raises when an edge endpoint is absent. Preserve it. Strengthen `origin` to exactly canonical/candidate/user, but avoid passing user relationships through `GraphClaim` because `GraphClaim` requires `source_id` and `evidence_ids` (`29-44`). Strict mutation models should use `ConfigDict(extra="forbid", str_strip_whitespace=True)`, constrained `Field`s, enums/Literals, and a validator requiring at least one non-null mutable PATCH field.

### Database read boundary and managed-write extension

Current read helper at `backend/app/graph/database.py:46-52`:

```python
async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
    records, _, _ = await self.driver.execute_query(
        query, parameters_=parameters, database_=self.database,
    )
    return [record.data() for record in records]
```

Keep this for single-query reads. Add a narrowly typed write hook equivalent to:

```python
async with database.driver.session(database=database.database) as session:
    return await session.execute_write(work, command)
```

Validation/classification and mutation belong inside `work(tx, command)`. Callbacks must have no external side effects because Neo4j can retry. Generate stable ID/timestamps before entering the callback. Never perform route-level check-then-write, `SET node += $request`, or unchecked string interpolation.

### Ontology allowlists

`backend/app/graph/ontology.py:18-19,34-74` currently flattens YAML groups into `frozenset`s and exposes `require_*` validators. That is authoritative for global validity but loses relationship category identity. Preserve or expose named groups so the public predicate enum can be tested against exactly:

- custom nodes: `Character`, `Location`, `Organization`, `Object`, `Event` (`ontology/node_types.yaml:10-15`);
- note targets: `Character`, `Claim` (`node_types.yaml:10-18`);
- custom predicates: participation values (`ontology/relation_types.yaml:10-16`) plus character values (`18-28`);
- relationship representation: existing `user_authored` claim type (`ontology/claim_types.yaml:3-8`).

A model/ontology test must prove the static OpenAPI enum equals those YAML groups and excludes structural/provenance/revision groups. Validation permits choosing a static query; it does not make raw dynamic Cypher labels/types safe.

### Seed DDL and canonical-only setup

DDL pattern at `backend/app/graph/seed.py:112-149`:

```python
f"CREATE CONSTRAINT {normalized}_id_unique IF NOT EXISTS "
f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
...
f"CREATE INDEX {normalized}_visible_idx IF NOT EXISTS "
f"FOR (n:{label}) ON (n.visible_from_order)"
```

Queries execute one at a time and tolerate only Community's unsupported property-existence constraint error (`142-149`). Extend the closed server-owned label tuple to cover UserNote/Organization/Object and add series/look-up indexes as justified. `_upsert_nodes()` uses dynamic labels plus `SET node += row` (`152-164`), but this is safe only because labels are internal constants and rows are curated seed records validated before setup. It is **not** reusable for public writes.

Canonical upserts run only over loaded JSON (`seed.py:42-71,167-246`). Keep user resources out of those arrays. Note that setup's report counts all series-owned nodes and relationships (`249-265`), so tests must separate canonical 41/26 assertions from preserved user-layer totals.

### Fail-closed Cypher boundaries

Persisted boundary (`backend/app/spoiler/filter.py:8-13`):

```cypher
MATCH (:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
WHERE episode.episode_order = $visible_until_order
  AND episode.visible_from_order <= $visible_until_order
RETURN episode.id AS episode_id
```

Node filter (`15-27`) requires same series, an allowlisted label, and `node.visible_from_order <= $visible_until_order` before projection. There is no `coalesce`; malformed/missing visibility fails closed.

Structural edge closure (`29-45`) matches only `PART_OF|PRECEDES|OCCURRED_IN`, then checks source, target, and edge series/visibility. Do not treat this as a generic narrative relationship query.

Canonical/candidate claim visibility (`47-78`) requires subject/object plus both `SUPPORTED_BY` evidence and `REFERS_TO` source paths before projection. Source/evidence collections repeat endpoint/provenance/visibility checks (`80-126`). Keep these mandatory. Add a separate user branch constrained by `origin='user' AND claim_type='user_authored'`, safe predicate allowlist, same-series visible endpoints, and positive resource visibility.

### Live TestClient/Neo4j fixtures

`backend/tests/conftest.py:15-18` supplies local Neo4j defaults. `backend/tests/test_graph_api.py:34-49` seeds and then starts the real app lifespan:

```python
async def _seed_live_database() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        await setup_database(database)
    finally:
        await database.close()

@pytest.fixture
def live_client() -> Iterator[TestClient]:
    asyncio.run(_seed_live_database())
    main_module = importlib.import_module("backend.app.main")
    with TestClient(main_module.app) as client:
        yield client
```

Reuse this infrastructure, but add cleanup that deletes only API-owned `origin=user` records before/after each user-content test. Never wipe/reseed canonical data merely to remove user fixtures. For failures, override `get_database` with `UnavailableDatabase` and clear overrides in `finally` (`test_graph_api.py:155-168`). For direct setup assertions, reuse the async fixture at `test_seed_idempotency.py:14-22`.

### OpenAPI generation

FastAPI generates the contract from the module-level app (`backend/app/main.py:35-54`) without opening a database. The established smoke form is:

```bash
uv run python -c "from backend.app.main import app; app.openapi(); print('openapi-ok')"
```

Contract tests should directly inspect `app.openapi()` dictionaries, not depend on Swagger UI or live Neo4j. Current live output confirms: 5 paths; graph boundary optional `string|null`; graph and series detail only 200/422; health 200 has an empty schema. This is the D-28 regression baseline, not a pattern to preserve.

## Route/Model/Repository/Test Patterns

### Route matrix

| Family | Locked operations | Response pattern | Required checks |
|---|---|---|---|
| Existing | health; series list/detail/episodes; series graph | Preserve names/fields; add typed summaries/errors; graph read 200. | Real DB health; stable series 404; persisted positive graph boundary. |
| Notes | POST collection; GET filtered collection; GET/PATCH/DELETE item | 201 create, 200 reads/PATCH, 204 DELETE. Typed note arrays; no totals. | Exact Character/Claim target, same series, derived target visibility, user ownership, hidden/missing equivalence, paired filters. |
| Custom nodes | POST collection; GET/PATCH/DELETE item | 201/200/204; GraphNode-compatible fields. | Exact five types, persisted episode, explicit fields, origin+namespace ownership, dependencies before delete. |
| Custom relationships | POST collection; GET/PATCH/DELETE item | 201/200/204; GraphEdge-compatible fields. | Safe predicate, same-series endpoints, persisted episode, conservative max visibility, user-authored representation. |

Every story-sensitive GET requires `VisibleUntilOrder`. Positive but non-persisted boundaries return `422 invalid_visible_until_order`; hidden and missing resources return indistinguishable 404s. Locked PATCH routes lack a boundary parameter: do not add one silently or run global probes to classify IDs. Keep responses limited to API-owned resources and document the ambiguity from `03-RESEARCH.md:329-336`.

### Model rules

- Requests contain only mutable/request-authoritative fields; `id`, `series_id`, `origin`, timestamps, and `visible_from_order` are absent and rejected as extras (D-07, D-12/13, D-20).
- Note PATCH: content only. Custom-node type and custom-relationship endpoints are immutable. Empty PATCH and explicit null for non-null fields are 422.
- Responses use server IDs (`user-note:`, `user-node:`, `user-rel:`), literal/shared user origin, positive visibility, and UTC Pydantic datetimes.
- Lists are deterministic arrays with no hidden count metadata. Pick and document one stable ordering (research recommends notes by updated time descending then ID ascending).
- Graph models remain the one public graph representation (D-15); no parallel custom graph schema.

### Repository/query rules

- Repository receives validated commands/models, not arbitrary dictionaries; it returns explicit projected records or typed outcomes.
- All data values are Cypher parameters. Dynamic labels/types are selected only from closed server mappings after enum/ontology validation; static per-label queries are safer.
- Write matches include expected representation/label, stable ID, path `series_id`, `origin='user'`, and namespace defense in depth.
- Derive note visibility from target; custom-node visibility from persisted episode; custom-relationship visibility from max episode/source/target visibility. Missing visibility is rejection/exclusion, never default 1.
- Use atomic managed transactions for validation+mutation. Map uniqueness collisions to sanitized 409; never expose Neo4j text.
- Explicit SET clauses only. Use `DETACH DELETE` only after ownership/dependency checks and never against a canonical/candidate match.

### Test pattern matrix

| Layer | Required evidence | Reuse point |
|---|---|---|
| Models | Strict extras, enums, lengths, server-owned rejection, immutable/empty PATCH, exact Origin values, ontology-safe subset. | `test_graph_api.py:106-135`; `test_seed_idempotency.py:117-122`. |
| OpenAPI | 18 route inventory; summaries; typed 200/201/204 and 404/409/422/503; required integer boundary; examples; health models. | `app.openapi()` from `main.py:35-54`; docs availability test `test_graph_api.py:73-87`. |
| Live CRUD | Full lifecycles, hard deletes, timestamps/IDs, all five node types, predicates, same-series validation, canonical isolation. | `live_client` at `test_graph_api.py:34-49`; async DB fixture `test_seed_idempotency.py:14-22`. |
| Spoiler/security | Hidden vs missing equality, no labels/count leaks, endpoint closure, malformed missing-visibility exclusion, no early-order sentinels. | Error and serialized sentinel patterns `test_graph_api.py:138-209`. |
| Graph | Visible user nodes/edges, hidden endpoints omit edge, GraphResponse closure, user evidence exemption cannot admit malformed canonical claims. | Graph closure `test_graph_api.py:106-135,205-209`; claim validity `212-223`. |
| Setup | Repeated setup preserves exact canonical layer plus existing user records; constraints/indexes singleton; user deletes stay deleted. | Snapshot/idempotency `test_seed_idempotency.py:25-71`; DDL/provenance `74-114`. |
| DB failure | Every route family emits declared sanitized 503 and no secret/Cypher. | `UnavailableDatabase` and overrides `test_graph_api.py:20-31,52-70,155-168`. |

Wave 0 must create the three new test files before/with implementation (`03-VALIDATION.md:55-61`). Final verification remains targeted tests, existing regression files, full `uv run pytest -q`, setup smoke, OpenAPI generation, and `git diff --check`.

## Shared-File Ownership and Plan Boundaries

Use dependency-ordered plans; do not let parallel executors edit the same shared integration file. Recommended exclusive ownership:

| Plan/slice | Exclusive files / duties | Must not edit |
|---|---|---|
| **03-01 Contract foundation** | Sole owner of `backend/app/main.py`, `backend/app/core/errors.py`, `backend/app/domain/graph.py`, `backend/app/api/series.py`; create `domain/user_content.py`, model/OpenAPI tests; define shared boundary/error/OpenAPI contracts and all main/health/router wiring once. | `spoiler/filter.py`, persistence Cypher, seed behavior, frontend. |
| **03-02 Persistence + notes** | Sole owner of `backend/app/graph/database.py`, initial `backend/app/graph/user_content.py`, note repository/API behavior and focused live tests. | `main.py`, `core/errors.py`, `domain/graph.py`, `api/graph.py`, `spoiler/filter.py`. Consume shared helpers rather than modifying them. |
| **03-03 Custom nodes** | Extend only user-content domain/API/repository/test files for the five-node contract; if DDL is grouped here, make this the sole owner of `backend/app/graph/seed.py` until handoff. | All five shared integration files and frontend. |
| **03-04 Relationships + graph integration + handoff** | Sole owner of `backend/app/api/graph.py` and `backend/app/spoiler/filter.py`; finish user relationship repository/API tests; extend `test_graph_api.py`; sole owner of final `test_seed_idempotency.py` changes and `docs/frontend-api-contract.md`. | `main.py`, `core/errors.py`, `domain/graph.py`; never weaken canonical claim queries. |

Coordination rules:

- `main.py`: one owner performs health modeling, validation-handler installation, and router registration together; later plans only consume the registered router.
- `core/errors.py`: one owner establishes codes/models/helpers. Other plans import them; they do not add route-local variants.
- `domain/graph.py`: one owner changes Origin/compatibility/closure. CRUD models live in `domain/user_content.py`.
- `api/graph.py` and `spoiler/filter.py`: one graph-integration owner adds user projection and node labels together so edges cannot land without endpoints.
- `test_graph_api.py` and `test_seed_idempotency.py`: keep canonical regression edits with final integration ownership; CRUD plans use `test_user_content_api.py` to avoid count/fixture conflicts.
- If executors run concurrently, split by these files, not merely by endpoint family. Any unavoidable shared-file edit must be queued after the current owner finishes.

## Pitfalls and Non-Reusable Patterns

1. **Evidence requirement is currently structural, not optional.** `VISIBLE_CLAIMS_QUERY` requires `SUPPORTED_BY` and `REFERS_TO` (`spoiler/filter.py:47-78`). Broad `OPTIONAL MATCH` would leak malformed canonical/candidate claims. Add a separate exact user-authored projection.
2. **Structural edges are not generic relationships.** `STRUCTURAL_EDGES_QUERY` matches only PART_OF, PRECEDES, OCCURRED_IN (`29-45`). Custom narrative predicates cannot be expected to appear there.
3. **Unchecked labels/types are Cypher injection.** Parameters cannot replace Cypher labels or relationship types. Do not interpolate request strings. Strict enums + ontology checks must select a static server-owned query/mapping.
4. **Seed dynamic labels/`SET +=` are not a public-write pattern.** `_upsert_nodes()` (`seed.py:152-164`) is restricted to curated, validated internal rows. Public PATCH must use explicit fields.
5. **Setup must preserve user data.** Seed only canonical JSON; no cleanup, overwrite, or resurrection of `origin=user`. Existing setup count (`seed.py:249-265`) includes user records, so a raw 41/26 assertion becomes misleading once user content exists.
6. **No route-level check-then-write.** Validation and mutation in separate autocommit queries introduce TOCTOU races. Use one managed write transaction and stable pre-generated ID/timestamps.
7. **No visibility defaults.** Missing/malformed/non-positive/non-persisted values fail closed; `coalesce(visible_from_order, 1)` is forbidden. Filter before Pydantic construction and before counts.
8. **404 must not classify hidden resources.** A direct lookup that first discovers ownership/existence and later checks visibility leaks facts. Match ownership, series, targets/endpoints, and boundary together; hidden and random IDs share the response.
9. **Origin is classification, not identity.** Use only canonical/candidate/user. Do not add `is_custom`, `source_type`, account IDs, or pretend `origin=user` identifies a person (D-16/17).
10. **Namespace alone does not authorize mutation.** Match namespace plus expected representation, path series, and `origin=user`; canonical/candidate resources remain immutable (D-14).
11. **Graph closure must hold twice.** Filter edge and endpoints in Cypher, then retain the Pydantic closure validator. Adding Organization/Object edges without adding visible nodes would fail closure.
12. **Do not put UserNote nodes into graph by accident.** Notes have dedicated APIs. Add them to graph nodes only after an explicit product/UI decision; current scope only requires custom nodes/relationships in the graph.
13. **Default FastAPI 422 is the wrong envelope.** A required integer query improves schema but invokes framework validation; install and test the shared `RequestValidationError` handler.
14. **PATCH/read visibility ambiguity is not permission to change paths.** POST/PATCH locked routes lack caller boundaries. Derive write visibility, avoid global probes, document the limitation, and seek explicit approval before adding parameters.
15. **No frontend and no phase-complete claim.** Backend NOTE-01..03 evidence is partial acceptance only; visual/editing UI remains in `frontend-work` (D-01, D-04).
16. **No Phase 4/5 scaffolding.** Hard delete/direct update only; no revisions, tombstones, moderation, extraction, queues, model clients, or new ingestion path (D-02).

## Planner Handoff Checklist

- [ ] Every D-01..D-28 decision appears in must-haves/tasks or explicit verification; NOTE-01..03 are labeled backend acceptance evidence only.
- [ ] File lists include all additions/modifications above and explicitly exclude `frontend/`, ontology expansion, and curated fixture mutation.
- [ ] One user-content router/domain/repository boundary is used; routes contain no Cypher and repository contains no FastAPI imports.
- [ ] `main.py`, `core/errors.py`, `domain/graph.py`, `api/graph.py`, and `spoiler/filter.py` each have one integration owner; parallel plans do not overlap them.
- [ ] OpenAPI foundation includes shared ErrorResponse, sanitized framework validation, summaries/examples, exact status schemas, health 200/503, and required positive integer boundaries.
- [ ] Model tests prove `extra=forbid`, exact Origin values, immutable/server-owned rejection, and safe enum equality with YAML groups.
- [ ] Repository plan adds a narrow managed-write hook and atomic validation+mutation; IDs/timestamps are generated before retry callbacks.
- [ ] Note plan covers exactly one Character/Claim target, content-only PATCH, paired collection filters, deterministic arrays, and hard delete.
- [ ] Custom-node plan fixes the five labels and explicit fields, derives visibility from a persisted episode, and defines 409 dependency behavior.
- [ ] Custom-relationship plan keeps endpoints immutable, uses only participation+character predicates, and represents/project user-authored records without weakening evidence-backed claims.
- [ ] Graph plan adds Organization/Object nodes and a separate user-edge query, filters edge plus endpoints before projection, and retains GraphResponse closure.
- [ ] Error tests prove hidden/missing equivalence, no count/label/Cypher/credential leaks, and sanitized 404/409/422/503 behavior.
- [ ] Setup plan adds missing UserNote/Organization/Object DDL idempotently and proves reruns preserve existing user data and canonical 41/26 content.
- [ ] Wave 0 creates `test_user_content_models.py`, `test_openapi_contract.py`, and `test_user_content_api.py`; no new test framework is introduced.
- [ ] Final commands include targeted new tests, existing graph/idempotency regressions, `uv run pytest -q`, `uv run python -m backend.app.graph.setup`, an `app.openapi()` smoke, and `git diff --check`.
- [ ] `docs/frontend-api-contract.md` records all locked routes, schemas/examples, stable errors, boundary rules, compatibility corrections, and pending frontend work.

## PATTERN MAPPING COMPLETE
