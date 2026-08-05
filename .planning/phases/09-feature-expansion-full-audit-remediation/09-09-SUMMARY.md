---
phase: 09-feature-expansion-full-audit-remediation
plan: 09
type: execute
status: complete
executed_by: gsd-executor (deleg_292f7e41 — Task 1 committed, Task 2 partial) + orchestrator inline completion (Task 2 fixes, verification, SUMMARY)
---

# Phase 09 — Plan 09-09 Summary: Search + command palette

## Objective

FEAT-01 (series-wide entity search), FEAT-07 (⌘K command palette),
FEAT-08 (episode quick-switcher). ZERO-COST: payload-local search, no new
endpoint (UI-SPEC §10.9: "no new spoiler surface"), fuse.js FORBIDDEN.

## Commits

| Task | SHA | Message |
|------|-----|---------|
| 1 | `fa28282` | feat(09-09): payload-local search index + NodeSearch UI (FEAT-01/07) |
| 2 | `0896725` | feat(09-09): command palette ⌘K (FEAT-08) + useHotkey + App wiring |

## What shipped

### Task 1 — search index + NodeSearch (`fa28282`, executor)
- `frontend/src/lib/searchIndex.ts` (NEW): pure zero-dep substring index over
  nodes (label + id secondary), claims (label/predicate/object label), notes
  (content); ranked, ≤8/collection, collection tags `nodes|claims|notes`;
  payload-local — no fetch, no new endpoint, no new spoiler surface
- `frontend/src/lib/searchIndex.test.ts` (NEW, 9 tests)
- `frontend/src/components/graph/NodeSearch.tsx` (NEW): UI-SPEC 10.3/10.9 bar
  — mode ToggleGroup (EpisodeSelector pill contract), grouped sticky
  Claims/Notes headers, locked empty copy verbatim (`No nodes match
  "{query}"` / `Try a different name, or search Notes & Claims.`),
  Enter/click select via `onSelect`, Esc closes
- `frontend/src/components/graph/NodeSearch.test.tsx` (NEW, 8 tests incl.
  no-fetch assertion)
- `GraphLegend.tsx`: exported NODE_TYPES + NodeSwatch for search rows

### Task 2 — command palette (`0896725`, executor partial + orchestrator fixes)
- `frontend/src/hooks/useHotkey.ts` + tests (NEW, 7 tests): ⌘K / `/` /
  Esc handling
- `frontend/src/components/palette/CommandPalette.tsx` + tests (NEW, 7
  tests): Dialog-style overlay, groups "Jump to node" / "Switch episode" /
  "Actions"; node rows share payload-local searchIndex; episode rows route
  through `onRequestChange` prop → App wires to `watchProgress.requestChange`
  (PROB-31: locked episodes → unlock dialog, never silent no-op); action
  rows: chat/timeline/settings/dashboard + export seam; ↑/↓/Enter/Esc
- `App.tsx`: ⌘K hotkeys, `/` → search focus, `handleJumpToNode` reuses
  onSelect + graphFocus/cy.fit — NO second selection mechanism; episode
  switch → `handleEpisodeSelect` → `watchProgress.requestChange`; palette
  mounted in all views
- `AppShell.tsx`: Command icon trigger via HeaderNavAction
- `GraphFocusIndicator.tsx`: copy `Highlighting {N}` (old "from chat" text
  was wrong — search/palette now drive focus)
- **Orchestrator fixes** (build/lint were RED on the executor's partial):
  - `NODE_TYPES`/`NodeTypeMeta` moved to new `lib/nodeTypes.ts` (GraphLegend
    must stay components-only for react-refresh/only-export-components);
    NodeSearch + CommandPalette re-pointed
  - `Row` node variant narrowed via `Extract<SearchResult, {collection:
    'nodes'}>` (TS2339 on `row.node.nodeType`)
  - `ComponentType` type-only import (verbatimModuleSyntax)
  - Stray `notes={[]}` prop removed from CommandPalette.test.tsx Harness

## Verification (real runs)

- Full vitest: **249/249** (32 files)
- `npm run lint`: **0 errors**
- `npm run build` (tsc -b + vite): **green** (pre-existing chunk-size warning)
- Grep gates: `rg "fuse" frontend/src` — only the FORBIDDEN-comment; palette
  `requestChange` is prop/doc only (App wiring owns the call)
- No backend changes (search is payload-local per UI-SPEC §10.9)

## Self-Check

✅ PASS — all tasks complete, zero new deps, zero new endpoints, lint+build
green, no `.planning/config.json` or `.env` touched.

*Completed: 2026-08-05 (executor + orchestrator closeout)*
