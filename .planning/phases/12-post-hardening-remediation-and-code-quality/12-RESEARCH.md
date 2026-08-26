# Phase 12 RESEARCH — Architecture Deepening Additions (6 candidates)

**Date:** 2026-08-24 · **Author:** deep-dive research agent
**Source findings:** `C:\Users\arhan\AppData\Local\hermes\cache\delegation\subagent-summary-0-20260824_121511_440607.txt` (2026-08-24 codebase walk)
**Skills applied:** `.agents/skills/deslopify/SKILL.md` (deletion test, god-file/slop elimination, behavioral-preserving refactors), `.agents/skills/hdgrafcehennemi/SKILL.md` (repo conventions, test discipline)
**Existing plans:** `12-01-PLAN.md` .. `12-09-PLAN.md` (all read; phase NOT yet executed — STATE.md: "Phase 12 planned — ready for execution")

> **Note on required files:** `.planning/REQUIREMENTS.md` does not exist (only STATE.md, PROJECT.md, ROADMAP.md, MILESTONES.md, HANDOFF.json, RETROSPECTIVE.md under `.planning/`). STATE.md + 12-CONTEXT.md were used as the requirements/decisions source. All file:line evidence below was re-verified at HEAD against the actual repo.

---

## 1. Executive summary — plan mapping

| # | Candidate | Rating | Recommendation | New plan | Wave | depends_on |
|---|-----------|--------|----------------|----------|------|------------|
| C1 | Graph read path as one deep module | Strong | **Own plan** | 12-12 | 3 | 02, 06, 11 |
| C2 | Boundary resolution single authority (share bypass) | Strong | **Own plan** (merge into 12-02 is acceptable alternative; see §3.2) | 12-10 | 2 | 02 |
| C3 | Revision module: name it, unseam from HTTP | Worth exploring | **Own plan** | 12-11 | 3 | 02, 06 |
| C4 | Scene state: one reducer, single authority | Strong | **Own plan** (do NOT merge into 12-08) | 12-13 | 3 | 08 |
| C5 | Unify Cytoscape element adapters | Worth exploring | **Own plan** (serial after C4 — same file) | 12-14 | 3 | 08, 13 |
| C6 | Structural cache invalidation | Speculative | **Own plan**, kept small — upgraded by a real omission found (see §3.6) | 12-15 | 3 | 02, 12 |

**Key principle:** none of the 6 candidates are re-plans of existing plans; all are additive. All six are **behavioral-preserving consolidations** (deletion-test-positive), which is exactly the class of work the deslopify skill endorses. Wave 2 gains one plan (12-10), Wave 3 gains five (12-11..12-15).

**Corrected evidence that changes plan content (vs the findings file):**
1. **C6 has 12 call sites, not 7**: `api/candidates.py:153,292,324,364`; `api/change_set.py:116,189`; `api/user_content.py:168,205,221,234,270,286`. The findings file undercounted user_content (1 vs actual 6). This *strengthens* the structural-seam case.
2. **`POST /revisions/{id}/revert` does NOT invalidate the cache** (`api/revisions.py:152-177` has no `invalidate_series`), even though revert mutates visible graph content (UserNote/CustomNode restore/re-create). That is a **live staleness window up to the 300s TTL** — C6 is not purely speculative; it fixes a real omission.
3. **`filterState.ts` is not only filter state** — it also owns the module-level `positionCache` (`getCachedPositions`/`setCachedPositions`, bounded Map, `__resetPositionCacheForTests` test seam, lines 62-107). Deleting `filterState.ts` (C4) requires relocating the position cache, and `GraphCanvas.test.tsx:7` imports the reset seam from it.
4. **`focusReducer.ts` re-exports `applyFocusToCytoscape` from `../../lib/graph/highlight`** — deleting it (C4) must preserve that export path or update importers (`GraphCanvas.tsx:32-35`).
5. **The `(node as Record).subplot ?? .cluster` cast (C5) is dead code**: neither `spoiler/app/spoiler/filter.py` (NODES_QUERY) nor `graph/ontology.py` nor backend `GraphNode` (pydantic ignores extras) ever produce `subplot`/`cluster`; frontend `types/graph.ts` does not declare them. Deleting the cast is a **zero-behavior-change** fix (the episode-band fallback always fires today).
6. **STATE.md's D-01 record lists every gated route and omits share** ("graph, candidates, notes, custom nodes/relationships, revisions, episodes, visualization, expand, path, export") — direct documentary proof of the C2 bypass.

