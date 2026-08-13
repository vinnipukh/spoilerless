# Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign - Research

**Researched:** 2026-08-13
**Domain:** spoiler-safe narrative graph projections, Cytoscape scene state, GraphRAG/evidence visualization, regression/UAT closeout
**Confidence:** HIGH for repository architecture and locked requirements; MEDIUM for implementation details that require new design and benchmark measurements

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Scope amendment
- **D-01:** Phase 10 includes both original polish obligations and narrative visualization redesign. This supersedes ROADMAP's prior “no new features or architectural changes” sentence. Planner must reconcile `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` before execution.
- **D-02:** Work incrementally: audit/baseline; neutral DTO; Episode Overview projection; Cytoscape adaptation; stable layout; timeline sync; expansion; Answer Graph/Evidence Chain; benchmark/refine; final regression/UAT/docs.
- **D-03:** Significant architecture choices require concise evidence-based Decision Log: observed problem, alternatives, repository evidence, choice, reason, rejection, remaining risk.

### Graph separation and spoiler boundary
- **D-04:** Storage graph, GraphRAG retrieval graph, visual projection are separate systems. Visual reduction never deletes Neo4j detail or limits GraphRAG safe knowledge.
- **D-05:** Mandatory order: Neo4j, spoiler filtering, visualization projection, serialization, frontend. `effective_view_order = min(requested_view_order, watched_progress)` applies to graph, expansion, path, search, autocomplete, GraphRAG focus, saved restoration.
- **D-06:** Audit indirect leaks: hidden counts/degrees/layout forces/space/group names/expansion hints/search ranking/path existence/focus IDs/cache/totals. Future elements must not influence visible projection or layout. Importance uses safe-boundary editorial data, never full-graph degree.

### Renderer and visual projections
- **D-07:** Keep Cytoscape.js. NVL may exist only as isolated `/viz-lab` experiment; never production dependency.
- **D-08:** Backend returns library-neutral visualization DTO (`metadata`, `nodes`, `edges`, `groups`, `timeline`, `focus`). Frontend owns `toCytoscapeElements()` and timeline adapters.
- **D-09:** Default Episode Overview target 12–28 nodes, hard max 40; preferred under 35 edges, hard max 60; persistent procedural labels 0.
- **D-10:** Evaluate two fixed-data Episode Overview variants before choosing: A characters + major Events; B mostly Character Network, Events primarily timeline. Compare counts, crossings, clarity, stability, episode comprehension.
- **D-11:** Full Graph remains Advanced/debug/deep exploration, never default.

### Event and relationship presentation
- **D-12:** Detailed Events remain canonical and GraphRAG-accessible. Main visualization uses major/supporting/micro distinction, reusing existing cluster/sequence/plot metadata where possible.
- **D-13:** Episode Overview omits `PARTICIPATED_IN` and `OCCURRED_IN`. Participation becomes avatars/chips/highlighting/Inspector/timeline lists. Episode membership becomes context metadata. `LOCATED_IN` usually becomes Event-card metadata.
- **D-14:** Classify edges as narrative versus procedural. Raw Neo4j relation names stay hidden outside explicit debug mode. Label policy supports `never`, `on_hover`, `on_select`, `on_path`, `medium_zoom`, `always`; human wording replaces technical names.
- **D-15:** Canonical visual importance field is `display_tier` unless audit proves an equivalent exists. Semantics: 1 core, 2 supporting, 3 detail; classification valid only at resource's visible boundary.

### View navigation and mobile structure
- **D-16:** Desktop uses top-level tabs.
- **D-17:** Four top-level tabs: **Story**, **Characters**, **Evidence**, **Advanced**. Specialized modes nest contextually rather than exposing seven equal tabs.
  - Story: Episode Overview + Event Timeline coordination.
  - Characters: Character Network + Local Neighborhood.
  - Evidence: Investigation/Evidence Chain + temporary GraphRAG Answer Graph.
  - Advanced: Full Graph Explorer/debug tools.
- **D-18:** Mobile mirrors same hierarchy using horizontally scrollable top tabs, not bottom navigation.
- **D-19:** Mobile Inspector opens as bottom sheet with half-height and full-height states, preserving graph/timeline context.
- **D-20:** Do not squeeze graph, timeline, Inspector simultaneously onto narrow screens.

### Interaction and scene state
- **D-21:** Semantic expansion keys are human concepts (`family`, `work`, `conflict`, `episode_events`, `clues`, `locations`, `evidence`), server allowlisted and spoiler-safe. Preferred 8–12 additions, hard max 25. No hidden totals or future hints. Collapse, Undo, Reset required.
- **D-22:** Expansion preserves scene: existing important nodes fixed/constrained; new nodes arranged locally via concentric/local fCoSE. Never rerun random global layout.
- **D-23:** Initial Overview/Character layout uses fCoSE, then stored preset positions. Shared characters remain mostly stable across Episode changes. Evidence uses left-to-right Dagre through pinned `cytoscape-dagre@4.0.0` plus TypeScript declarations pinned to `2.3.4`; ELK is not added. Timeline uses React/CSS.
- **D-24:** Stable Cytoscape instance. React state owns scene; Cytoscape changes apply through batched diffs. Selection dims unrelated content, syncs Inspector/timeline, preserves camera, never triggers relayout.
- **D-25:** Semantic zoom changes labels/icons/secondary text only. Zoom never fetches or expands graph data.

