---
quick_id: 260813-ftl
status: complete
key-files.created:
  - frontend/src/App.test.tsx (new visitor integration test: "visitor detail inspector hides all note-adding and revision-history UI")
---

# Summary

Closed the 260805-te3 wiring gap: `App.tsx` now passes `readOnly={isVisitor}` to `DetailPanel`, activating the dormant visitor gates so a misafir sees no Notes tab, no History tab, no Add Note button, and no Create Relationship button. Defense-in-depth in `DetailPanel.tsx`: the Add Note button is gated on `!readOnly` and `NoteItem` receives `readOnly` so its edit/delete affordances hide for guests. Since the History tab is the only entry point to `RevisionHistoryPanel`, hiding the tab removes the revision-history panel (and its Revert buttons) entirely for visitors. Authenticated rendering is unchanged; backend 403/401 enforcement untouched (frontend-only).

## Verification

- `npm run build` (tsc -b + vite): passed, BUILD_EXIT=0 (run after each task).
- Task 1 targeted `NODE_ENV=test CI=1 npm run test -- src/components/detail/DetailPanel.test.tsx src/components/graph/GraphCanvas.test.tsx`: 2 files / 45 tests passed.
- Task 2 targeted `NODE_ENV=test CI=1 npm run test -- src/App.test.tsx`: 19/19 passed (18 existing + 1 new).
- RED proof: with Task 1's App.tsx wiring reverted (HEAD~1), the new test fails on the Notes-tab assertion (1 failed / 18 skipped); green with the wiring in place.
- Full suite `NODE_ENV=test CI=1 npm run test`: 40 files / 338 tests passed.
- `git diff --check`: clean (no whitespace errors).

## Commits

- `ed24814` feat(quick-260813-ftl): thread readOnly={isVisitor} into DetailPanel and harden note affordances (Task 1: App.tsx, DetailPanel.tsx)
- `49d69ae` test(quick-260813-ftl): visitor inspector hides all note-adding and revision-history UI (Task 2: App.test.tsx)

## Self-check

- A visitor opening the detail inspector sees zero note-adding affordances (Notes tab, Add Note button, note editor, NoteItem edit/delete) and zero revision-history UI (History tab / RevisionHistoryPanel) — locked by the new App-level integration test plus the existing DetailPanel readOnly suite.
- A visitor can never reach RevisionHistoryPanel: the History tab is its only mount point and is gated `!readOnly`.
- Authenticated users see every note-adding and revision-history affordance exactly as before (readOnly defaults undefined/false; no App-level gating beyond the single prop).
- All changes are inline Tailwind, DaisyUI-free, no new deps/context; backend untouched (`spoilerless/` not modified).
