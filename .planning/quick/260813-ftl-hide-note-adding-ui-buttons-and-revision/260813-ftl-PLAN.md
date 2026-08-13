---
quick_id: 260813-ftl
description: "Hide note-adding UI (buttons and frontend stuff) and the revision history panel/page from visitor (misafir) mode users; backend already blocks note creation for visitors."
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/App.tsx
  - frontend/src/components/detail/DetailPanel.tsx
  - frontend/src/App.test.tsx
autonomous: true

estimate:
  tokens: 16000
  raw_tokens: 12000
  tasks: 2
  confidence: high

must_haves:
  truths:
    - A visitor (misafir) opening the detail inspector sees no Notes tab, no History tab, no Add Note button, and no Create Relationship button.
    - A visitor can never reach the revision history panel (including its Revert buttons) — the History tab is its only entry point.
    - Authenticated users still see every note-adding and revision-history affordance exactly as before.
  artifacts:
    - frontend/src/App.tsx (readOnly={isVisitor} wired into DetailPanel)
    - frontend/src/App.test.tsx (visitor integration test asserting the hidden surfaces)
  key_links:
    - App.tsx isVisitor (line 115) -> DetailPanel readOnly prop (lines 579-603) -> tab/button gates (DetailPanel.tsx 717, 718, 793, 863)
---

<objective>
Hide all note-adding UI and the revision history panel from visitor (misafir) mode users, purely on the frontend (the backend already returns 403/401 for visitor note/revert writes — no API changes).

Purpose: 260805-te3 built all the readOnly gating inside DetailPanel/GraphCanvas but App.tsx never passed `readOnly={isVisitor}` into DetailPanel, so today a visitor still sees the Notes tab (Add Note button, note editor, edit/delete), the History tab (full RevisionHistoryPanel incl. Revert), and Create Relationship. This plan closes that wiring gap and hardens the two ungated note affordances inside DetailPanel.

Output: `readOnly={isVisitor}` threaded into DetailPanel in App.tsx; Add Note button and NoteItem render gated by readOnly in DetailPanel.tsx; an App-level visitor integration test that would fail (RED) if the wiring regresses.
</objective>

<context>
Key facts (verified against current source):
- `const isVisitor = state.status === 'visitor'` — frontend/src/App.tsx:115. Already threaded: AppShell `visitor={isVisitor}` (App.tsx:460), ChatLauncher/ChatSheet hidden via `!isVisitor` (App.tsx:473, 605), GraphCanvas `readOnly={isVisitor}` + `onShareLink` gate (App.tsx:561-562).
- DetailPanel receives NO `readOnly` prop today (App.tsx:579-603) — its internal gates are dead: Notes tab `{!readOnly && ...}` (DetailPanel.tsx:717), History tab (718), Create Relationship button (793-805).
- DetailPanel.tsx:863-874 "Add Note" button is NOT gated by readOnly (currently unreachable only because the Notes tab trigger at 717 is hidden).
- DetailPanel.tsx:909-914 renders NoteItem WITHOUT `readOnly={readOnly}` — the NoteItem-level edit/delete gate (DetailPanel.tsx:207-259) is therefore also dead.
- RevisionHistoryPanel (with Revert buttons at RevisionHistoryPanel.tsx:150-163) is mounted ONLY from the History tab (DetailPanel.tsx:971-979). No standalone page/route, no nav entry (CommandPalette.tsx has no note/history rows; AppShell topBar has Timeline/Series/Settings only). Hiding the tab removes the panel entirely — the documented design (DetailPanel.tsx:714-716, 851-853: "hide the tabs entirely instead of showing dead-end affordances").
- GraphCanvas already wired: Create Custom Node FAB + dialog + share-link gated by `readOnly` (GraphCanvas.tsx:891, 895, 907; App.tsx:561-562). CommandPalette chat row gated via `onOpenChat={isVisitor ? undefined : ...}` (App.tsx:635, CommandPalette.tsx:111). NodeSearch "Notes & Claims" mode (App.tsx:568-573) is read-only browsing — intentionally kept.
- Test conventions: NODE_ENV=test CI=1 npm run test; typecheck via npm run build (tsc -b). Component-level readOnly tests already exist: DetailPanel.test.tsx:329-352 ("hides the Create Relationship action", "hides the Notes and History tabs entirely"). Visitor-entry integration pattern: App.test.tsx:218-231; canvas stub renders one clickable button per node (App.test.tsx:110-114, data-testid `graph-element-{id}`).