### GraphRAG and evidence
- **D-26:** GraphRAG keeps full spoiler-safe retrieval graph. Visible focus highlights in place; hidden safe focus opens small temporary Answer Graph; micro Event maps to visible major Event plus Inspector detail; Claim/Evidence opens Evidence Chain.
- **D-27:** Answer Graph target 5–20 visual elements. Closing restores camera, selection, expansions, timeline state.
- **D-28:** Investigation view answers “Why do we know this?” using layered Claim/Evidence/Source path; never placed on default Episode Overview.

### Backend, cache, tests, closeout
- **D-29:** Exact read contracts: `GET /api/series/{series_id}/graph/visualization` supports `episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`; `GET /api/series/{series_id}/graph/expand` enforces boundary, semantic allowlist, and limit server-side. Both use strict neutral DTOs, existing optional-user graph access semantics, required positive `episode_order`, typed 404/422/503 envelopes, and synchronized OpenAPI/frontend-contract inventories.
- **D-30:** Projection cache key includes series, effective order, view type, projection version, Redis-local per-series cache epoch (`graph_revision`), and user scope where needed. Existing write invalidation atomically increments epoch; read failure bypasses cache. Never cross-return view or boundary.
- **D-31:** Baseline fixed safe snapshots for S01E01 and cumulative S01E02. Measure current node kinds, edge types, layout duration, payload before production behavior changes.
- **D-32:** Benchmarks cover 30/50, 75/150, 150/400, 300/1000 node/edge datasets; measure payload, adapter, init/layout, interaction, expansion, switch, memory, React commits, displacement, labels/crossings where practical.
- **D-33:** Automated tests cover spoiler-before-projection, bounds, Episode 1 safety, expansion, hidden leaks, GraphRAG independence/focus, cache separation, default view, timeline sync, label hiding, focus, collapse/reset, stable positions, Episode switch, Answer Graph, Evidence Chain, Inspector, responsive UI.
- **D-34:** Finish original Phase 10 obligations: backend pytest, frontend vitest/lint/build; real golden-path UAT; shipped-state README/root docs. Manual tasks include Dexter family, Doakes distrust, Episode events/clues/cases, return to Overview, GraphRAG visualization, Episode 2 to 1 spoiler disappearance.

### Claude's Discretion
- Exact nesting controls inside four top-level tabs.
- Exact fCoSE/preset/local-layout tuning and position persistence format.
- Exact DTO field names where repository already has cleaner equivalents.
- Exact benchmark harness and edge-crossing approximation.
- Exact editorial assignment mechanism after auditing existing metadata; do not add parallel priority fields.

