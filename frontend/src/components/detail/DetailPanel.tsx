import { useCallback, useRef, useState } from 'react'
import { Download, X } from 'lucide-react'
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { SpoilerGuard } from '@/components/ui/SpoilerGuard'
import { fetchExportMarkdown, downloadMarkdownBlob } from '@/api/export'
import { renderGraphMarkdown, exportFilename } from '@/lib/exportMarkdown'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import type { SelectedElement } from '../graph/GraphCanvas'
import type { GraphClaim, GraphEvidence, GraphResponse } from '../../types/graph'
import { useNotes } from '../../hooks/useNotes'
import type { CustomRelationshipResponse, NoteResponse } from '../../types/userContent'
import { CUSTOM_NODE_TYPE_NAMES, type CustomNodeType } from '../../lib/nodeTypes'
import { RevisionHistoryPanel } from './RevisionHistoryPanel'
import { BacklinksTab } from './BacklinksTab'
import { CharacterPortrait } from './CharacterPortrait'
import { CreateRelationshipDialog } from '../dialogs/CreateRelationshipDialog'
import { OverviewTab } from './tabs/OverviewTab'
import { NotesTab } from './tabs/NotesTab'
import { ClaimsTab, CLAIM_ACCENT_COLOR } from './tabs/ClaimsTab'
import { EvidenceTab, EVIDENCE_ACCENT_COLOR } from './tabs/EvidenceTab'

// CitationChip.tsx imports these accents from this module (06-09) — the
// canonical homes are now tabs/ClaimsTab.tsx + tabs/EvidenceTab.tsx; kept as
// re-exports so the existing import path keeps working.
export { CLAIM_ACCENT_COLOR, EVIDENCE_ACCENT_COLOR }

