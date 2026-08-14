---
phase: 10-polish-finishing-touches
plan: 05
subsystem: ui
tags: [react, tabs, responsive, accessibility, inspector, timeline, mobile, shadcn]

# Dependency graph
requires:
  - phase: 10-polish-finishing-touches
    provides: 10-04 scene reducer/actions + GraphCanvas visualization path + view-scoped positions
provides:
  - Four-tab narrative hierarchy (Story/Characters/Evidence/Advanced) with nested per-tab modes
  - Bidirectional graph/timeline/Inspector selection convergence (no layout calls)
  - Responsive mobile Inspector bottom sheet (half/full heights, drag handle, Escape close, safe-area)
  - 44px mobile touch targets in GraphFilterPanel; zero/one/many copy states
affects: [10-06 expansion entry points, 10-07 Answer Graph, 10-08 benchmarks, 10-10 UAT]

# Actuals (#2632) — pairs with the plan's `estimate` (36000 tokens) on the same scale (chars/4 over the realized diff).
actuals:
  tokens: 19800
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-tab nested mode state (storyMode/characterMode/evidenceMode/advancedMode) — tab switches never reset Filters/camera/selection (D-47)
    - Shared selection only on timeline interactions — Inspector opens, canvas never unmounts/relayouts (D-38)
    - Escape/close funnel through the single onDeselect path (no Radix auto-close; two non-modal sheets coexist)

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/components/timeline/TimelineView.tsx
    - frontend/src/components/timeline/TimelineView.test.tsx
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/components/detail/DetailPanel.test.tsx
    - frontend/src/components/graph/GraphFilterPanel.tsx

key-decisions:
  - "Story rail mounts beside the still-mounted canvas only for story+event_timeline; narrow screens keep one primary region (D-20)."
  - "Mobile Inspector is a bottom sheet with two heights (50vh half / 85vh full) toggled by a 44px drag handle; Escape and the explicit Close Inspector button both funnel through onDeselect (D-42)."
  - "Inspector scope disambiguation: the new top-level tab strip shares labels with DetailPanel inner tabs ('Evidence'), so component tests scope queries to the dialog (within(getByRole('dialog')))."
  - "Answer Graph in this plan is an entry point + notice copy only; functional expansion/Answer Graph work belongs to 10-06/10-07."

patterns-established:
  - "Pattern 1: shared-selection convergence — canvas tap, timeline rail row, and Inspector all mutate one scene selection; no layout calls on selection (graphStubHooks.layoutRuns === 0 assertion)."
  - "Pattern 2: mobile sheet height as local component state with CSS-only effect (max-sm:max-h-[50vh]/[85vh] + transition) — desktop path untouched."
  - "Pattern 3: UI-SPEC copy contract — zero/one/many/loading/error/partial/long-text states asserted in component tests; visual/gesture backstops deferred to 10-10 UAT rows."

requirements-completed: [VIZ-04, VIZ-05]
coverage:
  - id: D1
    description: "Four accessible top tabs (Story default) with nested responsibilities per tab and filters/camera/selection preserved across tab switches"
    requirement: VIZ-04
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#renders four accessible top tabs with Story selected by default"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#exposes the nested responsibilities for Characters, Evidence, and Advanced"
        status: pass
    human_judgment: false
  - id: D2
    description: "Story rail (Event Timeline) beside the still-mounted canvas; graph/timeline/Inspector selections converge without layout calls"
    requirement: VIZ-04
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#Story opens the bounded Episode Overview and reveals the coordinated Event Timeline rail"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#graph, timeline, and Inspector selections converge on one shared selection without layout calls"
        status: pass
      - kind: unit
        ref: "frontend/src/components/timeline/TimelineView.test.tsx#heading"
        status: pass
    human_judgment: false
  - id: D3
    description: "Responsive Inspector bottom sheet — half/full height toggle, accessible close, Escape close, safe-area padding, 44px filter controls"
    requirement: VIZ-05
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#toggles the mobile sheet between half and full height"
        status: pass
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#closes via the explicit Close Inspector button and via Escape"
        status: pass
    human_judgment: false
  - id: D4
    description: "Visual/gesture/readable-node backstops for responsive composition, gestures, long readable text, keyboard/readable node access"
    verification: []
    human_judgment: true
    rationale: "DOM/state checks cannot prove real-device composition quality, drag gesture ergonomics, or long-label readability — assigned to 10-10 UAT rows UI-RESP-01, UI-GESTURE-01, UI-TEXT-01, UI-A11Y-01."

