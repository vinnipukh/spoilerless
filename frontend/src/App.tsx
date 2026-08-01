import { useState } from 'react'
import { AuthProvider } from './providers/AuthProvider'
import { useAuth } from './providers/useAuth'
import { LoginPage } from './components/auth/LoginPage'
import { AppShell } from './components/layout/AppShell'
import { SeriesSelect } from './components/episode/SeriesSelect'
import { EpisodeSelector } from './components/episode/EpisodeSelector'
import { ConfirmAdvanceModal } from './components/episode/ConfirmAdvanceModal'
import { GraphCanvas, type FocusedElementIds, type SelectedElement } from './components/graph/GraphCanvas'
import { GraphLoadingState, GraphErrorState, GraphEmptyState } from './components/graph/GraphStatus'
import { DetailPanel, type DetailPanelMode } from './components/detail/DetailPanel'
import { StructuralEdgeCard } from './components/detail/StructuralEdgeCard'
import { ChatLauncher } from './components/chat/ChatLauncher'
import { useSeries } from './hooks/useSeries'
import { useEpisodes } from './hooks/useEpisodes'
import { useGraph } from './hooks/useGraph'
import { useWatchProgress } from './hooks/useWatchProgress'
import type { Citation } from './types/chat'

function AuthenticatedApp() {
  const { state, logout } = useAuth()
  const user = state.status === 'authenticated' ? state.user : undefined

  const seriesState = useSeries()
  const watchProgress = useWatchProgress()
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(watchProgress.seriesId)
  const episodesState = useEpisodes(selectedSeriesId)
  const graphState = useGraph(watchProgress.seriesId, watchProgress.confirmedOrder)
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null)

  // DetailPanel's Sheet `open`/mode state, lifted here per 06-UI-SPEC.md
  // "Chat & Panel Architecture" — `ChatLauncher` lives in AppShell's topBar
  // slot, outside DetailPanel, so it needs to control the panel from here.
  // Defaults closed/Inspector on every mount, never persisted across
  // sessions (no sessionStorage/localStorage read for either value).
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelMode, setPanelMode] = useState<DetailPanelMode>('inspector')

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

  // "Show in graph" only ever sets the highlight — it must never touch
  // `panelMode`/`panelOpen` (06-UI-SPEC.md "Citations": "letting the user
  // stay in Chat while looking at the canvas").
  function handleShowInGraph(citation: Citation) {
    setGraphFocus({ nodeIds: citation.related_node_ids, edgeIds: citation.related_edge_ids })
  }

  // Clicking a citation chip's body switches to Inspector and selects the
  // referenced resource — an intentional, expected mode switch (the user
  // explicitly asked to see detail). Prefers a related node over a related
  // edge when both are present; silently does nothing if neither resolves
  // against the currently-fetched graph (defensively — RAG-08 already makes
  // an unresolvable reference architecturally impossible).
  function handleOpenDetail(citation: Citation) {
    if (graphState.status !== 'success') return
    const nodeId = citation.related_node_ids[0]
    if (nodeId) {
      const node = graphState.data.nodes.find((n) => n.id === nodeId)
      if (node) {
        setPanelMode('inspector')
        setPanelOpen(true)
        setSelectedElement({ kind: 'node', id: node.id, label: node.label, nodeType: node.type })
        return
      }
    }
    const edgeId = citation.related_edge_ids[0]
    if (edgeId) {
      const edge = graphState.data.edges.find((e) => e.id === edgeId)
      if (edge) {
        setPanelMode('inspector')
        setPanelOpen(true)
        setSelectedElement({ kind: 'edge', id: edge.id, edgeType: edge.type, source: edge.source, target: edge.target })
      }
    }
  }

  // Node/edge selection only opens the panel (in Inspector mode) when the
  // panel isn't already showing Chat — selecting while in Chat mode must
  // never force-switch the content mode back to Inspector (06-UI-SPEC.md
  // "Mode state (independent of node/edge selection)"). The canvas's own
  // `.selected-dominant` glow is unaffected either way (GraphCanvas.tsx owns
  // that independently of DetailPanel).
  function handleSelectElement(element: SelectedElement | null) {
    setSelectedElement(element)
    if (element && panelMode === 'inspector') {
      setPanelOpen(true)
    }
  }

  // Clicking ChatLauncher: opens the panel (if collapsed) and switches to
  // Chat mode in one action; clicking again while already open in Chat mode
  // collapses the entire right panel — the one way this panel can close.
  function handleChatLauncherClick() {
    if (panelMode === 'chat' && panelOpen) {
      setPanelOpen(false)
      return
    }
    setPanelMode('chat')
    setPanelOpen(true)
  }

  // The Inspector/Chat pill toggle only ever renders while the panel is
  // already open (it lives inside SheetHeader, which unmounts when closed),
  // so this never needs to touch `panelOpen` itself.
  function handlePanelModeChange(mode: DetailPanelMode) {
    setPanelMode(mode)
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

  const pendingEpisode = watchProgress.pendingChange
    ? episodes.find((episode) => episode.episode_order === watchProgress.pendingChange?.nextOrder)
    : null

  function handleSeriesSelect(seriesId: string) {
    setSelectedSeriesId(seriesId)
    setSelectedElement(null)
  }

  function handleEpisodeSelect(episodeOrder: number) {
    if (!selectedSeriesId) return
    watchProgress.requestChange(selectedSeriesId, episodeOrder)
  }

  function handleConfirm() {
    watchProgress.confirmChange()
    setSelectedElement(null)
  }

  function handleCancel() {
    watchProgress.cancelChange()
  }

  const episodeSelectorValue = watchProgress.pendingChange
    ? watchProgress.pendingChange.nextOrder
    : selectedSeriesId === watchProgress.seriesId
      ? watchProgress.confirmedOrder
      : null

  return (
    <AppShell
      user={user}
      onLogout={logout}
      topBar={
        <>
          <SeriesSelect series={series} value={selectedSeriesId} onSelect={handleSeriesSelect} />
          <EpisodeSelector
            episodes={episodes}
            value={episodeSelectorValue}
            onSelect={handleEpisodeSelect}
            disabled={!selectedSeriesId}
          />
          <ChatLauncher active={panelMode === 'chat' && panelOpen} onClick={handleChatLauncherClick} />
        </>
      }
    >
      {watchProgress.pendingChange && (
        <ConfirmAdvanceModal
          open
          direction={watchProgress.pendingChange.direction}
          episodeCode={pendingEpisode?.code ?? `order ${watchProgress.pendingChange.nextOrder}`}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}

      {graphState.status === 'loading' && <GraphLoadingState />}
      {graphState.status === 'error' && <GraphErrorState onRetry={graphState.refetch} />}
      {graphState.status === 'success' && graphState.data.nodes.length === 0 && <GraphEmptyState />}
      {graphState.status === 'success' && graphState.data.nodes.length > 0 && (
        <>
          <GraphCanvas
            graph={graphState.data}
            onSelect={handleSelectElement}
            seriesId={watchProgress.seriesId}
            onRefetchGraph={graphState.refetch}
            episodes={episodes}
            focusedElementIds={graphFocus}
            onClearFocus={handleClearFocus}
          />
          {selectedElement?.kind === 'edge' &&
          graphState.data.edges.find((edge) => edge.id === selectedElement.id)?.claim_id == null ? (
            <StructuralEdgeCard selected={selectedElement} nodes={graphState.data.nodes} />
          ) : (
            <DetailPanel
              selected={selectedElement}
              graph={graphState.data}
              seriesId={watchProgress.seriesId}
              visibleUntilOrder={watchProgress.confirmedOrder}
              onRefetchGraph={graphState.refetch}
              episodes={episodes}
              open={panelOpen}
              mode={panelMode}
              onModeChange={handlePanelModeChange}
              onShowInGraph={handleShowInGraph}
              onOpenDetail={handleOpenDetail}
            />
          )}
        </>
      )}
      {graphState.status === 'idle' && <GraphEmptyState />}
    </AppShell>
  )
}

function AppContent() {
  const { state } = useAuth()

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
