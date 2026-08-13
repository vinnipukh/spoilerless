# Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign - Pattern Map

**Mapped:** 2026-08-13  
**Files analyzed:** 33 likely created/modified files  
**Analogs found:** 30 / 33

This map is for planning only. The existing `GraphResponse` is the complete, spoiler-safe read model; Phase 10 should add a separate neutral visualization projection and adapters rather than make the full graph view-specific.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `spoilerless/app/domain/visualization.py` | DTO/model | request-response / transform | `spoilerless/app/domain/graph.py` | exact role |
| `spoilerless/app/services/visualization.py` | projection service | transform | `spoilerless/app/services/graph.py` | role + boundary match |
| `spoilerless/app/api/graph.py` | API/controller | request-response | same file: `get_graph`, `_resolve_effective_boundary` | exact seam |
| `spoilerless/app/cache/graph_cache.py` | cache utility | cache-aside request-response | same file: `_cache_key`, get/set | exact |
| `spoilerless/app/spoiler/policy.py` | policy utility | pure transform / guard | same file: `effective_view_order`, `is_visible` | exact |
| `spoilerless/app/retrieval/*` (focus contract only) | retrieval integration | request-response | `spoilerless/app/retrieval/tools.py` + current graph API | role match |
| `spoilerless/tests/test_visualization_projection.py` | backend unit/contract test | transform | `spoilerless/tests/test_graph_api.py` | exact test style |
| `spoilerless/tests/test_visualization_cache.py` | backend cache test | cache-aside | `spoilerless/tests/test_graph_api.py` cache tests | exact test style |
| `spoilerless/tests/test_spoiler_policy.py` | backend policy test | pure transform | same file | exact |
| `frontend/src/types/graph.ts` | wire/DTO types | request-response | same file: `GraphResponse` | exact |
| `frontend/src/api/graph.ts` | API adapter | request-response | same file: `getGraph`, `findPath` | exact |
| `frontend/src/lib/visualizationAdapter.ts` | frontend adapter | transform | `frontend/src/components/graph/graphElements.ts::graphToElements` | exact role |
| `frontend/src/lib/timelineAdapter.ts` (or timeline adapter in same lib) | adapter | transform | `TimelineView` grouping logic | role match |
| `frontend/src/hooks/useSceneState.ts` | hook/store/reducer | event-driven state | `frontend/src/App.tsx` state + `focusReducer.ts` | role match |
| `frontend/src/hooks/useSceneState.test.ts` | frontend state test | event-driven | `focusReducer` tests / `App.test.tsx` | role match |
| `frontend/src/App.tsx` | composition/controller | event-driven shared scene | `AuthenticatedApp` lines 109-701 | exact |
| `frontend/src/components/graph/GraphCanvas.tsx` | renderer component | event-driven / imperative diff | same file `runLayout`, cy refs | exact |
| `frontend/src/components/graph/graphElements.ts` | Cytoscape adapter | transform | same file | exact |
| `frontend/src/components/graph/layoutConfig.ts` | layout utility | transform/config | same file `layoutOptionsFor` | exact |
| `frontend/src/components/graph/graphStylesheet.ts` | presentation policy | event-driven render | same file | exact |
| `frontend/src/components/graph/focusReducer.ts` | reducer | event-driven | same file | exact |
| `frontend/src/components/timeline/TimelineView.tsx` | component | event-driven selection | same file | exact |
| `frontend/src/components/timeline/TimelineEventRow.tsx` | component | event-driven selection/filter | same file | exact |
| `frontend/src/components/detail/DetailPanel.tsx` | Inspector component | request-response / selection | same file | exact |
| `frontend/src/components/graph/GraphCanvas.test.tsx` | renderer regression test | event-driven | same file | exact |
| `frontend/src/components/graph/graphElements.test.ts` | adapter test | transform | same file | exact |
| `frontend/src/components/graph/layoutConfig.test.ts` | layout test | transform/config | same file | exact |
| `frontend/src/components/timeline/TimelineView.test.tsx` | component test | event-driven | same file | exact |
| `frontend/src/components/detail/DetailPanel.test.tsx` | Inspector test | request-response/selection | same file | exact |
| `frontend/src/App.test.tsx` | integration test | event-driven composition | same file | exact |
| `frontend/src/test/fixtures/visualizationS01E01.ts` and cumulative S01E02 fixture | safe fixture | transform/benchmark input | `frontend/src/test/fixtures/graphResponse.ts` | exact fixture pattern |
| `scripts/benchmark_visualization.py` (or equivalent) | benchmark utility | batch/transform | no close repository analog | none |
| `docs/API.md`, `docs/ARCHITECTURE.md`, `README.md` / root docs | documentation | static contract | existing docs + `docs/TESTING.md` | role match |
| `.planning/phases/10-polish-finishing-touches/10-UAT.md` | UAT/script | request-response/manual flow | `.planning/phases/08-production-deployment-automated-ci-cd/08-UAT.md` | exact planning analog |