### Deferred Ideas (OUT OF SCOPE)
- NVL production migration.
- 3D visualization.
- Research-grade StoryFlow optimization.
- Free-form graph editing in Episode Overview.
- Saved scenes beyond state needed for restoration, unless required by current acceptance.
- Unrelated auth/settings/chat/header redesign.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|---|---|---|
| VIZ-01 | Neutral DTO and task-specific projections while storage/GraphRAG retain safe detail | Add a backend projection layer beside `GraphResponse`; frontend adapter is the only Cytoscape conversion seam. |
| VIZ-02 | Boundary before projection/serialization and no indirect leaks | Reuse `effective_view_order()` and move all new reads through one server resolver; test metadata, topology, layout, search, focus, and cache as observable outputs. |
| VIZ-03 | Bounded Episode Overview and fixed S01E01/S01E02 variant comparison | Snapshot fixtures and projection contract tests enforce 12–28 target, 40/60 hard caps, edge omissions, and variant evidence. |
| VIZ-04 | Story/Characters/Evidence/Advanced hierarchy | Replace current graph/timeline/settings action navigation at the `AuthenticatedApp`/`App.tsx` composition boundary while retaining existing feature routes. |
| VIZ-05 | Responsive tabs, bottom-sheet Inspector, synchronized selection without relayout | Add focused component tests around `App.tsx`, `DetailPanel.tsx`, and the scene reducer; use viewport-level browser UAT for gestures/layout. |
| VIZ-06 | Allowlisted, bounded semantic expansion with collapse/undo/reset | Backend validates concept and limit; frontend stores expansion history and applies batched local diffs. |
| VIZ-07 | Cytoscape stable scene, fCoSE/preset/local layout, evidence/timeline rendering | Preserve `GraphCanvas.tsx` instance/callback lifecycle and refactor `graphToElements()` into a neutral-DTO adapter. |
| VIZ-08 | GraphRAG focus, temporary Answer Graph, Evidence Chain and restoration | Keep retrieval pipeline boundary independent; map citations/focus to DTOs and snapshot/restore scene state around temporary modes. |
| VIZ-09 | Projection cache separation and broad automated coverage | Extend `graph_cache.py` with view/version/revision dimensions and add unit/API/FE contract tests without live shared data. |
| VIZ-10 | Real baselines, scale benchmarks, and Decision Logs | Freeze safe fixtures, add synthetic benchmark harness, and record measured alternatives in phase research/plan notes and shipped docs. |
| POLISH-01 | Backend pytest, frontend vitest, lint, and build green | Run local disposable-DB backend path and frontend commands; do not use the shared live DB or `series_dexter`. |
| POLISH-02 | Golden-path conversational UAT | Exercise login through new views, BYOK chat, notes, export, and spoiler transitions with manual operator evidence. |
| POLISH-03 | README/root docs reflect shipped v1.3 | Update only after behavior is verified; reconcile `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and moved project-spec index. |
</phase_requirements>

## Summary

The repository already has the right safety and rendering seams, but its public graph contract is a single `GraphResponse` and its frontend graph mode is a client-side `overview` reduction. `[VERIFIED: spoilerless/app/domain/graph.py:79-104]` The current model quotes `class GraphResponse(BaseModel)` with fields `series`, `visible_until_order`, `effective_view_order`, `nodes`, `edges`, `claims`, `sources`, and `evidence`; `[VERIFIED: frontend/src/types/graph.ts:71-79]` the frontend mirrors the older shape. `[VERIFIED: frontend/src/components/graph/graphElements.ts:27-50]` `graphToElements(graph, mode)` currently decides between `full` and `overview` after receiving the already-filtered response. The plan should introduce a neutral, task-specific projection contract without making the client a second spoiler authority.

The strongest implementation path is additive and incremental: centralize effective-boundary resolution, fetch the complete safe graph once per request, project by task on the backend, serialize a neutral DTO, then adapt that DTO to Cytoscape or React/CSS. `[VERIFIED: spoilerless/app/spoiler/policy.py:94-116]` The current policy defines `effective_view_order(view_as_of_order, watched_through_order)` as `min(...)` and `require_visible_resource()` as the safe projection gate. `[VERIFIED: spoilerless/app/api/graph.py:66-127]` The graph route resolves the authenticated user's persisted progress before cache lookup and calls `GraphService.fetch_graph()` with the effective boundary. Preserve this order for every new endpoint and treat any client-side filtering, hidden metadata, or cache reuse across view/boundary as a defect.

The UI should be organized as a story map: Story, Characters, Evidence, Advanced. Keep the stable Cytoscape instance and existing GraphRAG/evidence plumbing, but make React own a serializable scene state and make graph mutations batched diffs. `[VERIFIED: frontend/src/components/graph/GraphCanvas.tsx:376-470]` The existing canvas already memoizes elements/layout, keeps a Cytoscape ref, and guards relayout by graph/mode/canvas identity; its recent launch-refresh lifecycle waits for startup `layoutstop`. Phase work should extend these seams rather than replace them. Benchmarks and S01E01/S01E02 fixtures must be created before selecting the Episode Overview variant.

**Primary recommendation:** Build one boundary-safe backend projection service plus versioned neutral DTO, one frontend adapter/scene reducer, and view-specific tests/fixtures; never reduce Neo4j or GraphRAG storage to satisfy visual density.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Boundary resolution and spoiler filtering | API / Backend | Database / Storage | Existing route resolves persisted progress and `GraphService` queries filtered rows before serialization. `[VERIFIED: spoilerless/app/api/graph.py:66-127]` |
| Complete canonical/storage graph | Database / Storage | API / Backend | Neo4j remains the canonical graph; projections must be read-only reductions. `[VERIFIED: .planning/PROJECT.md:1-35]` |
| Task-specific projection and neutral DTO | API / Backend | Database / Storage | Projection must not see hidden rows and must preserve GraphRAG detail independently. `[VERIFIED: spoilerless/app/services/graph.py:51-130]` |
| Projection cache | Database / Storage | API / Backend | Existing cache-aside is backend-owned and currently keyed only by series, effective boundary, and user. `[VERIFIED: spoilerless/app/cache/graph_cache.py:21-80]` |
| Cytoscape conversion and scene diffs | Browser / Client | API / Backend | D-08 assigns `toCytoscapeElements()` and timeline adapters to frontend; stable Cytoscape lifecycle is in `GraphCanvas.tsx`. |
| View hierarchy, Inspector, timeline synchronization | Browser / Client | API / Backend | `App.tsx` currently owns selected element, view, focus, timeline, and graph state coordination. `[VERIFIED: frontend/src/App.tsx:109-701]` |
| GraphRAG focus and evidence chain | API / Backend | Browser / Client | Retrieval stays complete and safe; UI receives citations/focus and renders temporary/linked views. `[VERIFIED: .planning/PROJECT.md:14-35]` |
| Benchmarks and UAT | Test/operations boundary | Browser / API | Synthetic benchmarks can be zero-cost and deterministic; real UAT must use the deployed golden path without mutating shared graph data. |

## Standard Stack

### Core

| Component | Verified version/shape | Purpose | Guidance |
|---|---|---|---|
| FastAPI + Pydantic | `fastapi>=0.140.7`, `pydantic-settings>=2.14.2` in `pyproject.toml` | API routes and DTO validation | Add projection models in the existing domain/service/API layering; do not add a new web framework. `[VERIFIED: pyproject.toml:1-16]` |
| Neo4j async driver | `neo4j>=6.2.0` | Canonical graph reads | Keep complete safe graph reads and parameterized Cypher; never access live users or `series_dexter` during tests. `[VERIFIED: pyproject.toml:1-16]` |
| Redis client | `redis>=8.1.0` | Cache-aside | Extend the existing cache key, preserve best-effort degradation on Redis failure. `[VERIFIED: spoilerless/app/cache/graph_cache.py:31-80]` |
| React + TypeScript + Vite | `react ^19.2.7`, `typescript ~6.0.2`, `vite ^8.1.1` | View hierarchy and scene state | Use existing app and component seams; no frontend rewrite. `[VERIFIED: frontend/package.json:1-47]` |
| Cytoscape.js + fCoSE | `cytoscape ^3.34.0`, `cytoscape-fcose ^2.2.0` | Production graph renderer/layout | Retain Cytoscape; initial layouts may use fCoSE, while expansion uses constrained/local layout. `[VERIFIED: frontend/package.json:14-25]` |
| Vitest + Testing Library | `vitest ^4.1.10`, `@testing-library/react ^16.3.2`, `jsdom ^30.0.1` | FE unit/component tests | Keep `frontend/vite.config.ts` jsdom setup and the existing Cytoscape test double. `[VERIFIED: frontend/vite.config.ts:18-24]` |
| pytest + pytest-asyncio | `pytest>=9.1.1`, `pytest-asyncio>=1.4.0`, async mode `auto` | Backend tests | Reuse `spoilerless/tests/conftest.py` fixtures and local disposable Neo4j only. `[VERIFIED: pyproject.toml:20-27]` |

### Supporting

| Existing seam | Use in Phase 10 |
|---|---|
| `spoilerless/app/spoiler/policy.py` | Single effective-boundary and visibility rule; no projection may run before this. |
| `spoilerless/app/api/graph.py::_resolve_effective_boundary` | Refactor into the shared resolver used by projection, expansion, path, focus, search, and restoration rather than copying route logic. `[VERIFIED: spoilerless/app/api/graph.py:129-180]` |
| `spoilerless/app/domain/graph.py` | Preserve current storage/read DTOs; add separate neutral visualization DTOs rather than overloading `GraphResponse`. |
| `frontend/src/components/graph/GraphCanvas.tsx` | Stable Cytoscape instance, batched updates, focus, position cache, and layout lifecycle. |
| `frontend/src/components/timeline/TimelineView.tsx` | React/CSS timeline adapter; selection should dispatch the same scene action as graph selection. |
| `frontend/src/components/detail/DetailPanel.tsx` | Inspector base for evidence, event participation, claim/source detail, and mobile sheet states. |

## Architecture Patterns

### 1. Safe read pipeline

Use this fixed pipeline for every projection:

```text
Neo4j parameterized read
  -> effective boundary resolved from server-side progress
  -> spoiler-safe node/edge/claim/source/evidence filtering
  -> task projection and bounded reduction
  -> neutral DTO validation/serialization
  -> cache keyed by all safety dimensions
  -> frontend adapter and scene diff