---

## 2. Sequencing vs the existing 9 plans

Current structure: Wave 1 = 12-01, 12-02, 12-04, 12-07 (no deps); Wave 2 = 12-03 (dep 02), 12-05 (dep 04), 12-06 (dep 01+02), 12-08 (dep 07), 12-09 (dep 08).

File-collision map with the new candidates (same-file conflicts must be serialized):

| File | Existing plans | New candidates |
|---|---|---|
| `api/boundary.py` | 12-02 | C2 |
| `api/candidates.py` | 12-02 (removes `_require_resolved_boundary` + its 2 call sites), 12-03 (graph/candidates.py — different file) | C2 (None-guard), C1 (DI factories), C6 (invalidate sites) |
| `api/revisions.py` | 12-02 (removes `_require_persisted_boundary` at :90, :125) | C1 (DI factories), C3 (imports move) |
| `api/user_content.py` | 12-02 | C1 (DI factories), C6 (6 invalidate sites) |
| `api/share.py` | — | C1, C2 (same 20-line region) |
| `revisions/__init__.py` | 12-06 Task 3 (hygiene: duplicate imports, double `_from_json`) | C3 (relocation) |
| `api/exceptions.py` | — | C3 (new sentinels) |
| `App.tsx`, `GraphCanvas.tsx` | 12-08 (full decomposition), 12-09 (DetailPanel only) | C4, C5 |
| `useSceneState.ts` + its test | — (only App.tsx + useSceneState.test.ts consume it today) | C4 |
| `types/graph.ts` | 12-07 (DTO sync) | C5 (minor) |
| `domain/user_content.py` | 12-01, 12-07 | — |

**Binding constraints:**
- **C3 must run after 12-06**: 12-06 Task 3 edits `revisions/__init__.py` (duplicate `CustomNodeType` import, double `before_snapshot` deserialization at `revisions/__init__.py:201+205`). If C3 relocates the module first, 12-06's edit breaks. Sequence: 12-06 hygiene lands in the old file, then C3 moves the *cleaned* content.
- **C2 must run after 12-02**: 12-02 already deletes `_require_resolved_boundary` (candidates.py:51-76) and its two call sites, and re-types `boundary.py`. C2 then closes only the share bypass + decides the candidates None-guard fate. Running C2 before 12-02 would fight over the same helper.
- **C4/C5 must run after 12-08**: 12-08 moves App.tsx scene logic into `useWorkspaceScene.ts` and GraphCanvas Cytoscape logic into `useCytoscapeBridge/useCytoscapeLayout`. C4/C5 operate on the *post-decomposition* file layout. C4 and C5 both touch GraphCanvas.tsx → run them serially (C4 → C5) to avoid merge churn.
- **C1 last-ish among backend plans**: it edits `api/candidates.py`, `api/revisions.py`, `api/user_content.py`, `api/series.py` (DI factories) which 12-02 and 12-06 also churn; and it touches `api/revisions.py` imports which C3 rewrites. Dep chain 02 → 06 → 11 → 12 keeps every hand-off clean.
- **C6 depends on C1's deps landing** so the invalidation facade sits in a stable service layer; but C6's revert-omission fix could be split out as an independent first task if Wave 3 planning wants an early win.

---

## 3. Per-candidate implementation research

### C1 — Graph read path as one deep module (12-12, Wave 3, dep 02/06/11) — Strong

