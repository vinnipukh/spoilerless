import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { SelectedElement } from '../graph/GraphCanvas'
import type { GraphClaim, GraphEvidence, GraphNode, GraphResponse } from '../../types/graph'
import { useNotes } from '../../hooks/useNotes'
import type { CustomRelationshipResponse, NoteResponse } from '../../types/userContent'
import { createCustomRelationship } from '../../api/userContent'
import { RevisionHistoryPanel } from './RevisionHistoryPanel'

// Reused by CitationChip.tsx (06-09-PLAN.md Task 2) so claim/evidence citation
// accents are never redefined as a second, drifting hex literal — the exact
// same visual meaning ("this points at that Claims/Evidence card") applies to
// a citation chip as it does to these Overview-tab accent bars.
export const CLAIM_ACCENT_COLOR = '#D946EF'
export const EVIDENCE_ACCENT_COLOR = '#FB923C'

function initialsFor(label: string): string {
  const initials = label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
  return initials || '?'
}

// Portrait shown next to a Character's name in the detail panel header.
// Falls back to an initials avatar both when image_url is null AND when the
// external image fails to load (broken link, 404, blocked) — never renders
// an empty broken-image box.
//
// D-14/MEDIA-02: the two fallback paths (missing vs failed) render the
// IDENTICAL placeholder (same testid, same classes, no error text, no retry
// affordance) so a failed image request can never imply a hidden future
// character exists. The alt text is always the safe visible label, never a
// filename or URL.
function CharacterPortrait({
  node,
  visibleUntilOrder,
}: {
  node: GraphNode
  visibleUntilOrder: number | null
}) {
  const [failed, setFailed] = useState(false)
  const showImage = Boolean(node?.image_url) && !failed

  // D-14 defensive guard: the image source link renders only when the
  // resource is visible at the current boundary. The backend already nulls
  // image_source_url above the boundary; this makes a future regression
  // unable to surface a URL as text. A null/unknown boundary fails closed —
  // no link.
  const isVisibleAtBoundary =
    visibleUntilOrder != null && node.visible_from_order <= visibleUntilOrder
  const showSourceLink = Boolean(node.image_source_url) && isVisibleAtBoundary

  const avatar = showImage ? (
    <img
      src={node.image_url ?? undefined}
      alt={node.label}
      className="h-10 w-10 rounded-full object-cover"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      loading="lazy"
    />
  ) : (
    <div
      data-testid="character-avatar"
      className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground"
    >
      {initialsFor(node.label)}
    </div>
  )

  if (!showSourceLink) return avatar

  // Generic accessible link label — never the URL (D-14: URLs and filenames
  // never appear as user-visible text).
  return (
    <a
      href={node.image_source_url ?? undefined}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Image source"
    >
      {avatar}
    </a>
  )
}

// Full Overview/Notes/Claims/Evidence tabbed Sheet (D-07) for nodes and claim-backed
// narrative edges (edge.claim_id !== null). Structural edges (claim_id ===
// null) never reach this component — App.tsx routes those to
// StructuralEdgeCard instead (D-06), so every branch below can assume the
// selected edge (if any) is claim-backed.
type Props = {
  selected: SelectedElement | null
  graph: GraphResponse
  seriesId: string | null
  visibleUntilOrder: number | null
  onRefetchGraph?: () => void
  /** In-place graph data refresh (useGraph's `refresh`) — preferred for
   * create/edit/delete operations that land in the graph, so the canvas
   * updates without a destructive loading unmount. */
  onRefreshGraph?: () => void
  /** Called with the created relationship so the caller can reveal/frame it. */
  onRelationshipCreated?: (rel: CustomRelationshipResponse) => void
  episodes: { id: string; code: string; title: string; episode_order: number }[]
  // Inspector-panel open state is lifted to App.tsx — the panel opens whenever
  // an element is selected (`open={selected != null}`) and closes via
  // `onDeselect` (canvas background tap clears the selection in App.tsx).
  // The chat surface lives in its own independent right-side sheet (ChatSheet);
  // this component is the left-side inspector only, so both can be open at
  // once.
  open: boolean
  onDeselect: () => void
}

type ResolvedEvidence = {
  evidence: GraphEvidence
  sourceLabel: string
}