```

`GraphService.fetch_graph()` already gathers series, nodes, structural edges, claims, user edges, sources, and evidence, then validates models and closure. `[VERIFIED: spoilerless/app/services/graph.py:51-130]` Keep this complete safe read as the source for projections; do not make an Episode Overview query that uses hidden degree or full-graph counts.

### 2. Neutral DTO boundary

Recommended shape, with exact field names subject to the existing type audit:

```python
class VisualizationDTO(BaseModel):
    metadata: VisualizationMetadata
    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]
    groups: list[VisualizationGroup]
    timeline: list[TimelineItem]
    focus: VisualizationFocus | None = None
```

The projection model must carry only safe labels, human semantic edge classes, display tier, event context, and evidence references required for the requested view. It must not carry full-graph degree, hidden totals, raw Neo4j technical relation names, or future group names. `GraphResponse` remains the complete safe backend graph contract for GraphRAG and Advanced/full mode; the visualization DTO is a separate presentation contract.

### 3. Projection variants and editorial importance

Implement two deterministic Episode Overview functions over the same fixed safe snapshot: Variant A retains characters plus major Events; Variant B makes the character network primary and puts Events in the timeline. Use existing `subplot`, `cluster`, sequence/plot metadata, or a verified equivalent before introducing `display_tier`; `graphElements.ts` currently reads optional `subplot`/`cluster` and falls back to `visible_from_order` episode bands. `[VERIFIED: frontend/src/components/graph/graphElements.ts:82-105]` Do not derive importance from degree, because degree is an indirect leak and D-06 explicitly forbids it.

Record counts, edge families, crossings, layout duration, displacement, and comprehension observations for S01E01 and cumulative S01E02. Select the production variant only after the comparison; the decision is not a styling preference.

### 4. Stable scene state

Use a serializable React scene model containing view, selected node/edge, camera, expansion records, timeline selection/filter, focus mode, and temporary-view restoration snapshot. Existing `GraphCanvas` already keys cached positions by series/order/mode and only relayouts when graph, mode, or Cytoscape instance changes. `[VERIFIED: frontend/src/components/graph/GraphCanvas.tsx:430-470]` Preserve existing important positions, use batched Cytoscape updates, and never run a global random layout for selection, zoom, timeline selection, or expansion.

### 5. Human UI hierarchy

Implement four primary tabs with nested controls. Story owns Overview + Timeline; Characters owns Character Network + Neighborhood; Evidence owns Investigation/Evidence Chain + temporary Answer Graph; Advanced owns Full Graph/debug. On mobile, tabs remain horizontally scrollable at the top and the Inspector becomes a half/full bottom sheet. Selection should produce one scene action that updates graph highlight, timeline selection, and Inspector, with no relayout.

### 6. GraphRAG/evidence independence

GraphRAG retrieval remains complete safe knowledge, not the Episode Overview payload. Visible focus can highlight existing nodes; hidden-safe focus can be represented only by a bounded temporary Answer Graph. Claim/Evidence citations should open the Evidence Chain; closing must restore the prior scene snapshot. The current app already keeps chat independent from left Inspector selection and routes citations through existing selection/focus paths. `[VERIFIED: frontend/src/App.tsx:109-260]` Preserve this separation while adding view state.

## Don't Hand-Roll

| Problem | Do not build | Use/preserve | Why |
|---|---|---|---|
| Spoiler boundary | Frontend filtering or a second visibility policy | `effective_view_order()` plus backend filtered queries | Two authorities drift and indirect leaks are hard to detect. `[VERIFIED: spoilerless/app/spoiler/policy.py:94-116]` |
| Graph renderer | New renderer/NVL production dependency | Cytoscape.js and existing `GraphCanvas` lifecycle | D-07 and package lock already establish the renderer. |
| Global scene synchronization | Independent selection implementations per view | One React scene reducer/action path | Existing graph search, palette, timeline, and backlinks already converge on selection/focus. |
| Layout stability | Random global relayout on every change | fCoSE initial layout, preset positions, local constrained expansion | Preserves camera, selection, and shared-character positions. |
| Cache safety | Ad hoc string keys per endpoint | Central versioned key builder containing series/order/view/projection/revision/user scope | Existing key omits view and projection version. `[VERIFIED: spoilerless/app/cache/graph_cache.py:21-31]` |
| Evidence graph | Reconstructing citation facts in the UI | Existing claims/sources/evidence and GraphRAG citation IDs | Evidence must remain grounded and boundary-safe. |
| Edge crossing metric | Research-grade optimizer | Deterministic approximate benchmark metric, documented with limits | D-32 permits approximation; benchmark reproducibility matters more than sophistication. |

## Common Pitfalls

### Pitfall 1: Projection before effective boundary

**What goes wrong:** A task endpoint accepts requested order and projects before clamping to persisted progress, or a cache returns a later-boundary DTO. **Why:** `get_graph()` currently performs resolution and cache lookup in one route, while `_resolve_effective_boundary()` is duplicated for other routes. `[VERIFIED: spoilerless/app/api/graph.py:66-180]` **Avoid:** one shared resolver, tests that request S01E02 while progress is S01E01, and cache-key assertions. **Warning sign:** any projection function accepts an unvalidated client boundary.

### Pitfall 2: Indirect leak through visual absence

**What goes wrong:** Hidden degree, counts, group labels, empty space, ranking, force values, path existence, or focus IDs reveal future data. **Avoid:** construct projection candidates only from safe rows; cap and classify using safe-boundary editorial fields; compare Episode 1 output against a graph where future rows are physically absent, not merely hidden. D-06 is the acceptance checklist.

### Pitfall 3: Reusing `visible_from_order` as a frontend display band

**What goes wrong:** Existing `graphElements.ts` fallback `Ep #${node.visible_from_order}` becomes a persistent group name that leaks procedural structure or future episode grouping. `[VERIFIED: frontend/src/components/graph/graphElements.ts:82-105]` **Avoid:** backend supplies safe context metadata; hide procedural labels outside debug and never create groups from records the viewer cannot see.