## Pattern Assignments

### Backend DTO, projection, API, and spoiler boundary

**Analog:** `spoilerless/app/domain/graph.py` (lines 11-99)

Copy the Pydantic model style: small `BaseModel` records, `Field(ge=1)` for reveal orders, nullable optional fields, and a top-level response validator. `GraphResponse.enforce_graph_closure()` (lines 89-99) rejects dangling edges; a visualization DTO should similarly validate stable IDs/references and hard bounds without replacing `GraphResponse`.

```python
class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    visible_from_order: int = Field(ge=1)
    origin: Origin
```

**Analog:** `spoilerless/app/services/graph.py::GraphService.fetch_graph` (lines 29-128)

The service owns Neo4j reads and domain assembly. It gathers independent queries with `asyncio.gather` (lines 67-89), validates rows into domain models (91-127), derives claim-backed edges (91-103), and applies `filter_public_metadata(row, effective)` before serialization (105-115). A new projection service should consume this complete safe result or an equivalent safe domain output; do not put projection reduction into Cypher or the canonical full graph response.

```python
nodes = [
    GraphNode.model_validate(filter_public_metadata(row, effective))
    for row in nodes_rows
]
return GraphResponse(..., nodes=nodes, edges=..., claims=..., sources=..., evidence=...)
```

**Analog:** `spoilerless/app/api/graph.py::get_graph` (lines 60-118) and `::_resolve_effective_boundary` (129-187)

Preserve dependency injection (`Annotated[..., Depends(...)]`), `_error()` envelopes (53-57), series-not-found handling (73-76), persisted episode validation (83-89), and the authenticated/anonymous boundary rules (77-99). Consolidate all new projection, expansion, focus, search, path, and restoration routes through `_resolve_effective_boundary`; never trust a client order directly.

```python
requested_view = min(visible_until_order, record.view_as_of_order)
effective = effective_view_order(requested_view, record.watched_through_order)
...
result = await service.fetch_graph(..., effective_view_order=effective)
```

**Analog:** `spoilerless/app/spoiler/policy.py::is_visible`, `effective_view_order`, `filter_public_metadata` (lines 62-138)

This is the authoritative policy. Missing `visible_from_order` fails closed (80-91); effective order is `min(view_as_of_order, watched_through_order)` (94-106); sensitive metadata is dropped, never replaced with a revealing placeholder (119-138). Projection, expansion, Answer Graph focus, and search must run only after this boundary and must not reconstruct hidden counts, degree, labels, groups, or layout inputs.

### Cache

**Analog:** `spoilerless/app/cache/graph_cache.py::_cache_key`, `get_cached_graph`, `set_cached_graph`, `invalidate_series` (lines 1-87)

Retain cache-aside semantics: Redis is optional, errors return a miss, values are JSON payloads, writes use TTL, and content-changing writes invalidate conservatively. Use a Redis-local per-series cache epoch as `graph_revision`; default 0, atomically increment it in existing `invalidate_series` write paths, and bypass cache when epoch resolution fails. Extend keys with view, projection version, epoch, effective order, series, user scope, and request signature. GraphRAG focus uses a deterministic digest of validated/deduplicated/sorted focus IDs. Expansion bypasses cache in Phase 10. A hit must never cross view, user, revision, focus set, or spoiler boundary.

