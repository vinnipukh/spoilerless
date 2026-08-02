---
phase: 02-polished-cytoscape-graph-experience
plan: 01
subsystem: ui
tags: [react, cytoscape, vitest, react-testing-library, shadcn, tailwind, sessionstorage]

# Dependency graph
requires:
  - phase: 01-backend-graph-foundation
    provides: verified spoiler-safe GET /api/series, GET /api/series/{id}/episodes, GET /api/series/{id}/graph?visible_until_order=N
provides:
  - Product App.tsx replacing the Vite starter (UI-01)
  - Typed API client (api/client.ts, api/series.ts, api/graph.ts) mirroring backend/app/domain/{graph,series}.py and backend/app/core/errors.py
  - sessionStorage-backed useWatchProgress hook with hydration guard (D-02) and forward/backward confirmation gating (D-03)
  - Cytoscape rendering (GraphCanvas.tsx + graphElements.ts) with tap-to-select/tap-background-to-clear wiring (D-05)
  - Minimal unified DetailPanel (node/edge inspection, D-06/D-07 split deferred to Plan 03)
  - Vitest + React Testing Library test infrastructure (test/setup.ts, vite.config.ts test block) — first in this repo
  - One passing end-to-end component test (App.test.tsx) covering the full select-confirm-fetch-render-inspect flow
affects: [02-02, 02-03]

# Tech tracking
tech-stack:
  added: [cytoscape-cose-bilkent, "@types/react-cytoscapejs", vitest, "@testing-library/react", "@testing-library/jest-dom", "@testing-library/user-event", jsdom]
  patterns:
    - "status-union fetch hooks ({status:'idle'|'loading'|'error'|'success'}) over api/* functions"
    - "React 'adjust state when a prop changes' pattern (compare current key to a useState-tracked previous key, setState during render) instead of synchronous setState in a useEffect body — required by this project's react-hooks/set-state-in-effect and react-hooks/refs lint rules"
    - "mocking react-cytoscapejs in RTL tests via a useRef-backed stub component that captures GraphCanvas's real cy.on('tap', ...) registrations, since jsdom has no real canvas 2D context for per-node hit-testing"

key-files:
  created:
    - frontend/src/types/graph.ts
    - frontend/src/types/series.ts
    - frontend/src/types/cytoscape-cose-bilkent.d.ts
    - frontend/src/api/client.ts
    - frontend/src/api/series.ts
    - frontend/src/api/graph.ts
    - frontend/src/hooks/useSeries.ts
    - frontend/src/hooks/useEpisodes.ts
    - frontend/src/hooks/useGraph.ts
    - frontend/src/hooks/useWatchProgress.ts
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/components/episode/SeriesSelect.tsx
    - frontend/src/components/episode/EpisodeSelector.tsx
    - frontend/src/components/episode/ConfirmAdvanceModal.tsx
    - frontend/src/components/graph/graphElements.ts
    - frontend/src/components/graph/GraphCanvas.tsx
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/test/setup.ts
    - frontend/src/test/fixtures/graphResponse.ts
    - frontend/src/App.test.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/App.css
    - frontend/package.json
    - frontend/vite.config.ts
    - .planning/phases/02-polished-cytoscape-graph-experience/02-UI-SPEC.md

key-decisions:
  - "Backward-copy variant ('Rewatch S01E0X?') added to ConfirmAdvanceModal and documented as a new row in 02-UI-SPEC.md's Copywriting Contract table, alongside (not replacing) the locked forward-only row"
  - "GraphCanvas uses the built-in 'cose' layout for this tracer plan; cytoscape-cose-bilkent is registered at module scope but the layout swap to 'cose-bilkent' is Plan 02's scope, per the plan's own explicit scope boundary"
  - "DetailPanel is a single unified Sheet with no Tabs (Overview/Claims/Evidence split and the separate tab-less StructuralEdgeCard for structural edges are Plan 03's scope, per the plan's explicit scope boundary)"

patterns-established:
  - "graphElements.ts: pure GraphResponse -> Cytoscape ElementDefinition[] mapping that reads only already-filtered fields, never re-filtering by visible_from_order (T-02-03 mitigation)"
  - "useWatchProgress.ts: sessionStorage hydration happens via a lazy useState initializer only, bypassing requestChange/confirmChange entirely, so restoring from storage can never open ConfirmAdvanceModal (Pitfall 5)"

requirements-completed: [UI-01, UI-02]