### Pitfall 4: Stable Cytoscape lifecycle regression

**What goes wrong:** Changing element/layout object identity causes react-cytoscapejs to relayout or remount, losing camera and positions. **Avoid:** keep memoized layout/elements, use batched diffs, test the existing fake Cytoscape instance identity and `layoutstop` lifecycle. `[VERIFIED: frontend/src/components/graph/GraphCanvas.tsx:70-112,376-470]`

### Pitfall 5: Overloading `GraphResponse`

**What goes wrong:** Full GraphRAG fields become view-specific, or the frontend cannot distinguish complete safe graph from a bounded projection. **Avoid:** separate `GraphResponse`, `VisualizationDTO`, and adapter types; add explicit `view_type` and `projection_version` metadata.

### Pitfall 6: Expansion silently changes the scene

**What goes wrong:** Expansion causes a global relayout, changes selection/camera, or reveals hidden totals. **Avoid:** server allowlist/limit, return only additions and safe relationships, local constrained layout, history-based Collapse/Undo/Reset.

### Pitfall 7: False green regression suite

**What goes wrong:** Tests pass because they use a shared live DB, FakeLLM bypasses the actual boundary, or an old fixture lacks S01E02 future rows. **Avoid:** zero-cost unit/contract tests with synthetic DTOs and FakeLLM; backend integration tests only against disposable local Neo4j scratch series; explicitly do not run tests against live users or `series_dexter`.

## Baselines and Benchmark Research

Create immutable, checked-in safe fixtures for S01E01 and cumulative S01E02 before production projection changes. `[VERIFIED: frontend/src/test/fixtures/graphResponse.ts]` Existing frontend graph fixtures and `GraphCanvas.test.tsx` establish a pattern; the test suite currently asserts connected-node pruning, pass-through of backend visibility, claims, focus classes, and layout lifecycle. `[VERIFIED: frontend/src/components/graph/GraphCanvas.test.tsx:1-180]` Add a backend-equivalent fixture or serialized DTO snapshot that includes node kinds, edge types, claims, sources, evidence, and episode events.

Benchmark synthetic datasets with exactly 30/50, 75/150, 150/400, and 300/1000 node/edge sizes. Report payload bytes, JSON/DTO validation, adapter time, Cytoscape initialization/layout, selection/focus, expansion, view switch, episode switch, memory, React commits, node displacement, label visibility, and approximate crossings. Keep benchmarks deterministic, isolate browser and backend measurements, and publish raw results with the chosen variant and projection version. No benchmark needs Neo4j or Redis; use generated in-memory safe DTOs and the existing FakeLLM/no-network test discipline.

## Decision Log Recommendations

The following decisions should become concise records during planning/execution, each with observed problem, alternatives, repository evidence, choice, rejection, and remaining risk as required by D-03.