function resolveClaimsForSelection(
  selected: SelectedElement | null,
  graph: GraphResponse,
): GraphClaim[] {
  if (!selected) return []

  if (selected.kind === 'node') {
    return graph.claims.filter(
      (claim) => claim.subject_id === selected.id || claim.object_id === selected.id,
    )
  }

  // Edge selection: DetailPanel only ever renders for claim-backed edges
  // (App.tsx's centralized branch keeps structural edges out of this
  // component entirely) — resolve the single associated claim via the full
  // GraphResponse rather than widening GraphCanvas's onSelect contract.
  const graphEdge = graph.edges.find((edge) => edge.id === selected.id)
  const claim = graphEdge?.claim_id
    ? graph.claims.find((c) => c.id === graphEdge.claim_id)
    : undefined
  return claim ? [claim] : []
}

function resolveEvidenceForClaims(claims: GraphClaim[], graph: GraphResponse): ResolvedEvidence[] {
  const seen = new Set<string>()
  const resolved: ResolvedEvidence[] = []

  for (const claim of claims) {
    for (const evidenceId of claim.evidence_ids) {
      if (seen.has(evidenceId)) continue
      const evidence = graph.evidence.find((entry) => entry.id === evidenceId)
      if (!evidence) continue
      seen.add(evidenceId)
      const source = graph.sources.find((entry) => entry.id === evidence.source_id)
      resolved.push({ evidence, sourceLabel: source?.label ?? evidence.source_id })
    }
  }

  return resolved
}

function NoteItem({
  note,
  onEdit,
  onDelete,
}: {
  note: NoteResponse
  onEdit: (note: NoteResponse) => void
  onDelete: (noteId: string) => void
}) {
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="rounded-md border border-border p-2 text-sm">
      <p className="whitespace-pre-wrap break-words">{note.content}</p>
      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
        <button
          type="button"
          className="hover:text-foreground transition-colors"
          onClick={() => onEdit(note)}
          aria-label="Edit note"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4 inline mr-0.5" aria-hidden="true">
            <path d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
          </svg>
          Edit
        </button>
        <span aria-hidden="true">·</span>
        {confirmDelete ? (
          <span className="flex items-center gap-1">
            <span className="text-destructive">Delete?</span>
            <button
              type="button"
              className="text-destructive hover:text-destructive/80 font-medium transition-colors"
              onClick={() => {
                setDeleting(true)
                onDelete(note.id)
              }}
              disabled={deleting}
              aria-label="Confirm delete note"
            >
              {deleting ? '...' : 'Yes'}
            </button>
            <button
              type="button"
              className="hover:text-foreground transition-colors"
              onClick={(e) => { e.stopPropagation(); setConfirmDelete(false) }}
              aria-label="Cancel delete"
            >
              No
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="hover:text-destructive transition-colors"
            onClick={() => setConfirmDelete(true)}
            aria-label="Delete note"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4 inline mr-0.5" aria-hidden="true">
              <path d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
            Delete
          </button>
        )}
      </div>
    </div>
  )
}

const PREDICATE_OPTIONS = [
  'PARTICIPATED_IN', 'WITNESSED', 'CAUSED', 'AFFECTED', 'TARGETED', 'MENTIONED',
  'KNOWS', 'FAMILY_OF', 'WORKS_WITH', 'TRUSTS', 'DISTRUSTS', 'HELPS',
  'OPPOSES', 'THREATENS', 'ATTACKS', 'KILLS',
]

function CreateRelationshipDialog({
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
  episodes: { id: string; code: string; title: string }[]
  onSuccess: (rel: CustomRelationshipResponse) => void
}) {
  const [targetId, setTargetId] = useState('')
  const [predicate, setPredicate] = useState('KNOWS')
  const [episodeId, setEpisodeId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Filter out the source node from targets
  const targetOptions = graphNodes.filter((n) => n.id !== selectedNodeId)

  useEffect(() => {
    if (!episodeId && episodes.length > 0) {
      const highest = episodes.reduce((a, b) => a.id > b.id ? a : b)
      setEpisodeId(highest.id)
    }
  }, [episodes, episodeId])

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

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setTargetId('')
      setPredicate('KNOWS')
      setError('')
    }
  }, [open])

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

