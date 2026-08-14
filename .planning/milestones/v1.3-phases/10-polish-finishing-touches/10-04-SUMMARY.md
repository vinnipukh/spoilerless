---
phase: 10-polish-finishing-touches
plan: 04
subsystem: ui
tags: [cytoscape, react, dagre, visualization, scene-state, adapter, typescript, vitest]

# Dependency graph
requires:
  - phase: 10-polish-finishing-touches
    provides: 10-03 typed VisualizationDTO wire contract (/api/series/{id}/graph/visualization, 6 views, projection_version 1.0.0)
provides:
  - Typed frontend VisualizationDTO wire types + fetchVisualization API call
  - Pure DTO→Cytoscape/timeline adapters (no client spoiler filtering, debugLabels opt-in)
  - Serializable scene reducer (view/filters/selection/focus/camera/positions/expansions/Inspector/Answer-Graph)
  - View-scoped stored positions + dagre left-to-right Investigation layout (cytoscape-dagre@4.0.0, types 2.3.4)
  - medium_zoom label policies (min-zoomed-font-size) on nodes + interaction-driven edge labels
affects: [10-05 story-map UI, 10-06 semantic expansion, 10-07 focus/restoration, 10-08 benchmarks, 10-10 UAT]

# Actuals (#2632) — pairs with the plan's `estimate` (36000 tokens) on the same scale (chars/4 over the realized diff).
actuals:
  tokens: 18400
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added:
    - cytoscape-dagre 4.0.0 (exact pin, runtime dep)
    - @types/cytoscape-dagre 2.3.4 (exact pin, dev dep)
  patterns:
    - Pure adapter seam (visualizationAdapter) between DTO and Cytoscape — never filters, never computes visibility
    - Serializable scene reducer with JSON round-trip; server-safe-id rejection
    - View-scoped stored positions scene key `viz:<view>` (D-23) — stable shared characters across episode switches, never crosses views
    - Layout engine per task view: dagre rankDir LR for investigation, fcose + presets otherwise (D-25)

key-files:
  created:
    - frontend/src/lib/visualizationAdapter.ts
    - frontend/src/lib/visualizationAdapter.test.ts
    - frontend/src/hooks/useSceneState.ts
    - frontend/src/hooks/useSceneState.test.ts
  modified:
    - frontend/src/types/graph.ts
    - frontend/src/api/graph.ts
    - frontend/src/components/graph/GraphCanvas.tsx
    - frontend/src/components/graph/GraphCanvas.test.tsx
    - frontend/src/components/graph/layoutConfig.ts
    - frontend/src/components/graph/graphStylesheet.ts
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Adapter is pure and lossless within the DTO contract: it converts every serialized visible field and adds nothing (T10-LEAK-04); technical labels only via explicit debugLabels=true for the full view (D-14)."
  - "Scene key for stored positions is `viz:<view>`: presets persist across episode switches per view but never cross views (T10-CACHE-04)."
  - "Investigation/Evidence Chain uses left-to-right Dagre (cytoscape-dagre 4.0.0, pinned; TS types 2.3.4); ELK deliberately not added; all other views keep fcose + stored presets (D-25)."
  - "medium_zoom label policy implemented via min-zoomed-font-size 7 on node labels and interaction-driven edge labels — labels vanish below the threshold (semantic zoom, presentation-only)."

patterns-established:
  - "Pattern 1: stable-scene wiring — the visualization path renders through the SAME react-cytoscapejs instance as the legacy graph path; last-DTO hold while loading (D-44)."
  - "Pattern 2: additions never re-relayout — new node ids get local concentric placement merged into the stored preset (D-22)."
  - "Pattern 3: declarative layout memo keyed on view — incident parent renders cannot start layouts; runLayout derives the engine from the view param."

requirements-completed: [VIZ-07]
coverage:
  - id: D1
    description: "Typed VisualizationDTO wire types + fetchVisualization(view, episodeOrder, focusIds?) API call"
    requirement: VIZ-07
    verification:
      - kind: unit
        ref: "frontend/src/lib/visualizationAdapter.test.ts#data-shape"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pure DTO→Cytoscape/timeline adapters — exact-shape, no client filtering, poisoned-field rejection, debugLabels only for full view"
    requirement: VIZ-07
    verification:
      - kind: unit
        ref: "frontend/src/lib/visualizationAdapter.test.ts#poisoned-field"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#debugLabels"
        status: pass
    human_judgment: false
  - id: D3
    description: "Serializable scene reducer with stable Cytoscape identity across re-renders, last-DTO hold during loading, server-safe-id rejection"
    requirement: VIZ-07
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useSceneState.test.ts#json-roundtrip"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#same cytoscape instance"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#retains prior scene"
        status: pass
    human_judgment: false
  - id: D4
    description: "Layout contracts — investigation routed to left-to-right dagre (pinned cytoscape-dagre 4.0.0), other views fcose; selection/focus never re-runs layout; zoom-aware label policies"
    requirement: VIZ-07
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#routes investigation to left-to-right dagre"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#never re-runs the layout"
        status: pass
    human_judgment: false
  - id: D5
    description: "Visual/gesture/readable-node backstops for responsive composition, gestures, long readable text, keyboard/readable Cytoscape node access"
    verification: []
    human_judgment: true
    rationale: "DOM/state checks cannot prove visual composition quality, gesture ergonomics, or readability of long labels at real sizes — these are 10-10 UAT rows UI-RESP-01, UI-GESTURE-01, UI-TEXT-01, UI-A11Y-01."

# Metrics
duration: 65min
completed: 2026-08-13
status: complete
---

# Phase 10: Polish & Finishing Touches Summary