coverage:
  - id: D1
    description: "App.tsx replaces the Vite starter and loads series/episode/graph data from the backend (UI-01)"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#App > shows the empty state and fires no /graph request until a series and episode are confirmed"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#App > runs select -> confirm -> fetch -> render -> inspect end-to-end, and gates cancel/forward/backward changes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Watch-progress changes (forward and backward) are gated behind a confirmation modal; sessionStorage restores state without re-prompting (mechanical core of UI-02)"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#App > runs select -> confirm -> fetch -> render -> inspect end-to-end, and gates cancel/forward/backward changes"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#App > restores confirmed state from sessionStorage on mount without opening the confirmation modal"
        status: pass
    human_judgment: false
  - id: D3
    description: "Manual npm run dev smoke test against the live backend — Cytoscape canvas renders 11 elements at S01E01 and DetailPanel opens on node click, visually confirmed in a real browser"
    verification: []
    human_judgment: true
    rationale: "This autonomous execution had no browser-automation tool available in-session; the automated component test (D1) exercises the identical GraphCanvas/DetailPanel code paths end-to-end via a jsdom-compatible stub, and the live backend was independently curl-verified to return the exact fixture shape (11 nodes/6 edges/4 claims/1 source/3 evidence) this test's fixture mirrors, but a human should still confirm the real Cytoscape canvas renders/looks correct in an actual browser before sign-off"