// Full Overview/Notes/Claims/Evidence tabbed Sheet (D-07) for nodes and claim-backed
// narrative edges (edge.claim_id !== null). Structural edges (claim_id ===
// null) never reach this component — App.tsx routes those to
// StructuralEdgeCard instead (D-06), so every branch below can assume the
// selected edge (if any) is claim-backed.
//
// 12-08 (THERMO-P0-04): tab bodies, dialogs, and the portrait live in their
// own modules (tabs/, dialogs/CreateRelationshipDialog, CharacterPortrait);
// this file is the lean shell owning selection state, note handlers, and
// layout chrome. The artificial setTimeout(()=>setResolved(true),0) gate is
// GONE: claims/evidence resolution is a synchronous local lookup over the
// already-fetched GraphResponse, computed with useMemo — no one-tick Skeleton
// phase, no timer state.
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

  // Reset note editing state when the selection changes — guarded render-time
  // adjustment with a state copy of the previous key (react-hooks clean).
  const selectionKey = selected ? `${selected.kind}:${selected.id}` : 'none'
  const [prevSelectionKey, setPrevSelectionKey] = useState(selectionKey)
  if (prevSelectionKey !== selectionKey) {
    setPrevSelectionKey(selectionKey)
    setEditingNote(null)
    setShowNewNoteForm(false)
  }

  const selectedNode =
    selected?.kind === 'node' ? graph.nodes.find((node) => node.id === selected.id) : undefined
  const nodeLabel = useCallback(
    (id: string) => graph.nodes.find((node) => node.id === id)?.label ?? id,
    [graph.nodes],
  )
  // Synchronous local lookups (12-08: pure useMemo, no setTimeout gate).
  const relevantClaims = resolveClaimsForSelection(selected, graph)
  const activeClaim = selected?.kind === 'edge' ? relevantClaims[0] : undefined
  const evidenceEntries = resolveEvidenceForClaims(relevantClaims, graph)

  // Determine the target info for notes
  // THERMO-P1-03: the backend's NoteTargetType now accepts every custom node
  // label — map selectedNode.type straight through instead of collapsing
  // everything non-Claim to 'Character' (which 404'd on Location/Event/etc).
  const noteTargetType = selectedNode
    ? (selectedNode.type === 'Claim'
        ? ('Claim' as const)
        : CUSTOM_NODE_TYPE_NAMES.includes(selectedNode.type as CustomNodeType)
          ? (selectedNode.type as CustomNodeType)
          : undefined)
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
  // hook-returned values whose stability the React Compiler cannot prove.
  const handleCreateNote = async (content: string) => {
    if (!seriesId || !selectedNode && !activeClaim) return
    setSaving(true)
    try {
      if (selectedNode) {
        await createNoteApi({
          // Guarded cast: noteTargetType above already proved this is one of
          // the five custom labels (or Claim) — GraphNode.type is plain string.
          target_type:
            selectedNode.type === 'Claim'
              ? 'Claim'
              : CUSTOM_NODE_TYPE_NAMES.includes(selectedNode.type as CustomNodeType)
                ? (selectedNode.type as CustomNodeType)
                : 'Character',
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

  // THERMO-P3-10: focus restoration target for post-delete focus management.
  const panelContainerRef = useRef<HTMLDivElement | null>(null)

  const handleDeleteNote = async (noteId: string) => {
    if (!seriesId) return
    try {
      await deleteNoteApi(noteId)
      // THERMO-P3-10: the deleted note row unmounts, dropping focus to
      // document.body — restore it to the panel container.
      requestAnimationFrame(() => panelContainerRef.current?.focus())
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
  // 10-05 (D-20/D-42): mobile Inspector bottom sheet has two heights —
  // half (default) and full — toggled by the drag handle. Desktop (sm+)
  // keeps the fixed left-side sheet; the state only affects max-sm classes.
  const [sheetHeight, setSheetHeight] = useState<'half' | 'full'>('half')

  const closeInspector = useCallback(() => {
    // Escape / explicit close both funnel through onDeselect — the single
    // selection-clearing path App.tsx already owns. Radix restores focus to
    // the trigger on close; the canvas tap target remains the primary
    // return-focus destination (D-42).
    onDeselect()
  }, [onDeselect])

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
        ref={panelContainerRef}
        tabIndex={-1}
        // Two independent non-modal Radix sheets (left inspector + right chat)
        // must coexist: without this, opening one fires DismissableLayer's
        // focus-outside on the other (Radix Dialog closes a non-modal dialog
        // when a second dialog steals focus) and the first silently closes.
        // Close is driven by selection state (onDeselect), never by outside
        // interaction. Escape CLOSES the inspector (10-05, D-42) but only via
        // the explicit onDeselect funnel — it never lets Radix auto-close.
        onInteractOutside={(event) => event.preventDefault()}
        onEscapeKeyDown={(event) => {
          event.preventDefault()
          closeInspector()
        }}
        className={cn(
          'mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 max-sm:rounded-t-xl max-sm:pb-[env(safe-area-inset-bottom)] max-sm:transition-[max-height] max-sm:duration-300',
          // 10-05 (D-20/D-42): half/full-height mobile bottom sheet.
          sheetHeight === 'half' ? 'max-sm:max-h-[50vh]' : 'max-sm:max-h-[85vh]',
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
        {/* 10-05 (D-42): mobile drag handle — 44×4px touch target that toggles
            the sheet between half and full height. Desktop-hidden. */}
        <button
          type="button"
          aria-label="Toggle Inspector height"
          aria-expanded={sheetHeight === 'full'}
          onClick={() => setSheetHeight((h) => (h === 'half' ? 'full' : 'half'))}
          className="sm:hidden mx-auto mt-2 flex h-11 w-16 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="h-1 w-8 rounded-full bg-muted-foreground/40" aria-hidden="true" />
        </button>
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
                    aria-label="Close Inspector"
                    className="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={closeInspector}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">Close Inspector</TooltipContent>
              </Tooltip>
            )}
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

              <OverviewTab
                selectedKind={selected.kind}
                selectedNode={selectedNode}
                activeClaim={
                  activeClaim
                    ? {
                        predicate: activeClaim.predicate,
                        claim_type: activeClaim.claim_type,
                        status: activeClaim.status,
                        confidence_level: activeClaim.confidence_level,
                      }
                    : undefined
                }
                selectedEdge={
                  selected.kind === 'edge'
                    ? (() => {
                        const edge = graph.edges.find((e) => e.id === selected.id)
                        return edge ? { source: edge.source, target: edge.target } : undefined
                      })()
                    : undefined
                }
                nodeLabel={nodeLabel}
                relevantClaimsCount={relevantClaims.length}
                notesCount={notes.length}
                visibleUntilOrder={visibleUntilOrder}
                readOnly={readOnly}
                onOpenRelDialog={() => setRelDialogOpen(true)}
              />

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

              {!readOnly && noteTargetType && (
                <NotesTab
                  notesState={
                    notesState.status === 'success'
                      ? { status: 'success', data: notes }
                      : { status: 'loading' as const, data: [] }
                  }
                  notes={notes}
                  editingNote={editingNote}
                  showNewNoteForm={showNewNoteForm}
                  saving={saving}
                  readOnly={readOnly}
                  setShowNewNoteForm={setShowNewNoteForm}
                  handleCreateNote={handleCreateNote}
                  handleEditNote={handleEditNote}
                  setEditingNote={setEditingNote}
                  handleDeleteNote={handleDeleteNote}
                />
              )}

              <ClaimsTab
                resolved={true}
                claims={relevantClaims}
                visibleUntilOrder={visibleUntilOrder}
              />
              <EvidenceTab resolved={true} entries={evidenceEntries} />

              {(selectedNode || activeClaim) && (
                <TabsContent value="history" className="flex flex-col gap-1 overflow-y-auto px-4 pb-4 pt-2">
                  <RevisionHistoryPanel
                    seriesId={seriesId}
                    visibleUntilOrder={visibleUntilOrder}
                    resourceType={selectedNode?.type ?? 'Claim'}
                    resourceId={selectedNode?.id ?? activeClaim?.id}
                    onRefetchGraph={onRefetchGraph}
                  />
                </TabsContent>
              )}
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