```python
def _cache_key(series_id: str, effective_boundary: int, user_id: str | None) -> str:
    return f"graph:{series_id}:{effective_boundary}:{user_id or 'anon'}"

try:
    value = await get_redis().get(_cache_key(...))
except Exception:
    return None
```

### Frontend wire types and adapters

**Analog:** `frontend/src/types/graph.ts` (lines 1-87) and `frontend/src/api/graph.ts` (lines 1-18)

Keep existing wire types field-for-field and add neutral visualization types alongside them. `getGraph()` and `findPath()` are thin `apiFetch` wrappers; new task-view/expansion calls should follow this pattern with typed request/response bodies. Do not make `GraphResponse` contain view-specific fields.

**Analog:** `frontend/src/components/graph/graphElements.ts::graphToElements` (lines 1-156)

This is the closest adapter. It is pure, maps backend data to `ElementDefinition[]`, selects `overview` vs `full` (27-42), derives only from already-filtered lists, preserves claim metadata, and returns parent/node/edge elements. New `toCytoscapeElements()` should take neutral DTOs, hide technical edge names by policy, preserve deterministic IDs, and never apply spoiler filtering or hidden-data inference in the browser.

```ts
export function graphToElements(graph: GraphResponse, mode: GraphMode = 'full') {
  let nodes = graph.nodes
  let edges = graph.edges
  if (mode === 'overview') {
    const projection = overviewProjection(graph)
    nodes = graph.nodes.filter((n) => projection.keptNodeIds.has(n.id))
    edges = projection.keptEdges
  }
  return [...parentElements, ...nodeElements, ...edgeElements]
}
```

Use `frontend/src/components/graph/overviewTiers.ts` as the existing editorial-tier analog. Audit it and the backend seed/row metadata before introducing `display_tier`; do not infer importance from full-graph degree or invent plot communities automatically.

### Stable Cytoscape scene and layout

**Analog:** `frontend/src/components/graph/GraphCanvas.tsx::runLayout` (88-145), `GraphCanvas` (376-480)

Keep one Cytoscape instance and use refs/memoization. `elements` is memoized from `[graph, mode]` (406), the declarative `layout` is memoized from `[mode]` (411-414), and `cyInstanceRef`/`lastLayoutCyRef` distinguish a fresh instance from an in-place graph refresh (427-475). `runLayout` applies cached positions in a Cytoscape batch (112-127) and records positions on `layoutstop` (131-141). Selection/focus must use batched class/data diffs and preserve camera; expansion gets local constrained positions, not a random global relayout.

**Analog:** `frontend/src/components/graph/layoutConfig.ts::layoutOptionsFor` (50-118)

Reuse fCoSE registration, reduced-motion handling, mode-dependent spacing, and `randomize: false` (73-96). Initial overview/character layout can extend this with presets; Evidence layout should remain an adapter boundary unless an already-installed engine is confirmed. `frontend/src/components/graph/graphStylesheet.ts` is the analog for semantic label culling, hover/select/path labels, provenance restraint, non-color distinctions, and zoom-only presentation changes.

**Analog:** `frontend/src/components/graph/focusReducer.ts` (5-26) plus `frontend/src/lib/graph/highlight.ts`

Use a reducer for serializable focus actions (`FOCUS_NODE`, `CLEAR_FOCUS`) and keep Cytoscape mutation in an application-side helper. Extend the state machine for selection, expansion history, temporary Answer Graph restoration, timeline selection, and recovery actions rather than distributing those transitions through unrelated components.

### App, timeline, Inspector, and GraphRAG coordination

**Analog:** `frontend/src/App.tsx::AuthenticatedApp` (109-701)

This is the composition seam. It owns `useGraph` (121), `selectedElement` (141), `graphFocus` (195), graph/timeline selection wiring (399-400), and passes shared state to `TimelineView` (499), `GraphCanvas` (547), and `DetailPanel` (579). A scene reducer/hook should be introduced narrowly here, preserving ChatSheet, search, path, export, Notes, ChangeSet refresh, series/episode selectors, and the existing rule that Inspector open state derives from selection.

