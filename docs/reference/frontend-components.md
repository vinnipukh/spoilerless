<!-- generated-by: gsd-doc-writer -->
# Frontend Component Reference

> **Snapshot (2026-08-12).** Point-in-time component map — verify against the
> live tree before trusting; not regenerated automatically.

This reference describes the live React frontend under `frontend/src`. The application uses React 19, TypeScript, Vite, Vitest, Tailwind CSS, Radix primitives, and Cytoscape. Paths and symbols below match the current source.

## Contents

- [Application composition](#application-composition)
- [State, providers, and hooks](#state-providers-and-hooks)
- [Selection and focus flow](#selection-and-focus-flow)
- [Component groups](#component-groups)
- [Graph architecture](#graph-architecture)
- [Visitor and snapshot behavior](#visitor-and-snapshot-behavior)
- [Shared types and utilities](#shared-types-and-utilities)
- [Testing](#testing)
- [Safe extension points](#safe-extension-points)

## Application composition

`frontend/src/main.tsx` mounts the application in React `StrictMode`. `frontend/src/App.tsx` is the composition root and exports the default `App` component. There is no routing library.

`App` wraps `AppContent` in `AuthProvider`. `AppContent` then chooses among:

1. `ShareView` when `window.location.pathname` matches `/share/:token`; this check happens before the auth gate.
2. A loading screen while auth restoration runs.
3. `LoginPage` for `unauthenticated` and `error` auth states.
4. The internal `AuthenticatedApp` workspace for authenticated users and visitors.

`AuthenticatedApp` owns the cross-component state:

- selected series and episode boundary;
- selected graph node or edge;
- graph focus and transient reveal identifiers;
- graph, timeline, or settings view;
- timeline filters;
- chat, command-palette, dashboard, and share-dialog visibility.

The top-level data chain is:

```text
useAuth
  └─ AuthenticatedApp
      ├─ useSeries
      ├─ useWatchProgress
      │   ├─ useEpisodes(selectedSeriesId, viewAsOfOrder)
      │   └─ useGraph(seriesId, confirmedOrder)
      └─ useNotes(seriesId, confirmedOrder)
```

`AppShell` supplies the page frame and top bar. Navigation among graph, timeline, and settings is state-driven. `SeriesDashboard`, `CommandPalette`, and `ShareDialog` are mounted as overlays/dialogs rather than routes.

## State, providers, and hooks

### Authentication provider

| Symbol | Path | Responsibility |
|---|---|---|
| `AuthProvider` | `frontend/src/providers/AuthProvider.tsx` | Restores `/api/auth/me`, performs Google login/logout, and enters visitor mode. |
| `AuthContext`, `AuthState`, `AuthContextValue` | `frontend/src/providers/AuthContext.ts` | Defines the context and its discriminated auth state. |
| `useAuth` | `frontend/src/providers/useAuth.ts` | Reads `AuthContext` and enforces provider usage. |

`AuthProvider` persists visitor intent in session storage under `spoilerless.visitor`. A successful `/me` response always takes precedence over that flag.

### Data and interaction hooks

Most fetch hooks expose discriminated `idle | loading | success | error` state. Consumers should narrow on `status` before reading `data` or `error`.

| Hook | Inputs | Important output/behavior |
|---|---|---|
| `useSeries` | none | Fetches the series list. |
| `useEpisodes` | `seriesId`, optional `visibleUntilOrder` | Fetches episode metadata with the current boundary so the server can mask spoiler-sensitive titles. |
| `useGraph` | `seriesId`, `visibleUntilOrder` | Returns graph state plus `refetch()` and `refresh()`. `refetch()` re-enters loading; `refresh()` keeps the mounted graph visible during an in-place update. |
| `useWatchProgress` | optional `{ persist?: boolean }` | Owns `seriesId`, `watchedThroughOrder`, `viewAsOfOrder`, `confirmedOrder`, `pendingChange`, `requestChange`, `confirmChange`, and `cancelChange`. |
| `useNotes` | series/boundary and optional target filters | Fetches notes and exposes create/update/delete operations. |
| `useRevisions` | series/boundary/resource filters | Fetches revision history and exposes its status/data/error. |
| `useChatSessions` | `seriesId` | Returns normalized `sessions`, status/error, and `refetch`. |
| `useChatMessages` | `seriesId`, `sessionId`, optional boundary | Loads messages, streams a turn, accumulates citations/graph focus/proposed change set, and exposes `sendMessage` and `stop`. |
| `useHotkey` | key specification, callback, options | Registers keyboard shortcuts; `modLabel` supplies the platform modifier label. |

`useWatchProgress` is the boundary authority in the normal workspace:

- session storage key: `spoilerless.watchProgress`;
- legacy read-migration key: `hdgraf.watchProgress`;
- `watchedThroughOrder`: highest confirmed contiguous watched episode;
- `viewAsOfOrder`: temporary effective spoiler boundary;
- `confirmedOrder`: compatibility alias for `viewAsOfOrder`;
- selecting an already watched episode is a view-only update;
- selecting above the watched boundary creates a `PendingChange` rendered by `ConfirmAdvanceModal`;
- `{ persist: false }` makes changes local-only and bypasses hydration, POSTs, and confirmation.

The hook guards mount-time backend hydration with `userInteractedRef`, preventing a late progress response from overwriting a newer user selection.

## Selection and focus flow

Selection and focus are related but intentionally separate.

### Selection

`GraphCanvas` exports:

- `SelectedNode`;
- `SelectedEdge`;
- `SelectedElement` (`SelectedNode | SelectedEdge`).

A Cytoscape node or edge tap calls `GraphCanvas.onSelect`. `App.tsx` stores the result in `selectedElement` and renders one of two inspectors:

- a structural, non-user edge without `claim_id` goes to `StructuralEdgeCard`;
- nodes, claim-backed edges, and user-origin edges go to `DetailPanel`.

An empty-canvas tap calls `onSelect(null)`, which closes the inspector. Timeline and search selections reuse the same App-level selection shape. `NodeSearch` and `CommandPalette` both call `handleJumpToNode`, which sets both selection and focus.

### Focus

`GraphCanvas` exports `FocusedElementIds`:

```ts
type FocusedElementIds = {
  nodeIds: string[]
  edgeIds: string[]
}
```

App owns external `graphFocus`. Sources include:

- node search and command-palette results;
- chat citations (`handleShowInGraph`);
- an applied `ChangeSet`;
- timeline row selection.

`GraphCanvas` resolves those IDs through Cytoscape, adds `.selected-dominant`, fades the remainder, reveals relevant edge labels, and fits the focused collection with 48 px padding. `GraphFocusIndicator` displays the focused count and clears through `onClearFocus`.

Internal tap focus uses `focusReducer`, `initialFocusState`, and `applyFocusToCytoscape` from `frontend/src/components/graph/focusReducer.ts`. New features should reuse the App-level `selectedElement`/`graphFocus` flow rather than adding a second selection store.

### Reveal flows

There are two transient highlight channels:

- `revealElementIds`: newly created nodes/relationships, framed for 2.2 seconds;
- `newlyRevealedIds`: graph elements exposed by a forward episode advance, highlighted for 4 seconds.

App computes the forward-boundary graph set difference and passes the result into `GraphCanvas`. Relationship creation calls `graphState.refresh()`, clears old focus, and reveals the new relationship and endpoints.

## Component groups

### Authentication — `frontend/src/components/auth`

| Export | Responsibility |
|---|---|
| `LoginPage` | Google credential entry surface plus the visitor-mode action from `useAuth`. |

### Layout — `frontend/src/components/layout`

| Export | Important props and responsibility |
|---|---|
| `AppShell` | Receives `user`, logout/sign-in callbacks, `visitor`, `topBar`, children, and optional palette trigger. Renders the persistent frame and account/visitor controls. |
| `HeaderNavAction` | Reusable top-bar action with `icon`, visible `label`, `ariaLabel`, active state, and click callback. |

### Episode and series selection — `frontend/src/components/episode`

| Export | Important props and responsibility |
|---|---|
| `SeriesSelect` | Controlled series dropdown: `series`, selected `value`, `onSelect`. |
| `EpisodeSelector` | Controlled episode dropdown with current view, `watchedThroughOrder`, and `onSelect`. |
| `ConfirmAdvanceModal` | Opens only for a forward selection above `watchedThroughOrder` and calls `onConfirm` or `onCancel`; backward or already-watched selections are view-only and do not open the modal. |

### Graph — `frontend/src/components/graph`

| Export/file | Responsibility |
|---|---|
| `GraphCanvas` | Cytoscape host and graph interaction coordinator. Owns general `FilterState` internally through `GraphFilterPanel`; its only external filtering prop is `timelineFilterIds`. It also accepts graph data, selection/focus/reveal channels, episodes, read-only mode, sharing, and graph mode. |
| `GraphControls` | Reset/refresh, overview/full mode, path mode, export, and optional share controls. |
| `GraphFilterPanel` | Node-type and edge-family filter controls over `FilterState`. |
| `GraphLegend`, `NodeSwatch` | Node and relationship visual key. |
| `GraphFocusIndicator` | Count and clear action for externally focused elements. |
| `GraphLoadingState`, `GraphErrorState`, `GraphEmptyState` | Fetch lifecycle states used by App. |
| `NodeHoverCard` | Hover details for a graph node. |
| `NodeSearch`, `NodeSearchSelection` | Payload-local node plus notes/claims search; selection is returned to App. |
| `PathFinder`, `PathPick` | Two-node path-picking mode using `frontend/src/api/graph.ts`. |
| `graphToElements` | Converts `GraphResponse` to Cytoscape elements and applies overview projection metadata. |
| `buildGraphStylesheet`, `graphStylesheet` | Cytoscape styling and interaction classes. |
| `overviewProjection`, `displayTierFor`, `GraphMode` | Curated overview/full graph projection. |
| `layoutOptionsFor`, `nodeRepulsionFor` | fcose/cose layout configuration. |
| `initialFilterState`, filter mutators, position-cache functions | Filter state and per-series/boundary/mode position caching. |
| `focusReducer`, `applyFocusToCytoscape` | Internal focus state and Cytoscape class application. |
| `relationshipStyles.ts` | Edge-family classification and color lookup. |
| `autoZoomHold` | Module-level last-touch and viewport state that survives canvas remounts. |

### Detail — `frontend/src/components/detail`

| Export | Important props and responsibility |
|---|---|
| `DetailPanel` | Left non-modal inspector for nodes and claim-backed/user edges. Resolves overview, backlinks, notes, history, claims, and evidence from `GraphResponse` plus hooks. Supports Markdown export and relationship creation. |
| `StructuralEdgeCard` | Compact read-only presentation for structural edges that do not carry a claim. |
| `BacklinksTab` | Computes and displays backlinks for the current selection using graph data and notes. |
| `RevisionHistoryPanel`, `DiffDetail` | Resource revision list, diff display, and revert interaction. |

`DetailPanel` accepts `readOnly`, `onSelectNode`, `onRefreshGraph`, and `onRelationshipCreated` as extension seams. It self-wraps in `TooltipProvider`; adding a Radix tooltip to a sibling component requires its own provider or a verified common ancestor.

### Chat — `frontend/src/components/chat`

| Export | Responsibility |
|---|---|
| `ChatSheet` | Independent right-side non-modal sheet; wraps `ChatPanel` in `ErrorBoundary`. |
| `ChatPanel` | Session selection, message composition, streaming lifecycle, provider error states, suggestions, and callbacks into graph selection/focus. |
| `SessionPicker` | Selects, creates, and deletes conversations. |
| `MessageList` | Renders stored/streaming/failed turns, citations, and a proposed change set. |
| `MessageBubble`, `StreamingMessageBubble`, `ThinkingBubble`, `FailedMessageBubble` | Message-state presentations. |
| `CitationChip` | Opens referenced detail or requests graph focus. |
| `ChangeSetCard` | Confirms/rejects a proposed `ChangeSet` and reports successful application. |
| `ChatLauncher` | Top-bar chat toggle built on `HeaderNavAction`. |

`ChatPanel` creates a `New conversation` session on demand, prevents concurrent sends while streaming, and maps API error codes to disabled, unavailable, busy, retryable, or non-retryable UI states. `useChatMessages` owns the `AbortController` used by Stop.

### Search and command palette — `frontend/src/components/palette`

`CommandPalette` exposes `CommandPaletteSelection` and receives graph data, episodes, node/episode callbacks, and action callbacks. It shares `searchIndex` with `NodeSearch`. The optional `onOpenChat` prop controls whether the chat action exists, which is how App removes that action for visitors.

App registers:

- `mod+k`: toggle palette;
- `Escape`: close palette;
- `/`: focus `NodeSearch` when the graph is active and no input owns focus.

### Timeline and dashboard

| Export | Path | Responsibility |
|---|---|---|
| `TimelineView`, `TimelineSelection` | `frontend/src/components/timeline/TimelineView.tsx` | Builds an episode-oriented event view from graph nodes/claims and supports selected event filters. |
| `TimelineEventRow` | `frontend/src/components/timeline/TimelineEventRow.tsx` | One timeline row with selection and optional graph-filter toggle. |
| `SeriesDashboard` | `frontend/src/components/series/SeriesDashboard.tsx` | Dialog-based series overview that reports a selected series through `onOpenSeries`. |

Timeline selections return through App's existing node selection/focus path. `timelineFilterIds` is passed back into `GraphCanvas`, which hides nodes outside selected event neighborhoods.

### Settings, share, and error containment

| Export | Path | Responsibility |
|---|---|---|
| `SettingsPage` | `frontend/src/components/settings/SettingsPage.tsx` | Local BYOK LLM settings editor using `getStoredLLMSettings` and `saveLLMSettings`. |
| `ShareDialog` | `frontend/src/components/share/ShareDialog.tsx` | Creates and manages boundary-pinned snapshot links. |
| `ShareView` | `frontend/src/components/share/ShareView.tsx` | Public `/share/:token` loader and minimal read-only graph shell. |
| `ErrorBoundary` | `frontend/src/components/ErrorBoundary.tsx` | Class-based component error boundary with configurable fallback copy. |

### UI primitives — `frontend/src/components/ui`

The UI layer exports local wrappers for `Alert`, `Badge`, `Button`, cards, collapsibles, dialogs, scroll areas, selects, separators, sheets, skeletons, tabs, textareas, and tooltips. `SpoilerGuard` is application-specific: it renders text according to revealed/current order. Compose these wrappers instead of importing a second primitive system.

## Graph architecture

`GraphResponse` from `frontend/src/types/graph.ts` is the frontend graph boundary. It contains `series`, `visible_until_order`, `nodes`, `edges`, `claims`, `sources`, and `evidence`. `GraphNode`, `GraphEdge`, `GraphClaim`, `GraphSource`, `GraphEvidence`, and `PathResponse` are exported from the same module.

The rendering pipeline is:

```text
GraphResponse
  └─ graphToElements(graph, mode)
      ├─ overviewProjection(graph) when mode === 'overview'
      └─ Cytoscape elements
          ├─ buildGraphStylesheet(prefersReducedMotion)
          └─ layoutOptionsFor(layoutName, prefersReducedMotion, mode, fit)
```

`GraphCanvas` defaults to `initialMode="overview"`; full mode renders all already spoiler-filtered elements. fcose is the primary layout, with built-in cose as runtime fallback. Position cache keys include series, visible boundary, and graph mode.

A fresh Cytoscape instance forces a layout and fit. Graph-driven relayout respects a 20-second interaction hold stored in `autoZoomHold`; explicit mode changes and refreshes still re-fit. Incremental updates with active focus/reveal avoid destructive relayout and use Cytoscape framing instead.

Graph mutations currently enter through:

- custom-node creation inside `GraphCanvas`;
- custom-relationship creation inside `DetailPanel`;
- note mutation inside `DetailPanel`;
- revision revert inside `RevisionHistoryPanel`;
- proposed changes through `ChangeSetCard`.

Use `useGraph.refresh()` after an in-place mutation when preserving the mounted Cytoscape viewport matters. Reserve `refetch()` for loading/error recovery or flows that intentionally remount.

## Visitor and snapshot behavior

### Visitor auth state

`AuthState` includes `visitor`. In App, visitor mode:

- calls `useWatchProgress({ persist: false })`;
- seeds the first available series at order 1 when no local series exists;
- does not render `ChatLauncher` or `ChatSheet`;
- omits the command-palette chat action;
- passes `readOnly` to `GraphCanvas`;
- exposes a visitor badge/sign-in path through `AppShell`.

`GraphCanvas.readOnly` hides custom-node creation and suppresses its share-link callback. It does not alter server data; it only removes those frontend affordances.

**Current integration note:** `DetailPanel` supports a `readOnly` prop that hides relationship creation plus Notes and History tabs, but the current `App.tsx` `DetailPanel` call does not pass `readOnly={isVisitor}`. Because the prop defaults to `false`, those inspector affordances are not currently suppressed by App-level visitor wiring. Treat the backend's write authorization as the final guard and pass this existing prop when fixing or extending visitor behavior.

### Shared snapshot

`ShareView` is reachable before authentication, fetches through `getShareGraph(token)`, and renders `GraphCanvas` with `readOnly={true}`, no episodes, and a no-op selection callback. It displays a fixed snapshot boundary and does not mount App's detail, chat, progress, settings, dashboard, or mutation flows.

## Shared types and utilities

| Module | Main exports |
|---|---|
| `frontend/src/types/auth.ts` | `User`, `UserResponse`, `GoogleAuthRequest` |
| `frontend/src/types/series.ts` | `SeriesResponse`, `EpisodeResponse` |
| `frontend/src/types/graph.ts` | Graph payload entities and `PathResponse` |
| `frontend/src/types/chat.ts` | `Citation`, `GraphFocus`, messages, sessions, response envelope |
| `frontend/src/types/changeSet.ts` | Typed change-set status and operation union |
| `frontend/src/types/userContent.ts` | Notes, custom nodes, and custom relationships request/response types |
| `frontend/src/types/revision.ts` | `RevisionAction`, `RevisionResponse` |
| `frontend/src/types/settings.ts` | `LLMProvider`, `StoredLLMSettings` |
| `frontend/src/types/share.ts` | Share-token request/response/item types |
| `frontend/src/lib/searchIndex.ts` | `searchIndex` and its collection/result/options types |
| `frontend/src/lib/nodeTypes.ts` | `NODE_TYPES`, `NodeTypeMeta` |
| `frontend/src/lib/exportMarkdown.ts` | `renderGraphMarkdown`, `exportFilename` |
| `frontend/src/lib/byok.ts` | BYOK storage/header functions and `BYOK_STORAGE_KEY` |
| `frontend/src/lib/utils.ts` | `cn` class-name merge helper |

Cytoscape plugin declarations live in `frontend/src/types/cytoscape-fcose.d.ts` and `frontend/src/types/cytoscape-cose-bilkent.d.ts`.

## Testing

Vitest uses jsdom. Configuration is in `frontend/vite.config.ts`; global test setup is `frontend/src/test/setup.ts`. Shared fixtures live in:

- `frontend/src/test/fixtures/graphResponse.ts`;
- `frontend/src/test/fixtures/chatFixtures.ts`.

Tests are colocated with source:

- component tests: `frontend/src/components/**/*.test.tsx`;
- hook tests: `frontend/src/hooks/*.test.ts` and `*.test.tsx`;
- API tests: `frontend/src/api/*.test.ts`;
- library tests: `frontend/src/lib/*.test.ts`;
- App integration tests: `frontend/src/App.test.tsx`.

Graph coverage is split across `GraphCanvas.test.tsx`, pure transform/style/layout tests such as `graphElements.test.ts`, `overviewTiers.test.ts`, `layoutConfig.test.ts`, and `relationshipStyles.test.ts`. Cytoscape behavior in component tests uses fakes/stubs, so new calls on `cy`, nodes, edges, layouts, or collections must be added to the relevant test doubles.

Canonical frontend commands from `frontend/package.json` are:

```bash
cd frontend
npm run test -- --run
npm run lint
npm run build
```

`npm run build` runs `tsc -b && vite build`; use it as the final TypeScript gate because it also checks test files included by the project references.

## Safe extension points

- **New top-bar action:** use `HeaderNavAction` and lift its state/callback into `AuthenticatedApp`.
- **New workspace view:** extend App's `view` union and conditional body; do not add a router solely for state-driven views. Reserve the existing pathname check pattern for genuinely public URL entry points.
- **New graph-originated selection:** return `SelectedElement` through `onSelect`; for search/chat-style framing, set `FocusedElementIds` through App.
- **New mutation:** call `useGraph.refresh()` on success when viewport/layout preservation is required, and provide explicit reveal/focus IDs when the result should be framed.
- **New graph style/filter/layout behavior:** extend `graphElements.ts`, `graphStylesheet.ts`, `filterState.ts`, `focusReducer.ts`, or `layoutConfig.ts` rather than adding more policy to `GraphCanvas.tsx`.
- **New payload-local search collection:** extend `SearchCollection`, `SearchResult`, and `searchIndex`; keep `NodeSearch` and `CommandPalette` on the shared index.
- **New visitor-sensitive action:** make the action callback optional or accept `readOnly`, hide the affordance, and still rely on backend authorization. Verify App actually threads the prop.
- **New Radix tooltip:** ensure a `TooltipProvider` is in that component's real ancestor tree; providers in sibling components do not apply.
- **New async hook:** follow the existing discriminated status shape, cancel stale effects, and preserve the distinction between destructive `refetch` and in-place `refresh` where applicable.
- **New Cytoscape API use:** update `GraphCanvas.test.tsx` stubs and run the pure graph transform tests plus the full TypeScript build.
