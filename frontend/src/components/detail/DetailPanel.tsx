import { useCallback, useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { SpoilerGuard } from '@/components/ui/SpoilerGuard'
import { fetchExportMarkdown, downloadMarkdownBlob } from '@/api/export'
import { apiUrl } from '../../api/client'
import { renderGraphMarkdown, exportFilename } from '@/lib/exportMarkdown'
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
import { BacklinksTab } from './BacklinksTab'

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
      src={apiUrl(node.image_url) ?? undefined}
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
  /** Quick task 260805-te3: read-only visitor (misafir) mode — hides the
   * Create Relationship action and all note write affordances (add/edit/
   * delete). The inspector stays fully browsable. */
  readOnly?: boolean
  onSelectNode?: (nodeId: string) => void
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
  readOnly = false,
}: {
  note: NoteResponse
  onEdit: (note: NoteResponse) => void
  onDelete: (noteId: string) => void
  /** Quick task 260805-te3: read-only (visitor) mode hides edit/delete. */
  readOnly?: boolean
}) {
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="rounded-md border border-border p-2 text-sm">
      <p className="whitespace-pre-wrap break-words">{note.content}</p>
      {!readOnly && (
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
      )}
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

  // Default to the highest visible episode via a guarded render-time
  // adjustment — the same "adjust state when a prop/key changes" pattern
  // useGraph.ts uses (react-hooks/set-state-in-effect clean: never a
  // synchronous setState in an effect body).
  if (!episodeId && episodes.length > 0) {
    const highest = episodes.reduce((a, b) => a.id > b.id ? a : b)
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
  readOnly = false,
  onSelectNode,
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
    // Reset note editing state when the selection changes — merged into the
    // same state-copy adjustment (was a separate ref-based copy) so no ref
    // is read or written during render (react-hooks/refs clean).
    setEditingNote(null)
    setShowNewNoteForm(false)
  }

  useEffect(() => {
    if (resolved) return
    const id = setTimeout(() => setResolved(true), 0)
    return () => clearTimeout(id)
  }, [resolved])

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

  // The hook returns a FRESH object every render — depending on the whole
  // object in useCallback deps would recreate the callback every render and
  // defeat the memoization (react-hooks/preserve-manual-memoization).
  // Destructure its stable inner callbacks instead.
  const {
    createNote: createNoteApi,
    updateNote: updateNoteApi,
    deleteNote: deleteNoteApi,
  } = notesState

  // Plain async handlers, NOT useCallback: their only non-trivial deps are
  // hook-returned values (createNoteApi/updateNoteApi/deleteNoteApi) whose
  // stability the React Compiler cannot prove — useCallback memoization is
  // neither preserved nor effective here (the note components are
  // non-memoized), so the unnecessary memoization is deleted rather than
  // suppressed (react-hooks/preserve-manual-memoization clean).
  const handleCreateNote = async (content: string) => {
    if (!seriesId || !selectedNode && !activeClaim) return
    setSaving(true)
    try {
      if (selectedNode) {
        await createNoteApi({
          target_type: selectedNode.type === 'Claim' ? 'Claim' : 'Character',
          target_id: selectedNode.id,
          content,
        })
      } else if (activeClaim) {
        await createNoteApi({
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
  }

  const handleEditNote = async (noteId: string, content: string) => {
    if (!seriesId) return
    setSaving(true)
    try {
      await updateNoteApi(noteId, { content })
      setEditingNote(null)
    } catch {
      // Error handled by hook
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteNote = async (noteId: string) => {
    if (!seriesId) return
    try {
      await deleteNoteApi(noteId)
    } catch {
      // Error handled by hook
    }
  }

  const title =
    selectedNode?.label ??
    activeClaim?.label ??
    (selected?.kind === 'edge'
      ? graph.edges.find((edge) => edge.id === selected.id)?.type
      : undefined) ??
    'Details'

  const [exported, setExported] = useState(false)

  const handleExport = async () => {
    if (!seriesId) return
    const targetId = selectedNode?.id ?? activeClaim?.id
    try {
      const { text, filename } = await fetchExportMarkdown(
        seriesId,
        visibleUntilOrder ?? 1,
        targetId,
      )
      downloadMarkdownBlob(text, filename)
    } catch {
      const text = renderGraphMarkdown(graph, targetId)
      const filename = exportFilename(graph, targetId)
      downloadMarkdownBlob(text, filename)
    }
    setExported(true)
    setTimeout(() => setExported(false), 2000)
  }

  return (
    // Self-contained provider (same pattern as GraphCanvas.tsx:531) — the
    // Export Markdown Tooltip in the header renders on every selection, and
    // DetailPanel is a sibling of GraphCanvas (App renders both), so without
    // this Radix throws "Tooltip must be used within TooltipProvider" and
    // selecting any node crashes the app (2026-08-05, caught by the
    // DetailPanel/App test reds).
    <TooltipProvider>
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
          'mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 max-sm:max-h-[70vh]',
          // 08-06+: the base shadcn sheet pins the width with a
          // DATA-ATTRIBUTE variant (`data-[side=left]:sm:max-w-sm`, 384px) —
          // higher specificity than plain lg:max-w-xl, so the inspector was
          // stuck at 384px and six tabs (~374px) clipped the rightmost one.
          // Override at the SAME specificity: 448px on sm+, 576px on lg+.
          'data-[side=left]:sm:max-w-md data-[side=left]:lg:max-w-xl',
          // Fix 3: explicit left-border + shadow prevents canvas bleed-through
          'border-r border-border shadow-lg',
        )}
      >
        {/* Fix 2/3: flex-col layout with sticky header + tab bar, scrollable body */}
        <SheetHeader className="shrink-0">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              {selectedNode?.type === 'Character' && (
                <CharacterPortrait
                  key={selectedNode.id}
                  node={selectedNode}
                  visibleUntilOrder={visibleUntilOrder}
                />
              )}
              <SheetTitle className="min-w-0 break-words">
                {selected ? (
                  <SpoilerGuard
                    text={title}
                    revealedOrder={selectedNode?.visible_from_order ?? 0}
                    currentOrder={visibleUntilOrder}
                  />
                ) : (
                  'Details'
                )}
              </SheetTitle>
            </div>
            {selected && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="Export Markdown"
                    className={`shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      exported ? 'text-accent' : ''
                    }`}
                    onClick={handleExport}
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">{exported ? 'Exported' : 'Export Markdown'}</TooltipContent>
              </Tooltip>
            )}
          </div>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col text-sm">
          {!selected && <p className="px-4 pb-4">Select a node to see details.</p>}
          {selected && (
            <Tabs defaultValue="overview" className="flex min-h-0 flex-1 flex-col">
              {/* Fix 2: sticky tab bar with opaque bg and relative z-10 prevents
                  canvas control overlays from bleeding through */}
              {/* 08-06+: the base shadcn TabsList is w-fit — with 6 tabs it
                  grows past the panel and the parent clips the rightmost tab
                  (Evidence) with no scrollbar. Cap it at the available width
                  (mx-4 margins accounted) so overflow-x-auto actually
                  scrolls; triggers are shrink-0 so they keep natural width. */}
              <TabsList className="sticky top-0 z-10 shrink-0 w-fit max-w-[calc(100%-2rem)] overflow-x-auto flex-nowrap bg-popover mx-4">
                <TabsTrigger value="overview" className="shrink-0">Overview</TabsTrigger>
                {selectedNode && <TabsTrigger value="backlinks" className="shrink-0">Backlinks</TabsTrigger>}
                {/* Visitor (misafir) mode: Notes and History are auth-gated
                    surfaces (note writes + revert 401 for guests) — hide the
                    tabs entirely instead of showing dead-end affordances. */}
                {!readOnly && noteTargetType && <TabsTrigger value="notes" className="shrink-0">Notes</TabsTrigger>}
                {!readOnly && (selectedNode || activeClaim) && <TabsTrigger value="history" className="shrink-0">History</TabsTrigger>}
                <TabsTrigger value="claims" className="shrink-0">Claims</TabsTrigger>
                <TabsTrigger value="evidence" className="shrink-0">Evidence</TabsTrigger>
              </TabsList>

              {/* Fix 3: overflow-y-auto ONLY on the tab content body — header
                  and tab bar stay fixed at top via shrink-0 + sticky */}
              <TabsContent value="overview" className="flex flex-col gap-1 overflow-y-auto px-4 pb-4 pt-2">
                {selected.kind === 'node' && selectedNode && (
                  /* Fix 1: CSS Grid with fixed label column prevents text collision.
                     word-break + overflow-wrap ensure long values wrap cleanly. */
                  <dl className="grid grid-cols-[minmax(110px,130px)_1fr] gap-x-3 gap-y-1.5 text-xs">
                    <dt className="text-muted-foreground shrink-0">Node Type</dt>
                    <dd className="font-medium break-words overflow-wrap-anywhere">{selectedNode.type}</dd>

                    <dt className="text-muted-foreground shrink-0">Name</dt>
                    <dd className="font-medium break-words overflow-wrap-anywhere">
                      <SpoilerGuard
                        text={selectedNode.label}
                        revealedOrder={selectedNode.visible_from_order}
                        currentOrder={visibleUntilOrder}
                      />
                    </dd>

                    <dt className="text-muted-foreground shrink-0">Origin</dt>
                    <dd className="break-words overflow-wrap-anywhere">
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

                    <dt className="text-muted-foreground shrink-0">Revealed in</dt>
                    <dd className="font-medium break-words overflow-wrap-anywhere">
                      {selectedNode.visible_from_order != null
                        ? `Episode #${selectedNode.visible_from_order}`
                        : '-'}
                    </dd>

                    {selectedNode.episode_id && (
                      <>
                        <dt className="text-muted-foreground shrink-0">Episode ID</dt>
                        <dd className="font-medium break-words overflow-wrap-anywhere">{selectedNode.episode_id}</dd>
                      </>
                    )}

                    <dt className="text-muted-foreground shrink-0">Claims count</dt>
                    <dd className="font-medium">{relevantClaims.length}</dd>

                    <dt className="text-muted-foreground shrink-0">Notes count</dt>
                    <dd className="font-medium">{notes.length}</dd>

                    {selectedNode.image_source_url && (
                      <>
                        <dt className="text-muted-foreground shrink-0">Image source</dt>
                        <dd className="font-medium">
                          <a
                            href={selectedNode.image_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary underline hover:text-primary/80"
                          >
                            Source link
                          </a>
                        </dd>
                      </>
                    )}
                  </dl>
                )}
                {selected.kind === 'node' && selectedNode && !readOnly && (
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
                  <dl className="grid grid-cols-[minmax(110px,130px)_1fr] gap-x-3 gap-y-1.5 text-xs">
                    <dt className="text-muted-foreground shrink-0">Relationship</dt>
                    <dd className="break-words overflow-wrap-anywhere">{activeClaim.predicate}</dd>

                    <dt className="text-muted-foreground shrink-0">Claim Type</dt>
                    <dd className="break-words overflow-wrap-anywhere">{activeClaim.claim_type}</dd>

                    <dt className="text-muted-foreground shrink-0">Status</dt>
                    <dd className="break-words overflow-wrap-anywhere">{activeClaim.status}</dd>

                    <dt className="text-muted-foreground shrink-0">Confidence</dt>
                    <dd className="break-words overflow-wrap-anywhere">{activeClaim.confidence_level}</dd>
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

              <TabsContent value="backlinks" className="overflow-y-auto px-4 pb-4 pt-2">
                <BacklinksTab
                  selectedElement={selected}
                  graph={graph}
                  userNotes={notes}
                  onSelectNode={(nodeId) => {
                    if (onSelectNode) onSelectNode(nodeId)
                    else onDeselect()
                  }}
                />
              </TabsContent>

              <TabsContent value="notes" className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
                {/* The Notes trigger itself is hidden in read-only (visitor)
                    mode — the notes routes are auth-gated, so a guest can
                    never reach this content. */}
                {/* Create note form */}
                {showNewNoteForm ? (
                  <NoteEditor
                    initialContent=""
                    onSave={handleCreateNote}
                    onCancel={() => setShowNewNoteForm(false)}
                    saving={saving}
                  />
                ) : (
                  !readOnly && (
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
                  )
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
                          onDelete={handleDeleteNote}
                          readOnly={readOnly}
                        />
                      )
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="claims" className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
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
                      <p className="font-medium break-words overflow-wrap-anywhere">
                        <SpoilerGuard
                          text={claim.label}
                          revealedOrder={claim.visible_from_order}
                          currentOrder={visibleUntilOrder}
                        />
                      </p>
                      <p className="text-muted-foreground">
                        {claim.predicate} · {claim.status} · {claim.confidence_level}
                      </p>
                    </div>
                  ))}
              </TabsContent>

              <TabsContent value="evidence" className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
                {!resolved && <Skeleton className="h-16 w-full" />}
                {resolved && evidenceEntries.length === 0 && (
                  <p>No evidence recorded for this claim yet</p>
                )}
                {resolved &&
                  evidenceEntries.map(({ evidence, sourceLabel }) => (
                    // 08-06+ (product owner): render evidence as CLAIMS-style
                    // cards — bold title + muted metadata line, cards grow
                    // naturally (no max-h-32 inner scroll; the panel scrolls
                    // as a whole, matching the Claims tab).
                    <div
                      key={evidence.id}
                      className="rounded-md border border-border p-2"
                      style={{ borderLeft: `4px solid ${EVIDENCE_ACCENT_COLOR}` }}
                    >
                      <p className="font-medium break-words overflow-wrap-anywhere">
                        Source: {sourceLabel} - {evidence.locator}
                      </p>
                      <p className="text-muted-foreground">{evidence.origin}</p>
                    </div>
                  ))}
              </TabsContent>

              <TabsContent value="history" className="flex flex-col gap-1 overflow-y-auto px-4 pb-4 pt-2">
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
        {/* end scrollable tab content wrapper */}
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
    </TooltipProvider>
  )
}
