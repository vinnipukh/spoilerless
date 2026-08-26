import { useCallback, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { EpisodeResponse } from '../../types/series'
import { createCustomNode } from '../../api/userContent'
import type { CustomNodeResponse, CustomNodeType } from '../../types/userContent'
import { ALLOWED_NODE_TYPES } from '@/lib/nodeTypes'

// 12-08 (THERMO-P0-03): extracted verbatim from GraphCanvas.tsx — the floating
// create-node dialog. The node types come from the NODE_TYPES registry in
// lib/nodeTypes.ts (PROB-09 #81), not a second inline list.
export function CreateCustomNodeDialog({
  open,
  onOpenChange,
  seriesId,
  episodes,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  seriesId: string | null
  episodes: EpisodeResponse[]
  onSuccess: (node: CustomNodeResponse) => void
}) {
  const [nodeType, setNodeType] = useState<CustomNodeType>('Character')
  const [label, setLabel] = useState('')
  const [episodeId, setEpisodeId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Default to the highest visible episode via a guarded render-time
  // adjustment (the same "adjust state when a prop changes" pattern
  // useGraph.ts uses) — react-hooks/set-state-in-effect clean.
  if (!episodeId && episodes.length > 0) {
    const highest = episodes.reduce((a, b) => (a.episode_order > b.episode_order ? a : b))
    setEpisodeId(highest.id)
  }

  const handleCreate = useCallback(async () => {
    if (!seriesId || !label.trim()) return
    setSaving(true)
    setError('')
    try {
      const created = await createCustomNode(seriesId, { node_type: nodeType, label: label.trim(), episode_id: episodeId })
      setLabel('')
      setNodeType('Character')
      onOpenChange(false)
      onSuccess(created)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create node.')
    } finally {
      setSaving(false)
    }
  }, [seriesId, nodeType, label, episodeId, onOpenChange, onSuccess])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Create Custom Node</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3 py-2">
          {/* Node type */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-type" className="text-xs font-medium">Node Type</label>
            <select
              id="node-type"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={nodeType}
              onChange={(e) => setNodeType(e.target.value as CustomNodeType)}
            >
              {ALLOWED_NODE_TYPES.map((nt) => (
                <option key={nt.value} value={nt.value}>{nt.label}</option>
              ))}
            </select>
          </div>
          {/* Label */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-label" className="text-xs font-medium">Label</label>
            <input
              id="node-label"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px]"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Enter node label..."
              maxLength={255}
            />
          </div>
          {/* Episode */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-episode" className="text-xs font-medium">Episode</label>
            <select
              id="node-episode"
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
              disabled={saving || !label.trim()}
            >
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