**Verified anatomy of the duplication:**
- Read-path blocks (series check → boundary → cache-aside → `fetch_graph` → write-through) exist **3 times**: `api/graph.py:119-145` (get_graph), `api/graph.py:191-274` (get_visualization — adds projection), `api/share.py:118-145` (get_share_graph); plus 2 partial variants (expand `:330-371` no-cache by design T10-CACHE-06; export `:439-459` no-cache).
- Contract constants in the router: `VISIBLE_NODE_LABELS` (`api/graph.py:46-54`), `USER_RELATIONSHIP_TYPES` (`:55`), `VisualizationView`/`ExpansionKey` Literals (`:60-81`); `api/share.py:13-17` imports constants + `ProgressServiceDependency` **from api.graph** (api→api seam smell); `main.py:22` imports only the router (fine).
- DI factory copies: `get_graph_service` in graph.py:87, candidates.py:33, revisions.py:43, series.py:25, user_content.py:35 (5×); `get_progress_service` in graph.py:91, candidates.py:37, progress.py:35, revisions.py:47, series.py:29, user_content.py:39 (6×, progress.py is the natural owner); `DatabaseDependency` re-aliased at graph.py:45, revisions.py:19, series.py:18, user_content.py:27 despite `api/deps.py:27`.
- Private-attr leak: `find_path(service._database, ...)` at `api/graph.py:413-420` (imported from `retrieval/tools.py:34`).

**Approach:**
1. `GraphService.read_visible_graph(series_id, effective: int, user_id: str | None) -> GraphResponse` in `services/graph.py` owning cache-aside (`get_cached_graph`/`set_cached_graph`) + `fetch_graph` + write-through. **Deliberate deviation from the findings sketch:** do NOT move boundary resolution inside the service. `resolve_effective_boundary` stays the single D-01 authority in `api/boundary.py` (aligns with C2; keeps the 422 envelope and progress-service dependency out of the services layer, which must not import the api layer). Routes compose: series check → `resolve_effective_boundary` → `read_visible_graph`. The deletion test still passes (cache/fetch/write-through complexity concentrates in one deep method).
2. `GraphService.find_path(...)` wrapper (delegates to `retrieval/tools.py::find_path` with `self._database`), killing the private-attr leak at the call site. (Moving the BFS itself is optional; wrapper is the minimal diff and keeps `retrieval/tools.py` intact — deletion test: the seam is the fix, not the algorithm.)
3. Move `VISIBLE_NODE_LABELS`/`USER_RELATIONSHIP_TYPES` into `domain/graph.py`; move `VisualizationView`/`ExpansionKey` into `domain/visualization.py` (its natural home — `EXPANSION_*`/`GRAPHRAG_FOCUS_VIEW_TYPE` already live there). Cycle check done: `graph/ontology.py` imports stdlib+yaml only, so `USER_RELATIONSHIP_TYPES = sorted(load_ontology().user_safe_relationship_types)` is safe in domain. Update `api/graph.py`, `api/share.py` imports; share drops its `from api.graph` import entirely.
4. Centralize in `api/deps.py` (already exists): one `GraphServiceDependency`, one `ProgressServiceDependency`, delete the 4-5 re-aliases; routers import from deps. Delete the duplicated `DatabaseDependency` aliases (keep `deps.py:27`).
5. `get_share_graph` (`api/share.py:118-145`) and `get_graph` both call `read_visible_graph` → the byte-parallel cache blocks (share.py:129-145 vs graph.py:130-144) collapse into one copy.

**Risk:** LOW. No route signature, response model, cache key, TTL, or error envelope changes. OpenAPI surface untouched (52 ops / 39 templates locked by `test_openapi_contract.py` + `test_frontend_contract_doc.py`). Cache policy must stay single-copy — do not let `read_visible_graph` and a leftover route copy diverge. `get_cached_graph`/`set_cached_graph` swallow Redis errors (T-08-06-02) — preserve that.

**Test strategy:** `test_graph_api.py`, `test_share_api.py`, `test_visualization_cache.py`, `test_visualization_projection.py`, `test_deps.py` (deps module still imports cleanly), `test_openapi_contract.py`, `test_frontend_contract_doc.py`, plus `test_security_boundary.py` (boundary behavior unchanged through the new call shape). Live-DB rules: scratch series + teardown, never `series_dexter`.