**Analog:** `frontend/src/components/timeline/TimelineView.tsx` (7-12, 57-104, 124-203) and `TimelineEventRow.tsx` (4-79)

Timeline currently consumes the already boundary-filtered graph (no second data call), filters Event nodes, sorts by reveal order/episode/label, groups under episode headers, and emits a compact `TimelineSelection` through `onSelect`. Keep this first-class React/CSS pattern; adapt neutral timeline DTOs through a pure adapter. Preserve keyboard ArrowUp/ArrowDown/Enter, `aria` labels, 44px targets, selected state, independent filter checkbox, and sparse empty-state copy.

**Analog:** `frontend/src/components/detail/DetailPanel.tsx` (111-187, 48-109) and `DetailPanel.test.tsx`

Keep Inspector tabs and evidence resolution separate from the main graph. `resolveClaimsForSelection()` resolves node claims or a single claim-backed edge (149-169); `resolveEvidenceForClaims()` joins evidence to safe sources (172-187). Character images fail closed to identical initials fallback on missing/failed images (48-109). New Claims/Evidence/Source/Answer Graph actions should open detail first and require explicit “Show in graph”; preserve `readOnly` permissions and safe image behavior.

### Tests, fixtures, benchmark, docs, and UAT

**Analogs:** `frontend/src/components/graph/GraphCanvas.test.tsx` (268 onward), `graphElements.test.ts` (5 onward), `layoutConfig.test.ts` (10 onward), `TimelineView.test.tsx` (101-149), `DetailPanel.test.tsx` (57 onward), `App.test.tsx` (1-203 onward)

Extend existing focused tests rather than replacing them. Current tests explicitly cover pass-through of backend visibility, deterministic element IDs, claims, focus classes, layout lifecycle, cached positions, no relayout on selection/refresh, overview/full switching, timeline ordering/keyboard selection/empty state, Inspector evidence/image fallbacks, and App-level graph focus/change-set wiring. New tests should add DTO bounds, deterministic projection, technical-label suppression, spoiler-before-projection, stable positions, expansion collapse/undo/reset, temporary-view restoration, four tabs/mobile sheet, timeline bidirectionality, and cache separation.

**Fixtures:** `frontend/src/test/fixtures/graphResponse.ts` and `spoilerless/tests/conftest.py`

Create immutable safe S01E01 and cumulative S01E02 fixtures before changing production projection behavior. Include node kinds, event metadata, claims, sources, evidence, reveal orders, and enough future rows to prove Episode 1 safety. Backend integration tests use disposable scratch series/teardown; never use `series_dexter`, live users, or production LLM calls.

**Benchmark:** no close analog found. Use deterministic in-memory DTO generation for exactly 30/50, 75/150, 150/400, and 300/1000 node/edge pairs; record payload/validation, adapter, Cytoscape init/layout, interaction, expansion, switch, memory/React commits where feasible, displacement, labels, and approximate crossings. Check in raw results and chosen A/B Episode Overview variant; do not build a research harness or query Neo4j/Redis.

