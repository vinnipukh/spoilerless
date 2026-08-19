# frontend-components.md doc facts (verified 2026-08-14)

`docs/reference/frontend-components.md` (360 lines, snapshot dated 2026-08-13) verified
against live `frontend/src`: **189 checked / 187 passed / 2 failed**. Artifact:
`.planning/tmp/verify-frontend-components.md.json`. NOTE: an older baseline
`.planning/tmp/verify-FRONTEND-COMPONENTS.json` (pre-`<doc>.md` naming) is SUPERSEDED —
compare re-verifies against the new artifact.

## Live-drift failures (2) — re-check each pass
- **L183**: doc row "`buildGraphStylesheet`, `graphStylesheet`" — `frontend/src/components/graph/graphStylesheet.ts`
  exports ONLY `buildGraphStylesheet`; no standalone `graphStylesheet` identifier exists anywhere
  in `src` (only filename mentions in comments). The second named export claimed does not exist.
- **L294 "current integration note"**: doc claims App.tsx's `<DetailPanel>` call does NOT pass
  `readOnly={isVisitor}` (so Notes/History/relationship-creation stay visible for visitors).
  LIVE App.tsx DOES pass `readOnly={isVisitor}` → the note is stale; visitor wiring now suppresses
  those affordances. Doc must be updated or the note removed.

## Verified facts (reuse instead of re-deriving)
- Hook call sites (App.tsx): `useWatchProgress({ persist: !isVisitor })`,
  `useEpisodes(selectedSeriesId, watchProgress.viewAsOfOrder)`,
  `useGraph(watchProgress.seriesId, watchProgress.viewAsOfOrder)`,
  `useNotes({ seriesId: watchProgress.seriesId, visibleUntilOrder: watchProgress.confirmedOrder })`.
  Doc's data-chain diagram says `useGraph(seriesId, confirmedOrder)` — PASSes because the doc itself
  defines `confirmedOrder` as the alias of `viewAsOfOrder` (useWatchProgress.ts:
  `confirmedOrder: state.viewAsOfOrder`). Adjudicate alias claims via the doc's own definitions.
- All fetch hooks delegate to `hooks/useFetchState.ts`: discriminated `FetchState<T>` union
  `idle|loading|error|success` + `refetch`. useGraph: `refetch` = key-bump that re-enters
  'loading'; `refresh` = in-place no-status-flip (mounted graph stays visible).
- `GraphLoadingState`/`GraphErrorState`/`GraphEmptyState` are exports of
  `components/graph/GraphStatus.tsx` (imported by App.tsx) — NOT separate files. When a doc names
  components, grep the whole src tree; the file name may differ from the component name.
- `GraphFocusIndicator` props are `{count, onClear}`; the App-level wiring prop is
  `onClearFocus={handleClearFocus}` (a GraphCanvas prop). Doc's "clears through onClearFocus"
  PASSes: the identifier exists in the flow, not in the component file.
- Storage keys: AuthProvider `VISITOR_STORAGE_KEY = 'spoilerless.visitor'` (sessionStorage;
  a successful `/me` always wins over the flag — comment + only the AUTH_UNAUTHENTICATED branch
  honors the flag); useWatchProgress `spoilerless.watchProgress` + legacy `hdgraf.watchProgress`.
- Reveal timings (GraphCanvas.tsx): `revealElementIds` framed 2200ms; `newlyRevealedIds`
  `.newly-revealed` glow 4000ms (App computes the payload diff). Focus fit `cy.fit(focused, 48)`;
  GraphControls `cy.fit(undefined, 48)`.
- Layout pipeline: react-cytoscapejs declarative startup layout `fit:false`; the `cy` callback
  `cy.one('layoutstop', refreshAfterStartup)` then runs the forced `runLayout(..., forceRelayout, ...)`
  (two-stage intent per GraphCanvas comments; comment "starts this before invoking its cy callback").
  `layoutOptionsFor(name, prefersReducedMotion = false, mode = 'full', fit = true)` — first param
  named `name`, NOT `layoutName`; doc claim PASSes on signature shape. Layout union is now
  `'fcose' | 'cose-bilkent' | 'cose' | 'dagre'` (Phase 10: dagre rankDir LR for investigation view).
- Position cache (filterState.ts): `getCachedPositions(seriesId, visibleUntilOrder, mode, viewKey?)`,
  key `${seriesId}:${visibleUntilOrder}:${mode}` (scene variant `${seriesId}:${viewKey}`) — matches
  doc's "series, visible boundary, graph mode".
- Mutation entry points: `handleRelationshipCreated` (App.tsx) = `graphState.refresh()` +
  `handleClearFocus()` + `setRevealIds({nodeIds:[rel.source, rel.target], edgeIds:[rel.id]})`;
  custom node via GraphCanvas `createCustomNode`; inspector routing condition =
  `kind==='edge' && claim_id == null && origin !== 'user'` → StructuralEdgeCard, else DetailPanel;
  share gate = `window.location.pathname.match(/^\/share\/([A-Za-z0-9_-]+)$/)` BEFORE auth checks
  (`if (state.status === 'loading')`, then `'unauthenticated' || 'error'` → LoginPage).
- ShareView imports ONLY `getShareGraph` + `GraphCanvas`; renders
  `<GraphCanvas graph={graph} seriesId={graph.series.id} episodes={[]} onSelect={() => {}} readOnly={true} />`.
- Visitor mode (App.tsx): `useWatchProgress({persist: !isVisitor})`; seeds first series at order 1
  via `visitorSeededRef` + `watchProgress.requestChange(firstSeries.id, 1)`; `{!isVisitor && <ChatLauncher>}`
  and `{!isVisitor && <ChatSheet>}`; `onOpenChat={isVisitor ? undefined : ...}` on CommandPalette;
  `readOnly={isVisitor}` on BOTH GraphCanvas and DetailPanel; `visitor={isVisitor}
  onSignIn={isVisitor ? logout : undefined}` on AppShell.
- Hotkeys (App.tsx): `useHotkey('mod+k', ...)`, `useHotkey('escape', () => setPaletteOpen(false))`
  (lowercase 'escape'), `useHotkey('/', ...)`.
- Types modules: userContent.ts = NoteResponse/Create/Update, CustomNode{Create,Update,Response},
  CustomRelationship{Create,Update,Response} (CustomNodeType re-exported from lib/nodeTypes);
  share.ts = ShareTokenCreateRequest/Response + ShareTokenItem; changeSet.ts = typed status +
  operation union; settings.ts = LLMProvider/StoredLLMSettings; byok.ts = BYOK_STORAGE_KEY +
  getStoredLLMSettings/saveLLMSettings.
- Commands (frontend/package.json): `test` = "vitest", `lint` = "eslint .",
  `build` = "tsc -b && vite build" (verbatim). Deps: react ^19.2.7, radix-ui ^1.6.7, cytoscape,
  cytoscape-fcose, cytoscape-cose-bilkent, react-cytoscapejs ^2.0.0, jsdom ^30.0.1. NO router dep.
- Phase 10 files exist but are NOT documented in frontend-components.md (no claims to fail):
  `components/graph/cytoscapeReconciler.ts`, `components/graph/AnswerGraph.tsx`,
  `components/graph/GraphStatus.tsx`, `hooks/useSceneState.ts`, `lib/visualizationAdapter.ts`,
  `lib/graph/highlight.ts`, `components/evidence/EvidenceChain.tsx`. If a future doc-writer pass
  adds these, verify them against this list.