| Decision | Repository evidence to cite | Recommended choice | Remaining risk |
|---|---|---|---|
| Neutral DTO location | `spoilerless/app/domain/graph.py:79-104`, `spoilerless/app/services/graph.py:51-130` | Add `domain/visualization.py` models and a projection service adjacent to `GraphService`; keep `GraphResponse` complete. | DTO duplication until all consumers migrate. |
| Boundary resolver ownership | `spoilerless/app/api/graph.py:66-180` | Extract one backend resolver used by graph, projection, expansion, path, search/focus, and restoration. | Route-specific authorization/scope must remain explicit. |
| Episode Overview variant | S01E01/S01E02 fixture metrics and benchmark output | Choose A or B only after fixed-data comparison; store the chosen projection version. | Editorial metadata may be incomplete; do not add parallel priority fields without audit. |
| Cache key versioning | `spoilerless/app/cache/graph_cache.py:21-80` | Central key includes `series_id`, effective order, view, projection version, Redis-local per-series epoch, and required user scope; existing invalidation atomically increments epoch. | No Neo4j schema migration; Redis failure bypasses cache. |
| Stable scene update | `GraphCanvas.tsx:88-112,430-470` and existing tests | Keep one Cytoscape instance and apply batched add/update/remove plus preset/local positions. | Cytoscape diff edge cases and mobile remount behavior. |
| UI hierarchy | `App.tsx:109-701`, `TimelineView.tsx`, `DetailPanel.tsx` | Four top tabs, nested modes, shared scene actions; mobile horizontal tabs + bottom sheet. | Existing header actions/settings/chat must remain reachable without unrelated redesign. |
| GraphRAG Answer Graph | Existing citation/focus path in `App.tsx` and current GraphRAG contract | Temporary bounded view with explicit restoration snapshot; do not reduce retrieval graph. | Hidden-safe focus semantics need an explicit safe explanation and tests. |
| Benchmark methodology | `frontend/vite.config.ts`, package scripts, test doubles | Zero-cost deterministic harness; approximate crossings documented; no live DB. | Browser memory/React commit metrics vary by environment. |

## Code-Seam Recommendations

1. `spoilerless/app/spoiler/policy.py::effective_view_order` remains the invariant. Add tests first for requested order above persisted progress and for missing visibility failing closed. `[VERIFIED: spoilerless/app/spoiler/policy.py:62-116]`
2. `spoilerless/app/api/graph.py::get_graph` and `::_resolve_effective_boundary` are the first backend seams to consolidate. Do not copy their logic into each projection route. `[VERIFIED: spoilerless/app/api/graph.py:66-180]`
3. `spoilerless/app/services/graph.py::GraphService.fetch_graph` should continue returning complete safe detail; a new projection service should consume its safe domain output. `[VERIFIED: spoilerless/app/services/graph.py:51-130]`
4. `spoilerless/app/cache/graph_cache.py::_cache_key` must become a versioned, view-aware key builder; preserve `get_cached_graph`/`set_cached_graph` best-effort behavior. `[VERIFIED: spoilerless/app/cache/graph_cache.py:21-80]`
5. `frontend/src/types/graph.ts` should retain the existing wire types and add neutral visualization types; `frontend/src/api/graph.ts` should expose typed task-view/expansion calls. `[VERIFIED: frontend/src/types/graph.ts:9-88]`
6. `frontend/src/components/graph/graphElements.ts::graphToElements` should become the Cytoscape adapter for neutral DTOs. It must not gain visibility filtering, hidden-count logic, or full-graph degree. `[VERIFIED: frontend/src/components/graph/graphElements.ts:1-50]`
7. `frontend/src/components/graph/GraphCanvas.tsx::runLayout` and `GraphCanvas` lifecycle should receive scene diffs/presets rather than a new renderer. Existing layout caching and `layoutstop` handling are regression-sensitive. `[VERIFIED: frontend/src/components/graph/GraphCanvas.tsx:88-112,430-470]`
8. `frontend/src/App.tsx::AuthenticatedApp` is the scene/navigation composition seam. Move view coordination into a reducer or narrowly scoped scene hook, keeping `DetailPanel`, `TimelineView`, ChatSheet, search, path, export, and share integrations working. `[VERIFIED: frontend/src/App.tsx:109-701]`

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Backend framework | pytest 9.1.1+, pytest-asyncio 1.4.0+, async mode `auto` `[VERIFIED: pyproject.toml:20-27]` |
| Backend config | `pyproject.toml` (`testpaths = ["spoilerless/tests"]`) `[VERIFIED: pyproject.toml:20-27]` |
| Frontend framework | Vitest 4.1.10+, Testing Library, jsdom 30.0.1 `[VERIFIED: frontend/package.json:28-46]` |
| Frontend config | `frontend/vite.config.ts` (`environment: 'jsdom'`, `setupFiles: ['./src/test/setup.ts']`) `[VERIFIED: frontend/vite.config.ts:18-24]` |
| Quick backend run | `uv run pytest spoilerless/tests/test_spoiler_policy.py spoilerless/tests/test_graph_api.py -q` (fixture/config dependent; do not point at live shared data) |
| Full backend run | `uv run pytest` through the repository's disposable/local-DB test runner; inspect `docs/TESTING.md` and `scripts/run_backend_tests.py` before execution |
| Quick frontend run | `cd frontend; $env:NODE_ENV='test'; $env:CI='1'; npm test -- --run src/components/graph/GraphCanvas.test.tsx src/components/graph/graphElements.test.ts` |
| Full frontend run | `cd frontend; $env:NODE_ENV='test'; $env:CI='1'; npm test -- --run` |
| Lint/build | `cd frontend; npm run lint` and `cd frontend; npm run build` |

