---
phase: 02-polished-cytoscape-graph-experience
plan: 03
subsystem: ui
tags: [react, shadcn, tabs, sheet, radix-ui, vitest, react-testing-library]

requires:
  - phase: 02-polished-cytoscape-graph-experience (Plan 01)
    provides: GraphCanvas onSelect contract (SelectedNode/SelectedEdge), Plan 01's minimal single-panel DetailPanel, Vitest+RTL infra, graphResponse fixtures
  - phase: 02-polished-cytoscape-graph-experience (Plan 02)
    provides: App.tsx's full useGraph status branch (loading/error/empty/populated/idle) that this plan's DetailPanel/StructuralEdgeCard branch nests inside
provides:
  - Full Overview/Claims/Evidence tabbed DetailPanel (D-07) for nodes and claim-backed edges, resolving claims/evidence/sources from the already-fetched GraphResponse (no second fetch)
  - Distinct tab-less StructuralEdgeCard (D-06) for structural edges (PART_OF/PRECEDES, claim_id null)
  - Centralized D-06/D-07 branch decision in App.tsx (single conditional, not duplicated)
affects: [02-04 (spoiler-safety grep audit / final verification)]

tech-stack:
  added: []
  patterns:
    - "DetailPanel resolves Claims/Evidence data by looking up the selected edge's claim_id in the already-fetched GraphResponse.edges (not by widening GraphCanvas's onSelect contract), keeping SelectedElement's shape stable across plans"
    - "Skeleton-gated tab content reset: a render-time key-comparison ('adjusting state when a prop changes') resets `resolved` to false when the selection changes, with a real effect only ever flipping it back to true from a setTimeout callback — avoids the react-hooks/set-state-in-effect lint rule while still gating Claims/Evidence tab bodies behind a one-tick Skeleton"

key-files:
  created:
    - frontend/src/components/detail/StructuralEdgeCard.tsx
    - frontend/src/components/detail/DetailPanel.test.tsx
    - frontend/src/components/detail/StructuralEdgeCard.test.tsx
  modified:
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/App.tsx

key-decisions:
  - "Locked evidence copy implemented as \"Source: {source label} - {locator}\" (plain hyphen) matching 02-03-PLAN.md's must_haves.truths and Task 1 action text verbatim, rather than the em dash (\"—\") shown in 02-UI-SPEC.md's Copywriting Contract example row. The plan's own truths/acceptance-criteria are the graded target for this plan's test, and both documents describe the same locked element; no UI-SPEC edit was made since this is a typographic dash-character nuance, not a content/functional divergence."
  - "GraphCanvas's onSelect contract (SelectedNode/SelectedEdge) is intentionally left unchanged, per the plan objective. Both App.tsx's branch decision and DetailPanel's internal claim resolution independently look up the selected edge's claim_id via GraphResponse.edges rather than adding claim_id to SelectedEdge — this keeps Plan 01/02's selection contract stable and avoids a second place that needs to change if the contract shape evolves later."
  - "The one-tick Claims/Evidence Skeleton gate uses the same render-time key-comparison ('adjusting state when a prop changes') pattern already established in useGraph.ts's retry/reset logic, rather than a bare synchronous setState in an effect body, to satisfy react-hooks/set-state-in-effect (caught by npm run lint during Task 1's own verify step)."
  - "Rule 3 auto-fix: Task 1's own <verify> requires npm run build to pass, but 02-03-PLAN.md's Task 1 <files> list doesn't include App.tsx even though DetailPanel's prop shape changed (added a required `graph` prop). Made the minimal necessary edit to App.tsx during Task 1 (pass `graph={graphState.data}` to DetailPanel) to keep the build green, deferring the actual StructuralEdgeCard branch logic to Task 2 as originally scoped."

requirements-completed: [UI-04]