function NoteEditor({
  initialContent,
  onSave,
  onCancel,
  saving,
}: {
  initialContent: string
  onSave: (content: string) => void
  onCancel: () => void
  saving: boolean
}) {
  const [content, setContent] = useState(initialContent)

  return (
    <div className="flex flex-col gap-2">
      <textarea
        className="w-full min-h-[60px] rounded-md border border-border bg-background p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Write a note..."
        aria-label="Note content"
        rows={3}
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 min-h-[44px]"
          onClick={() => onSave(content)}
          disabled={saving || !content.trim()}
          aria-label={saving ? 'Saving...' : 'Save note'}
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors min-h-[44px]"
          onClick={onCancel}
          disabled={saving}
          aria-label="Cancel"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export function DetailPanel({
  selected,
  graph,
  seriesId,
  visibleUntilOrder,
  onRefetchGraph,
  onRefreshGraph,
  onRelationshipCreated,
  episodes,
  open,
  onDeselect,
}: Props) {
  // Selection-aware state
  const [editingNote, setEditingNote] = useState<NoteResponse | null>(null)
  const [showNewNoteForm, setShowNewNoteForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [relDialogOpen, setRelDialogOpen] = useState(false)

  // Claims/Evidence content is a synchronous lookup over the already-fetched
  // GraphResponse (no network round trip) — a one-tick Skeleton gates the
  // Claims/Evidence tab bodies while this local resolve runs.
  const selectionKey = selected ? `${selected.kind}:${selected.id}` : 'none'
  const [resolved, setResolved] = useState(false)
  const [prevSelectionKey, setPrevSelectionKey] = useState(selectionKey)
  if (prevSelectionKey !== selectionKey) {
    setPrevSelectionKey(selectionKey)
    setResolved(false)
  }

  useEffect(() => {
    if (resolved) return
    const id = setTimeout(() => setResolved(true), 0)
    return () => clearTimeout(id)
  }, [resolved])

  // Reset note editing state when selection changes
  const prevSelectionKeyRef = useRef(selectionKey)
  if (prevSelectionKeyRef.current !== selectionKey) {
    prevSelectionKeyRef.current = selectionKey
    setEditingNote(null)
    setShowNewNoteForm(false)
  }

  const selectedNode =
    selected?.kind === 'node' ? graph.nodes.find((node) => node.id === selected.id) : undefined
  const selectedEdge =
    selected?.kind === 'edge' ? graph.edges.find((edge) => edge.id === selected.id) : undefined
  const nodeLabel = (id: string) => graph.nodes.find((node) => node.id === id)?.label ?? id
  const relevantClaims = resolveClaimsForSelection(selected, graph)
  const activeClaim = selected?.kind === 'edge' ? relevantClaims[0] : undefined
  const evidenceEntries = resolveEvidenceForClaims(relevantClaims, graph)

  // Determine the target info for notes
  const noteTargetType = selectedNode
    ? (selectedNode.type === 'Claim' ? 'Claim' as const : 'Character' as const)
    : activeClaim
      ? 'Claim' as const
      : undefined

  // Use seriesId from props instead of graph.series.id for API compatibility
  const notesState = useNotes({
    seriesId: seriesId,
    visibleUntilOrder: visibleUntilOrder,
    targetType: noteTargetType,
    targetId: selectedNode?.id ?? activeClaim?.id,
  })

  const notes = notesState.status === 'success' ? notesState.data : []

  const handleCreateNote = useCallback(async (content: string) => {
    if (!seriesId || !selectedNode && !activeClaim) return
    setSaving(true)
    try {
      if (selectedNode) {
        await notesState.createNote({
          target_type: selectedNode.type === 'Claim' ? 'Claim' : 'Character',
          target_id: selectedNode.id,
          content,
        })
      } else if (activeClaim) {
        await notesState.createNote({
          target_type: 'Claim',
          target_id: activeClaim.id,
          content,
        })
      }
      setShowNewNoteForm(false)
      onRefetchGraph?.()
    } catch {
      // Error handled by hook
    } finally {
      setSaving(false)
    }
  }, [seriesId, selectedNode, activeClaim, notesState, onRefetchGraph])

  const handleEditNote = useCallback(async (noteId: string, content: string) => {
    if (!seriesId) return
    setSaving(true)
    try {
      await notesState.updateNote(noteId, { content })
      setEditingNote(null)
    } catch {
      // Error handled by hook
    } finally {
      setSaving(false)
    }
  }, [seriesId, notesState])

  const handleDeleteNote = useCallback(async (noteId: string) => {
    if (!seriesId) return
    try {
      await notesState.deleteNote(noteId)
    } catch {
      // Error handled by hook
    }
  }, [seriesId, notesState])

  const title =
    selectedNode?.label ??
    activeClaim?.label ??
    (selected?.kind === 'edge'
      ? graph.edges.find((edge) => edge.id === selected.id)?.type
      : undefined) ??
    'Details'

  // Workaround for stale-ref callback: keep the latest delete in a ref
  const handleDeleteNoteRef = useRef(handleDeleteNote)
  handleDeleteNoteRef.current = handleDeleteNote

  return (
    <Sheet open={open} onOpenChange={(next) => !next && onDeselect()} modal={false}>
      <SheetContent
        side="left"
        showCloseButton={false}
        // Two independent non-modal Radix sheets (left inspector + right chat)
        // must coexist: without this, opening one fires DismissableLayer's
        // focus-outside on the other (Radix Dialog closes a non-modal dialog
        // when a second dialog steals focus) and the first silently closes.
        // Close is driven by selection state (onDeselect), never by outside
        // interaction or Escape.
        onInteractOutside={(event) => event.preventDefault()}
        onEscapeKeyDown={(event) => event.preventDefault()}
        className={cn(
          'mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 max-sm:max-h-[70vh] lg:max-w-md',
        )}
      >
        <SheetHeader>
          <div className="flex min-w-0 items-center gap-3">
            {selectedNode?.type === 'Character' && (
              <CharacterPortrait
                key={selectedNode.id}
                node={selectedNode}
                visibleUntilOrder={visibleUntilOrder}
              />
            )}
            <SheetTitle className="truncate">{selected ? title : 'Details'}</SheetTitle>
          </div>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-2 px-4 pb-4 text-sm">
          {!selected && <p>Select a node to see details.</p>}
          {selected && (
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                {noteTargetType && <TabsTrigger value="notes">Notes</TabsTrigger>}
                {(selectedNode || activeClaim) && <TabsTrigger value="history">History</TabsTrigger>}
                <TabsTrigger value="claims">Claims</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="flex flex-col gap-1 pt-2">
                {selected.kind === 'node' && selectedNode && (
                  <dl className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Node Type</dt>
                      <dd>{selectedNode.type}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Name</dt>
                      <dd>{selectedNode.label}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Origin</dt>
                      <dd>
                        {selectedNode.origin === 'user' ? (
                          <span className="inline-flex items-center gap-1 rounded border-2 border-dashed border-primary/50 px-1.5 py-0.5 text-xs font-medium">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-3 w-3" aria-hidden="true">
                              <path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                            </svg>
                            User
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs">{selectedNode.origin}</span>
                        )}
                      </dd>
                    </div>
                  </dl>
                )}
                {selected.kind === 'node' && selectedNode && (
                  <button
                    type="button"
                    className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors min-h-[44px]"
                    onClick={() => setRelDialogOpen(true)}
                    aria-label="Create relationship"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden="true">
                      <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                    </svg>
                    Create Relationship
                  </button>
                )}
                {selected.kind === 'edge' && activeClaim && (
                  <dl className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Relationship</dt>
                      <dd>{activeClaim.predicate}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Claim Type</dt>
                      <dd>{activeClaim.claim_type}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Status</dt>
                      <dd>{activeClaim.status}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">Confidence</dt>
                      <dd>{activeClaim.confidence_level}</dd>
                    </div>
                  </dl>
                )}
                {selected.kind === 'edge' && !activeClaim && selectedEdge && (
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 rounded-md border border-border p-3">
                      <span>{nodeLabel(selectedEdge.source)}</span>
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true">
                        <path d="M5 12h14"></path>
                        <path d="m12 5 7 7-7 7"></path>
                      </svg>
                      <span>{nodeLabel(selectedEdge.target)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      User-created relationship (origin: user).
                    </p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="notes" className="flex flex-col gap-2 pt-2">
                {/* Create note form */}
                {showNewNoteForm ? (
                  <NoteEditor
                    initialContent=""
                    onSave={handleCreateNote}
                    onCancel={() => setShowNewNoteForm(false)}
                    saving={saving}
                  />
                ) : (
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors min-h-[44px]"
                    onClick={() => setShowNewNoteForm(true)}
                    aria-label="Add note"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden="true">
                      <path d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                    Add Note
                  </button>
                )}

                {/* Loading state */}
                {notesState.status === 'loading' && (
                  <div className="flex flex-col gap-2">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                )}

                {/* Error state */}
                {notesState.status === 'error' && (
                  <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive">
                    Failed to load notes. Try again.
                  </div>
                )}

                {/* Empty state */}
                {notesState.status === 'success' && notes.length === 0 && (
                  <p className="text-xs text-muted-foreground py-2">No notes yet — add one above.</p>
                )}

                {/* Notes list */}
                {notes.length > 0 && (
                  <div className="flex flex-col gap-2 max-h-[40vh] overflow-y-auto">
                    {notes.map((note) => (
                      editingNote?.id === note.id ? (
                        <NoteEditor
                          key={note.id}
                          initialContent={note.content}
                          onSave={(content) => handleEditNote(note.id, content)}
                          onCancel={() => setEditingNote(null)}
                          saving={saving}
                        />
                      ) : (
                        <NoteItem
                          key={note.id}
                          note={note}
                          onEdit={(n) => setEditingNote(n)}
                          onDelete={handleDeleteNoteRef.current}
                        />
                      )
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="claims" className="flex flex-col gap-2 pt-2">
                {!resolved && <Skeleton className="h-16 w-full" />}
                {resolved && relevantClaims.length === 0 && (
                  <p>No claims recorded for this node yet</p>
                )}
                {resolved &&
                  relevantClaims.map((claim) => (
                    <div
                      key={claim.id}
                      className="rounded-md border border-border p-2"
                      style={{ borderLeft: `4px solid ${CLAIM_ACCENT_COLOR}` }}
                    >
                      <p className="font-medium">{claim.label}</p>
                      <p className="text-muted-foreground">
                        {claim.predicate} · {claim.status} · {claim.confidence_level}
                      </p>
                    </div>
                  ))}
              </TabsContent>

              <TabsContent value="evidence" className="flex flex-col gap-2 pt-2">
                {!resolved && <Skeleton className="h-16 w-full" />}
                {resolved && evidenceEntries.length === 0 && (
                  <p>No evidence recorded for this claim yet</p>
                )}
                {resolved &&
                  evidenceEntries.map(({ evidence, sourceLabel }) => (
                    <div
                      key={evidence.id}
                      className="max-h-32 overflow-y-auto rounded-md border border-border p-2"
                      style={{ borderLeft: `4px solid ${EVIDENCE_ACCENT_COLOR}` }}
                    >
                      <p>
                        Source: {sourceLabel} - {evidence.locator}
                      </p>
                      <p className="text-muted-foreground">{evidence.text}</p>
                    </div>
                  ))}
              </TabsContent>

              <TabsContent value="history" className="flex flex-col gap-1 pt-2">
                <RevisionHistoryPanel
                  seriesId={seriesId}
                  visibleUntilOrder={visibleUntilOrder}
                  resourceType={selectedNode?.type ?? 'Claim'}
                  resourceId={selectedNode?.id ?? activeClaim?.id}
                  onRefetchGraph={onRefetchGraph}
                />
              </TabsContent>
            </Tabs>
          )}
        </div>
        <CreateRelationshipDialog
          open={relDialogOpen}
          onOpenChange={setRelDialogOpen}
          seriesId={seriesId}
          selectedNodeId={selectedNode?.id ?? null}
          selectedNodeLabel={selectedNode?.label ?? null}
          graphNodes={graph.nodes}
          episodes={episodes}
          onSuccess={(rel) => {
            ;(onRefreshGraph ?? onRefetchGraph)?.()
            onRelationshipCreated?.(rel)
          }}
        />
      </SheetContent>
    </Sheet>
  )
}