---

### C2 — Boundary resolution single authority (12-10, Wave 2, dep 02) — Strong

**Verified bypass:** `api/share.py:59-77` re-implements the clamp inline: progress lookup → `min(requested, view_as_of)` → `effective_view_order` → `resolve_boundary` → 422, plus a direct `spoiler.policy` import at `:31`. It is semantically IDENTICAL to `resolve_effective_boundary(service, progress_service, series_id, user, requested_order)` with default `boundary_label="visible_until_order"` — byte-identical 422 message ("visible_until_order must identify a persisted episode order."). `ShareCreateRequest.visible_until_order` is required (`domain/share.py:16`, `Annotated[int, Field(gt=0)]`) and `user` is a `CurrentUserDependency` (never None), so the anonymous branch is unreachable in this call — no behavior delta.

**Options:**
- **A (recommended): own plan 12-10.** Task 1: replace share.py:59-77 with one `resolve_effective_boundary` call; delete the `effective_view_order` import; use a `GraphServiceDependency` (from deps after C1) instead of inline `GraphService(database)`. Task 2: decide the candidates None-guard. After 12-02, `_require_resolved_boundary` is deleted; the only candidates-specific semantic left is the **"omitted boundary must not default to everything" guard** (inline at candidates.py:189-195 and :235-241, raising 422 `INVALID_REQUEST`). Extract it into `boundary.py` as `def require_boundary(visible_until_order: int | None) -> int` (raises the 422; returns the value) so the route keeps one boundary import story — or keep it inline if the plan prefers minimal churn (it is already inline and duplicated 1:1). Task 3: tests. Update the `api/boundary.py` module docstring + STATE.md D-01 list to include share.
- **B (acceptable alternative): merge into 12-02.** Same invariant, same test file (`test_security_boundary.py`). Downside: 12-02 is already planned/reviewed with fixed must_haves; mutating it mid-flight muddies the review trail. Since the phase has not started executing, a maintainer could still fold it in — but the task directive is to ADD plans without re-planning, so Option A is the default.

**Risk:** LOW. Envelope byte-parity verified; clamp math identical. One nuance: the inline code and the resolver both fail closed when the creator has no progress record (→ 1), and both 422 when order 1 has no persisted episode — assert this exact behavior in tests.

**Test strategy:** extend `test_share_api.py` (create-share clamps to persisted progress; `visible_until_order` beyond progress → response `visible_until_order` = clamped value; non-persisted order → 422 `INVALID_VISIBLE_UNTIL_ORDER`), `test_security_boundary.py` (existing suite must stay green), `test_openapi_contract.py` (share route signature unchanged — no response_model/param changes).

---

### C3 — Revision module: named module + domain exceptions (12-11, Wave 3, dep 02+06) — Worth exploring

**Verified anatomy:** `revisions/__init__.py` (340 lines) holds `REVISION_CREATE_QUERY`, `RevisionRepository` (static tx-callback methods), `_REVERT_LABEL_ALLOWLIST`, `revert_revision_work(tx, command)` raising `http_error` from inside the DB write transaction at :184 (404 RESOURCE_NOT_FOUND), :189 (422 CANNOT_REVERT_CREATE), :199/:204 (422 INVALID_ACTION), :218 (404), :222 (409 CANNOT_REVERT_CANONICAL), :232 (403 FORBIDDEN), :270 (403), :283 (409 RESOURCE_ALREADY_EXISTS), :321 (422 INVALID_ACTION). The `api/exceptions.py::_SENTINEL_SPECS` registry (:44-69) that every other data-layer error flows through has **no revision entries**. Importers: `api/revisions.py:14`, `graph/candidates.py:14`, `repository/change_set.py:61`, `repository/user_content.py:28`.

