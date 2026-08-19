# 10-04 Frontend Viz Scene — Wire Types, Adapters, Reducer, Stable Lifecycle (Phase 10 wave 4)

Companion to `plan-10-03-visualization-openapi-stub-tests.md` (backend DTO side).
Task 1 commit `56decea`; Task 2 (dagre layout + label policies) was mid-flight at
handoff — verify current repo state before trusting the Task-2 notes below.

## Architecture (what shipped / where)

- **Wire types**: `frontend/src/types/graph.ts` — `VisualizationDTO` mirrors
  `spoilerless/app/domain/visualization.py` field-for-field (metadata/nodes/edges/
  groups/timeline/focus; `origin: string | null`; `VisualizationViewType` union).
- **API**: `frontend/src/api/graph.ts` `fetchVisualization(seriesId, view,
  episodeOrder, focusIds?)` — repeated `focus_id` appended only when provided
  (backend caps at 20, graphrag_focus only). Never filters client-side (D-05).
- **Pure adapters**: `frontend/src/lib/visualizationAdapter.ts` —
  `toCytoscapeElements(dto, {debugLabels})` (groups→compound parents `group:<id>`,
  nodes→`nodeType`/`displayTier`/`order`/`origin`/`episodeId`/`imageUrl`,
  edges→human `relation_class` as label) and `toTimelineEvents(dto)`. Exact-shape
  tests pin the documented data-key sets (`NODE_DATA_KEYS` etc.) and inject a
  poisoned hidden field into the DTO to prove it never reaches Cytoscape data
  (T10-LEAK-04). `debugLabels: true` is the ONLY switch adding a `debugLabel` key
  (Advanced/full view only, D-14).
- **Scene reducer**: `frontend/src/hooks/useSceneState.ts` — fully JSON-
  serializable state (JSON round-trip test): activeView, nodeKind/edgeClass
  filters, selection, focus, camera, positions, expansions, timelineSelection,
  inspector, temporary. `SET_FOCUS`/`OPEN_TEMPORARY`/`ADD_EXPANSION` refuse ids
  not matching `/^[A-Za-z0-9][A-Za-z0-9:_-]*$/` (T10-FOCUS-04). `OPEN_TEMPORARY`
  snapshots camera/selection/expansions/timeline; `CLOSE_TEMPORARY` restores
  (D-27). `RESET_VIEW` clears expansions/focus/temporary, keeps view/filters/
  camera (D-49).
- **GraphCanvas viz wiring** (D-08/D-22/D-23/D-44): optional `visualization` prop;
  last-non-null DTO held in a ref while prop is `null` → loading keeps the prior
  scene (no flash, no instance recreation). `runLayout` derives the positions
  scene key from the `view` param: `viz:<view_type>` — key has NO episode order
  so shared characters stay stable across episode switches (D-23), and views
  never share positions (T10-CACHE-04). Additions (expansion/new nodes) detected
  as new node ids vs previous render → deterministic local concentric placement
  (`LOCAL_PLACEMENT_RADIUS = 110` around bounding-box centre) merged into the
  cache — never a global relayout (D-22).

## Pitfalls

- **`frontend/tsconfig.app.json` has `noUnusedLocals` + `noUnusedParameters:
  true`** — a param added for a later task but unused in the current commit
  FAILS `npm run build` (tsc -b). Fix pattern: make the param genuinely used
  (derive a second value from it, e.g. scene key from view) rather than passing
  redundant args.
- **Vitest is NOT a typecheck**: esbuild transform passes broken type imports.
  A wrong relative path in a test (`../../types/graph` from `src/lib/` — must be
  `../types/graph`) passed vitest and was caught only by `npm run build`. Run
  the build after EVERY task, not just at plan end.
- **Module-level caches need test reset seams**: `filterState.positionCache`
  and `autoZoomHold` state persist across tests in GraphCanvas.test.tsx; both
  expose `__reset...ForTests()` called in `beforeEach`. Any new module-level
  state in GraphCanvas-adjacent modules must ship a reset seam or tests leak
  positions/layout behavior across tests.
- **Fake-cy layoutstop capture** (GraphCanvas.test.tsx): the fake `layout()`
  returns `{one: noop, run: noop}`, so runLayout's position-STORAGE handler
  never fires. Tests needing stored positions must extend the fake to capture
  `one('layoutstop')` and expose an explicit `emitLayoutstop()`. Do NOT wire it
  into the render-loop `emitOne('layoutstop')` — that fires the launch-refresh
  handler every render; storing positions mid-render makes the layout effect
  early-return from cache and breaks the auto-zoom-hold tests that expect a new
  layout call.
- **T10-SC-04 audit gate**: `cytoscape-dagre@4.0.0` + `@types/cytoscape-dagre@
  2.3.4` (both `--save-exact`; ELK NOT added) contribute ZERO npm-audit findings.
  The 5 findings (brace-expansion, fast-uri, hono, js-yaml, nanoid) are
  pre-existing transitive tooling deps — record them, don't `npm audit fix`
  mid-plan.
- **Requirements ready-gate**: VIZ-07 is declared by BOTH 10-04 and 10-08 (and
  VIZ-03/VIZ-10 by 10-03/10-08). `gsd-tools query requirements.ready-ids
  <PLAN> <ID> --raw` returns empty until every declaring plan has a SUMMARY —
  do not mark shared IDs complete early.

## Layout contracts (Task 2, D-23)

- investigation / Evidence Chain → dagre, left-to-right (`rankDir: 'LR'`),
  registered once in `layoutConfig.ts` beside fcose/cose-bilkent; other views
  fCoSE then stored presets.
- Label policies (D-14): stylesheet classes `edge.hovered/.edge-active/
  .label-visible` implement never/on_hover/on_select/on_path; medium_zoom via a
  zoom-handler toggling `label-visible` tracked in a per-id Set so zoom-out
  doesn't clobber selection labels; `always` for investigation via
  `edges().addClass('label-visible')`; technical labels only via `debugLabels`.
- Prior scene retained during loading/error is enforced by the
  last-DTO-hold ref (D-44); tests must prove selection/focus/expansion never
  grow `layoutCalls`.