### Requirements → Test Map

| Requirement group | Test type | Required assertions and likely location |
|---|---|---|
| VIZ-01/02 | Backend unit/API | Projection receives only safe `GraphResponse`; requested order is clamped before projection; serialized DTO has no hidden counts/degree/technical labels. Add `spoilerless/tests/test_visualization_projection.py` and extend `test_graph_api.py` with mocked services, not live shared data. |
| VIZ-03/10 | Snapshot/benchmark | Fixed S01E01 and cumulative S01E02 DTO snapshots; A/B metrics; hard 40-node/60-edge caps; synthetic four-scale benchmark report. Add `spoilerless/tests/fixtures/visualization/` and a zero-cost `scripts/benchmark_visualization.py` or equivalent documented harness. |
| VIZ-04/05 | React component/e2e | Four tab labels, nested modes, mobile scrollable tabs, Inspector half/full sheet, selection synchronization, no layout call on selection. Add focused tests near `App.test.tsx`, `DetailPanel.test.tsx`, and new scene reducer tests. |
| VIZ-06 | Backend + FE unit | Allowlist exact keys, server hard max 25, no hidden totals, additions only, collapse/undo/reset history. Add API tests and a reducer/adapter test. |
| VIZ-07 | FE unit/component | Stable Cytoscape identity, batched diffs, preset stability, local expansion layout, zoom changes labels only, selection does not relayout. Extend `GraphCanvas.test.tsx`, `layoutConfig.test.ts`, and add adapter tests. |
| VIZ-08 | GraphRAG contract + FE | FakeLLM retrieval remains complete safe; visible focus highlights in place; temporary Answer Graph is 5–20 elements; Evidence Chain opens from claim/evidence; close restores camera/selection/expansion/timeline. Extend chat/citation tests and add scene restoration tests. |
| VIZ-09 | Cache unit/API | Keys differ for view/order/projection/revision/user; cache hit cannot cross a boundary; Redis failure falls through. Extend `test_graph_api.py`/new cache tests with mocked Redis. |
| POLISH-01 | Full regression | Backend pytest, frontend Vitest, lint, build; zero known failures and no live-user/`series_dexter` mutation. |
| POLISH-02 | Manual browser UAT | Login → series/episode → Story/Characters/Evidence/Advanced → BYOK chat → notes → export → expansion → Answer Graph/Evidence Chain → Episode 2→1 disappearance; record evidence for Dexter family, Doakes distrust, events/clues/cases, Overview restoration. |
| POLISH-03 | Documentation contract | Search README/root docs for stale prototype/no-deployment claims; run existing docs verification; ensure API/architecture/roadmap describe actual projection routes and hierarchy. |

### Sampling Rate

- Per backend task: focused pytest with mocked/scratch fixtures; never shared live data.
- Per frontend task: focused Vitest with `NODE_ENV=test CI=1`.
- Per wave: full backend suite and full frontend Vitest.
- Phase gate: full pytest, full Vitest, lint, build, benchmark report, and manual UAT evidence all green before verification.

### Wave 0 Gaps

- `spoilerless/tests/test_visualization_projection.py` — neutral DTO, projection order, bounds, edge omission, hidden-leak cases.
- `spoilerless/tests/test_visualization_cache.py` — view/version/revision/user key separation and Redis-degrade behavior.
- `frontend/src/lib/visualizationAdapter.test.ts` — DTO-to-Cytoscape/timeline conversion, technical-label suppression, stable IDs.
- `frontend/src/hooks/useSceneState.test.ts` or equivalent — selection, camera, expansion history, temporary-view restoration.
- `frontend/src/test/fixtures/visualizationS01E01.ts` and cumulative S01E02 fixture — fixed safe baseline and A/B comparison input.
- Benchmark harness and checked-in result format for the four required synthetic scales.
- Responsive/browser UAT script with explicit zero-cost/FakeLLM mode and a written prohibition on live Neo4j users/`series_dexter`.

## Security Domain

| ASVS category | Applies | Phase control |
|---|---|---|
| V2 Authentication | Indirect | Reuse existing auth; no new auth/settings work. |
| V3 Session management | Indirect | User scope in cache keys; never restore a scene across users. |
| V4 Access control | Yes | Projection/expansion/focus routes use existing authenticated/user scope and server boundary; GraphRAG focus cannot widen access. |
| V5 Input validation | Yes | Pydantic DTOs; enum/allowlist view types and expansion keys; bounded limits; parameterized Cypher. |
| V6 Cryptography | No new crypto | Do not introduce tokens or custom encryption; preserve existing share/session mechanisms. |

Known threat patterns: cache poisoning/cross-boundary reuse is prevented by complete key dimensions; indirect inference is tested through counts, degree, group names, layout, ranking, path/focus existence, and empty space; prompt/GraphRAG leakage is prevented by keeping retrieval safe and FakeLLM tests boundary-aware. These controls follow D-06/D-30 and existing backend-first filtering. `[VERIFIED: spoilerless/app/cache/graph_cache.py:1-18]`

## Project Constraints (from HERMES.md)

No repository `HERMES.md` exists at the working-directory path. `[VERIFIED: filesystem check]` The actionable constraints supplied by the phase context and canonical project documents are therefore: preserve the existing FastAPI/Pydantic/Neo4j + React/Vite/Cytoscape stack; keep backend filtering before frontend/LLM/tools; do not create a second graph DB, frontend/backend, GraphQL layer, or renderer; use `uv`/`pyproject.toml` and npm; keep tests deterministic and avoid live shared data. `[VERIFIED: .planning/PROJECT.md:180-230]`