@frontend/src/App.tsx
@frontend/src/components/detail/DetailPanel.tsx
@frontend/src/components/detail/RevisionHistoryPanel.tsx
@frontend/src/App.test.tsx
@frontend/src/components/detail/DetailPanel.test.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Thread readOnly={isVisitor} into DetailPanel and harden its note affordances</name>
  <files>frontend/src/App.tsx, frontend/src/components/detail/DetailPanel.tsx</files>
  <action>
    frontend/src/App.tsx — in the DetailPanel render block (lines 579-603), add the prop `readOnly={isVisitor}` (the exact same value already passed to GraphCanvas at line 561). Do NOT introduce new context/providers — reuse the existing prop; do NOT gate or hide anything else at the App level (GraphCanvas/ChatLauncher/ChatSheet gates already exist).

    frontend/src/components/detail/DetailPanel.tsx — two defense-in-depth changes so the "readOnly ⇒ no note write affordance" invariant holds even if a tab ever becomes reachable again:
    1. Gate the "Add Note" button (lines 862-874) with `{!readOnly && ( ... )}` — mirror the existing `!readOnly` gate style used at lines 717/718/793.
    2. Pass `readOnly={readOnly}` to the NoteItem render at lines 909-914 so the NoteItem-internal edit/delete gate (line 207) actually receives the prop it already supports.

    Leave as-is (they become effective once wired): Notes tab gate (717), History tab gate (718), Create Relationship gate (793-805), RevisionHistoryPanel mount (971-979), NoteEditor (418-463, 855-861, 900-907). Do NOT add a readOnly prop to RevisionHistoryPanel — the History tab is its only entry point and hiding the tab is the established design; do NOT touch GraphCanvas.tsx or CommandPalette.tsx. No DaisyUI classes; inline Tailwind only; do not run `git add -A`; commit only these two files atomically (code-only commit).
  </action>
  <verify>
    <automated>cd frontend && npm run build && NODE_ENV=test CI=1 npm run test -- src/components/detail/DetailPanel.test.tsx src/components/graph/GraphCanvas.test.tsx</automated>
  </verify>
  <done>
    App.tsx passes readOnly={isVisitor} to DetailPanel; with readOnly set, DetailPanel renders no Notes tab, no History tab, no Add Note button, and no Create Relationship button (DetailPanel.test.tsx:329-352 passes); npm run build (tsc -b) clean; authenticated render unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: App-level visitor integration test for hidden note/history surfaces</name>
  <files>frontend/src/App.test.tsx</files>
  <action>
    Add one test in App.test.tsx modeled on the existing visitor test at lines 218-231, using the assertion set from DetailPanel.test.tsx:338-351:
    - render &lt;App /&gt;, click the "Continue as visitor" button, wait for the "Visitor" badge (lines 222-228 pattern).
    - Wait for the graph to render (visitor seeding loads graphResponseS01E01 — the canvas stub renders a clickable button per node, data-testid `graph-element-char_dexter_morgan`, App.test.tsx:110-114), then click that node button to open the DetailPanel sheet.
    - Assert: tab "Notes" NOT in document, tab "History" NOT in document, button "Add note" NOT in document, button "Create relationship" NOT in document; and tabs "Overview", "Claims", "Evidence" present (inspector stays browsable — same assertions as DetailPanel.test.tsx:343-350).
    - Do not assert RevisionHistoryPanel internals (unreachable once the History tab is hidden) and do not stub useNotes or the revisions API — the fetch stub's fallback (notFoundResponse, App.test.tsx:190) already covers any stray GET.
    - Keep the test self-contained in the visitor describe area; no changes to existing tests. Commit atomically (test-only commit); do not run `git add -A`.
  </action>
  <verify>
    <automated>cd frontend && NODE_ENV=test CI=1 npm run test -- src/App.test.tsx && NODE_ENV=test CI=1 npm run test</automated>
  </verify>
  <done>
    New test passes; it fails (RED) when Task 1's App.tsx wiring is reverted, proving it guards the regression; full suite green; typecheck clean.
  </done>
</task>

</tasks>

<verification>
- cd frontend && npm run build  (tsc -b typecheck gate)
- cd frontend && NODE_ENV=test CI=1 npm run test  (full suite)
- Manual spot check (optional): enter visitor mode in the running app, select any character node — Notes/History tabs, Add Note, Create Relationship all absent; login as a real user — all note/history UI present.
</verification>

<success_criteria>
- A visitor sees zero note-adding affordances (tab, button, editor, edit/delete) and zero revision-history UI anywhere; backend enforcement (403/401) unchanged and now invisible to the user.
- The wiring is a single prop thread (no new context), all changes are inline-Tailwind, DaisyUI-free, and each task lands as its own atomic commit.
</success_criteria>