coverage:
  - id: D1
    description: "DetailPanel's Evidence tab renders each linked GraphEvidence for the selected node or claim-backed edge via the locked copy template \"Source: {source label} - {locator}\" for every entry in the claim's evidence_ids"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#renders all three tabs for a node with claims/evidence, including the exact evidence copy"
        status: pass
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#renders the claim-backed edge Overview tab with claim fields and its single evidence entry"
        status: pass
    human_judgment: false
  - id: D2
    description: "A selected node or claim-backed edge with zero linked claims or zero linked evidence renders an explicit per-tab empty sub-state rather than a blank tab"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#renders the \"No claims recorded\" empty sub-state for a node with zero linked claims"
        status: pass
    human_judgment: false
  - id: D3
    description: "With no node/edge selected, the detail panel renders the locked placeholder copy \"Select a node to see details.\" exactly, with no Tabs shown"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#renders the locked no-selection placeholder with no Tabs"
        status: pass
    human_judgment: false
  - id: D4
    description: "Structural edges (claim_id null) open the distinct tab-less StructuralEdgeCard showing relationship type and both connected node labels; nodes and claim-backed edges open the tabbed DetailPanel; the branch is centralized in exactly one place in App.tsx"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/StructuralEdgeCard.test.tsx#renders the relationship type and both connected node labels for a PART_OF edge"
        status: pass
      - kind: unit
        ref: "frontend/src/components/detail/StructuralEdgeCard.test.tsx#renders no TabsList/TabsTrigger elements"
        status: pass
      - kind: other
        ref: "frontend/src/App.tsx static inspection: exactly one ternary (selectedElement.kind === 'edge' && matching graphState.data.edges[].claim_id == null) deciding StructuralEdgeCard vs DetailPanel"
        status: pass
    human_judgment: true
    rationale: "Visual confirmation that clicking a real PART_OF/PRECEDES edge on the running canvas shows the minimal card (no tabs) and that a character node or claim-backed edge shows the tabbed Sheet is best done by a human looking at the rendered app, per this plan's own <verification> manual step — the component tests prove the branch logic and each component's isolated render, not the live Cytoscape tap-to-select wiring end-to-end for a structural edge specifically."
  - id: D5
    description: "Long evidence text wraps and scrolls within a fixed-height evidence card (max-h-32 overflow-y-auto) rather than expanding the panel indefinitely; Claims/Evidence tabs show a one-tick Skeleton while resolving already-fetched data with no additional network round trip"
    requirement: "UI-04"
    verification: []
    human_judgment: true
    rationale: "Both are explicitly marked 'backstop' in 02-03-PLAN.md's must_haves.truths (no dedicated automated test required) — overflow/scroll behavior and the one-tick Skeleton timing are best confirmed visually against the running app rather than asserted via jsdom, which has no real layout/scroll metrics."

duration: ~15min
completed: 2026-07-29
status: complete
---

# Phase 2 Plan 03: DetailPanel Tabbed Sheet and StructuralEdgeCard Summary

**Full Overview/Claims/Evidence tabbed DetailPanel (D-07) resolving claim/evidence/source data from the already-fetched GraphResponse, plus a distinct tab-less StructuralEdgeCard (D-06) for structural edges, with the branch decision centralized in exactly one place in App.tsx.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-29
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- Rewrote `DetailPanel.tsx` to accept the full `GraphResponse` and render `Overview`/`Claims`/`Evidence` `Tabs` for a selected node or claim-backed edge, resolving claims by `subject_id`/`object_id` (node selection) or the edge's associated claim (edge selection), and evidence/source labels via `GraphResponse.evidence`/`sources` — no second network round trip.
- Locked "Source: {source label} - {locator}" copy per evidence entry, each rendered inside a `max-h-32 overflow-y-auto` card so long evidence text scrolls rather than expanding the panel.
- Explicit "No claims recorded for this node yet" / "No evidence recorded for this claim yet" empty sub-states instead of blank tabs.
- A one-tick `Skeleton` gates the Claims/Evidence tab bodies while DetailPanel's local resolve "runs", implemented via the same render-time key-comparison reset pattern already used in `useGraph.ts` (not a bare synchronous `setState` in an effect body, which `react-hooks/set-state-in-effect` flags).
- Added `StructuralEdgeCard.tsx`: a tab-less `Sheet` showing the edge's relationship type as the title and the two connected node labels (resolved from `GraphResponse.nodes`) in the body.
- Centralized the D-06/D-07 branch in `App.tsx`: exactly one ternary resolves the selected edge's `claim_id` from `graphState.data.edges` and renders `StructuralEdgeCard` for structural edges or `DetailPanel` otherwise — `GraphCanvas`'s `onSelect` contract is unchanged.
- Added `DetailPanel.test.tsx` (4 tests) and `StructuralEdgeCard.test.tsx` (2 tests) covering the no-selection placeholder, populated node/edge tabs with the exact evidence copy, the zero-claims empty sub-state, and the structural-edge card's content/no-Tabs assertions.

## Task Commits

1. **Task 1: Full Overview/Claims/Evidence tabbed DetailPanel (D-07)** - `fc7fa13` (feat)
2. **Task 2: StructuralEdgeCard (D-06) and App.tsx selection branch** - `3e8fb8d` (feat)

