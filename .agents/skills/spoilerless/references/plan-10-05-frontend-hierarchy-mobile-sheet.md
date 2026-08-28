# 10-05 Frontend Hierarchy & Mobile Inspector Sheet — Patterns and Pitfalls

Plan 10-05: four-tab narrative hierarchy (Story/Characters/Evidence/Advanced)
+ responsive mobile Inspector bottom sheet + accessibility/copy coverage.
Frontend-only (vitest + npm run build). The durable patterns below apply to
later phase-10 plans (10-06/10-07 wire the same tabs' real content).

## Preserving scene state across navigation (D-47)

- Radix `TabsContent` UNMOUNTS inactive panels. Any stateful surface inside it
  (GraphCanvas holds filterState/camera internally; DetailPanel selection lives
  in App) silently resets on tab switch — violates "views do not silently reset
  Filters".
- Correct shape: render `Tabs`/`TabsList`/`TabsTrigger` for the semantics
  (role=tab, aria-selected, roving tabindex) but keep the shared workspace as a
  SIBLING outside the Tabs root; only light mode-bars/notices live inside
  `TabsContent`. Nested mode state (storyMode/characterMode/evidenceMode/
  advancedMode) lives in App useState, defaulting per tab and never reset on
  switch.
- Story timeline = coordinated right rail (`<aside aria-label="Event Timeline">`,
  `hidden lg:flex`, w-80) beside the STILL-MOUNTED canvas; `hidden lg:flex`
  keeps ONE primary region on narrow screens (D-20). TimelineView gained an
  optional `showHeading` prop that renders the heading in BOTH zero and
  populated states (UI-SPEC zero/one/many layout contract).

## Shared selection without layout (D-38)

- A timeline row select must NOT `setView('graph')`: that unmounts/remounts
  GraphCanvas → relayout + camera loss. Use a selection-only handler
  (setSelectedElement) so graph/timeline/Inspector converge on ONE selection.
  Keep the legacy jump-to-graph handler only for the legacy full-screen
  timeline surface.
- App.test.tsx proves "no layout calls" via `graphStubHooks.layoutRuns` — reset
  to 0 after the initial canvas mount, assert 0 after interactions.

## Radix test pitfalls (accessible-name collisions)

- Top-tab labels that repeat as nested-mode labels (Evidence, Answer Graph) or
  as DetailPanel Inspector tabs (Evidence) make `getByRole('tab', {name})` /
  `getByText` ambiguous once a node is selected. Use `getAllByText().length`,
  `{ selected: true }`, or `within()` scoping.
- The App react-cytoscapejs stub renders one BUTTON per node labelled with the
  node label — timeline rows duplicate those labels. Scope rail queries:
  `within(screen.getByRole('complementary', { name: 'Event Timeline' }))`.

## Non-modal Radix Sheet Escape/focus contract (D-45)

- Two coexisting non-modal sheets (left inspector + right chat): each Radix
  DismissableLayer handles Escape independently. To make Escape close the
  inspector while chat stays open, REMOVE `onEscapeKeyDown preventDefault` from
  the inspector (Radix then calls `onOpenChange(false)` → `onDeselect()`); the
  chat sheet keeps its own preventDefault.
- Return focus: open-controlled sheets have no Radix trigger to restore focus
  to. Capture `document.activeElement` in a `useEffect` on open, restore +
  clear in the close branch. Effect-scoped ref reads/writes keep the
  react-hooks/refs lint rule clean — this codebase forbids ref reads during
  render (use the "state copy" pattern for render-phase adjustments instead).
- Mobile bottom sheet: keep desktop side-panel classes, add `max-sm:` overrides
  (inset-x-0 bottom-0 w-full border-t; half 55vh / full 90vh via a
  `sheetExpanded` state), `max-sm:pb-[env(safe-area-inset-bottom)]`, drag handle
  `h-1 w-11` (4×44px, aria-hidden), close + expand buttons `size-11` (44px) with
  `hidden max-sm:inline-flex`, and a `data-sheet-height="half|full"` attribute
  on SheetContent so jsdom tests can assert the state without CSS media
  queries. UI-SPEC Spacing: mobile sheet drag handle is 44px wide × 4px high.

## Windows git-bash execution quirks (this machine)

- Passing MSYS `$HOME`-derived paths to node mangles them
  (`Cannot find module 'C:\c\Users\...'`). Use native `C:/Users/...`
  forward-slash paths.
- search_files (ripgrep) can return "IO error ... Sistem belirtilen yolu
  bulamıyor" for files that DO exist; fall back to terminal `grep -n`.
- gsd-tools shim lives at
  `C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs` (not in the
  repo). `node <shim> query requirements.ready-ids <plan-path> <REQ>... --raw`
  prints "N/N requirement(s) ready to mark complete".
- Local npm config omits dev deps: if vitest is missing,
  `npm --prefix frontend install --include=dev`.