**Frontend DTO wire types, pure Cytoscape/timeline adapters, serializable scene reducer, and view-scoped dagre/fcose layout contracts on a stable Cytoscape instance**

## Performance

- **Duration:** 65 min (executor Task 1 + orchestrator inline Task 2)
- **Started:** 2026-08-13 18:42
- **Completed:** 2026-08-13 19:10
- **Tasks:** 2
- **Files modified:** 11 (8 tracked modified + 4 created; package.json/lock updated)

## Accomplishments
- `VisualizationDTO` wire types + `fetchVisualization(seriesId, view, episodeOrder, focusIds?)` typed API call (repeated focus_id only when provided)
- Pure `visualizationAdapter.ts`: `toCytoscapeElements` (groups→compound parents, nodes carry nodeType/displayTier/order/origin/episodeId/imageUrl, edges use human relation_class labels) + `toTimelineEvents`; exact-shape data-key tests + poisoned-field rejection (T10-LEAK-04); technical labels opt-in via debugLabels, passed only for the full view (D-14)
- Serializable scene reducer `useSceneState.ts`: view, filters, selection, focus, camera, positions, expansions, timeline selection, Inspector, Answer-Graph snapshot/restore (D-27); server-safe-id rejection (T10-FOCUS-04)
- Stable lifecycle: visualization path renders through the SAME react-cytoscapejs instance; last-DTO hold while loading (D-44); view-scoped stored presets key `viz:<view>` (D-23); additions get local concentric placement, no global relayout (D-22)
- Layout contracts: `layoutNameForView` routes investigation → dagre rankDir LR (cytoscape-dagre@4.0.0 exact-pinned + @types/cytoscape-dagre@2.3.4, registered once, ELK not added); all other views fcose + presets; zoom-aware label policies via `min-zoomed-font-size: 7` (medium_zoom, D-14); npm audit: 5 findings all pre-existing tooling deps, zero on dagre

## Task Commits

Each task was committed atomically:

1. **Task 1: wire types, pure adapters, scene reducer, stable lifecycle** - `56decea` (feat)
2. **Task 2: dagre investigation layout + zoom-aware label policies** - `5aedd1a` (feat)

**Plan metadata:** pending (SUMMARY + STATE.md + ROADMAP.md commit)

## Files Created/Modified
- `frontend/src/types/graph.ts` - VisualizationDTO wire types, VisualizationViewType union
- `frontend/src/api/graph.ts` - fetchVisualization typed call
- `frontend/src/lib/visualizationAdapter.ts` + test - pure DTO→Cytoscape/timeline adapters
- `frontend/src/hooks/useSceneState.ts` + test - serializable scene reducer
- `frontend/src/components/graph/GraphCanvas.tsx` - viz path, scene keys, dagre routing, layout memo keyed on view
- `frontend/src/components/graph/layoutConfig.ts` - dagre branch + layoutNameForView
- `frontend/src/components/graph/graphStylesheet.ts` - min-zoomed-font-size label policies
- `frontend/package.json` / `package-lock.json` - cytoscape-dagre 4.0.0 + @types/cytoscape-dagre 2.3.4 (exact pins)

## Decisions Made
- Adapter purity: converts only serialized visible DTO fields, never filters/computes visibility client-side — the frontend cannot become a second spoiler authority (D-05)
- Investigation = dagre LR chain (Claim → Evidence → Source readable path); everything else stays force-directed (D-25)
- medium_zoom via min-zoomed-font-size rather than JS zoom listeners — pure stylesheet semantics, presentation-only (D-14)

## Deviations from Plan

### Auto-fixed Issues

**1. [Build contract] noUnusedParameters in tsconfig.app.json**
- **Found during:** Task 1
- **Issue:** scene key derivation used a now-unused param — tsc build failure
- **Fix:** derive scene key inside runLayout from the view param
- **Files modified:** frontend/src/components/graph/GraphCanvas.tsx
- **Verification:** npm run build passes
- **Committed in:** 56decea (Task 1 commit)

**2. [Test contract] import path typo in adapter test**
- **Found during:** Task 1 build
- **Issue:** `../../types/graph` from src/lib resolved wrong
- **Fix:** corrected to `../../types/graph` relative import
- **Verification:** npm run build passes
- **Committed in:** 56decea

**3. [Dead code] module-level layoutName became write-only**
- **Found during:** Task 2 (dagre routing)
- **Issue:** after routing layout engine through layoutNameForView(view), the module var had no readers (noUnusedLocals failure risk)
- **Fix:** removed the module-level layoutName + its fallback assignment; catch path now falls back to cose directly
- **Files modified:** frontend/src/components/graph/GraphCanvas.tsx
- **Verification:** npm run build + 50 vitest tests pass
- **Committed in:** 5aedd1a (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 build contract, 1 test contract, 1 dead code)
**Impact on plan:** All fixes necessary for correctness; no scope creep.

## Issues Encountered
- Executor finished Task 1 (committed) then hit its tool cap; orchestrator completed Task 2 inline (dagre routing, label policies, tests, build).
- npm audit findings (brace-expansion, fast-uri, hono, js-yaml, nanoid) are pre-existing transitive tooling deps — zero findings on cytoscape-dagre. Noted, not deviations.
- Local npm config `omit=dev` globally — vitest missing after node_modules re-sync; `npm install --include=dev` restored dev deps.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Story-map UI (10-05) can consume the four-view scene + shared selection
- Semantic expansion (10-06) uses the local-placement addition path
- GraphRAG focus (10-07) rides the focus/restoration reducer state
- UAT backstops recorded: UI-RESP-01, UI-GESTURE-01, UI-TEXT-01, UI-A11Y-01 (10-10)

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*