# Metrics
duration: ~45min (this resumed session; prior session's steps 1-12 duration not separately tracked)
completed: 2026-07-29
status: complete
---

# Phase 2 Plan 1: End-to-End Select-Confirm-Fetch-Render-Inspect Tracer Summary

**React/Vite frontend now composes a real product layout (AppShell > SeriesSelect/EpisodeSelector > ConfirmAdvanceModal > GraphCanvas > DetailPanel) driven by a typed API client and a sessionStorage-backed watch-progress hook, replacing the Vite starter entirely and rendering the spoiler-safe graph from the verified Phase 1 backend in Cytoscape.**

## Performance

- **Duration:** ~45 min (this session, resuming from a prior session cut off mid-task by a usage limit)
- **Completed:** 2026-07-29T12:00Z
- **Tasks:** 1 (Task 2 of the plan — Task 1 was the package-legitimacy checkpoint, already approved in the prior session)
- **Files modified:** 26 (20 created, 6 modified)

## Important Context: Resumed Execution

**This plan's Task 2 was started by a prior executor agent that was cut off mid-task by a session usage limit — not a task failure.** Steps 1-12 of the task's 19-step action list (dependency installs, Vitest config, ambient types, `types/graph.ts`/`types/series.ts`, the API client, the three data-fetching hooks, `useWatchProgress`, `SeriesSelect`/`EpisodeSelector`/`ConfirmAdvanceModal`) were already present and uncommitted in the working tree when this session began. Nothing had been committed. This session verified each of those files against the plan (field names, exports, behavior) before building on top of them, found them complete and correct as-is (aside from the deviations below, discovered while finishing the remaining steps), completed steps 13-19, ran the full verification suite, and made one atomic commit covering the entire task.

## Accomplishments
- `App.tsx` fully replaced (no Vite-starter markup/imports/assets remain); composes the real product layout end-to-end.
- Cytoscape canvas (`GraphCanvas.tsx` + `graphElements.ts`) renders the fetched graph and wires tap-to-select/tap-background-to-clear (D-05), with `cytoscape-cose-bilkent` registered for Plan 02's later layout swap.
- `DetailPanel.tsx` shows selected node/edge fields or the locked "Select a node to see details." placeholder.
- `ConfirmAdvanceModal.tsx` gates every watch-progress change (forward and backward) with distinct copy per direction (D-03); the backward variant is documented as an addition in `02-UI-SPEC.md`.
- Vitest + React Testing Library stood up from scratch (no test infra existed before this plan) with a hand-written `GraphResponse` fixture matching the live S01E01 shape (11 nodes/6 edges/4 claims/1 source/3 evidence — independently curl-verified against the running backend).
- `App.test.tsx` passes 3/3: empty-state-no-fetch, the full select→confirm→fetch→render→inspect flow with cancel/forward/backward gating, and sessionStorage restore without modal re-trigger.

## Task Commits

Task 2 was completed and committed as a single atomic commit (steps 1-12 from the prior session plus steps 13-19 from this session, since nothing from the prior session had been committed yet):

1. **Task 2: End-to-end "select series to inspect element" - one path only** - `6ce15a1` (feat)

_Task 1 (package-legitimacy checkpoint) was approved in the prior session; no separate commit exists for it since it gates installs performed as part of Task 2._

**Plan metadata:** pending (this SUMMARY's commit)

## Files Created/Modified

- `frontend/src/types/graph.ts` / `series.ts` - types mirroring `backend/app/domain/{graph,series}.py` field-for-field (already correct from prior session; verified, not modified)
- `frontend/src/types/cytoscape-cose-bilkent.d.ts` - ambient module declaration (already correct)
- `frontend/src/api/client.ts` / `series.ts` / `graph.ts` - typed fetch wrappers + `{code,message}` error envelope (already correct)
- `frontend/src/hooks/useSeries.ts` / `useEpisodes.ts` / `useGraph.ts` - status-union data-fetching hooks (rewritten this session — see Deviations)
- `frontend/src/hooks/useWatchProgress.ts` - sessionStorage-backed watch-progress state (already correct)
- `frontend/src/components/episode/SeriesSelect.tsx` / `EpisodeSelector.tsx` - shadcn `Select` compositions (fixed this session — see Deviations)
- `frontend/src/components/episode/ConfirmAdvanceModal.tsx` - forward/backward spoiler-confirmation dialog (already correct)
- `frontend/src/components/graph/graphElements.ts` - GraphResponse -> Cytoscape ElementDefinition[] mapping (new)
- `frontend/src/components/graph/GraphCanvas.tsx` - Cytoscape canvas wrapper with tap wiring (new)
- `frontend/src/components/detail/DetailPanel.tsx` - minimal unified detail Sheet (new)
- `frontend/src/components/layout/AppShell.tsx` - top-bar + content wrapper (new)
- `frontend/src/App.tsx` - rewritten root composition (new)
- `frontend/src/App.css` - emptied of Vite-starter rules (new)
- `frontend/src/test/setup.ts` - jest-dom/vitest matcher types + jsdom/Radix polyfills (extended this session — see Deviations)
- `frontend/src/test/fixtures/graphResponse.ts` - hand-written S01E01 GraphResponse fixture (new)
- `frontend/src/App.test.tsx` - end-to-end component test (new)
- `.planning/phases/02-polished-cytoscape-graph-experience/02-UI-SPEC.md` - added backward-copy-variant row to Copywriting Contract

## Decisions Made
- Reused the single locked "Nothing revealed yet" / "Advance your watch progress to unlock the story." empty-state copy for both the D-01 initial-mount empty state and the (currently unreachable) zero-node-response case, since `02-UI-SPEC.md` only defines one empty-state row and no separate initial-state copy is specified.
- `DetailPanel` is rendered as a persistently-`open`, non-modal (`modal={false}`) `Sheet` rather than toggled open/closed on selection, so the placeholder text is always visible once the graph has rendered — matching the plan's literal wording ("...and the locked placeholder copy...when nothing is selected").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed controlled/uncontrolled Select warning in SeriesSelect/EpisodeSelector**
- **Found during:** Task 2, step 19 (writing `App.test.tsx`)
- **Issue:** Both selects passed `value={value ?? undefined}` (or the string/undefined equivalent), which switches the underlying Radix `Select` from uncontrolled to controlled the first time a real value is selected, triggering React's controlled/uncontrolled console warning.
- **Fix:** Changed both to always pass a defined string (`''` sentinel when nothing is selected) so the component is controlled from the very first render.
- **Files modified:** `frontend/src/components/episode/SeriesSelect.tsx`, `frontend/src/components/episode/EpisodeSelector.tsx`
- **Verification:** Warning no longer appears in test output; `App.test.tsx` still passes 3/3.
- **Committed in:** `6ce15a1` (Task 2 commit)

**2. [Rule 3 - Blocking] Rewrote useSeries/useEpisodes/useGraph to satisfy react-hooks/set-state-in-effect and react-hooks/refs**
- **Found during:** Task 2, final `npm run lint` verification step
- **Issue:** The prior session's hooks called `setState({status:'loading'})` synchronously at the top of each `useEffect` body, which this project's `eslint-plugin-react-hooks@^7.1.1` flags as `react-hooks/set-state-in-effect` (a blocking lint error, not a warning). A first fix attempt using a `useRef` to track "did the fetch key change" also failed a second, stricter rule (`react-hooks/refs` — forbids reading/writing ref `.current` during render).
- **Fix:** Rewrote all three hooks to use React's documented "adjust state when a prop changes" pattern with a **`useState`-tracked previous key** (not a ref) compared during render: when the key changes, `setState` is called directly in the render body (React explicitly supports this for derived-state resets), and the `useEffect` body itself now only ever calls `setState` from its async `.then`/`.catch` callbacks — never synchronously at the top.
- **Files modified:** `frontend/src/hooks/useSeries.ts`, `frontend/src/hooks/useEpisodes.ts`, `frontend/src/hooks/useGraph.ts`
- **Verification:** `npm run lint` exits 0; `npm run test -- --run` still passes 3/3; `npm run build` (which type-checks these files via `tsc -b`) exits 0.
- **Committed in:** `6ce15a1` (Task 2 commit)

**3. [Rule 3 - Blocking] Added jest-dom/vitest typing and jsdom/Radix polyfills to test/setup.ts**
- **Found during:** Task 2, step 19 (writing/running `App.test.tsx`)
- **Issue:** The prior session's `test/setup.ts` imported the bare `@testing-library/jest-dom` entry point, which augments Jest's global namespace, not Vitest's `Assertion` interface — `expect(...).toBeInTheDocument()` would fail `tsc -b` type-checking (which includes `.test.tsx` files per `tsconfig.app.json`'s `"include": ["src"]`). jsdom also lacks `hasPointerCapture`/`setPointerCapture`/`releasePointerCapture`/`scrollIntoView` and `ResizeObserver`, all used internally by the Radix Select/Dialog/Sheet primitives this task's components compose.
- **Fix:** Switched to `import '@testing-library/jest-dom/vitest'` (the subpath that augments Vitest's own `Assertion`/`AsymmetricMatchersContaining` interfaces) and added minimal polyfills for the four pointer/scroll methods plus a `ResizeObserver` stub.
- **Files modified:** `frontend/src/test/setup.ts`
- **Verification:** `npm run build` (tsc -b) exits 0 with no matcher-typing errors; Select/Dialog/Sheet interactions in `App.test.tsx` work under jsdom without throwing.
- **Committed in:** `6ce15a1` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three were necessary for `npm run test`/`npm run build`/`npm run lint` to exit 0 as required by the plan's own `<verify>` block. No scope creep — no behavior beyond the plan's stated 19 action steps was added.

## Issues Encountered
- `react-cytoscapejs` renders to a `<canvas>` with no real 2D context under jsdom (no per-node hit-testing possible). Resolved by mocking `react-cytoscapejs` in `App.test.tsx` with a `useRef`-backed stub component that captures `GraphCanvas`'s real `cy.on('tap', 'node'/'edge', ...)` and background-tap registrations (verified against the real `react-cytoscapejs` source, which calls the `cy` prop on every `componentDidUpdate`, not just mount — the stub had to preserve identity across re-renders to match this) and exposes plain clickable `<button>`/`<div>` stand-ins for "a rendered node/edge" and "an empty patch of canvas" that RTL can query and click.
- A pre-existing, unrelated Vite dev server was found already running on port 5173 from a different project checkout (`hdgrafcehennemi`, not this `hdgraf-frontend` worktree) — serving stale Vite-starter content. This is not part of this task's scope; it was left untouched. This session's own dev-server smoke-test instance (spawned on port 5174 after 5173 conflicted) was stopped after confirming the app served HTTP 200 with no build/transform errors, and the live backend (`localhost:8000`) was independently curl-verified to return exactly the node/edge/claim/source/evidence counts this plan's fixture encodes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The tracer's full select→confirm→fetch→render→inspect path is proven end-to-end against the live backend contract (curl-verified) and covered by an automated component test — a solid foundation for Plan 02 (cose-bilkent layout swap, full node/edge stylesheet, neighbor highlight/fade) and Plan 03 (Overview/Claims/Evidence tabs, StructuralEdgeCard, loading/error states).
- **Recommended before Plan 02 starts:** a human should do a quick manual `npm run dev` + real-browser check (D3 in the coverage block above) — the automated suite proves the logic wiring but not the actual visual Cytoscape render, since that was stubbed out for jsdom compatibility.
- No blockers identified.

---
*Phase: 02-polished-cytoscape-graph-experience*
*Completed: 2026-07-29*

## Self-Check: PASSED

All 9 listed created files verified present on disk; commit `6ce15a1` verified present in `git log --all`.
