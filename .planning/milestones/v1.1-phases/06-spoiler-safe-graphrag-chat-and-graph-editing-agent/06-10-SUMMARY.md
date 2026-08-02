---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "10"
subsystem: ui
tags: [typescript, react, cytoscape, vitest, chat, graph-focus, watch-progress]

# Dependency graph
requires:
  - phase: 06-08
    provides: "Typed chat/progress API clients (api/progress.ts's getProgress/updateProgress) and useChatMessages' citations/graphFocus fields"
  - phase: 06-09
    provides: "CitationChip's onShowInGraph/onOpenDetail callback props, ChatPanel/MessageList prop threading down to CitationChip"
provides:
  - "frontend/src/hooks/useWatchProgress.ts — backend-authoritative on hydration (getProgress), confirmChange() awaits updateProgress() before committing local state (RAG-01 complete on the frontend)"
  - "frontend/src/components/graph/GraphCanvas.tsx — externally-driven focusedElementIds prop, extending the existing internal tap-to-select .selected-dominant/.faded mechanism without forking it"
  - "frontend/src/components/graph/GraphFocusIndicator.tsx — canvas overlay pill announcing an active chat-driven graph_focus highlight with a Clear action"
  - "App.tsx wiring: CitationChip 'Show in graph' -> graphFocus state -> GraphCanvas; citation body click -> Inspector mode + resource selection; progress-decrease auto-clears a graph focus referencing a now-hidden element"
affects: [06-11]

# Actuals (#2632)
actuals:
  tokens: 12300
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GraphCanvas's focusedElementIds effect is a second, independent prop-driven effect (useGraph.ts-style) alongside the existing tap/hover event-listener registration — both write to the same .selected-dominant/.faded classes and never fight each other, since a manual tap always fully reassigns them"
    - "App.tsx's progress-decrease-clears-stale-focus logic uses the codebase's established 'adjust state during render, comparing a state copy of the previous key' pattern (useGraph.ts/ChatPanel.tsx) instead of an effect + setState — the key is a joined node/edge-id string computed from the freshly-fetched GraphResponse"
    - "useWatchProgress's mount-time hydration effect and confirmChange() both prefer the backend's echoed/fetched value over sessionStorage, treating sessionStorage strictly as a loading-state placeholder / optimistic cache from this point on"

key-files:
  created:
    - frontend/src/components/graph/GraphFocusIndicator.tsx
  modified:
    - frontend/src/hooks/useWatchProgress.ts
    - frontend/src/hooks/useWatchProgress.test.ts
    - frontend/src/components/graph/GraphCanvas.tsx
    - frontend/src/components/graph/GraphCanvas.test.tsx
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx

key-decisions:
  - "confirmChange() prefers the backend's own echoed UserSeriesProgress (from updateProgress's response) over the locally-known nextOrder when the write succeeds, falling back to the optimistic nextOrder only if the backend call rejects — maximally backend-authoritative without ever blocking ConfirmAdvanceModal's confirm action on network success"
  - "GraphFocusIndicator's count (\"Highlighting {N} from chat\") is the total requested target count (nodeIds.length + edgeIds.length) from focusedElementIds, not the post-filter resolved-element count — matches the citation's own related_node_ids/related_edge_ids size the user just clicked, and keeps the count independent of the (architecturally-should-never-happen) silent-drop path"
  - "handleOpenDetail (citation chip body click) prefers a related node over a related edge when both are present, and does nothing if neither resolves against the currently-fetched graph — defensive per RAG-08, since an unresolvable citation target should be architecturally impossible"
  - "Combined Task 2 and Task 3 into a single commit (see Deviations) — both modify the same App.tsx region (graphFocus state + its render-time reconciliation) and were implemented together in one working pass rather than two isolated diffs"

requirements-completed: [RAG-01, RAG-17]

