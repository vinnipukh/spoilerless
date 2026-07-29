import { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { SeriesSelect } from './components/episode/SeriesSelect'
import { EpisodeSelector } from './components/episode/EpisodeSelector'
import { ConfirmAdvanceModal } from './components/episode/ConfirmAdvanceModal'
import { GraphCanvas, type SelectedElement } from './components/graph/GraphCanvas'
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

      {graphState.status === 'success' ? (
        <>
          <GraphCanvas graph={graphState.data} onSelect={setSelectedElement} />
          <DetailPanel selected={selectedElement} />
        </>
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <h2 className="text-lg font-semibold">Nothing revealed yet</h2>
          <p className="text-sm text-muted-foreground">
            Advance your watch progress to unlock the story.
          </p>
        </div>
      )}
    </AppShell>
  )
}

export default App
