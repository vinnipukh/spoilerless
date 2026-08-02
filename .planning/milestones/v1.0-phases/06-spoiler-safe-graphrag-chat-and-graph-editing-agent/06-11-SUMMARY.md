---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "11"
subsystem: ui
tags: [typescript, react, cytoscape, vitest, chat, changeset, graph-edit, protected-content]

# Dependency graph
requires:
  - phase: 06-08
    provides: "Typed ChangeSet API clients (api/changeSet.ts's confirmChangeSet/rejectChangeSet) and the ChangeSet types"
  - phase: 06-09
    provides: "ChatPanel/MessageList chat surface, citation chips, DetailPanel Chat mode"
  - phase: 06-10
    provides: "GraphCanvas focusedElementIds prop + GraphFocusIndicator + App.tsx graphFocus state (the focus mechanism the post-apply refresh reuses)"
provides:
  - "frontend/src/components/chat/ChangeSetCard.tsx — propose-time preview card: singular/plural title, per-operation summary lines, Before/After rows (update ops only), affected-elements list in CitationChip style, warnings row, destructive banner, Confirm/Reject controls (the ONLY UI path into confirm/reject endpoints), terminal Applied/Rejected/Failed badges, stale 'no longer valid' banner, and the Protected badge for canonical/candidate-edit refusals"
  - "frontend/src/App.tsx handleChangeSetApplied — post-apply incremental graph refresh: useGraph.refresh() (new: re-fetches without flipping to 'loading') + setGraphFocus(focusTargetsForAppliedChangeSet) reusing 06-10's focusedElementIds mechanism"
  - "frontend/src/hooks/useGraph.ts refresh() — data-preserving refetch distinct from refetch() (error recovery)"
  - "frontend/src/components/graph/GraphCanvas.tsx — layout-effect guard: no destructive runLayout while focusedElementIds is active; ref guard prevents re-layout on focus-only changes"
affects: [06-12]

# Actuals (#2632)
actuals:
  tokens: 42000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useGraph.refresh() vs refetch(): refresh re-issues the same getGraph fetch WITHOUT flipping status back to 'loading' (refreshToken excluded from the state-key that re-enters loading), so GraphCanvas is neither unmounted nor re-laid-out — refetch remains the error-recovery path that does flip to loading"
    - "GraphCanvas's layout effect guard: skip runLayout when focusedElementIds is non-null (the focus effect already provides the gentle cy.fit re-frame); a lastLayoutGraphRef guard keeps focus-clear/apply state changes from re-laying-out an unchanged graph"
    - "focusTargetsForAppliedChangeSet maps each ChangeSet operation_type to its focusable id (create_note -> target_id, update_node/delete_node -> node_id, update/delete_relationship -> relationship_id, claim ops -> claim_id) — a single switch, no per-op special-casing in App.tsx"

key-files:
  created:
    - frontend/src/components/chat/ChangeSetCard.tsx
    - frontend/src/components/chat/ChangeSetCard.test.tsx
  modified:
    - frontend/src/components/chat/MessageList.tsx
    - frontend/src/components/chat/ChatPanel.tsx
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/hooks/useGraph.ts
    - frontend/src/components/graph/GraphCanvas.tsx
    - frontend/src/test/fixtures/chatFixtures.ts

key-decisions:
  - "The Protected badge is INFORMATIONAL, not a control replacement: a protected (canonical/candidate-edit refusal) proposal is still a confirmable create_note annotation ('Propose a note instead' is the actual action), so Confirm/Reject controls remain rendered alongside the badge — the badge only carries the honesty signal that the canonical record itself stays untouched"
  - "The post-apply refresh must NOT call cy.layout()/runLayout: GraphCanvas's layout effect early-returns while focusedElementIds is active, so the fresh graph data updates in place and the 06-10 focus effect's cy.fit(focused, 48) is the only re-frame — the next full relayout happens on a later non-focused graph change (e.g. progress boundary change after focus clears)"
  - "ChangeSetCard's Confirm button label stays 'Confirm changes' in both primary and destructive re-skins (per 06-UI-SPEC: the destructive banner carries the warning in full-sentence form, not the label text — deliberate difference from ConfirmAdvanceModal's label-switching precedent)"

requirements-completed: [RAG-14, RAG-16, RAG-17]

