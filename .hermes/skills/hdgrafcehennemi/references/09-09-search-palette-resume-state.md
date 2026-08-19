# 09-09 search + command palette — budget-handoff resume state (2026-08-05)

Plan 09-09 (FEAT-01 node search, FEAT-07 notes & claims search, FEAT-08 ⌘K
palette) is frontend-only and payload-local: `frontend/src/lib/searchIndex.ts`
over the already-boundary-filtered GraphResponse + notes. **No backend
endpoint** (UI-SPEC §10.9 "no new endpoint, no new spoiler surface" — a
parent prompt mentioning "backend search endpoint + targeted pytest" is
stale; the plan frontmatter's NO-NEW-SPOILER-SURFACE prohibition wins).

## Committed

- `fa28282` — `feat(09-09): node search + notes&claims search (FEAT-01/07)`.
  5 files: `lib/searchIndex.ts` (+`searchIndex.test.ts` 9 tests),
  `components/graph/NodeSearch.tsx` (+`NodeSearch.test.tsx` 8 tests),
  `GraphLegend.tsx` (exported `NODE_TYPES`/`NodeSwatch`/`NodeTypeMeta` —
  additive, required for search-row swatches).
- Verified pre-commit: targeted vitest 17/17 green; `npm run build` green.

## Uncommitted Task 2 files (on disk, NOT committed)

- `frontend/src/hooks/useHotkey.ts` (NEW) + `useHotkey.test.ts` (NEW, 7 tests)
- `frontend/src/components/palette/CommandPalette.tsx` (NEW) + `CommandPalette.test.tsx` (NEW, 7 tests)
- `frontend/src/App.tsx` (MOD) — paletteOpen state, `useHotkey('mod+k'|'escape'|'/')`,
  `handleJumpToNode` (setSelectedElement + setGraphFocus — reuses existing
  focus path), seams `handleOpenTimeline`/`handleOpenDashboard`/`handleExportGraph`
  (no-op, filled by later plans), NodeSearch + CommandPalette rendered,
  `onOpenPalette` passed to AppShell
- `frontend/src/components/layout/AppShell.tsx` (MOD) — Command icon trigger
  via `HeaderNavAction` (label = `${modLabel()}K`)
- `frontend/src/components/graph/GraphFocusIndicator.tsx` (MOD) — copy
  `"Highlighting {N}"` (was "…from chat"; search-driven focus isn't chat)
- `frontend/src/App.test.tsx` + `frontend/src/components/graph/GraphCanvas.test.tsx`
  (MOD) — 5 assertions updated to the new indicator copy

## Verified before the last refactor

- useHotkey + CommandPalette tests: 14/14 green
- FULL suite: 249/249 green (after copy-assertion updates)
- lint: 2 errors + build: 2 TS2339 — all fixed by the final patches
  (removed unused `notes` prop from CommandPalette; narrowed SearchResult
  union via `if (result.collection !== 'nodes') continue` — do NOT cast)

## Remaining steps (exact)

1. `frontend/src/components/palette/CommandPalette.test.tsx` line ~58: the
   ⌘K-opens Harness still passes `notes={[]}` to `<CommandPalette …>` —
   delete that prop (source no longer accepts it; the only remaining TS error).
2. `cd frontend && NODE_ENV=test CI=1 npx vitest run` (expect 249/249),
   `npm run lint` (0 errors), `npm run build` (green).
3. Commit Task 2 — stage EXPLICIT paths (never `-A`; `.planning/config.json`
   sits dirty):
   `feat(09-09): command palette ⌘K (FEAT-08) + useHotkey + App wiring`
4. Grep gates: `rg -n "fuse" frontend/package.json frontend/src` = 0 hits;
   `rg -n "requestChange" frontend/src/components/palette/CommandPalette.tsx`
   hits via the `onRequestChange` prop name (App passes `handleEpisodeSelect`
   → `watchProgress.requestChange` — locked episodes route to the unlock
   dialog per PROB-31).
5. Write `09-09-SUMMARY.md` (template `~/AppData/Local/hermes/gsd-core/templates/summary.md`),
   commit `docs(09): summary for 09-09`, then stage
   `.planning/STATE.md` + `.planning/ROADMAP.md` + summary explicitly and
   commit tracking (house pattern; never `.planning/config.json`).
6. Return `## EXECUTION COMPLETE` with SHAs + test counts.

## Pitfalls that cost time this session (durable)

- Radix `ToggleGroup` items = `role="radio"`/`radiogroup`, NOT buttons.
- Palette node group is empty until a query is typed (searchIndex returns []
  on empty needle) — don't assert "Jump to node" on an empty query.
- write_file "lint error TS5112" (`tsc --noEmit <file>` + tsconfig present)
  is tooling noise; file writes fine (`verified: true`).
- App.test fetchStub default → `notFoundResponse()`; a new useNotes mount in
  App 404s → caught → error state → `notes=[]`. Safe.