**Approach:**
1. Move the package's content into a named module — `revisions/repository.py` for `RevisionRepository` + queries, `revisions/service.py` (or `services/revision.py`) for `revert_revision_work`. Package `revisions/__init__.py` becomes re-exports (back-compat for the 4 importers in one transaction) or importers are updated in the same plan (preferred — deletion test: the re-export shim is a shallow wrapper; delete it in the same plan so nothing keeps the old surface).
2. Introduce domain exceptions: `RevisionNotFound`, `RevisionForbidden`, `RevisionConflict` (covers CANNOT_REVERT_CANONICAL + RESOURCE_ALREADY_EXISTS), `RevisionActionInvalid` (covers INVALID_ACTION + CANNOT_REVERT_CREATE) — raised by `revert_revision_work` instead of `http_error`. Register in `_SENTINEL_SPECS` with **byte-identical envelopes** to today's:
   - `RevisionNotFound → 404 RESOURCE_NOT_FOUND "Resource not found."` (matches existing registry text)
   - `RevisionForbidden → 403 FORBIDDEN "This resource belongs to another user."` (matches `UserContentForbidden` text exactly — but keep a distinct class; the registry maps by type)
   - Context-varying messages (CANNOT_REVERT_CREATE, CANNOT_REVERT_CANONICAL, RESOURCE_ALREADY_EXISTS, INVALID_ACTION variants) do NOT fit uniform registry texts → follow the documented precedent ("Exceptions whose message varies by context … stay as explicit one-line catches at their routes", `exceptions.py:12-14`, precedent: `ChangeSetConflict`): register classes with the route-level catch for the code/message, or register per-code classes (4 small classes) if the plan prefers zero route-level try/except. **Decision to make in planning** — recommend per-code classes in the registry (5-6 entries) so `revert_revision` stays a one-liner, matching the PROB-10/#70 architecture.
3. `api/revisions.py` imports `revert_revision_work, REVISION_GET_QUERY` from the named module; route body unchanged (`:168-177` already just builds `command` + `execute_write`).

