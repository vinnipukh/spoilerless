import { useEffect, useRef, useState } from 'react'
import { AuthProvider } from './providers/AuthProvider'
import { useAuth } from './providers/useAuth'
import { LoginPage } from './components/auth/LoginPage'
import { AppShell } from './components/layout/AppShell'
import { HeaderNavAction } from './components/layout/HeaderNavAction'
import { SeriesSelect } from './components/episode/SeriesSelect'
import { EpisodeSelector } from './components/episode/EpisodeSelector'
import { ConfirmAdvanceModal } from './components/episode/ConfirmAdvanceModal'
import { GraphCanvas, type FocusedElementIds, type SelectedElement } from './components/graph/GraphCanvas'
import { NodeSearch } from './components/graph/NodeSearch'
import { CommandPalette, type CommandPaletteSelection } from './components/palette/CommandPalette'
import { TimelineView } from './components/timeline/TimelineView'
import { SeriesDashboard } from './components/series/SeriesDashboard'
import { GraphLoadingState, GraphErrorState, GraphEmptyState } from './components/graph/GraphStatus'
import { DetailPanel } from './components/detail/DetailPanel'
import { StructuralEdgeCard } from './components/detail/StructuralEdgeCard'
import { ChatLauncher } from './components/chat/ChatLauncher'
import { ChatSheet } from './components/chat/ChatSheet'
import { SettingsPage } from './components/settings/SettingsPage'
import { ShareDialog } from './components/share/ShareDialog'
import { ShareView } from './components/share/ShareView'

import { useSeries } from './hooks/useSeries'
import { useEpisodes } from './hooks/useEpisodes'
import { useGraph } from './hooks/useGraph'
import { useNotes } from './hooks/useNotes'
import { useWatchProgress } from './hooks/useWatchProgress'
import { useHotkey } from './hooks/useHotkey'
import type { CustomRelationshipResponse } from './types/userContent'
import type { Citation } from './types/chat'
import type { ChangeSet } from './types/changeSet'
import type { GraphResponse } from './types/graph'

// Inline SVG gear icon for the topBar Settings toggle (matches the inline
// icon pattern used by AppShell's UserIcon and ChatLauncher).
function SettingsIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4 shrink-0"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

// Inline SVG calendar-clock icon for the topBar Timeline toggle (FEAT-02).
function CalendarClockIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4 shrink-0"
    >
      <path d="M21 7.5V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3.5" />
      <path d="M16 2v4" />
      <path d="M8 2v4" />
      <path d="M3 10h5" />
      <path d="M17.8 11.2a2 2 0 1 0 2.4 3.2" />
      <path d="M18 16v-2.5" />
      <path d="M18 22a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
      <path d="M18 16.5v1.5l1 1" />
    </svg>
  )
}

// Inline SVG layout-grid icon for the topBar Series Dashboard toggle
// (FEAT-04).
function LayoutGridIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4 shrink-0"
    >
      <rect width="7" height="7" x="3" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="14" rx="1" />
      <rect width="7" height="7" x="3" y="14" rx="1" />
    </svg>
  )
}

