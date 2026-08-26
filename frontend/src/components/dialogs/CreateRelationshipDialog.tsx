import { useCallback, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { GraphNode } from '../../types/graph'
import type { CustomRelationshipResponse } from '../../types/userContent'
import { createCustomRelationship } from '../../api/userContent'

const PREDICATE_OPTIONS = [
  'PARTICIPATED_IN', 'WITNESSED', 'CAUSED', 'AFFECTED', 'TARGETED', 'MENTIONED',
  'KNOWS', 'FAMILY_OF', 'WORKS_WITH', 'TRUSTS', 'DISTRUSTS', 'HELPS',
  'OPPOSES', 'THREATENS', 'ATTACKS', 'KILLS',
]

// 12-08 (THERMO-P0-04): extracted verbatim from DetailPanel.tsx.
export function CreateRelationshipDialog({
  open,
  onOpenChange,
  seriesId,
  selectedNodeId,
  selectedNodeLabel,
  graphNodes,
  episodes,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  seriesId: string | null
  selectedNodeId: string | null
  selectedNodeLabel: string | null
  graphNodes: GraphNode[]
  episodes: { id: string; code: string; title: string; episode_order: number }[]
  onSuccess: (rel: CustomRelationshipResponse) => void
}) {
  const [targetId, setTargetId] = useState('')
  const [predicate, setPredicate] = useState('KNOWS')
  const [episodeId, setEpisodeId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Filter out the source node from targets
  const targetOptions = graphNodes.filter((n) => n.id !== selectedNodeId)

  // Default to the highest visible episode via a guarded render-time
  // adjustment — the same "adjust state when a prop/key changes" pattern
  // useGraph.ts uses (react-hooks/set-state-in-effect clean: never a
  // synchronous setState in an effect body).
  // THERMO-P1-04: compare NUMERIC episode_order — comparing string UUID ids
  // is alphabetical and picked an arbitrary "highest" episode.
  if (!episodeId && episodes.length > 0) {
    const highest = episodes.reduce((a, b) => a.episode_order > b.episode_order ? a : b)
    setEpisodeId(highest.id)
  }

  const handleCreate = useCallback(async () => {
    if (!seriesId || !selectedNodeId || !targetId) return
    setSaving(true)
    setError('')
    try {
      const rel = await createCustomRelationship(seriesId, {
        source_id: selectedNodeId,
        target_id: targetId,
        predicate,
        episode_id: episodeId,
      })
      setTargetId('')
      setPredicate('KNOWS')
      onOpenChange(false)
      onSuccess(rel)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create relationship.')
    } finally {
      setSaving(false)
    }
  }, [seriesId, selectedNodeId, targetId, predicate, episodeId, onOpenChange, onSuccess])

  // Reset form when the dialog opens — guarded render-time adjustment with a
  // state copy of the previous `open` value (react-hooks/set-state-in-effect
  // clean).
  const [prevOpen, setPrevOpen] = useState(open)
  if (prevOpen !== open) {
    setPrevOpen(open)
    if (open) {
      setTargetId('')
      setPredicate('KNOWS')
      setError('')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Create Relationship</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3 py-2 text-sm">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium">From</span>
            <span className="rounded-md bg-muted px-2 py-1.5 text-xs">{selectedNodeLabel}</span>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rel-target" className="text-xs font-medium">To</label>
            <select
              id="rel-target"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              <option value="">Select target...</option>
              {targetOptions.map((n) => (
                <option key={n.id} value={n.id}>{n.label} ({n.type})</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rel-predicate" className="text-xs font-medium">Predicate</label>
            <select
              id="rel-predicate"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={predicate}
              onChange={(e) => setPredicate(e.target.value)}
            >
              {PREDICATE_OPTIONS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rel-episode" className="text-xs font-medium">Episode</label>
            <select
              id="rel-episode"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={episodeId}
              onChange={(e) => setEpisodeId(e.target.value)}
            >
              {episodes.map((ep) => (
                <option key={ep.id} value={ep.id}>{ep.code} — {ep.title}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors min-h-[44px] disabled:opacity-50"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors min-h-[44px] disabled:opacity-50"
              onClick={handleCreate}
              disabled={saving || !targetId}
            >
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
