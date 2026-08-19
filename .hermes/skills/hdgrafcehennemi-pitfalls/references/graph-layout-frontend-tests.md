# Frontend graph layout, element mapping & verification pitfalls (08-05/08-06)

User-directed graph-usability iterations and the pitfalls they exposed.

For cross-view crashes or silent element loss on one persistent Cytoscape
instance, read `references/cytoscape-persistent-scene-reconciliation.md` first;
it contains the real-library headless probe, compound-parent cascade root cause,
safe mutation order, transition matrix, and regression contract.

## Where things live
- `frontend/src/components/graph/graphElements.ts` — pure GraphResponse → cytoscape
  elements (nodes/edges/clusters). D-16: consume ONLY backend-filtered lists; NEVER
  filter by visible_from_order client-side (backend's job — second authority = drift).
- `frontend/src/components/graph/graphStylesheet.ts` — node/edge styles; compound
  (cluster) box size is controlled via the `padding` style property.
- `frontend/src/components/graph/layoutConfig.ts` — fcose (default; `layoutName`
  starts 'fcose' in GraphCanvas.tsx), cose-bilkent and built-in cose fallbacks.
  `layoutOptionsFor()` is the single source for spacing constants; per-node
  repulsion lives in exported `nodeRepulsionFor()`.
- `frontend/src/components/graph/overviewTiers.ts` — Overview/Full graph modes
  (08-06+): `GraphMode`, semantic `displayTierFor` (curated suffix sets — id
  endsWith match so `dexter:character:X` and fixture-short `char_X` resolve the
  same; user-origin + Episode/Series always tier 1; NEVER degree-based), and
  `overviewProjection` (tier-1 + REQUIRED connector nodes via the exact
  articulation test over the filtered edge list — a node on an alternate route
  is NOT required and stays hidden — plus edge dedupe per (endpoint-pair, type)).

## Overview/Full modes (08-06+, product-owner presentation)
- **Overview is the DEFAULT** (`GraphCanvas initialMode='overview'`); Full shows
  every spoiler-safe element. Toggle lives in GraphControls (bottom-left stack,
  "Graph mode" group; buttons have aria-label "Overview mode"/"Full mode").
- Overview = tier-1 nodes + connectors (validated against live seed: 26 nodes /
  37 deduped edges, fully connected; +Episode/Series anchors ≈ 30). Edge list
  is deduped (repeated PARTICIPATED_IN/OCCURRED_IN/PART_OF collapse). Curated
  tier sets live in `overviewTiers.ts` — re-run the seed-based projection check
  if you touch them.
- **Edge labels are interaction-only**: base `edge` style has `label: ''`; the
  stylesheet selector `edge.hovered, edge.edge-active, edge.label-visible`
  shows `data(label)`. GraphCanvas applies `label-visible` on node tap (incident
  edges), external `focusedElementIds` focus, and clears it on empty-tap / focus
  clear / reveal cleanup. Node-hover also highlights incident edges (existing
  `.hovered` path) — labels flash on hover by design.
- **Mode switch re-runs the layout with forceRelayout** (different node set +
  spacing); position cache is keyed by mode (`filterState.ts`). Overview spacing:
  `OVERVIEW_SPACING_SCALE 1.6` repulsion, idealEdgeLength 420, gravity 0.015,
  tiling 45.
- **Overview zoom floor (08-06+)**: the sparse overview layout makes cytoscape's
  `fit` land ~0.37 zoom → nodes look tiny. `runLayout`'s `layoutstop` lifts the
  view to `OVERVIEW_MIN_ZOOM = 0.8` anchored on the graph's bounding-box centre
  (model-coordinate `position`, never `renderedPosition` — the cytoscape TS
  types lack `renderedPoint`). Guarded for test fakes (no `zoom`/`boundingBox`).
  VERIFY LIVE via `container._cyreg.cy.zoom()` in the browser console — vision
  checks misread it: at the all-episodes boundary the graph bbox (~1770px
  square) exceeds the short canvas, so the viewport shows a horizontal slice
  that still LOOKS zoomed out even at the floor.
- **Ep #1 `areaScale: 3` is Full-mode-only now** (08-06+): with ~6 curated nodes
  inside it, 300px padding was dead space that widened the fit bounding box and
  zoomed the whole view out. `graphElements.ts` stamps it only when
  `mode === 'full'`; Overview keeps the base 24px cluster padding.
- Test fakes: GraphCanvas.test.tsx fake cy MUST expose `connectedEdges` on both
  element handles AND collections (the focus effect calls
  `cy.getElementById(id).connectedEdges()`), and `fakeTarget` in App.test.tsx
  needs `connectedEdges` too — missing it makes the node-tap handler throw and
  selection silently dies (caught only in App.test.tsx integration runs).

## Current user-directed graph rules (tune here, not elsewhere)
- **Isolated-node pruning**: degree-0 nodes (zero edges in the filtered edge list)
  are dropped in `graphToElements`; clusters left empty are dropped too (cluster map
  built only from KEPT nodes). Topology-only, D-16-safe. The `simple` dot flag
  (degree < 3, no portrait) still applies to the rest.
- **Min clearance ~5cm** (~189px @96dpi; raised from 3cm 08-06+): fcose
  `nodeRepulsion` 833333 (non-parent) / 1666667 (parent), `idealEdgeLength` 320,
  `gravity` 0.02. fcose has NO hard min-gap param — gaps are enforced via forces;
  pair separation scales ~ sqrt(repulsion), so `new_rep = old_rep × (target/old)²`.
  Fallbacks: cose-bilkent plain 160000 (accepts no function), built-in cose uses
  `nodeRepulsionFor`.
- **Edge-driven cohesion** ("pull nodes toward only the nodes they're connected
  to"): `edgeElasticity` 0.75 (fcose) / 0.4 (fallbacks) + `gravity` 0.02 — springs
  between connected pairs dominate; nothing drags nodes to the canvas centre.
- **Dexter 7cm bubble**: `nodeRepulsionFor` returns `DEXTER_REPULSION` (1_633_333,
  ~1.96× base) for `char_dexter_morgan` across fcose + built-in cose (function
  repulsion); cose-bilkent takes a plain number so it has no per-node special case.
  Pair separation scales with sqrt(repulsion ratio) = 1.4× the 5cm gap ≈ 7cm.
  Pinned by `layoutConfig.test.ts`.
- **Ep-1 cluster 3× area**: graphElements stamps `areaScale: 3` on the `Ep #1`
  parent; stylesheet `node[areaScale = 3]` → `padding: 300px` (on top of the 24px
  cluster base). Same specificity as `node[isCluster]`, declared after it.

## PITFALL: run the FULL vitest suite, not just touched test files
Changing graphElements/layout/stylesheet can break `GraphCanvas.test.tsx`
integration tests that assert the rendered element-id set ("renders elements
corresponding to the S01E01 fixture…", "never filters elements by
visible_from_order…"). The isolated-node pruning broke 3 such tests while
`graphElements.test.ts` stayed green — narrow verification missed it; the full
`NODE_ENV=test CI=1 npm run test` (39 files / 297 tests) caught it.
ALWAYS run the full frontend suite after any element/layout change. Convention:
GraphCanvas.test.tsx mirrors graphToElements topology — when pruning rules change,
update both files' expectations together (connected nodes must render, isolated
must not; the visible_from_order pass-through intent stays intact).

## PITFALL: fixed vs absolute overlay positioning
Overlay positioning mixes two coordinate systems: `fixed` = VIEWPORT,
`absolute` = nearest positioned ancestor. The search bar (NodeSearch) is
`absolute left-1/2 top-4` inside the graph container (which sits BELOW the fixed
header); the Filters pill (GraphFilterPanel) is `fixed top-16`. Setting the pill
to `top-4` HID IT UNDER THE FIXED HEADER (16px from viewport top = header zone) —
user reported the Filters button "missing". Keep `top-16` (viewport row below the
header) and align horizontally with `md:ml-[15.5rem]` (bar w-96 centered → right
edge at 50%+192px; pill trigger is `mx-auto` inside a w-72 container). Lesson:
when co-locating a `fixed` overlay with an `absolute` overlay, both verticals must
be expressed in the SAME coordinate system — the pill cannot use the bar's `top-4`.

## Backend parallel-test finding (08-06)
`scripts/run_backend_tests.py` (10 chunks, 45 files, complete partition) —
sequential per-chunk is the safe local mode against the SHARED live AuraDB.
`--parallel` (all 10 at once) measured 27+ min WITHOUT completing — 10 driver
pools contend on the free instance's connection budget plus prod traffic, i.e.
slower than serial. Parallelism only pays off against an ISOLATED Neo4j (CI
ephemeral container, or local docker via `source scripts/env-local.sh`).
Never run two pytest processes concurrently against the live DB: ChangeSet /
candidate residue from one trips the seed audit of the other.

## Live-DB seed audit quirk
`seed.py::audit_visibility_integrity` fails if ANY node under the seeded series
has null `visible_from_order` — it excludes `UserSeriesProgress`, `ChatSession`
and (since 08-05) `ChangeSet`. ChangeSet nodes NEVER carry visible_from_order by
domain contract (`domain/change_set.py`), so a real user ChangeSet on
series_dexter used to break `spoilerless-setup` — the latent-bug class to check
when the audit fires.

## Deploy build-marker trick
`GET https://api.spoilerless.net/health` `service` field identifies the deployed
build: `hdgrafcehennemi-backend` = stale pre-rename build, `spoilerless-backend` =
current main. Use it to confirm a Render redeploy landed without dashboard access
(a live 200 `database: connected` does NOT prove the latest deploy succeeded —
Render keeps serving the last good build while deploys fail, e.g. a dashboard
Start Command override pointing at the renamed-away `backend.app.main:app`).

## Edge-collision reduction (08-06)
Dense graphs: long edges cross the whole canvas and edge labels overlap illegibly.
Fixes (all in place):
- fcose `quality: 'proof'` (more iterations → better crossing minimization) +
  `edgeElasticity: 0.75` (stiffer springs → straighter, shorter edges → fewer
  long-range crossings). Values live in `layoutConfig.ts`.
- Edge-label dark pills in `graphStylesheet.ts`: `text-background-color: '#0B1120'`,
  `text-background-opacity: 0.85`, `text-background-padding: 3px`,
  `text-background-shape: 'roundrectangle'`, label color `#E2E8F0` — overlapping
  labels in dense hubs stay legible instead of text-on-text.

## Settings drift pattern (08-06)
`Settings(_env_file=None)` requires `neo4j_uri/neo4j_username/neo4j_password`
(no defaults since env consolidation). Unit tests constructing Settings must pass
dummy creds — `neo4j_uri='bolt://localhost:7687', neo4j_username='u',
neo4j_password='p'` (see `test_database.py::_settings`; `test_config.py` uses a
`_settings()` helper). Symptom: pydantic ValidationError "Field required" for
aura_username/aura_password on `Settings(_env_file=None)`.

## Live-DB residue cleanup (08-06)
Killed or parallel pytest runs leave residue that trips the seed audit in later
runs. Clean before the next run (same classes conftest teardown removes; never
touch real dev user rows `user:ae8a41b7-...` or `:AppSetting`/`:Session`):
```cypher
MATCH (n) WHERE n.origin='candidate' OR n.series_id STARTS WITH 'series_scratch' OR n.id STARTS WITH 'series_scratch' DETACH DELETE n
MATCH (p:UserSeriesProgress) WHERE p.series_id STARTS WITH 'series_scratch' DETACH DELETE p
```
Verify: rerun the count query expecting 0 before starting a suite.

## Overview/Full graph modes (08-06+, presentation declutter)

User-directed "simplify the graph for the presentation": two modes, Overview
(default) = curated ~25-45-node projection, Full = every spoiler-safe element.
Backend/GraphRAG untouched — pure frontend (`frontend/src/components/graph/`).

### Design (`overviewTiers.ts`)
- `displayTierFor(node)` — semantic tiers (1 important / 2 supporting / 3
  detail), NEVER degree-based. User-origin nodes, Episode, Series → always 1.
  Curated suffix sets (main cast, case-arc events, anchor locations, signature
  objects) matched by `node.id.endsWith(suffix)` — NOT `Set.has` — so live seed
  ids (`dexter:character:dexter_morgan`) and fixture-short ids
  (`char_dexter_morgan`) resolve identically. Doc-vs-impl drift (documented
  endsWith, wrote set.has) = 16 test reds in one run; tests caught it.
- `overviewProjection(graph)` → tier-1 nodes + REQUIRED connectors + deduped
  edges. Connector = node whose removal splits two tier-1 nodes that were
  connected in the backend-filtered graph (exact articulation test, run per
  connected component of the FULL graph). PITFALL: the naive "≥2 tier-1 nodes
  reachable within ≤2 hops" rule over-keeps (51 connectors → 74 nodes on the
  hub-and-spoke seed); the articulation test kept 3 (26 nodes, all connected).
  Alternate-route nodes are NOT kept (neither is individually required) —
  accepted per "required connector" semantics.
- Edge dedupe: (sorted endpoint pair, type) keeps the first edge — repeated
  PARTICIPATED_IN / OCCURRED_IN / PART_OF connections collapse.
- VALIDATE CURATION FIRST: write a throwaway python sim (load
  `data/dexter/seed/*.json` + `claims.json`, build undirected adjacency, run
  the same projection) and check node count ∈ 25-45, single connected
  component, connector list BEFORE writing frontend code. Seeded overview = 26
  nodes / 37 edges, connected (+3 Episode +1 Series from the live API ≈ 30).

### Edge labels: interaction-only (`graphStylesheet.ts`)
Base `edge { label: '' }`; text/pill props stay in base; a
`edge.hovered, edge.edge-active, edge.label-visible { label: 'data(label)' }`
selector adds the label. `.label-visible` is applied by GraphCanvas: node tap
(`node.connectedEdges().addClass('label-visible')`), external `focusedElementIds`
effect (nodeIds loop + edgeIds loop), and cleared on empty-canvas tap / focus
clear / reveal cleanup. Edge tap uses `.edge-active` (same selector). Node
mouseover also shows labels (existing handler adds `.hovered` to
connectedEdges) — deliberate.

### Default-mode + test strategy
- `GraphCanvas` `initialMode` prop, default 'overview' (the app default);
  `graphToElements(graph, mode='full')` default 'full' keeps pure-function unit
  tests green. Sweep pre-existing GraphCanvas.test renders with
  `initialMode="full"` so their full-topology intent stays intact.
- Mode switch forces relayout (`forceRelayout=true` via a `lastLayoutModeRef`
  in the layout effect); `filterState.ts` position-cache key gained the mode —
  Overview and Full must NOT share cached positions.

### Fake-cy stub pitfalls (BOTH GraphCanvas.test.tsx and App.test.tsx)
- Element handles AND collections must expose `connectedEdges()`: the tap
  handler calls it unguarded. App.test.tsx's stub lacking it made the handler
  THROW before `onSelect` → DetailPanel never opened → "Unable to find heading
  Dexter Morgan". Same class as the TooltipProvider crash: a test red from a
  missing stub method = the real handler path is being exercised.
- The empty-tap handler checks `evt.target === cy` (identity): background-tap
  simulations must pass the SAME fake cy object the stub registered via
  `props.cy` — capture it in a module var, don't construct a lookalike.
- Build blind-spot instances: TS2353 (adding `connectedEdges` to the
  FakeCollection type) + TS2339 (union return of `layoutOptionsFor` —
  `tilingPaddingVertical` doesn't exist on the cose-bilkent member; cast to a
  local interface). Only `npm run build` catches test-file TS errors.

## Auto zoom-out + 20s interaction hold (08-06+, product rule)

User rule: the graph must NOT auto zoom-out for 20s after ANY touch anywhere in
the app; each touch resets the timer; after the hold expires the normal
fit/zoom-floor resumes. `AUTO_ZOOM_HOLD_MS = 20_000` in GraphCanvas.tsx.

- **`runLayout` is the SINGLE fit authority.** The declarative
  `<CytoscapeComponent layout>` prop is built with `fit:false`
  (`layoutOptionsFor(name, reducedMotion, mode, false)`) and MEMOIZED
  (`useMemo(..., [mode])` — `layoutName` is a module-level `let`, NOT a valid
  dep; including it trips `react-hooks/exhaustive-deps` "unnecessary
  dependency" warning).
- **react-cytoscapejs layout-prop trap (the REAL "auto zoom-out after
  interaction"):** its `diff()` compares per-key VALUES of the layout prop; a
  fresh `nodeRepulsion` closure per call makes it re-run the layout (fit:true!)
  on EVERY GraphCanvas re-render. Fix: memoize the layout object (stable ref →
  their `prev === next` short-circuit) AND never let the prop fit.
- **Remount trap:** GraphCanvas UNMOUNTS on every graph refetch (destructive
  loading unmount in useGraph) — per-mount `useRef` interaction state is lost
  and the fresh cy starts at the default zoom-1 origin. Interaction state lives
  at MODULE level: `lastTouchAt` + `lastViewport` + `__resetAutoZoomStateForTests()`
  test hook. `runLayout` restores `lastViewport` (cy.zoom/cy.pan,
  typeof-guarded) when the hold is active; a `cy.on('viewport')` recorder keeps
  it current.
- **Sentinel trap:** `lastTouchAt` init must be `Number.NEGATIVE_INFINITY` — a
  small negative (-1) makes `now - lastTouch < 20000` TRUE for the first 20s of
  page life and wrongly suppresses the very first fit.
- Hold applies to graph-change-driven layouts only
  (`holdView = suppressAutoZoom && !forceRelayout`): mode switch and reset-zoom
  always refit (forceRelayout bypasses the hold).
- Tests: the fake cy needs a `layout` spy (`() => ({ one: () => {}, run: () => {} })`)
  to make runLayout reachable and assert the `fit` flag per call; assert the
  layout PROP reference stays stable across graph-change re-renders and flips on
  mode change; call `__resetAutoZoomStateForTests()` in beforeEach (module state
  otherwise leaks across tests via userEvent pointerdowns).
- **react-refresh/only-export-components lint error**: a test hook exported from
  the COMPONENT file breaks fast-refresh (component files may only export
  components/types). Keep module-level state + `__reset...` in a separate tiny
  module (`autoZoomHold.ts`) and import the hook from there in tests.

## Debugging cytoscape live (verified, 08-06)

- Measure zoom, don't guess: `container._cyreg.cy.zoom()` via a
  `document.querySelectorAll('div')` walk for `d._cyreg?.cy`. Vision models
  misread zoom: a ~1770px-square graph bbox in a 1256×492 canvas looks "zoomed
  out" even at the 0.8 floor.
- Who re-fits? Patch `Object.getPrototypeOf(cy)` `fit`/`zoom`/`pan`/`layout`
  with stack-logging wrappers (`window.__log.push(name + new Error().stack)`),
  reproduce, read the log.
- `NO_CY` after an interaction = the canvas REMOUNTED (loading unmount) —
  per-mount state is gone; look for module-level/global causes, not the ref.

## Local dev run (08-06)

- Backend: root `.env` (AuraDB) → `unset PYTHONPATH && uv run uvicorn
  spoilerless.app.main:app --host 127.0.0.1 --port 8000`; `/health` →
  `{"status":"ok","database":"connected","service":"spoilerless-backend"}`.
- Frontend: `npm run dev` in frontend/ (vite proxies /api → 8000); app at
  http://localhost:5173 — "Continue as visitor" skips login for anonymous demo.