coverage:
  - id: D1
    description: "confirmChange() awaits updateProgress() before committing local state (preferring the backend's echoed value); on mount, getProgress() overrides a conflicting sessionStorage value; a failed getProgress()/updateProgress() call falls back to the optimistic/placeholder value without crashing; requestChange/confirmChange/cancelChange's signatures and ConfirmAdvanceModal's existing tests are unchanged"
    requirement: RAG-01
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useWatchProgress.test.ts (16 tests, incl. 3 new backend-wiring tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/episode/ConfirmAdvanceModal.test.tsx (4 pre-existing tests, unmodified, still pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "GraphCanvas's focusedElementIds prop applies .selected-dominant to every named node/edge and .faded to everything else, clears both on null, uses cy.fit(focused, 48) matching GraphControls' fit-to-view padding, silently drops an unresolvable id, and does not break a direct tap-to-select immediately after a focus update"
    requirement: RAG-17
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#focusedElementIds (06-10, RAG-17) (5 tests) + pre-existing 7 tests unmodified"
        status: pass
    human_judgment: false
  - id: D3
    description: "GraphFocusIndicator renders 'Highlighting {N} from chat' only when a focus is active, with a working Clear action wired to App.tsx's clearFocus"
    requirement: RAG-17
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#GraphFocusIndicator (06-10, RAG-17) (1 test)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Clicking a citation chip's 'Show in graph' icon sets App.tsx's graph focus without switching panel mode; clicking the chip body switches to Inspector and selects the referenced node"
    requirement: RAG-17
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#citation graph-focus wiring (06-10, RAG-17) (2 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A progress decrease that hides a currently-focused node clears the graph focus automatically (reusing the same clearFocus function the manual Clear action calls); a progress decrease that doesn't affect any focused element leaves the focus untouched"
    requirement: RAG-17
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#progress-decrease clears stale graph focus (06-10 Task 3) (2 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full frontend suite (146 tests across 21 files) passes; npx tsc -b --noEmit clean; npm run build clean"
    verification:
      - kind: other
        ref: "cd frontend && npx vitest run (146/146 pass); npx tsc -b --noEmit (0 errors); npm run build (clean)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 10: useWatchProgress backend wiring + GraphCanvas focusedElementIds + GraphFocusIndicator + citation wiring Summary

**`useWatchProgress` now persists/hydrates through the backend progress endpoint (RAG-01 complete on the frontend); `GraphCanvas` gained its first externally-driven prop (`focusedElementIds`) plus a `GraphFocusIndicator` overlay, wired end-to-end from a chat citation's "Show in graph"/chip-body click through `App.tsx`, including automatic stale-focus clearing on a progress decrease (RAG-17).**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3
- **Files created:** 1 · **Files modified:** 6

## Accomplishments

- `useWatchProgress.ts`: `confirmChange()` now awaits `updateProgress(seriesId, nextOrder)` (from `api/progress.ts`, built in 06-08) before committing local state, preferring the backend's own echoed value on success and falling back to the optimistic value on failure — `requestChange`/`confirmChange`/`cancelChange`'s exported signatures are byte-for-byte unchanged, so `ConfirmAdvanceModal`'s existing UX/tests are untouched. A mount-time effect calls `getProgress()` for a sessionStorage-known `seriesId` and overrides `confirmedOrder` from the backend response, treating sessionStorage strictly as a loading-state placeholder from this point forward (never re-marked authoritative on a failed fetch).
- `GraphCanvas.tsx`: new `focusedElementIds: {nodeIds, edgeIds} | null` prop, applied/cleared in a second, independent `useEffect` alongside the existing tap/hover listener registration — extends rather than forks the `.selected-dominant`/`.faded` mechanism the internal `cy.on('tap', ...)` handlers already own. Documents the deliberate supersession of `03.1-UI-SPEC.md`'s "at most one node" constraint. Uses `cy.fit(focused, 48)`, matching `GraphControls.tsx`'s fit-to-view padding exactly. Unresolvable ids are silently dropped via `cy.getElementById(id)`/length checks, never thrown.
- New `GraphFocusIndicator.tsx`: `fixed top-4 left-4 z-[60]` overlay pill ("Highlighting {N} from chat" + inline "Clear" text action), matching `GraphLegend`'s collapsed-pill visual treatment; mounted by `GraphCanvas.tsx` whenever `focusedElementIds` is non-null.
- `DetailPanel.tsx` forwards `onShowInGraph`/`onOpenDetail` into `ChatPanel` (already accepted there since 06-09, previously unwired).
- `App.tsx`: owns `graphFocus` state independent of `selectedElement`/`panelMode`. `handleShowInGraph` sets the focus without touching panel mode; `handleOpenDetail` switches to Inspector mode and selects the referenced node (preferring a node over an edge when both are present in a citation's `related_node_ids`/`related_edge_ids`). A render-time reconciliation (the codebase's established "adjust state when a key changes" pattern) clears `graphFocus` whenever a freshly-fetched graph (e.g. after a progress decrease) no longer contains every currently-focused id — reusing `handleClearFocus`, never a second clearing code path.

## Task Commits

1. **Task 1: useWatchProgress backend wiring** - `9edea30` (feat)
2. **Task 2 + Task 3: GraphCanvas focusedElementIds/GraphFocusIndicator/citation wiring + progress-decrease stale-focus clearing** - `7de0551` (feat — see Deviations for why both tasks landed in one commit)

**Plan metadata:** committed separately after this summary (docs commit).

## Files Created/Modified

- `frontend/src/hooks/useWatchProgress.ts` - backend-authoritative hydration + `confirmChange()` awaiting `updateProgress()`
- `frontend/src/hooks/useWatchProgress.test.ts` - 4 new tests (confirm-awaits-backend, hydration-overrides-sessionStorage, hydration-fetch-failure-fallback, cancelChange-doesn't-call-backend) alongside all 7 pre-existing tests unmodified
- `frontend/src/components/graph/GraphCanvas.tsx` - `focusedElementIds`/`onClearFocus` props, focus-highlight effect, `GraphFocusIndicator` mount
- `frontend/src/components/graph/GraphCanvas.test.tsx` - enhanced fake-cytoscape stub (persistent element/class registry, `getElementById`/`collection`/`elements`/`fit`) + 6 new focus/indicator tests, all 7 pre-existing tests unmodified
- `frontend/src/components/graph/GraphFocusIndicator.tsx` - new overlay pill component
- `frontend/src/components/detail/DetailPanel.tsx` - `onShowInGraph`/`onOpenDetail` props threaded into `ChatPanel`
- `frontend/src/App.tsx` - `graphFocus` state, `handleShowInGraph`/`handleOpenDetail`/`handleClearFocus`, progress-decrease reconciliation, prop wiring to `GraphCanvas`/`DetailPanel`
- `frontend/src/App.test.tsx` - 4 new tests (citation "Show in graph"/chip-body wiring, progress-decrease clears/preserves stale focus), all 9 pre-existing tests unmodified

## Decisions Made

- `confirmChange()` prefers the backend's own echoed `UserSeriesProgress` over the locally-known `nextOrder` when `updateProgress()` succeeds, falling back to the optimistic value only on failure — maximizes backend-authoritativeness without blocking the confirm action on network success.
- `GraphFocusIndicator`'s count is the raw requested-target count (`nodeIds.length + edgeIds.length`), not the post-filter resolved-element count, matching what the citation itself carried.
- `handleOpenDetail` prefers a related node over a related edge when a citation carries both, silently no-ops if neither resolves (defensive, RAG-08).
- Task 2 and Task 3 landed in a single commit (`7de0551`) rather than two — both modify the same `App.tsx` `graphFocus`-adjacent region and were authored together in one working pass; documented as a deviation below rather than retroactively split (which would have required fragile partial-file staging of an already-committed diff).

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1/2/3 fixes were required; all three tasks' `<verify>` commands passed on the first implementation pass (aside from one iteration to correct a test-double bug, see Issues Encountered).

### Process deviation (not a Rule 1-4 case)

**1. Task 2 and Task 3 committed together, not atomically per-task**
- **Found during:** Task 3 (progress-decrease stale-focus clearing)
- **Issue:** Task 3's action text ("add an effect keyed on the resolved visibleUntilOrder/graph data...") and Task 2's `App.tsx` wiring (graphFocus state, handleShowInGraph/handleOpenDetail/handleClearFocus) are both small, tightly-coupled edits to the exact same region of `App.tsx` — implemented together in one working pass rather than as two isolated diffs.
- **Resolution:** Both tasks' code landed in commit `7de0551`. No functional impact — every truth/acceptance-criterion for both tasks is independently verified by its own dedicated test group (`GraphCanvas.test.tsx`'s `focusedElementIds`/`GraphFocusIndicator` describes for Task 2's GraphCanvas half; `App.test.tsx`'s `citation graph-focus wiring` describe for Task 2's App.tsx half; `App.test.tsx`'s `progress-decrease clears stale graph focus` describe for Task 3).

---

**Total deviations:** 0 auto-fixed, 1 process deviation (commit granularity, no functional/scope impact).
**Impact on plan:** None on correctness or scope — only the per-task commit boundary, documented here for the record.

## Issues Encountered

- `GraphCanvas.test.tsx`'s original fake-cytoscape stub only implemented `on`/`container`, insufficient to exercise real `.selected-dominant`/`.faded` class application. Extended it with a persistent (across re-renders), module-scoped element/class registry backing `getElementById`/`collection`/`elements`/`fit`, modeled on real cytoscape.js semantics (`.merge()` mutates the calling collection and returns it; `.difference()` is immutable) — verified this distinction mattered when the first draft's `addClass`/`removeClass` fakes treated a space-separated class string (`'selected-dominant faded edge-active'`, exactly how the tap handlers and the new focus effect call them) as one literal class name instead of splitting it, which initially failed the null-transition test; fixed by splitting on whitespace before add/delete, matching cytoscape's real multi-class string support.
- Pre-existing project-wide lint debt is unaffected: `GraphCanvas.tsx`'s 2 pre-existing findings (`setEpisodeId` in an effect, one `any` in `CreateCustomNodeDialog`'s catch) and `DetailPanel.tsx`'s 9 pre-existing `react-hooks/refs`/`preserve-manual-memoization` findings (documented in 06-09-SUMMARY.md) are identical before/after this plan's edits — confirmed via `eslint` on the pre-plan commit vs. the post-plan file.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-11 (ChangeSetCard) can build on this plan's `App.tsx` `graphFocus`/citation-wiring pattern if it needs to highlight a ChangeSet's affected elements similarly (not required by 06-11's own scope, but the mechanism is now proven end-to-end).
- Known limitation carried over from 06-09 (not addressed here, out of this plan's declared scope): Chat mode is still inaccessible while a structural edge is selected (`App.tsx` renders `StructuralEdgeCard` instead of `DetailPanel` for claim_id === null edges) — citations in this plan's fixtures never reference structural edges, so this didn't surface, but a future citation pointing at a structural edge via `handleOpenDetail` would hit the same pre-existing limitation.
- No blockers.

## Self-Check: PASSED

- FOUND: frontend/src/components/graph/GraphFocusIndicator.tsx
- FOUND: frontend/src/hooks/useWatchProgress.ts
- FOUND: frontend/src/components/graph/GraphCanvas.tsx
- FOUND: frontend/src/components/detail/DetailPanel.tsx
- FOUND: frontend/src/App.tsx
- FOUND commit 9edea30
- FOUND commit 7de0551

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*