# Metrics
duration: 50min
completed: 2026-08-13
status: complete
---

# Phase 10: Polish & Finishing Touches Summary

**Four-tab narrative story-map hierarchy with synchronized rail selection and a responsive half/full-height Inspector bottom sheet**

## Performance

- **Duration:** 50 min (executor Task 1 partial + orchestrator inline completion)
- **Started:** 2026-08-13 19:02
- **Completed:** 2026-08-13 19:22
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Story (default; Episode Overview + Event Timeline rail beside the still-mounted canvas), Characters (Character Network/Local Neighborhood), Evidence (Investigation/Evidence Chain/Answer Graph entry point + notice copy), Advanced (Full Graph/debug) — existing search/filters/chat/settings/notes/export/share/episode controls all reachable
- Per-tab nested mode memory; tab switches never reset Filters/camera/selection (D-47); timeline selection shares scene selection without unmount/relayout (D-38)
- Mobile Inspector bottom sheet: 50vh half / 85vh full toggle via 44px drag handle, explicit "Close Inspector" button, Escape close, safe-area padding, rounded top, transition; desktop left sheet unchanged
- GraphFilterPanel: 44px touch targets on trigger + chips (max-sm)
- Copy contract: zero/one/many/loading/error states asserted in component tests; visitor read-only suite scoped to the Inspector dialog

## Task Commits

Each task was committed atomically:

1. **Task 1: four-tab hierarchy + synchronized Story rail** - `cef799d` (feat)
2. **Task 2: responsive Inspector sheet** - `1554004` (feat)

**Plan metadata:** pending (SUMMARY + STATE.md + ROADMAP.md commit)

## Files Created/Modified
- `frontend/src/App.tsx` - four-tab strip, nested mode state, Story rail, shared selection
- `frontend/src/App.test.tsx` - 7 new tests (tabs, rail, convergence, Answer Graph copy) + 2 query scoping fixes
- `frontend/src/components/timeline/TimelineView.tsx` - optional showHeading prop
- `frontend/src/components/timeline/TimelineView.test.tsx` - 3 heading tests
- `frontend/src/components/detail/DetailPanel.tsx` - sheet height state, drag handle, Close button, Escape funnel
- `frontend/src/components/detail/DetailPanel.test.tsx` - 2 sheet behavior tests
- `frontend/src/components/graph/GraphFilterPanel.tsx` - 44px mobile touch targets

## Decisions Made
- Story rail coexists with the canvas (never a full-screen swap) — selection is shared, not view-switching (D-38)
- Escape close funnels through onDeselect instead of Radix auto-close — preserves the two-sheet coexistence contract (left inspector + right chat)
- Answer Graph = entry point + temporary-focus notice copy in this plan; function lands in 10-06/10-07

## Deviations from Plan

### Auto-fixed Issues

**1. [Test contract] ambiguous role queries after adding the top-level tab strip**
- **Found during:** Task 1 verification
- **Issue:** old tests used unscoped `getByRole('tab', {name: 'Evidence'})` / `getByText('Answer Graph')` — now ambiguous with the new tabs
- **Fix:** scoped visitor assertions to `within(getByRole('dialog'))`; Answer Graph assertion uses `{name, selected: true}`
- **Files modified:** frontend/src/App.test.tsx
- **Verification:** 34 focused + 385 full-suite tests pass
- **Committed in:** cef799d (Task 1 commit)

**2. [Build contract] unused test helper param**
- **Found during:** Task 2 build
- **Issue:** `renderGraphWorkspace(user)` param unused after query fixes — TS6133
- **Fix:** dropped the param and its call-site args
- **Files modified:** frontend/src/App.test.tsx
- **Verification:** npm run build passes
- **Committed in:** 1554004 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 test contract, 1 build contract)
**Impact on plan:** Both fixes necessary for correctness; no scope creep.

## Issues Encountered
- Executor hit its tool cap mid-Task-1 with 2 failing tests; orchestrator completed inline (query scoping fixes, Task 2 sheet behavior, full-suite run).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 10-06 expansion entry points consume the per-tab scene state
- 10-07 Answer Graph focus/restoration rides the evidence tab seam
- UAT backstops recorded: UI-RESP-01, UI-GESTURE-01, UI-TEXT-01, UI-A11Y-01 (10-10)

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*