**Plan metadata:** (this commit, `docs(02-03): complete plan`)

## Files Created/Modified

- `frontend/src/components/detail/DetailPanel.tsx` - full Overview/Claims/Evidence tabbed Sheet, resolving claims/evidence/sources from the fetched `GraphResponse`
- `frontend/src/components/detail/DetailPanel.test.tsx` - no-selection placeholder, populated node/edge tabs (incl. exact evidence copy), zero-claims empty sub-state
- `frontend/src/components/detail/StructuralEdgeCard.tsx` - tab-less minimal detail card for structural edges (D-06)
- `frontend/src/components/detail/StructuralEdgeCard.test.tsx` - relationship type + node labels, no-Tabs assertion
- `frontend/src/App.tsx` - centralized D-06/D-07 selection branch; `DetailPanel` now receives `graph`

## Decisions Made

- Used the plan's own literal locked copy ("Source: {source label} - {locator}", plain hyphen) over the UI-SPEC example's em dash — see `key-decisions` in frontmatter.
- Kept `GraphCanvas`'s `onSelect` contract unchanged; both `App.tsx` and `DetailPanel` independently resolve `claim_id` from the fetched `GraphResponse.edges` rather than widening `SelectedEdge`.
- Used a render-time key-comparison reset (matching `useGraph.ts`'s existing pattern) instead of a synchronous effect-body `setState` for the one-tick Skeleton gate, to satisfy `react-hooks/set-state-in-effect`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Minimal App.tsx edit during Task 1 to keep the build green**
- **Found during:** Task 1 (`npm run build` step of `<verify>`)
- **Issue:** Task 1 rewrote `DetailPanel.tsx` to require a new `graph` prop, but Task 1's `<files>` list didn't include `App.tsx` (the only caller) — the build failed with a missing-required-prop TS error since `App.tsx` still called `<DetailPanel selected={selectedElement} />`.
- **Fix:** Added `graph={graphState.data}` to the existing `<DetailPanel>` call in `App.tsx`, without introducing the `StructuralEdgeCard` branch (that remained Task 2's scope, executed immediately after).
- **Files modified:** `frontend/src/App.tsx`
- **Verification:** `npm run build` exits 0 after the fix; Task 2 then layered the full branch decision on top of this same call site.
- **Committed in:** `fc7fa13` (Task 1 commit)

**2. [Rule 3 - Blocking] Reworked the Skeleton-gate effect to satisfy react-hooks/set-state-in-effect**
- **Found during:** Task 1 (`npm run lint` step of `<verify>`)
- **Issue:** An initial `useEffect(() => { setResolved(false); setResolved(true) }, [...])` implementation was flagged by ESLint's `react-hooks/set-state-in-effect` rule (calling `setState` synchronously within an effect body).
- **Fix:** Replaced it with the render-time "adjusting state when a prop changes" pattern (comparing a stored previous selection key during render) plus a `setTimeout`-based effect that only ever flips `resolved` back to `true` from an async callback.
- **Files modified:** `frontend/src/components/detail/DetailPanel.tsx`
- **Verification:** `npm run lint` exits 0; `DetailPanel.test.tsx`'s 4 tests still pass.
- **Committed in:** `fc7fa13` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking build/lint issues surfaced by the plan's own `<verify>` steps).
**Impact on plan:** Both fixes were mechanically necessary to keep Task 1's own acceptance criteria (`npm run build`/`npm run lint` exit 0) green; no scope creep beyond what Task 1/2 already specified.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UI-04 is satisfied: node and claim-backed-edge detail views explain relationships via the Overview/Claims/Evidence tabs and display linked source/evidence episode locators in the locked copy format; structural scaffold edges get the distinct D-06 tab-less card.
- `npm run test -- --run` (13/13 tests), `npm run build`, and `npm run lint` all exit 0 as of this plan's final commit.
- Deferred to phase-gate UAT (per `human_judgment: true` coverage rows above): visual confirmation of the StructuralEdgeCard vs DetailPanel branch against the real running canvas (clicking an actual PART_OF/PRECEDES edge vs. a character node/claim-backed edge), and the overflow/scroll + one-tick Skeleton backstop behaviors.
- Plan 04 (spoiler-safety grep audit / final phase verification) can build on this detail-panel surface without further changes to its contract.

---
*Phase: 02-polished-cytoscape-graph-experience*
*Completed: 2026-07-29*

## Self-Check: PASSED

All created files and commit hashes verified present on disk / in git log.
