# Plan 12-08 Summary — Code Judo FE decomposition (all 4 tasks)

Executed by the orchestrator inline (5 provider deaths killed every dispatched executor; zero work was ever lost — each death was caught by transcript watchdog or completion notice with a clean tree).

## What landed

**Task 1 — shared primitives**
- `components/layout/ResizableRail.tsx` (NEW): pointer-capture drag rail (jsdom fallback), orientation prop, keyboard ±16px arrows, double-click reset seam.
- `ChatSheet.tsx` consumes it; clamp/persistence/double-click behavior preserved exactly.
- `components/layout/AppIcons.tsx` (NEW): SettingsIcon/CalendarClockIcon/LayoutGridIcon extracted from App.tsx.

**Task 2 — DetailPanel decomposition (THERMO-P0-04)**
- Extracted `dialogs/CreateRelationshipDialog.tsx`, `detail/CharacterPortrait.tsx`, `detail/tabs/{OverviewTab,NotesTab,ClaimsTab,EvidenceTab}.tsx`.
- DetailPanel.tsx **1074 → 531 lines**: lean shell owning selection/note handlers + Sheet chrome.
- `setTimeout(()=>setResolved(true),0)` hack DELETED; claims/evidence resolve synchronously.
- Accent-color constants moved to tabs/Claims+Evidence with DetailPanel re-exports (CitationChip import path intact).
- Test fix: "canonical origin" assertion scoped to the Origin dt/dd row (old `findByText('canonical')` ambiguous once claim cards render synchronously).

**Task 3 — GraphCanvas decomposition (THERMO-P0-03)**
- Extracted `useCytoscapeLayout.ts`: runLayout + localPlacementFor + prefersReducedMotion + zoom-floor logic (verbatim move).
- Extracted `dialogs/CreateCustomNodeDialog.tsx`.
- GraphCanvas.tsx **1120 → 800 lines**; all behavioral invariants preserved (focus/reveal early-returns, rAF fit deferral, `.filtered-out` marking, module-scope autoZoomHold).
- Note: further reduction below <350 is deliberately deferred to plans 12-13 (scene reducer fold deletes filterState/focusReducer from this file) and 12-14 (adapter unification collapses the elements useMemo).

**Task 4 — App.tsx decomposition (THERMO-P0-02 + P2-07)**
- NEW `hooks/useWorkspaceScene.ts`: activeView mapping, base/focus DTO fetches, expansion records, mergedVisualization useMemo, and the **THERMO-P2-07 race guard** (stale expansion responses dropped when series/boundary changed in-flight).
- NEW `hooks/useWorkspaceNavigation.ts`: view switch, four-tab hierarchy, nested modes, palette state.
- App.tsx **1128 → ~1017 lines**; scene/navigation logic out of the component. Render-phase `setActiveGraph` mutation intentionally NOT touched here — it is PROB-09/#74's documented guarded pattern (React 19 sanctioned alternative, comment at its site) and its removal belongs with 12-13's scene-reducer fold.

## Verification
- `NODE_ENV=test CI=1 npm run test` → **44 files / 404 tests passed**
- `npm --prefix frontend run build` (tsc strict) → 0 errors
- Per-task atomic commits; no STATE/ROADMAP/config edits.

## Self-Check: PASSED

Key files: components/layout/{ResizableRail,AppIcons}.tsx · components/dialogs/{CreateRelationshipDialog,CreateCustomNodeDialog}.tsx · components/detail/tabs/* · components/graph/useCytoscapeLayout.ts · hooks/{useWorkspaceScene,useWorkspaceNavigation}.ts