## Environment Availability

| Dependency | Required by | Available | Version/source | Fallback |
|---|---|---|---|---|
| Python/uv | Backend tests | Present project environment | `pyproject.toml`, `.venv` | None for full backend suite; use focused pure unit tests if DB unavailable. |
| Neo4j | Existing integration tests | Do not probe/mutate live instance | Required only through disposable/local scratch setup | Mocked service/unit tests; local disposable DB for full suite. |
| Redis | Cache integration | Configured dependency, but not required for correctness | Existing cache degrades on missing/error | Mock Redis or no-Redis unit tests. |
| Node/npm | FE tests/lint/build | Present (`frontend/node_modules`, package manifest) | `frontend/package.json` | None for full FE gate; install from lockfile if clean environment. |
| Browser | UAT/responsive checks | Required at operator UAT time | Existing browser workflow | Automated component tests cover non-visual behavior; manual UAT remains required. |
| LLM provider | GraphRAG UAT | Not required for automated tests | Use existing FakeLLM/no-cost test double | BYOK only for explicit real golden-path UAT. |

**Explicit safety boundary:** do not access or mutate live Neo4j users or `series_dexter`; no live DB query was used for this research. Integration fixtures must use scratch series and teardown, while projection/benchmark tests should be zero-cost and in-memory wherever possible.

## Sources

### Primary / verified repository sources

- `.planning/phases/10-polish-finishing-touches/10-CONTEXT.md` — locked D-01..D-49, discretion, canonical refs, and deferred ideas.
- `.planning/REQUIREMENTS.md` — exact VIZ-01..10 and POLISH-01..03 requirements.
- `.planning/ROADMAP.md` — Phase 10 goal/success criteria and D-01 scope reconciliation.
- `.planning/STATE.md` and `.planning/PROJECT.md` — current milestone, spoiler invariant, test/operational context.
- `docs/architecture/project-spec.md` — canonical moved project specification; requested `docs/PROJECT-SPEC.md` is absent.
- `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/PROBLEMS.md` — live architecture, route contract, and evidence ledger.
- `frontend/src/components/graph/GraphCanvas.tsx`, `graphElements.ts`, `layoutConfig.ts`, `graphStylesheet.ts`, `GraphFilterPanel.tsx`, `focusReducer.ts` — renderer, adapter, layout, styling, filters, focus.
- `frontend/src/components/timeline/TimelineView.tsx`, `frontend/src/components/detail/DetailPanel.tsx`, `frontend/src/App.tsx`, `frontend/src/types/graph.ts`, `frontend/src/api/graph.ts` — cross-view state, Inspector, timeline, and wire contract.
- `spoilerless/app/domain/graph.py`, `api/graph.py`, `services/graph.py`, `cache/graph_cache.py`, `spoiler/policy.py` — backend models, boundary, graph assembly, cache, and policy.
- `frontend/package.json`, `frontend/vite.config.ts`, `pyproject.toml`, existing GraphCanvas/graphElements/Timeline tests — installed stack and validation seams.

### External documentation

No external package or web research was required: this is a repository-constrained redesign with locked stack and all necessary implementation contracts present in source. Package installation is not recommended for Phase 10.

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | The existing full safe `GraphResponse` is sufficient as the projection input; no new Neo4j schema is needed. | A missing editorial/revision field could require a data/query change; audit before locking `display_tier`. |
| A2 | A browser benchmark can report React commits/memory consistently enough for comparative evidence. | Environment noise may require reporting ranges and separating hard gates from advisory metrics. |
| A3 | Existing GraphRAG focus/citation state can be adapted to temporary Answer Graph/Evidence Chain without changing retrieval semantics. | Hidden-safe focus may expose a new API contract; prove with FakeLLM and boundary tests first. |

## Open Questions

1. Which existing metadata is a safe, canonical source for `display_tier`/major-supporting-micro classification? Audit `overviewTiers`, graph seed metadata, and backend rows before adding any field.
2. Resolved: graph revision is a Redis-local per-series cache epoch, default 0, atomically incremented by existing `invalidate_series` write paths. It is not canonical graph data; Redis read failure bypasses cache.
3. Which exact nested controls fit the current `App.tsx` header and mobile layout without an unrelated header redesign? Validate with the four-tab UAT and preserve existing Chat, Settings, Series, and Episode access.
4. Resolved: add only pinned `cytoscape-dagre@4.0.0` plus TypeScript declarations pinned to `2.3.4`; commit lockfile and audit provenance. Do not add ELK.
5. What are the real S01E01/S01E02 counts and layout metrics? Do not invent them in plans; generate only from fixed safe fixtures or a disposable scratch dataset.

## Metadata

**Confidence breakdown:**
- Requirements and constraints: HIGH — read directly from Phase 10 context, requirements, roadmap, and project files.
- Backend boundary/cache architecture: HIGH — read current policy, route, service, domain, and cache symbols.
- Frontend lifecycle/state architecture: HIGH — read current adapter, canvas, layout, timeline, Inspector, types, API, and tests.
- Exact editorial fields, benchmark values, and final tab-control details: MEDIUM — intentionally left to audit/measurement and Claude's discretion.

**Research date:** 2026-08-13
**Valid until:** 2026-09-12 for repository architecture; revalidate package versions and deployment behavior before implementation if dependencies change.