**Risk:** MED-HIGH (the trickiest envelope work of the six). Transaction-callback semantics: exceptions raised inside `execute_write` propagate to FastAPI — registered handler types translate; an **unregistered** exception → 500. Therefore every `http_error` call converted MUST have a registered sentinel or explicit catch — audit all 10 raise sites. `test_revisions.py` + `test_error_handlers.py` assert envelopes; check whether `test_error_handlers.py` pins the registry contents/size (it does per the module docstring — verify at plan time and extend, don't break).

**Test strategy:** `test_revisions.py` (envelope byte-parity for all 6 codes across create/update/delete revert paths), `test_error_handlers.py` (sentinels installed), `test_change_set_revision.py` + `test_user_content_api.py` (revision logging unchanged), `test_candidate_review.py` (approve/reject/edit revision logging via `graph/candidates.py` importer). No OpenAPI surface change (route signatures untouched).

**Gotchas:** 12-06 Task 3 must land first (same file). `revert_revision_work` currently deserializes `before_snapshot` twice (:201 and :205) — 12-06 fixes that; C3 inherits the cleaned code. Do not change `_REVERT_LABEL_ALLOWLIST` or the `CREATE (r:{resource_type} ...)` interpolation guards (SEC-GR-014).

---

### C4 — Scene state: one reducer, single authority (12-13, Wave 3, dep 08) — Strong

**Verified split-brain:** `useSceneState.ts` (D-24, 340 lines, 13 fields / 16+ actions, serializable contract pinned by `useSceneState.test.ts`) is consumed **only by App.tsx**, which reads only `scene.temporary?.nodeIds` (`App.tsx:796`); expansions double-book `setExpansionRecords` + `dispatchScene` at `App.tsx:397-402` (expand), `:409-412` (undo), `:414-417` (collapse); `mergedVisualization` useMemo deps include `expansionRecords` (`App.tsx:380`). GraphCanvas keeps parallel state: `useState<FilterState>(initialFilterState(...))` at `GraphCanvas.tsx:601`, `useReducer(focusReducer, initialFocusState())` at `:605`. `GraphFilterPanel.tsx` is a controlled component (`filterState` + `onToggle*` props, `GraphFilterPanel.tsx:11-16`). `filterState.ts` also owns the module-level `positionCache` (lines 62-107 + `__resetPositionCacheForTests`).

**Approach (post-12-08 layout):**
1. Make the scene reducer the authority for filters, focus, and expansions. App (or `useWorkspaceScene` after 12-08) already owns `useSceneState`; GraphCanvas receives `scene` + `dispatchScene` via props.
2. **Expansions:** delete App/useWorkspaceScene's parallel `expansionRecords` useState; `mergedVisualization` derives from `scene.expansions` + `scene.expansionHistory` (the reducer already carries both and models undo/collapse — no new actions needed; `ADD_EXPANSION`'s `record` param was built for exactly this).
3. **Filters:** map vocabulary — GraphCanvas `allNodeTypes`/`allEdgeFamilies` (`GraphCanvas.tsx:599-600`, families hardcoded `['CHARACTER','STRUCTURAL','EPISODE','USER']`) → scene `nodeKindFilters`/`edgeClassFilters`. **Semantics trap:** `filterState` initializes all-`true` (visible); scene `INITIAL_SCENE_STATE` has `{}`. Either seed the reducer with initialized maps (from `NODE_TYPES` + `EDGE_TYPE_TO_FAMILY` — better: derive families from `relationshipStyles.ts` instead of the hardcoded list, killing a drift source) or define absent-key = visible and pin it with a test. Preserve default-all-visible behavior exactly. `GraphFilterPanel` rewire: keep it controlled but feed it scene slices and emit dispatches (`SET_NODE_KIND_FILTER`/`SET_EDGE_CLASS_FILTER`/`SET_ALL_FILTERS` already exist).
4. **Focus:** scene `focus: {nodeIds, edgeIds} | null` replaces `focusedId`; GraphCanvas dispatches `SET_FOCUS`/`CLEAR_FOCUS`; keep `lib/graph/highlight.ts::applyFocusToCytoscape` as the application side (import path moves from `focusReducer.ts` re-export to `lib/graph/highlight`).
5. **Deletes:** `filterState.ts` — but first relocate `positionCache` (with its test seam) to `frontend/src/lib/graph/positionCache.ts` (natural home next to `highlight.ts`); update `GraphCanvas.test.tsx:7` import. Delete `focusReducer.ts`. Confirm no other importer exists (verified: only GraphCanvas.tsx + a comment in `lib/graph/highlight.ts:5`).
6. Extend `useSceneState.test.ts`: filters/focus/expansion actions round-trip through the JSON-serializable contract (D-24/T10-FOCUS-04), undo/collapse semantics, absent-key-visible filter contract.

**Risk:** MED. Behavior must be pixel/semantics-identical: all-filters-default-on, focus animation entry, expansion undo/collapse remove exactly the recorded additions (reducer already implements D-48 history-based restoration). React 19: no render-phase dispatch — scene-derived `mergedVisualization` must be a `useMemo`, dispatches only in handlers/effects (12-08 eliminates render-phase setState; C4 must not reintroduce). GraphCanvas's filter *application* (`.filtered-out` class marking etc.) stays in GraphCanvas — only the state authority moves.

**Test strategy (Vitest/jsdom):** `useSceneState.test.ts` (extended), `GraphCanvas.test.tsx`, `GraphFilterPanel.test.tsx`, `App.test.tsx`, `graphElements.test.ts`/`cytoscapeReconciler.test.ts` untouched. Full gate: `cd frontend && NODE_ENV=test CI=1 npm run test` (44 suites / 404+ tests).

---

### C5 — Unify the Cytoscape element adapters (12-14, Wave 3, dep 08+13) — Worth exploring

