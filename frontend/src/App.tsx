import { useState } from 'react'
import { AuthProvider } from './providers/AuthProvider'
import { useAuth } from './providers/useAuth'
import { LoginPage } from './components/auth/LoginPage'
import { AppShell } from './components/layout/AppShell'
import { SeriesSelect } from './components/episode/SeriesSelect'
import { EpisodeSelector } from './components/episode/EpisodeSelector'
import { ConfirmAdvanceModal } from './components/episode/ConfirmAdvanceModal'
import { GraphCanvas, type SelectedElement } from './components/graph/GraphCanvas'
import { GraphLoadingState, GraphErrorState, GraphEmptyState } from './components/graph/GraphStatus'
import { DetailPanel, type DetailPanelMode } from './components/detail/DetailPanel'
import { StructuralEdgeCard } from './components/detail/StructuralEdgeCard'
import { ChatLauncher } from './components/chat/ChatLauncher'
import { useSeries } from './hooks/useSeries'
import { useEpisodes } from './hooks/useEpisodes'
import { useGraph } from './hooks/useGraph'
import { useWatchProgress } from './hooks/useWatchProgress'

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
          <GraphCanvas graph={graphState.data} onSelect={handleSelectElement} seriesId={watchProgress.seriesId} onRefetchGraph={graphState.refetch} episodes={episodes} />
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