function AuthenticatedApp() {
  const { state, logout } = useAuth()
  const user = state.status === 'authenticated' ? state.user : undefined
  // Quick task 260805-te3: read-only visitor (misafir) mode — the graph
  // stays fully browsable (all GET routes are anonymous) but every write
  // affordance is hidden and progress changes stay purely local.
  const isVisitor = state.status === 'visitor'

  const seriesState = useSeries()
  const watchProgress = useWatchProgress({ persist: !isVisitor })
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(watchProgress.seriesId)
  const episodesState = useEpisodes(selectedSeriesId, watchProgress.viewAsOfOrder)
  const graphState = useGraph(watchProgress.seriesId, watchProgress.confirmedOrder)
  // PROB-09/#74: the last successfully loaded graph survives refetch and
  // boundary loads so GraphCanvas never unmounts (loading/error render as
  // an OVERLAY above it — no destructive unmount + full relayout on every
  // refresh, and the autoZoomHold/positionCache module-level singletons
  // lose their reason to exist). PROB-10/#16: kept as a guarded render-phase
  // state update — the React 19 `react-hooks/refs` rule forbids ref reads in
  // render, and `setState` during render (when the value changed) is the
  // sanctioned alternative with identical single-paint semantics.
  const [activeGraph, setActiveGraph] = useState<GraphResponse | null>(null)
  const graphData = graphState.status === 'success' ? graphState.data : null
  if (graphData && activeGraph !== graphData) {
    setActiveGraph(graphData)
  }
  // FEAT-07 (09-09): raw notes for the current series, fed to NodeSearch's
  // Notes & Claims mode (search is payload-local over already-filtered
  // data — the hook already exposes the raw list via `data`).
  const notesState = useNotes({ seriesId: watchProgress.seriesId, visibleUntilOrder: watchProgress.confirmedOrder })
  const notes = notesState.status === 'success' ? notesState.data : []
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null)

  // Quick task 260805-te3: a visitor has no persisted progress record (the
  // progress GET/POST routes are auth-gated → 401 anonymous) — seed the
  // first series at order 1 with a purely local view so the canvas renders
  // immediately instead of an empty state. Guarded by a ref so a later
  // series change (dropdown) never re-seeds.
  const visitorSeededRef = useRef(false)
  useEffect(() => {
    if (
      !isVisitor ||
      visitorSeededRef.current ||
      watchProgress.seriesId != null ||
      seriesState.status !== 'success' ||
      seriesState.data.length === 0
    ) {
      return
    }
    visitorSeededRef.current = true
    const firstSeries = seriesState.data[0]
    setSelectedSeriesId(firstSeries.id)
    void watchProgress.requestChange(firstSeries.id, 1)
  }, [isVisitor, watchProgress, seriesState])

  // ChatSheet's `open` state, lifted here per 06-UI-SPEC.md "Chat & Panel
  // Architecture" — `ChatLauncher` lives in AppShell's topBar slot, outside
  // ChatSheet, so it needs to control the sheet from here. The inspector
  // panel (DetailPanel) has NO separate open state: it opens whenever an
  // element is selected and closes when the selection is cleared — so the
  // chat and the node info can be visible at the same time (chat right,
  // inspector left), which the old single-panel mode toggle made impossible.
  const [chatOpen, setChatOpen] = useState(false)

  // Top-level view switch: the graph workspace, the timeline, or the
  // settings page (no router in this app — navigation is state-driven,
  // mirroring the existing auth/series state pattern). Entering settings
  // unmounts the graph view (including the chat sheet); chat history
  // survives server-side.
  const [view, setView] = useState<'graph' | 'timeline' | 'settings'>('graph')
  // 08-06: events toggled in the Timeline view filter the graph to the
  // subgraph around them (nodes participating in the selected events).
  const [timelineFilterIds, setTimelineFilterIds] = useState<string[]>([])
  // FEAT-04 (09-10): series dashboard dialog open state.
  const [dashboardOpen, setDashboardOpen] = useState(false)
  // FEAT-09 (09-12): share dialog open state.
  const [shareDialogOpen, setShareDialogOpen] = useState(false)


  // Chat-driven graph_focus highlight (RAG-17, 06-10-PLAN.md) — set by a
  // citation chip's "Show in graph" action, cleared by GraphFocusIndicator's
  // "Clear" action or automatically whenever a progress change hides a
  // referenced element (see the render-time reconciliation below). Deliberately
  // independent of `selectedElement`/`panelMode` — highlighting never selects
  // a node/edge or switches panel content on its own.
  const [graphFocus, setGraphFocus] = useState<FocusedElementIds | null>(null)

  function handleClearFocus() {
    setGraphFocus(null)
  }

  // Freshly created elements (relationship created in the inspector): frame
  // them on screen. A chat `graph_focus` from an earlier turn would keep the
  // layout from re-running (and can pin the viewport right-of-center, hiding
  // the new edge under the chat sheet) — clear it so the reveal takes over.
  const [revealIds, setRevealIds] = useState<FocusedElementIds | null>(null)

  function handleRelationshipCreated(rel: CustomRelationshipResponse) {
    graphState.refresh()
    handleClearFocus()
    setRevealIds({ nodeIds: [rel.source, rel.target], edgeIds: [rel.id] })
  }

  // "Show in graph" only ever sets the highlight — it must never touch
  // `panelMode`/`panelOpen` (06-UI-SPEC.md "Citations": "letting the user
  // stay in Chat while looking at the canvas").
  function handleShowInGraph(citation: Citation) {
    setGraphFocus({ nodeIds: citation.related_node_ids, edgeIds: citation.related_edge_ids })
  }

  // The applied ChangeSet's already-existing target resources — the newly
  // created/changed element(s) the incremental refresh should highlight.
  // Operations whose target doesn't exist as a focusable id at apply time
  // (create_node/create_claim carry no persisted id on the response) and
  // delete operations (the element is gone) contribute nothing.
  function focusTargetsForAppliedChangeSet(changeSet: ChangeSet): FocusedElementIds {
    const nodeIds: string[] = []
    const edgeIds: string[] = []
    for (const op of changeSet.operations) {
      switch (op.operation_type) {
        case 'update_node':
        case 'delete_node':
          nodeIds.push(op.node_id)
          break
        case 'update_relationship':
        case 'delete_relationship':
          edgeIds.push(op.relationship_id)
          break
        case 'update_claim':
        case 'delete_claim':
        case 'attach_evidence':
          nodeIds.push(op.claim_id)
          break
        case 'create_note':
          nodeIds.push(op.target_id)
          break
        case 'update_note':
        case 'delete_note':
          nodeIds.push(op.note_id)
          break
        default:
          break
      }
    }
    return { nodeIds: [...new Set(nodeIds)], edgeIds: [...new Set(edgeIds)] }
  }

  // ChangeSetCard's Confirm-success callback (06-11): re-invokes useGraph's
  // own fetch (via `refresh()`, the data-preserving path that never flips to
  // 'loading', so GraphCanvas is neither unmounted nor re-laid-out) and sets
  // the 06-10 focus state to the newly created/changed resource so it
  // receives the `.selected-dominant` treatment and the focus effect's
  // gentle pan/fit — reusing the existing focus mechanism, not a second one.
  function handleChangeSetApplied(changeSet: ChangeSet) {
    graphState.refresh()
    setGraphFocus(focusTargetsForAppliedChangeSet(changeSet))
  }

  // Clicking a citation chip's body selects the referenced resource, opening
  // the left inspector — an intentional action (the user explicitly asked to
  // see detail); the chat sheet on the right is unaffected and stays open.
  // Prefers a related node over a related edge when both are present; silently
  // does nothing if neither resolves against the currently-fetched graph
  // (defensively — RAG-08 already makes an unresolvable reference
  // architecturally impossible).
  function handleOpenDetail(citation: Citation) {
    if (graphState.status !== 'success') return
    const nodeId = citation.related_node_ids[0]
    if (nodeId) {
      const node = graphState.data.nodes.find((n) => n.id === nodeId)
      if (node) {
        setSelectedElement({ kind: 'node', id: node.id, label: node.label, nodeType: node.type })
        return
      }
    }
    const edgeId = citation.related_edge_ids[0]
    if (edgeId) {
      const edge = graphState.data.edges.find((e) => e.id === edgeId)
      if (edge) {
        setSelectedElement({ kind: 'edge', id: edge.id, edgeType: edge.type, source: edge.source, target: edge.target })
      }
    }
  }

  // Node/edge selection opens the left inspector. The chat sheet is an
  // independent state, so both stay visible simultaneously.
  function handleSelectElement(element: SelectedElement | null) {
    setSelectedElement(element)
  }

  // Clicking ChatLauncher toggles the right-side chat sheet; it never touches
  // the inspector selection.
  function handleChatLauncherClick() {
    setChatOpen((open) => !open)
  }

  // Progress decreasing (or any graph refetch) that hides a currently-
  // focused element clears the graph focus automatically — reuses
  // `handleClearFocus`, the exact same function GraphFocusIndicator's manual
  // "Clear" action calls, never a second clearing code path (06-10-PLAN.md
  // Task 3). Adjusted during render (comparing a state copy of the previous
  // "which node/edge ids exist in the fetched graph" key) — the same
  // established "adjust state when a key changes" pattern useGraph.ts/
  // ChatPanel.tsx already use for reacting to an external data source
  // changing, rather than an effect + setState.
  const graphElementIdsKey =
    graphState.status === 'success'
      ? `${graphState.data.nodes.map((node) => node.id).join(',')}|${graphState.data.edges.map((edge) => edge.id).join(',')}`
      : ''
  const [prevGraphElementIdsKey, setPrevGraphElementIdsKey] = useState(graphElementIdsKey)
  if (prevGraphElementIdsKey !== graphElementIdsKey) {
    setPrevGraphElementIdsKey(graphElementIdsKey)
    if (graphFocus && graphState.status === 'success') {
      const nodeIdSet = new Set(graphState.data.nodes.map((node) => node.id))
      const edgeIdSet = new Set(graphState.data.edges.map((edge) => edge.id))
      const stillVisible =
        graphFocus.nodeIds.every((id) => nodeIdSet.has(id)) && graphFocus.edgeIds.every((id) => edgeIdSet.has(id))
      if (!stillVisible) handleClearFocus()
    }
  }

  const series = seriesState.status === 'success' ? seriesState.data : []
  const episodes = episodesState.status === 'success' ? episodesState.data : []

  // FEAT-03 (09-07): newly-revealed highlight on episode advance. When a
  // FORWARD advance changes watchProgress.confirmedOrder, diff the node/edge
  // id sets of the previous and current graph payloads and pass the
  // newly-appeared ids to GraphCanvas for a transient 4000ms glow. Uses the
  // established "adjust state when a key changes" pattern (state copies,
  // never refs) so it lints clean; only fires on an actual forward advance
  // (a first load, backward view-only move, or in-place refresh never
  // glows).
  const [prevGraphSnapshot, setPrevGraphSnapshot] = useState<{
    payload: GraphResponse | null
    order: number | null
  } | null>(null)
  const [newlyRevealedIds, setNewlyRevealedIds] = useState<FocusedElementIds | null>(null)
  if (graphState.status === 'success' && graphState.data !== prevGraphSnapshot?.payload) {
    const prevOrder = prevGraphSnapshot?.order ?? null
    const nextOrder = watchProgress.confirmedOrder
    const prevPayload = prevGraphSnapshot?.payload ?? null
    const advancedForward =
      prevPayload != null && prevOrder !== nextOrder && (nextOrder ?? 0) > (prevOrder ?? 0)
    if (advancedForward) {
      const prevNodeIds = new Set(prevPayload.nodes.map((node) => node.id))
      const prevEdgeIds = new Set(prevPayload.edges.map((edge) => edge.id))
      const nodeIds = graphState.data.nodes
        .filter((node) => !prevNodeIds.has(node.id))
        .map((node) => node.id)
      const edgeIds = graphState.data.edges
        .filter((edge) => !prevEdgeIds.has(edge.id))
        .map((edge) => edge.id)
      if (nodeIds.length > 0 || edgeIds.length > 0) {
        setNewlyRevealedIds({ nodeIds, edgeIds })
      }
    }
    setPrevGraphSnapshot({ payload: graphState.data, order: nextOrder })
  }

  const pendingEpisode = watchProgress.pendingChange
    ? episodes.find((episode) => episode.episode_order === watchProgress.pendingChange?.nextOrder)
    : null

  function handleSeriesSelect(seriesId: string) {
    setSelectedSeriesId(seriesId)
    setSelectedElement(null)
    // PROB-09/#61: the graph follows watchProgress.seriesId, so a series
    // switch must move the watch-progress series too — otherwise the OLD
    // series' graph stays rendered until an episode click. switchSeries is
    // navigation-only (never opens the unlock modal).
    if (seriesId !== watchProgress.seriesId) watchProgress.switchSeries(seriesId)
  }

  function handleEpisodeSelect(episodeOrder: number) {
    if (!selectedSeriesId) return
    void watchProgress.requestChange(selectedSeriesId, episodeOrder).then((persisted) => {
      // A failed view-only POST (network/401/422) must not look like a
      // silent no-op — re-issue the graph fetch so the UI re-syncs to the
      // chosen boundary (PROB-31/#56).
      if (!persisted) graphState.refresh()
    })
  }

  function handleConfirm() {
    watchProgress.confirmChange()
    setSelectedElement(null)
  }

  function handleCancel() {
    watchProgress.cancelChange()
  }

  // FEAT-08 (09-09): command palette open state — toggled by ⌘K/Ctrl+K (the
  // App-level hotkey below) or the AppShell topBar Command icon trigger.
  const [paletteOpen, setPaletteOpen] = useState(false)

  // FEAT-01 (09-09): '/' (graph view, no input focused) focuses the
  // NodeSearch input; NodeSearch registers its input element here.
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  // FEAT-01/08 (09-09): the shared jump-to-node selection path. Search and
  // palette rows select through the EXISTING mechanisms — onSelect opens
  // DetailPanel exactly like a canvas tap, and graphFocus frames the node
  // via GraphCanvas's existing focus effect (cy.getElementById +
  // .selected-dominant + fade + cy.fit(node, 48)). Never a second selection
  // implementation (plan 09-09 NO-SECOND-SELECTION-MECHANISM).
  function handleJumpToNode(selection: CommandPaletteSelection) {
    setSelectedElement({ kind: 'node', id: selection.id, label: selection.label, nodeType: selection.nodeType })
    setGraphFocus({ nodeIds: [selection.id], edgeIds: [] })
  }

  // FEAT-02 timeline / FEAT-04 dashboard / FEAT-05 export land in later
  // Phase 9 plans; the palette's Actions rows are wired through these seams
  // so 09-09 compiles and runs standalone (plan 09-09 Task 2: "prefer a
  // seam so this plan compiles standalone").
  const handleOpenTimeline = () => {
    setView('timeline')
  }
  const handleOpenDashboard = () => {
    setDashboardOpen(true)
  }
  const handleOpenSeries = (seriesId: string) => {
    setSelectedSeriesId(seriesId)
    setDashboardOpen(false)
    // PROB-09/#61: same stale-graph fix as handleSeriesSelect — the graph
    // follows watchProgress.seriesId and must move with the dashboard row.
    if (seriesId !== watchProgress.seriesId) watchProgress.switchSeries(seriesId)
    // Reset the episode selector to that series' watched boundary through
    // the existing watchProgress flow (T-09-10-02 — never a second
    // boundary mechanism).
    setView('graph')
  }
  // FEAT-02 (09-10): a timeline row click selects the node through the
  // existing onSelect path and switches to the graph view so it is framed.
  const handleTimelineSelect = (selection: { id: string; label: string; nodeType: string }) => {
    handleJumpToNode(selection)
    setView('graph')
  }

  // FEAT-08 (09-09): global keydown wiring (T-09-09-03 — '/' skips while an
  // input is focused; Esc closes the palette).
  useHotkey('mod+k', () => setPaletteOpen((open) => !open))
  useHotkey('escape', () => setPaletteOpen(false))
  useHotkey(
    '/',
    () => {
      if (view === 'graph' && graphState.status === 'success' && !paletteOpen) {
        searchInputRef.current?.focus()
      }
    },
    { skipWhenInputFocused: true },
  )

  const episodeSelectorValue = watchProgress.pendingChange
    ? watchProgress.pendingChange.nextOrder
    : selectedSeriesId === watchProgress.seriesId
      ? watchProgress.viewAsOfOrder
      : null

  return (
    <AppShell
      user={user}
      onLogout={logout}
      visitor={isVisitor}
      onSignIn={isVisitor ? logout : undefined}
      onOpenPalette={() => setPaletteOpen((open) => !open)}
      topBar={
        <>
          <SeriesSelect series={series} value={selectedSeriesId} onSelect={handleSeriesSelect} />
          <EpisodeSelector
            episodes={episodes}
            value={episodeSelectorValue}
            watchedThroughOrder={watchProgress.watchedThroughOrder}
            onSelect={handleEpisodeSelect}
            disabled={!selectedSeriesId}
          />
          {!isVisitor && <ChatLauncher active={chatOpen} onClick={handleChatLauncherClick} />}
          <HeaderNavAction
            icon={<CalendarClockIcon />}
            label={view === 'timeline' ? 'Graph' : 'Timeline'}
            ariaLabel={view === 'timeline' ? 'Back to graph' : 'Timeline'}
            active={view === 'timeline'}
            onClick={() => setView((current) => (current === 'timeline' ? 'graph' : 'timeline'))}
          />
          <HeaderNavAction
            icon={<LayoutGridIcon />}
            label="Series"
            ariaLabel="Series dashboard"
            active={false}
            onClick={handleOpenDashboard}
          />
          <HeaderNavAction
            icon={<SettingsIcon />}
            label={view === 'settings' ? 'Graph' : 'Settings'}
            ariaLabel={view === 'settings' ? 'Back to graph' : 'Settings'}
            active={view === 'settings'}
            onClick={() => setView((current) => (current === 'settings' ? 'graph' : 'settings'))}
          />
        </>
      }
    >
      {view === 'timeline' ? (
        <TimelineView
          nodes={graphState.status === 'success' ? graphState.data.nodes : []}
          claims={graphState.status === 'success' ? graphState.data.claims : []}
          episodes={episodes}
          selectedId={selectedElement?.kind === 'node' ? selectedElement.id : null}
          onSelect={handleTimelineSelect}
          filteredIds={timelineFilterIds}
          onToggleFilter={(id) =>
            setTimelineFilterIds((prev) =>
              prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
            )
          }
          onClearFilter={() => setTimelineFilterIds([])}
        />
      ) : view === 'settings' ? (
        <SettingsPage onBack={() => setView('graph')} />
      ) : (
        <>
      {watchProgress.pendingChange && (
        <ConfirmAdvanceModal
          open
          direction={watchProgress.pendingChange.direction}
          episodeCode={pendingEpisode?.code ?? `order ${watchProgress.pendingChange.nextOrder}`}
          episodeOrder={watchProgress.pendingChange.nextOrder}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}

      {graphState.status === 'idle' && <GraphEmptyState />}
      {/* PROB-09/#74: the canvas stays mounted once a graph has loaded —
          loading/error render as an OVERLAY above the last-known-good graph
          instead of unmounting it (no destructive relayout on refresh). */}
      {activeGraph == null && graphState.status === 'loading' && <GraphLoadingState />}
      {activeGraph == null && graphState.status === 'error' && <GraphErrorState onRetry={graphState.refetch} />}
      {activeGraph != null && activeGraph.nodes.length === 0 && <GraphEmptyState />}
      {activeGraph != null && activeGraph.nodes.length > 0 && (
        <>
          {graphState.status !== 'success' && (
            <div className="absolute inset-0 z-40 flex items-center justify-center bg-background/70 backdrop-blur-[2px]">
              {graphState.status === 'loading' ? (
                <GraphLoadingState />
              ) : (
                <GraphErrorState onRetry={graphState.refetch} />
              )}
            </div>
          )}
          <GraphCanvas
            graph={activeGraph}
            onSelect={handleSelectElement}
            seriesId={watchProgress.seriesId}
            onRefetchGraph={graphState.refetch}
            onRefreshGraph={graphState.refresh}
            episodes={episodes}
            focusedElementIds={graphFocus}
            onClearFocus={handleClearFocus}
            revealElementIds={revealIds}
            onRevealDone={() => setRevealIds(null)}
            timelineFilterIds={timelineFilterIds}
            newlyRevealedIds={newlyRevealedIds}
            onNewlyRevealedDone={() => setNewlyRevealedIds(null)}
            readOnly={isVisitor}
            onShareLink={isVisitor ? undefined : () => setShareDialogOpen(true)}
          />

          {/* FEAT-01/07 (09-09): floating search bar over the canvas — the
              '/' hotkey focuses it via searchInputRef; rows select through
              handleJumpToNode (existing onSelect + graphFocus paths). */}
          <NodeSearch
            graph={activeGraph}
            notes={notes}
            onSelect={handleJumpToNode}
            inputRef={searchInputRef}
          />
          {selectedElement?.kind === 'edge' &&
          activeGraph.edges.find((edge) => edge.id === selectedElement.id)?.claim_id == null &&
          activeGraph.edges.find((edge) => edge.id === selectedElement.id)?.origin !== 'user' ? (
            <StructuralEdgeCard selected={selectedElement} nodes={activeGraph.nodes} />
          ) : (
            <DetailPanel
              selected={selectedElement}
              graph={activeGraph}
              seriesId={watchProgress.seriesId}
              visibleUntilOrder={watchProgress.confirmedOrder}
              onRefetchGraph={graphState.refetch}
              onRefreshGraph={graphState.refresh}
              onRelationshipCreated={handleRelationshipCreated}
              episodes={episodes}
              open={selectedElement !== null}
              onDeselect={() => setSelectedElement(null)}
              onSelectNode={(nodeId) => {
                // PROB-09/#75: BacklinksTab "Open" must jump to the node via
                // the SAME selection path as search/palette (select + frame),
                // not fall into DetailPanel's onDeselect() fallback.
                const node = activeGraph.nodes.find((n) => n.id === nodeId)
                if (node) {
                  handleJumpToNode({
                    id: nodeId,
                    label: node.label,
                    nodeType: node.type,
                  })
                }
              }}
            />
          )}
          {!isVisitor && (
            <ChatSheet
              open={chatOpen}
              onClose={() => setChatOpen(false)}
              seriesId={watchProgress.seriesId}
              seriesTitle={activeGraph.series.title}
              viewAsOfOrder={watchProgress.viewAsOfOrder}
              currentEpisodeCode={
                episodes.find((episode) => episode.episode_order === watchProgress.confirmedOrder)?.code ?? null
              }
              onShowInGraph={handleShowInGraph}
              onOpenDetail={handleOpenDetail}
              onChangeSetApplied={handleChangeSetApplied}
            />
          )}
        </>
      )}
        </>
      )}
      {/* FEAT-08 (09-09): ⌘K command palette — available in every view;
          node rows reuse handleJumpToNode, episode rows ride
          handleEpisodeSelect (watchProgress.requestChange — locked episodes
          route to the unlock dialog per PROB-31). */}
      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        graph={graphState.status === 'success' ? graphState.data : null}
        episodes={episodes}
        onSelectNode={handleJumpToNode}
        onRequestChange={handleEpisodeSelect}
        onOpenChat={isVisitor ? undefined : () => setChatOpen(true)}
        onOpenTimeline={handleOpenTimeline}
        onOpenSettings={() => setView('settings')}
        onOpenDashboard={handleOpenDashboard}
      />
      {/* FEAT-04 (09-10): series dashboard dialog — augments the dropdown,
          never replaces it. */}
      <SeriesDashboard
        open={dashboardOpen}
        onOpenChange={setDashboardOpen}
        series={series}
        selectedSeriesId={selectedSeriesId}
        watchedThroughOrder={watchProgress.watchedThroughOrder}
        onOpenSeries={handleOpenSeries}
      />
      {/* FEAT-09 (09-12): share dialog — create & manage shareable snapshot links */}
      {watchProgress.seriesId && (
        <ShareDialog
          open={shareDialogOpen}
          onOpenChange={setShareDialogOpen}
          seriesId={watchProgress.seriesId}
          seriesTitle={series.find((s) => s.id === watchProgress.seriesId)?.title}
          visibleUntilOrder={watchProgress.confirmedOrder ?? 1}

        />
      )}
    </AppShell>
  )
}

function AppContent() {
  const { state } = useAuth()

  // FEAT-09 (09-12): Route snapshot links BEFORE the auth gate
  const shareMatch = typeof window !== 'undefined'
    ? window.location.pathname.match(/^\/share\/([A-Za-z0-9_-]+)$/)
    : null
  if (shareMatch) {
    return <ShareView token={shareMatch[1]} />
  }

  if (state.status === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  if (state.status === 'unauthenticated' || state.status === 'error') {
    return <LoginPage />
  }

  return <AuthenticatedApp />
}


function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