**Verified divergence:** `graphToElements(graph, mode)` (`graphElements.ts:27-157`): episode-band clusters (`Ep #N`/`Main` from `visible_from_order`, :93-100), `simple` dots (no-image AND degree < 3, :90), `areaScale: 3` for `Ep #1` in full mode (:134), `claimStatus` on edges (:151), drops isolated nodes (:68-72), Overview projection via `overviewProjection` (:38-42). `toCytoscapeElements(dto)` (`visualizationAdapter.ts:71-134`): 1:1 `group:`-prefixed parents from DTO groups (:33, :79-94), `displayTier/order/episodeId/relationClass/debugLabel` keys, NO simple/areaScale/claimStatus; exact data-key sets pinned by `NODE_DATA_KEYS/GROUP_DATA_KEYS/EDGE_DATA_KEYS` (:44-69) and `visualizationAdapter.test.ts` (T10-LEAK-04 contract). GraphCanvas branches at `:511-520`; `reconcileCytoscapeElements` (`cytoscapeReconciler.ts`) is vocabulary-agnostic (id/source/target/parent only — untouched).

**Approach:**
1. New neutral module `frontend/src/lib/graph/sceneElements.ts` (or `lib/sceneElements.ts`): one `SceneElementDefinition`-shaped model (nodes/edges/groups) + `normalize` per source + one `enrich` + one `emit` (parents-first ordering, matching both current behaviors: parents precede children in both adapters today).
2. **Cluster policy:** one function `clusterFor(node, groups?)` — DTO group membership when present, else episode band `Ep #N`, else `Main`. **Recommendation: keep the per-source policy selection explicit** (graph path: episode-band; viz path: group-membership) *inside the single function* via its input (groups list null vs present), NOT by adding episode bands to ungrouped viz nodes — adding bands would change the visualization path's visuals (new compound boxes) and risk the "no behavioral regression" gate. Document the single policy constant. (Full unification of *applied* policy is the findings' ideal; flag the visual delta as an explicit product decision if desired.)
3. **Decorations:** `enrich` applies `simple`/`areaScale`/`claimStatus` only where they exist today (graph path). If the plan wants the viz path to inherit them ("wins" list), that is an intentional visual change → update `visualizationAdapter.test.ts` exact-shape pins deliberately + justify in the T10-LEAK-04 comment (keys are benign presentation flags, no hidden field rides along). Default recommendation: enrich flags per path, viz path unchanged visually.
4. Delete the dead `subplot`/`cluster` cast (zero behavior change — verified no backend source emits those fields; keep `GraphNode`/`GraphResponse` types untouched, or declare the fields if a future backend contract intends them — out of scope).
5. GraphCanvas calls one adapter; the `:511-520` branch becomes: `activeVisualization ? sceneElements.fromVisualization(dto, opts) : sceneElements.fromGraph(graph, mode)` — or a single function over a union input.

**Risk:** MED. The exact-shape pin tests are the safety net (T10-LEAK-04) — any key-set change must be deliberate and commented. Reconciler untouched. `apiUrl(image_url)` handling must stay (Character-only portrait rule).

**Test strategy:** `visualizationAdapter.test.ts` (pin sets still exact; update only with justification), `graphElements.test.ts`, `cytoscapeReconciler.test.ts`, `GraphCanvas.test.tsx`, `npm run build` (tsc strict: the cast deletion must not surface type errors).

---

### C6 — Structural cache invalidation (12-15, Wave 3, dep 02+C1) — Speculative, upgraded by a real omission

