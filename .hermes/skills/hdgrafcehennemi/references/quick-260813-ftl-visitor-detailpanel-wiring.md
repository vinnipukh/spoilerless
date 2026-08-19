# Quick 260813-ftl — visitor DetailPanel wiring + note/history UI hardening (2026-08-13)

Executed by a subagent on local main (`USE_WORKTREES=false`), frontend-only.
Plan: `.planning/quick/260813-ftl-hide-note-adding-ui-buttons-and-revision/260813-ftl-PLAN.md`.

## What shipped

- **Task 1 (`ed24814`, feat(quick-260813-ftl))** — `frontend/src/App.tsx` +
  `frontend/src/components/detail/DetailPanel.tsx`:
  - App.tsx DetailPanel render block (~line 579): added `readOnly={isVisitor}`
    (same value already passed to GraphCanvas at ~line 561). This activates the
    dormant gates: Notes tab (`DetailPanel.tsx:717`), History tab (`:718`),
    Create Relationship (`:793`).
  - DetailPanel.tsx: "Add Note" button (`:862-874`) wrapped in `!readOnly && (...)`.
  - DetailPanel.tsx: `NoteItem` render (`:909-914`) now passes `readOnly={readOnly}`
    — the NoteItem-internal edit/delete gate (`:207`) was dead code before.
  - No new context/providers; RevisionHistoryPanel intentionally gets NO readOnly
    prop — the History tab (`!readOnly` gated, `:718`) is its only mount (`:971-979`),
    so hiding the tab removes the panel (and its Revert buttons) entirely.
- **Task 2 (`49d69ae`, test(quick-260813-ftl))** — `frontend/src/App.test.tsx`:
  new test "visitor detail inspector hides all note-adding and revision-history UI",
  modeled on the visitor-entry test at lines 218-231: click "Continue as visitor"
  → wait for Visitor badge → click `graph-element-char_dexter_morgan` canvas stub
  button → wait for heading "Dexter Morgan" → assert NO tab Notes/History, NO
  button "Add note"/"Create relationship", PRESENT tabs Overview/Claims/Evidence.
  No useNotes/revisions stubbing needed — fetchStub's `notFoundResponse()` fallback
  covers stray GETs.

## Verification results (all on the final tree)

- `npm run build` (tsc -b + vite): BUILD_EXIT=0, run after BOTH tasks (test-file
  TS errors only surface there — same rule as the TS18047/TS2339 trap).
- Task 1 targeted: DetailPanel.test.tsx + GraphCanvas.test.tsx = 2 files / 45 passed.
- Task 2 targeted: App.test.tsx = 19/19 (18 existing + 1 new).
- Full suite: 40 files / 338 tests passed (run twice consecutively, both green).
- RED proof: `git show HEAD~1:frontend/src/App.tsx > frontend/src/App.tsx` →
  `npm run test -- src/App.test.tsx -t "visitor detail inspector hides all note-adding"`
  → 1 failed / 18 skipped (failed exactly on the Notes-tab assertion) →
  `git checkout -- frontend/src/App.tsx` (status clean).
- Backend untouched: `git diff --name-only HEAD~2..HEAD -- spoilerless/` = 0 files.

## Durable techniques

1. **Committed-state RED proof** — `git show HEAD~1:<path> > <path>` temporarily
   restores the pre-change file (stash only works for uncommitted edits); run the
   single new test with `-t "<name>"`; restore with `git checkout -- <path>`.
2. **`hermes verify` trap** — `hermes verify --detect-only` on this repo reports a
   `FastAPI app` recipe: `pytest` + `uvicorn main:app` on :8000. The uvicorn entry
   doesn't exist at the repo root (real: `spoilerless/app/main.py`) and `pytest`
   would run the 75-min live-Neo4j suite. Frontend-only verification = build +
   vitest, with the `spoilerless/` diff check as the pytest-irrelevance proof.
3. **Visitor-mode full contract (current state)** — authenticated users see every
   note/history affordance (readOnly unset → false); visitors see zero note-adding
   UI and zero revision-history UI; GraphCanvas FAB/share and chat were already
   gated (260805-te3). Any future change must keep the App.test.tsx visitor test
   green — it is the regression net for the whole wiring.

## Context notes

- Working tree had unrelated dirty files (`.planning/config.json`,
  `.planning/tmp/docs-work-manifest.json`, `.hermes/`, root `run_*.py` verifiers) —
  left untouched; staged only the two/one explicit file(s) per commit.
- A sibling agent committed `bf85818 fix(ux): enlarge legend toggle hit area`
  on top of our commits mid-task — main is shared; `git log` after each commit to
  confirm position.
