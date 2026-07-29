---
phase: 02-polished-cytoscape-graph-experience
plan: 04
subsystem: ui
tags: [vitest, react-testing-library, security-audit, vite, cytoscape]

requires:
  - phase: 02-polished-cytoscape-graph-experience (Plans 01-03)
    provides: full end-to-end product experience (tracer, cose-bilkent canvas + overlay states, tabbed DetailPanel/StructuralEdgeCard)
provides:
  - Dedicated useWatchProgress unit tests (hydration guard, corruption fallback, same-episode no-op) independent of App.test.tsx's happy path
  - Dedicated ConfirmAdvanceModal component tests (forward/backward copy, Cancel/Confirm callback wiring)
  - Tree-wide grep audits proving the two highest-severity threat mitigations hold across all of frontend/src, not just the files that introduced them
  - 02-VALIDATION.md Per-Task Verification Map completed, nyquist_compliant/wave_0_complete set true
  - A completed conversational Definition-of-Done demo UAT against the live backend
  - A real bug found and fixed during that UAT: GraphCanvas.tsx's unmemoized `elements` prop was causing cose-bilkent layout thrashing/mis-fit
  - frontend/vite.config.ts dev-server proxy for /api/* -> the FastAPI backend (was silently missing; API calls returned Vite's own index.html)
affects: []

tech-stack:
  added: []
  patterns:
    - "renderHook + sessionStorage seeding to unit-test a hook's hydration path independent of any component that consumes it"
    - "useMemo around a pure mapping function (graphToElements) whenever its output is handed to a library (react-cytoscapejs) that re-triggers expensive async work on prop-identity change"

key-files:
  created:
    - frontend/src/hooks/useWatchProgress.test.ts
    - frontend/src/components/episode/ConfirmAdvanceModal.test.tsx
  modified:
    - .planning/phases/02-polished-cytoscape-graph-experience/02-VALIDATION.md
    - frontend/src/components/graph/GraphCanvas.tsx (useMemo fix, found during manual UAT)
    - frontend/vite.config.ts (added /api dev proxy, found during manual UAT)

key-decisions:
  - "GraphCanvas.tsx's `elements` array is now memoized via useMemo(() => graphToElements(graph), [graph]) rather than recomputed inline every render, so its reference is stable across unrelated parent re-renders. react-cytoscapejs re-applies its declarative layout whenever the elements prop reference changes, so the previous unmemoized version restarted the async cose-bilkent layout on every unrelated re-render, racing with itself and occasionally locking cy.fit()'s zoom onto a mid-computation snapshot."
  - "vite.config.ts gained a server.proxy entry for /api -> http://127.0.0.1:8000. Without it, relative fetch('/api/...') calls in dev silently returned Vite's own index.html (200 OK, wrong content-type) instead of reaching the backend, since nothing in the repo previously routed /api dev traffic anywhere."
  - "The manual Definition-of-Done UAT (Task 2's blocking checkpoint) was carried out via Chrome browser automation in the same session rather than deferred to a separate human pass, since the orchestrating session already had a live backend and browser tooling available; the user reviewed and accepted the reported results."

requirements-completed: [UI-05]

coverage:
  - id: D1
    description: "useWatchProgress's sessionStorage hydration guard never opens ConfirmAdvanceModal on remount, a corrupted value falls back to the empty state without throwing, and same-episode reselection is a no-op"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useWatchProgress.test.ts (12 tests: valid hydration, corrupted JSON, visibleUntilOrder 0/negative/non-integer/missing, empty seriesId, same-episode no-op)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ConfirmAdvanceModal renders exact locked forward/backward copy and wires Cancel/Confirm callbacks correctly"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/episode/ConfirmAdvanceModal.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "No component in frontend/src uses dangerouslySetInnerHTML, and no component client-side filters by visible_from_order"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "grep audit across frontend/src for dangerouslySetInnerHTML (zero matches) and for visible_from_order filter/exclude patterns in graphElements.ts/GraphCanvas.tsx (zero matches; one explanatory comment only)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full test suite (all 4 plans together for the first time), build, and lint all pass in a single run"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "npm run test -- --run (6 files, 25 tests, all pass); npm run build && npm run lint (both exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Conversational UAT confirms the full Definition-of-Done demo script end-to-end against the live backend"
    requirement: "UI-05"
    verification:
      - kind: e2e
        ref: "Manual browser walkthrough (2026-07-29): Dexter/S01E01 select, character + claim-backed edge inspection (tabbed Sheet), structural edge (StructuralEdgeCard, no tabs), advance-to-S01E02 confirmation modal, new S01E02 content appears post-confirm, no console errors"
        status: pass
    human_judgment: true
    rationale: "Cross-cutting UX/visual flow spanning graph, modal, and detail panel together, run once as a human-verify checkpoint and reviewed/accepted by the user rather than re-verified by a second independent pass."

duration: ~40min (Task 1 + automated Task 2 sub-checks by executor) + ~1.5hr (environment debugging + manual UAT + bug fix, orchestrator session)
completed: 2026-07-29
status: complete
---

# Phase 2 Plan 04: Nyquist Validation Gaps, Threat-Mitigation Audit, and Demo UAT Summary

**Closed the remaining Nyquist coverage gaps (useWatchProgress hydration/corruption/no-op edge cases, ConfirmAdvanceModal copy variants), ran a tree-wide grep audit proving the phase's two highest-severity threat mitigations hold across all of frontend/src, and completed the Definition-of-Done conversational UAT against the live backend — finding and fixing a real cose-bilkent layout-thrashing bug and a missing dev-server API proxy along the way.**

## Performance

- **Duration:** ~40 min (Task 1 + Task 2's four automated sub-checks, executor) + ~1.5 hr (dev-environment debugging, manual UAT, bug fix — orchestrator session)
- **Completed:** 2026-07-29
- **Tasks:** 2 (Task 1 fully automated; Task 2's checkpoint required a human-driven manual UAT pass)
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `useWatchProgress.test.ts`: 12 passing tests covering hydration-never-opens-modal, corrupted-JSON fallback, all four malformed-`visibleUntilOrder` shapes, and the same-episode no-op edge case — none of which App.test.tsx's happy path alone exercised.
- `ConfirmAdvanceModal.test.tsx`: forward/backward copy variants and Cancel/Confirm callback wiring, independently verified.
- Grep audits: zero `dangerouslySetInnerHTML` matches anywhere in `frontend/src`; zero client-side `visible_from_order` filter/exclude patterns in `graphElements.ts`/`GraphCanvas.tsx` (one harmless explanatory comment only).
- Full suite (6 files, 25 tests), build, and lint all green together for the first time across all four Phase 2 plans.
- `02-VALIDATION.md` completed: Per-Task Verification Map filled in, `nyquist_compliant: true`, `wave_0_complete: true`, `status: validated`.
- Completed the manual Definition-of-Done demo UAT via live browser automation, finding and fixing two real issues along the way (see Deviations).

## Task Commits

1. **Task 1: Dedicated useWatchProgress and ConfirmAdvanceModal edge-case tests** — `70a9c66` (feat)
2. **Task 2 (partial, automated sub-checks 1-4): 02-VALIDATION.md Per-Task Verification Map** — `ab270f7` (docs, WIP)
3. **Bug fix found during Task 2's manual UAT: GraphCanvas.tsx layout-thrashing fix** — this commit (fix)
4. **Bug fix found during Task 2's manual UAT: vite.config.ts /api dev proxy** — this commit (fix)

**Plan metadata:** this commit (`docs(02-04): complete plan`)

## Files Created/Modified

- `frontend/src/hooks/useWatchProgress.test.ts` — hydration-guard, corruption-fallback, same-episode no-op unit tests
- `frontend/src/components/episode/ConfirmAdvanceModal.test.tsx` — forward/backward copy and confirm/cancel callback tests
- `.planning/phases/02-polished-cytoscape-graph-experience/02-VALIDATION.md` — Per-Task Verification Map completed, frontmatter set to validated/nyquist_compliant/wave_0_complete
- `frontend/src/components/graph/GraphCanvas.tsx` — `elements` memoized via `useMemo(() => graphToElements(graph), [graph])`
- `frontend/vite.config.ts` — added `server.proxy` routing `/api` to `http://127.0.0.1:8000`

## Decisions Made

- Treated the manual demo UAT as completable within this session via Chrome browser automation rather than deferring it to a separate human-only pass, since a live backend and browser tooling were already available; results were reported to and accepted by the user.
- Fixed the `GraphCanvas.tsx` layout bug in place rather than filing it as a deferred issue, since it directly blocked the checkpoint's own demo script from being visually verifiable.
- Left `.planning/config.json`'s unrelated `_auto_chain_active` diff and the untracked `.claude/` directory (project skill installs) untouched — out of scope for this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] GraphCanvas.tsx `elements` prop not memoized, causing cose-bilkent layout thrashing**
- **Found during:** Task 2's manual Definition-of-Done demo UAT (sub-check 5)
- **Issue:** `const elements = graphToElements(graph)` was computed inline on every render, producing a new array/object identity each time even when `graph` itself hadn't changed. `react-cytoscapejs` re-applies its declarative `layout` prop whenever the `elements` prop reference changes, so any unrelated parent re-render restarted the async `cose-bilkent` layout mid-flight. Two overlapping layout runs raced with each other, and whichever `fit()` call landed last could lock the viewport onto a mid-computation snapshot — visually, this showed up as either all nodes crushed into a tiny overlapping cluster in one corner, or a single node zoomed in enormously, depending on timing.
- **Fix:** Wrapped the computation in `useMemo(() => graphToElements(graph), [graph])` so the reference is stable across renders and only changes when a genuinely new graph is fetched.
- **Files modified:** `frontend/src/components/graph/GraphCanvas.tsx`
- **Verification:** `tsc -b` clean, all 25 tests still pass, and manual re-verification showed the canvas correctly self-fitting within a few seconds of `cose-bilkent`'s convergence on every fresh load and every episode-boundary change, with no manual zoom/scroll needed.
- **Committed in:** this plan's commit

**2. [Rule 1 - Bug] Missing Vite dev-server proxy for /api**
- **Found during:** Task 2's manual Definition-of-Done demo UAT, before sub-check 5 could even begin
- **Issue:** `frontend/vite.config.ts` had no `server.proxy` entry. Relative `fetch('/api/series')` calls from the browser were served by Vite's own dev server (which has no route matching `/api/series`) and fell through to returning `index.html` with an HTTP 200 status — `apiFetch`'s `!res.ok` check never triggered (status was 200), so `res.json()` threw a silent JSON-parse error inside the fetch hook, leaving the series dropdown permanently empty with no visible error.
- **Fix:** Added `server.proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } }` to `vite.config.ts`.
- **Files modified:** `frontend/vite.config.ts`
- **Verification:** `fetch('/api/series')` from the browser now returns real JSON from the backend; the full demo script ran successfully end-to-end afterward.
- **Committed in:** this plan's commit

---

**Total deviations:** 2 auto-fixed (both bugs, both found only because the manual UAT was actually carried through rather than skipped)
**Impact on plan:** Both were necessary for the checkpoint's own demo script to be verifiable at all. No scope creep — the graph engine/copy/data itself needed no changes; both issues were plumbing (dev proxy) and a stale-render fix (memoization) already in the plan's affected files.

## Issues Encountered

- Before either app bug could even be reached, three environment problems had to be resolved (none were Phase 2 code defects): a stray dev server from an unrelated old `hdgrafcehennemi` checkout was bound to port 5173 (killed); Neo4j and the backend `uvicorn` process were not running (started); Vite's cold-start dependency-discovery caused several rapid full-page reloads early in the session (a known, harmless Vite quirk that settles on its own once all lazily-discovered dependencies — Radix Tabs/Dialog, cytoscape-cose-bilkent — are pre-bundled).

## User Setup Required

None for future sessions — Neo4j (docker-compose) and the backend (`uv run uvicorn backend.app.main:app`) must be running before `npm run dev`, same as documented in Phase 1's INFRA-01 verification; this was just not currently running when this plan's UAT began.

## Next Phase Readiness

- UI-05 is satisfied: build, lint, and the full 25-test component suite pass together, the two highest-severity threat mitigations are grep-verified tree-wide, and the full Definition-of-Done demo UAT passed against the live backend after the two bugs above were fixed.
- Phase 2 is now execution-complete (4/4 plans). All of UI-01 through UI-05 are satisfied.
- No blockers for Phase 3 (User Notes and Manual Editing) — `UserNote`'s dashed-border node styling is already reserved in `graphStylesheet.ts`, and the `automatic`-origin system-indicator glyph groundwork is deferred to Phase 5 per `02-UI-SPEC.md`, both as previously documented (not new deferrals from this plan).

---
*Phase: 02-polished-cytoscape-graph-experience*
*Completed: 2026-07-29*

## Self-Check: PASSED

All listed created files verified present on disk; `useWatchProgress.test.ts`/`ConfirmAdvanceModal.test.tsx` commit `70a9c66` and `02-VALIDATION.md` WIP commit `ab270f7` verified present in `git log`.
