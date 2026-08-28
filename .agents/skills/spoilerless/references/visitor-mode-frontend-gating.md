# Visitor (misafir) mode — frontend gating surface map & planning notes

Scope of quick task `260813-ftl` (hide note-adding UI + revision history from visitors).
Backend already 403/401s visitor writes — the task is PURELY frontend hiding.

## Core pitfall: prop gating exists but is never wired at the render site (dead gates)

DetailPanel.tsx already had COMPLETE `readOnly` gating (260805-te3) — Notes tab
`{!readOnly && ...}` (DetailPanel.tsx:717), History tab (:718), Create Relationship
button (:793), NoteItem edit/delete (:207) — but **App.tsx never passed
`readOnly={isVisitor}` to DetailPanel** (App.tsx:579-603; only GraphCanvas got it at
:561). Component-level tests passed (DetailPanel.test.tsx:329-352 render `readOnly`
directly), masking the integration gap: real visitors still saw everything.

**Lesson for "hide X for role Y" tasks:** grep EVERY render site of the component
(`<DetailPanel` — exactly one in App.tsx) and verify the role prop is actually
threaded there; component tests that pass `readOnly` by hand do NOT prove wiring.

Also found ungated inside DetailPanel (defense-in-depth gaps): "Add Note" button
(:863-874) and the NoteItem render (:909-914, which never passed `readOnly` to
NoteItem's own gate). Plan 260813-ftl Task 1 fixes wiring + both gaps.

## Scoped surface map (verified 260813)

| Surface | Evidence | Status |
|---|---|---|
| Notes tab trigger | DetailPanel.tsx:717 `!readOnly` | gated, dead until wired |
| History tab trigger | DetailPanel.tsx:718 `!readOnly` | gated, dead until wired |
| Add Note button | DetailPanel.tsx:863-874 | ungated (tab-hiding only) |
| NoteItem Edit/Delete | DetailPanel.tsx:189-262; render :909-914 | NoteItem gate :207 dead |
| Create Relationship | DetailPanel.tsx:793-805 | gated, dead until wired |
| RevisionHistoryPanel | mounted ONLY from History tab DetailPanel.tsx:971-979; Revert buttons RevisionHistoryPanel.tsx:150-163 | no standalone page/route/nav/palette entry — hiding the tab removes the panel; do NOT add readOnly to the panel itself (documented design at DetailPanel.tsx:714-716, 851-853) |
| GraphCanvas FAB/dialog/share | GraphCanvas.tsx:891, 895, 907 | already wired (App.tsx:561-562) |
| CommandPalette chat row | CommandPalette.tsx:111, gated App.tsx:635 | no note/history rows exist |
| NodeSearch Notes & Claims | App.tsx:568-573 | read-only browsing — intentionally kept |

## Visitor test reference patterns

- Visitor entry: App.test.tsx:218-231 (`Continue as visitor` → `Visitor` badge → chat hidden).
- Canvas stub renders one clickable button per node: App.test.tsx:110-114,
  `data-testid="graph-element-{id}"` — click e.g. `graph-element-char_dexter_morgan`
  to open DetailPanel in App-level tests. fetch stub fallback = 401 (App.test.tsx:190).
- readOnly assertions to copy: DetailPanel.test.tsx:338-351 (Notes/History/Add note
  absent; Overview/Backlinks/Claims/Evidence present).
- Commands: `cd frontend && npm run build` (tsc -b typecheck) ;
  `NODE_ENV=test CI=1 npm run test`. Conventions: NO DaisyUI (btn/select classes
  ignored), inline Tailwind, selects `[color-scheme:dark]`.

## GSD quick-mode planning quirks (260813)

- Template `AppData/Local/hermes/gsd-core/templates/plan.md` does NOT exist. Quick
  plan format = planner constraints in `gsd-core/workflows/quick.md` (Step 5):
  1-3 tasks, each with `files`/`action`/`verify`/`done`, target ~30% context,
  non-validate mode does not require must_haves.
- Plan file = `{quick_id}-PLAN.md` under `.planning/quick/{YYYYMMDD-slug}/`
  (quick_id is the `YYMMDD-xxx` prefix, e.g. `260813-ftl`). Repo has no existing
  quick plans to copy from; `.planning/quick/` is empty.
- Executor constraints: atomic per-task commits, code-only; SUMMARY.md with
  `status: complete`; never `git add -A`; docs artifacts committed by orchestrator.

## Tool quirk: search_files absolute paths fail on this Windows host

`search_files` with absolute paths (`C:\Users\...\frontend\src`) errors with
"Sistem belirtilen yolu bulamıyor" (os error 3). Use workspace-RELATIVE paths from
the project cwd (e.g. path=`frontend/src`). Terminal `find`/`ls` accept absolute
paths fine.
