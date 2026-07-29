import { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { SeriesSelect } from './components/episode/SeriesSelect'
import { EpisodeSelector } from './components/episode/EpisodeSelector'
import { ConfirmAdvanceModal } from './components/episode/ConfirmAdvanceModal'
import { GraphCanvas, type SelectedElement } from './components/graph/GraphCanvas'
import { GraphLoadingState, GraphErrorState, GraphEmptyState } from './components/graph/GraphStatus'
import { DetailPanel } from './components/detail/DetailPanel'
import { useSeries } from './hooks/useSeries'
import { useEpisodes } from './hooks/useEpisodes'
import { useGraph } from './hooks/useGraph'
import { useWatchProgress } from './hooks/useWatchProgress'

function App() {
  const seriesState = useSeries()
  const watchProgress = useWatchProgress()
  // Initialized once from the hydrated watch-progress state (D-02) so a
  // page refresh restores the previously-selected series without any user
  // interaction and without re-triggering ConfirmAdvanceModal.
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(watchProgress.seriesId)
  const episodesState = useEpisodes(selectedSeriesId)
  const graphState = useGraph(watchProgress.seriesId, watchProgress.confirmedOrder)
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null)

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
      topBar={
        <>
          <SeriesSelect series={series} value={selectedSeriesId} onSelect={handleSeriesSelect} />
          <EpisodeSelector
            episodes={episodes}
            value={episodeSelectorValue}
            onSelect={handleEpisodeSelect}
            disabled={!selectedSeriesId}
          />
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
          <GraphCanvas graph={graphState.data} onSelect={setSelectedElement} />
          <DetailPanel selected={selectedElement} graph={graphState.data} />
        </>
      )}
      {graphState.status === 'idle' && <GraphEmptyState />}
    </AppShell>
  )
}

export default App