**Docs/UAT:** use `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, root `README.md`, and `.planning/phases/08-production-deployment-automated-ci-cd/08-UAT.md` as structure analogs. Document backend-first projection order, DTO routes/fields, four-view hierarchy, cache key dimensions, benchmark method, and shipped-state limitations. UAT should follow the existing golden path: login/visitor boundary, Dexter family, Doakes distrust, events/clues/cases, Notes/export, Story return, GraphRAG focus, expansion/collapse, refresh, and Episode 2→1 disappearance.

## Shared Patterns

### Spoiler security is backend-first and fail-closed

**Sources:** `spoilerless/app/spoiler/policy.py:80-138`, `spoilerless/app/api/graph.py:77-118,129-187`, `spoilerless/app/services/graph.py:105-115`

Mandatory order: Neo4j read → effective boundary → spoiler/public metadata filtering → neutral projection → serialization → frontend. Hidden means absent, not masked with counts/placeholders. Never leak indirect signals through degree, group names, totals, layout forces, search ranking, path existence, focus IDs, cache hits, or empty space.

### Full graph, retrieval graph, and visual projection remain separate

**Sources:** `GraphResponse` in `spoilerless/app/domain/graph.py:79-99`, `graphToElements` in `frontend/src/components/graph/graphElements.ts:27-42`

GraphRAG continues using the complete safe graph. The visual DTO is task-specific and bounded (default overview 12–28 nodes, hard 40 / 60 caps). Full Graph is Advanced/debug only. Answer Graph and Evidence Chain are temporary visual contexts with explicit restoration snapshots; they must not narrow retrieval or mutate canonical storage.

### Stable identity and state ownership

**Sources:** `frontend/src/App.tsx:141-195,399-400`, `GraphCanvas.tsx:402-480`, `focusReducer.ts:17-26`

React owns scene state and transitions; Cytoscape owns rendering and receives batched diffs. Selection dims/highlights and syncs Inspector/timeline without relayout. Camera, expansion history, filters, and focus are preserved across view/episode changes where safe. Do not recreate Cytoscape on every fetch.

### Deterministic, no-cost tests

**Sources:** `frontend/src/App.test.tsx:54-122`, `GraphCanvas.test.tsx:268 onward`, `spoilerless/tests/test_graph_api.py`, `docs/TESTING.md`

Use Vitest with `NODE_ENV=test` and `CI=1`; reuse the fake Cytoscape instance and assert instance/layout call counts. Backend unit/contract tests mock services or use disposable scratch Neo4j only. Tests make no production LLM calls and never mutate live users or `series_dexter`.

## No Analog Found

| File/Concern | Role | Data Flow | Reason |
|---|---|---|---|
| `scripts/benchmark_visualization.py` | benchmark utility | batch/transform | No benchmark harness or checked-in metric format currently exists. |
| Neutral projection model/service | DTO/projection | transform | Existing `GraphResponse` is complete-detail, not a library-neutral task DTO; use its validation/boundary patterns, then record a Decision Log. |
| Scene restoration / semantic expansion reducer | state machine | event-driven | Existing `focusReducer` is the closest small reducer but has no history/temp-view/camera snapshot semantics. |

## Spoiler and Test Pitfalls to Preserve

- Do not move visibility filtering into `graphToElements`, a new adapter, CSS, or layout code; frontend tests currently assert backend pass-through.
- Do not derive importance from full-graph degree or expose hidden totals, group counts, layout influence, search ranking, path existence, or cache behavior.
- `visible_from_order is None` is hidden; missing visibility must fail closed rather than default to Episode 1.
- Clamp every requested order with persisted progress using `effective_view_order`; anonymous/no-progress readers remain at the safe Episode 1 surface.
- Do not overload `GraphResponse` with view-specific fields; preserve GraphRAG’s complete safe retrieval surface.
- Do not trigger a global random layout on selection, expansion, incremental refresh, or Answer Graph close; preserve camera and important-node positions.
- Keep stable Cytoscape instance/layout prop identity; tests use fake Cytoscape methods and inspect mount/layout counts.
- Keep technical Neo4j relation names out of normal UI; human labels are projection/adapter policy, with explicit debug-only raw labels.
- Keep Claims, EvidenceFragments, and Sources off the main story graph; explicit “Show in graph” is required.
- Character images must be episode-safe; missing and failed images use the same neutral fallback and never reveal source URLs above the boundary.
- Use fixed safe S01E01/S01E02 fixtures and synthetic benchmarks; never run projection tests against live `series_dexter`, real users, or production LLMs.

## Metadata

**Analog search scope:** `spoilerless/app/{domain,services,api,cache,spoiler,retrieval}`, `spoilerless/tests`, `frontend/src/{api,types,components,hooks,lib,test}`, `scripts`, `docs`, `.planning/phases/08-production-deployment-automated-ci-cd`  
**Files scanned:** 33 primary analogs plus adjacent tests/docs  
**Pattern extraction date:** 2026-08-13

## PATTERN MAPPING COMPLETE