**Verified:** 12 call sites (see §1 correction #1); `invalidate_series` (`cache/graph_cache.py:138-160`) = atomic epoch bump (`graph_revision:{series_id}` INCR) BEFORE `scan_iter` deletes of `graph:{sid}:*` + `viz:{sid}:*`, all best-effort swallowed. Deep semantics: viz keys embed the epoch (`:178-190`), graph keys do NOT (epoch protects only viz; graph keys rely on delete ordering). Over-invalidation is safe by construction (T-08-06-01); the risk is omission — and **revert is a live omission today** (`api/revisions.py:152-177` mutates visible content with no invalidation; up to 300s stale responses).

**Approach (bounded — no service-mesh heroics):**
1. New deep entry `services/graph.py::invalidate_series_cache(series_id)` (or a small `services/series_write.py` if C1 prefers separation): owns the epoch-bump-before-delete sequence + Redis-optional swallow; **routers stop importing `cache.graph_cache`** (the "api layer stops importing cache internals" win).
2. Replace all 12 call sites with the facade call. Deletion test: 12 remembered sites collapse into one seam; a new mutation path must import one service function instead of raw cache internals (still remembered, but the interface is deep and the import direction correct — the honest assessment for "Speculative": full structural impossibility-of-forgetting would need a write coordinator wrapping `execute_write`, which is over-engineering for this phase; document this as the deliberate boundary).
3. **Add the missing invalidation to `POST /revisions/{id}/revert`** (bug fix, independent of the seam) + regression test asserting cache entries for the series are gone after revert.
4. Optional cheap structural guard: an assertion-style test that greps the api layer for mutation routes without invalidation? — skip; instead document the call-site inventory in `graph_cache.py` docstring so the contract is discoverable.

**Risk:** LOW-MED. Never reorder epoch-bump → deletes (D-30 race separation); never make invalidation fail-closed on Redis errors (swallow — cache is a performance layer, T-08-06-02); TTL/key semantics unchanged.

**Test strategy:** `test_visualization_cache.py` (epoch bump + key deletion + race separation), `test_candidate_ingest.py`/`test_candidate_review.py`/`test_change_set_api.py`/`test_user_content_api.py` (behavior unchanged — invalidation is a side effect), new revert-invalidation regression in `test_revisions.py`.

---

## 4. Cross-cutting risks & gotchas (applies to all plans)

1. **OpenAPI contract is locked**: `test_openapi_contract.py` + `test_frontend_contract_doc.py` pin 52 ops / 39 templates. No candidate changes any route signature, parameter, or response model. Do not "improve" route metadata while touching routers.
2. **`api/exceptions.py` sentinel registry**: uniform envelopes; context-varying messages stay as route catches (ChangeSetConflict precedent). New exception classes must be registered or explicitly caught or they 500. `test_error_handlers.py` may pin registry contents — extend deliberately.
3. **Cache epoch semantics**: bump-before-delete ordering is D-30 race separation; graph keys lack the epoch (viz keys carry it) — any future "add epoch to graph keys" is a separate perf decision, not this phase.
4. **React 19 render-phase setState** is a P0 finding being fixed in 12-08; C4/C5 must keep all dispatches in handlers/effects and derive via `useMemo`.
5. **Vitest jsdom limits**: Cytoscape instances in tests are partial/adapted; module singletons (`positionCache`, `autoZoomHold`) need test-reset seams (`__resetPositionCacheForTests`, `__resetAutoZoomStateForTests`) — preserve them on relocation.
6. **Test discipline (backend)**: `uv run python scripts/run_backend_tests.py` (10-chunk runner); never two pytest processes in parallel on the shared AuraDB; `unset PYTHONPATH` first; scratch series + teardown only, never `series_dexter`.
7. **Frontend gate**: `cd frontend && NODE_ENV=test CI=1 npm run test` (44 suites, 404+ tests) + `npm run build` (tsc strict).
8. **Wave inventory**: keep `12-CONTEXT.md` plan-decomposition table updated with 12-10..12-15 when plans are written; STATE.md "Planned 12-01..12-09" line and D-01 gated-route list need the same touch.
9. **Findings-file tooling note**: the walker hit `search_files` returning 0 on Windows absolute paths; this research used terminal `find`/`grep` — plan execution should do the same.

## 5. Research verdict

All six candidates pass the deletion test; none overlap the THERMO findings already planned in 12-01..12-09; three (C1, C2, C4) are Strong and cheap relative to their wins; C3/C5 are worthwhile with explicit envelope/visual-parity gates; C6 is bounded by the honest "deep seam, not impossibility" boundary and gains real value from the revert-omission fix. Recommended additions: **12-10 (Wave 2, dep 02), 12-11..12-15 (Wave 3, deps per §2 table)**.

## RESEARCH COMPLETE