coverage:
  - id: D1
    description: "ChangeSetCard renders the full UI-SPEC structure: 'Proposed change' vs 'Proposed changes (N)' at exactly N=1 vs N>=2; Before/After rows only for update ops (create_node shows no Before); destructive banner 'This will permanently delete {N} graph element(s).' only when >=1 delete op; Confirm re-skins to destructive styling for delete-containing sets with identical 'Confirm changes' label; stale-status renders the 'no longer valid... ask again' banner; Applied/Rejected/Failed render terminal status badges with zero interactive Confirm/Reject controls"
    requirement: RAG-14
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/ChangeSetCard.test.tsx (11 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Confirm/Reject are the ONLY UI path into the confirm/reject endpoints (T-06-05): the api module is mocked in both ChangeSetCard.test.tsx and App.test.tsx, and the App-level apply test asserts confirmChangeSet was called exactly once by the card's own button — no other UI event is wired to it"
    requirement: RAG-14
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#ChangeSet-apply incremental refresh (06-11, RAG-14/RAG-17) first test (confirmChangeSet toHaveBeenCalledTimes(1)) + ChangeSetCard.test.tsx mock wiring"
        status: pass
    human_judgment: false
  - id: D3
    description: "Protected badge (Lock icon, border-l-2 border-destructive accent line) + 'Propose a note instead' renders for a canonical-edit refusal (PROTECTED_OVERRIDE_PATTERN create_note), in both isolated card render and full-app render; rendered copy never claims the canonical record was updated/changed/modified (T-06-12)"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/ChangeSetCard.test.tsx#Protected badge test + frontend/src/App.test.tsx#Protected badge test"
        status: pass
    human_judgment: false
  - id: D4
    description: "MessageList mounts ChangeSetCard directly below an assistant message carrying a non-null proposed_change_set (threaded through ChatPanel/DetailPanel props), and never renders it without a proposed ChangeSet/seriesId, while streaming, or on a failed turn"
    requirement: RAG-14
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/MessageList.test.tsx (2 new mount tests; total 8)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Confirming a ChangeSet triggers an incremental graph refresh: useGraph.refresh() re-issues the fetch without a loading flash (graph element stays in the DOM, no 'Loading…' state), GraphCanvas does NOT re-run the full layout (cy.layout spy stays 0), and the newly-created resource (create_note -> char_dexter_morgan) receives the 06-10 focusedElementIds treatment ('Highlighting 1 from chat') — reusing the existing focus mechanism, not a second one"
    requirement: RAG-17
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#ChangeSet-apply incremental refresh (06-11, RAG-14/RAG-17) first test (layoutRuns===0, refetch observed, focus indicator)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full frontend regression green: 161 tests across 22 files pass (NODE_ENV=test CI=1 npm run test); npx tsc -b clean; npm run build clean; eslint reports 0 NEW errors vs the pre-plan baseline of 28 pre-existing findings in committed Phase 3.1/4 files (DetailPanel/GraphCanvas react-hooks findings and useChatSessions/useNotes/useRevisions/useRevisions.test/RevisionHistoryPanel.test findings, unchanged before/after this plan)"
    verification:
      - kind: other
        ref: "cd frontend && NODE_ENV=test CI=1 npm run test (161/161 pass, 22 files); npx tsc -b (0 errors); npm run build (clean); npm run lint (28 pre-existing errors — baseline verified via git stash, 0 introduced by 06-11)"
        status: pass
    human_judgment: false

duration: 3h
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 11: ChangeSetCard + incremental post-apply graph refresh + Protected badge Summary

**`ChangeSetCard` is the sole UI-initiated write surface in the phase — propose-time preview with before/after rows, destructive banner, and Confirm/Reject controls wired exclusively to `confirmChangeSet`/`rejectChangeSet`; applying a ChangeSet refreshes the graph incrementally (no destructive relayout, no remount) and reuses 06-10's `focusedElementIds` to focus the newly-created resource; canonical/candidate-edit refusals render an honest Protected badge (RAG-14/RAG-16/RAG-17 frontend half).**

## Performance

- **Duration:** ~3 h (two executor passes died at iteration caps; remainder finished inline by orchestrator)
- **Tasks:** 3
- **Files created:** 2 · **Files modified:** 7

## Accomplishments

- **`ChangeSetCard.tsx`** (finished from a partial untracked file left by an earlier interrupted session): full UI-SPEC card structure — title with the exact N=1/N>=2 singular/plural boundary, one summary line per operation ("Create Location: Rita's House" via `op.node_type`), Before/After rows gated to update ops, affected-elements list reusing `CitationChip`'s visual style (imported, not reimplemented), warnings row, destructive banner with pluralization, Confirm/Reject controls visible only while `awaiting_confirmation`, terminal status badges (Applied `--success` CheckCircle2 / Rejected muted XCircle / Failed `--destructive` XCircle), stale "no longer valid... ask again" banner replacing the controls, and the Protected badge (`Lock`, `border-l-2 border-destructive`) for `PROTECTED_OVERRIDE_PATTERN` create_note operations. Confirm label always "Confirm changes" but re-skins to destructive styling when any delete op is present. Mounted in `MessageList.tsx` below the assistant message carrying the proposal.
- **Incremental post-apply refresh** (`App.tsx`): new `handleChangeSetApplied` calls the new `useGraph.refresh()` (re-issues the fetch WITHOUT flipping to `loading` — `refreshToken` excluded from the state-key that re-enters loading) and `setGraphFocus(focusTargetsForAppliedChangeSet(changeSet))`, which maps each op type to its focusable id. `GraphCanvas.tsx` gained a layout-effect guard: `runLayout` is skipped while `focusedElementIds` is active (the focus effect's `cy.fit(focused, 48)` is the only re-frame), with a `lastLayoutGraphRef` guard preventing focus-clear/apply state changes from re-laying-out an unchanged graph. Threaded `onChangeSetApplied` through `DetailPanel` -> `ChatPanel` -> `MessageList` -> `ChangeSetCard.onApplied`.
- **Tests (TDD):** `ChangeSetCard.test.tsx` (11 tests: singular/plural, before/after gating, destructive banner pluralization, Confirm destructive re-skin with identical label, confirm/reject wiring with terminal badges, stale banner, terminal zero-controls, Protected badge honesty, long-label wrap), 2 new `MessageList.test.tsx` mount tests, 2 new `App.test.tsx` integration tests (apply = refetch + no relayout + focus + no loading flash; Protected badge in full app).

## Task Commits

1. **Task 1: ChangeSetCard behavior tests + fixtures** - `a6de35e` (test)
2. **Task 1: ChangeSetCard + MessageList mounting + onApplied threading** - `f459110` (feat)
3. **Task 2 + Task 3: incremental post-apply refresh + Protected badge wiring + App tests** - `86b9e16` (feat — see Deviations)

**Plan metadata:** committed separately after this summary (docs commit).

## Files Created/Modified

- `frontend/src/components/chat/ChangeSetCard.tsx` - new preview/confirm card (sole UI write path)
- `frontend/src/components/chat/ChangeSetCard.test.tsx` - new, 11 tests
- `frontend/src/components/chat/MessageList.tsx` - ChangeSetCard mount below proposing assistant message
- `frontend/src/components/chat/ChatPanel.tsx` - `onApplied` prop threaded through
- `frontend/src/components/detail/DetailPanel.tsx` - `onChangeSetApplied` prop (was declared but NOT destructured — ReferenceError fixed here)
- `frontend/src/App.tsx` - `handleChangeSetApplied` + `focusTargetsForAppliedChangeSet`
- `frontend/src/hooks/useGraph.ts` - `refresh()` (data-preserving refetch)
- `frontend/src/components/graph/GraphCanvas.tsx` - layout guard + ref guard (and removed a debug `console.log` left by a prior executor pass)
- `frontend/src/App.test.tsx` - mock for `./api/changeSet`, spy counters, 2 new integration tests
- `frontend/src/test/fixtures/chatFixtures.ts` - ChangeSet behavior fixtures (one per card truth) + `createNodeOnlyChangeSet`

## Decisions Made

- Protected badge is informational: the refusal proposal is still a confirmable note annotation, so Confirm/Reject controls stay visible alongside the badge (the copy alone carries the "canonical record untouched" honesty signal).
- Post-apply refresh never calls `cy.layout()`: graph data updates in place; the 06-10 focus `cy.fit(focused, 48)` is the only re-frame; next full relayout waits for a later non-focused graph change.
- `refresh()` vs `refetch()` are distinct: refresh = in-place data update (no loading flash), refetch = error-recovery (loading state, Retry button).
- `useGraph.refresh()` is invoked via `graphState.refresh()` — `useGraph`'s return spreads `...state` so the refresh function rides along with the status.

## Deviations from Plan

### Auto-fixed Issues

**1. DetailPanel ReferenceError — `onChangeSetApplied is not defined`** (Rule 3: implementation couldn't work as authored)
- Found by the orchestrator's first App-test run: `DetailPanel.tsx` passed `onApplied={onChangeSetApplied}` to ChatPanel but never destructured the prop from `Props` (the prop was declared in the type but omitted from the destructuring list, so the identifier was undefined at render).
- Fixed by adding `onChangeSetApplied` to the destructuring. Caught by the new App-level apply tests — the standalone card tests could not see this because they render `ChangeSetCard` in isolation.

### Process deviations (not Rule 1-4 cases)

**1. Task 2 + Task 3 committed together, not atomically per-task**
- Both tasks' code and tests were completed in one orchestrator pass after two executor runs died at the 50-iteration cap (the second mid-Task-2). The remaining work was small and tightly coupled (App.tsx wiring + its tests + the regression run), so it landed as a single `86b9e16` commit. Every task's acceptance criteria is independently verified by its own test group.

**2. Executor iteration-cap deaths (process, not code)**
- Executor 1 (22m) burned its whole budget root-causing the `NODE_ENV=production` shell export breaking vitest (React prod build => `act` undefined) and died mid-Task-1 before committing. Executor 2 completed Task 1 (commits `a6de35e`/`f459110`, 19/19 green) then died mid-Task-2. The orchestrator finished Task 2/3 inline. Environment fact now captured for future runs: `cd frontend && NODE_ENV=test CI=1 npm run test ...` is mandatory on this machine.

---

**Total deviations:** 2 auto-fixed, 2 process deviations (commit granularity + executor deaths).
**Impact on plan:** None on correctness or scope — the sole functional defect (DetailPanel destructuring) was caught and fixed with tests proving it.

## Issues Encountered

- **`NODE_ENV=production` exported in the shell breaks all vitest runs** (React prod build has no `act`): the root cause of executor 1's death, now documented — always run `NODE_ENV=test CI=1 npm run test`. The full suite is green at 161/161 with this prefix.
- **`cyMounts` spy is not a mount counter**: the react-cytoscapejs test stub's render body runs on every re-render, so counting renders proved nothing about mounts. The mount-stability assertion was replaced with the honest proxy: the graph element stays in the DOM and no `Loading…` state appears during the refresh (a true remount would require the `loading` flip, which `refresh()` deliberately avoids).
- **Protected-badge test initially over-asserted**: the first App-level draft asserted Confirm/Reject controls are absent for a protected proposal — wrong per the card's design (the badge is informational; the proposal is a confirmable note annotation). Corrected to assert the badge renders AND the card stays confirmable.
- Pre-existing lint debt is unchanged: 28 eslint errors at HEAD (DetailPanel/GraphCanvas `react-hooks` findings documented since 06-09, plus useChatSessions/useNotes/useRevisions/useRevisions.test/RevisionHistoryPanel.test findings), verified identical before/after via `git stash` baseline run. 06-11 introduced 0 new lint errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-12 (phase close: full regression + docs + Manual Acceptance Matrix) can run the exact command list verified here: `cd backend && uv run pytest`, `cd frontend && NODE_ENV=test CI=1 npm run test && npm run lint && npx tsc -b && npm run build`.
- Known limitation for 06-12's manual matrix: item 14/15 (Confirm applies change, graph updates) is covered by the App-level automated test here, but the live-browser run still needs a real LLM provider for the qualitative items.
- The `_auto_chain_active` flag in `.planning/config.json` is ephemeral (this `--auto` run) — 06-12's executor should not treat it as a persistent config.
- No blockers.

## Self-Check: PASSED

- FOUND: frontend/src/components/chat/ChangeSetCard.tsx
- FOUND: frontend/src/components/chat/ChangeSetCard.test.tsx
- FOUND: frontend/src/components/chat/MessageList.tsx (ChangeSetCard mount)
- FOUND: frontend/src/App.tsx (handleChangeSetApplied)
- FOUND: frontend/src/hooks/useGraph.ts (refresh)
- FOUND: frontend/src/components/graph/GraphCanvas.tsx (layout guard)
- FOUND: frontend/src/components/detail/DetailPanel.tsx (onChangeSetApplied destructure)
- FOUND commit a6de35e
- FOUND commit f459110
- FOUND commit 86b9e16

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*
