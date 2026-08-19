import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs'
import { Button } from './components/ui/button'
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
import { fetchExpansion, fetchVisualization, type ExpansionKey } from './api/graph'
import type { VisualizationDTO, VisualizationViewType } from './types/graph'
import { useHotkey } from './hooks/useHotkey'
import { useSceneState } from './hooks/useSceneState'
import { AnswerGraph } from './components/graph/AnswerGraph'
import { EvidenceChain } from './components/evidence/EvidenceChain'
import type { CustomRelationshipResponse } from './types/userContent'
import type { Citation } from './types/chat'
import type { ChangeSet } from './types/changeSet'
import { operationTargetRefs } from './types/changeSet'
import type { GraphResponse } from './types/graph'
import type { GraphMode } from './components/graph/overviewTiers'

// 260814-viz: the 7 allowlisted expansion keys + human labels (D-21).
const EXPANSION_KEYS: ExpansionKey[] = [
  'family',
  'work',
  'conflict',
  'episode_events',
  'clues',
  'locations',
  'evidence',
]
const EXPANSION_KEY_LABELS: Record<ExpansionKey, string> = {
  family: 'Family',
  work: 'Work',
  conflict: 'Conflict',
  episode_events: 'Episode events',
  clues: 'Clues',
  locations: 'Locations',
  evidence: 'Evidence',
}

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

// 10-05 (D-16/D-17): the fixed four-tab narrative hierarchy and each tab's
// nested responsibilities. These are navigation-only values — the shared
// workspace below the strip stays MOUNTED across switches, so filters,
// camera, and selection are never silently reset (D-47) and a tab change
// never triggers a Cytoscape relayout (D-24).
type StoryTab = 'story' | 'characters' | 'evidence' | 'advanced'
type StoryMode = 'episode_overview' | 'event_timeline'
type CharacterMode = 'character_network' | 'local_neighborhood'
type EvidenceMode = 'investigation' | 'evidence_chain' | 'answer_graph'
type AdvancedMode = 'full_graph' | 'debug'

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
  const graphState = useGraph(watchProgress.seriesId, watchProgress.viewAsOfOrder)

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
  // 10-05 (D-16/D-17): the active top tab and its nested mode. Defaults to
  // Story / Episode Overview. The nested modes remember their last value per
  // tab; switching top tabs never resets Filters (D-47) because the shared
  // workspace (GraphCanvas + search + Inspector + chat) stays mounted below
  // the tab strip.
  const [topTab, setTopTab] = useState<StoryTab>('story')
  const [graphMode, setGraphMode] = useState<GraphMode>('overview')
  const [storyMode, setStoryMode] = useState<StoryMode>('episode_overview')
  const [characterMode, setCharacterMode] = useState<CharacterMode>('character_network')
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>('investigation')
  const [advancedMode, setAdvancedMode] = useState<AdvancedMode>('full_graph')
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
  // 10-07 (D-27/D-41): the serializable scene state owns the temporary
  // Answer Graph lifecycle — OPEN_TEMPORARY snapshots the exact scene,
  // CLOSE_TEMPORARY restores it.
  const [scene, dispatchScene] = useSceneState()

  useEffect(() => {
    if (evidenceMode === 'answer_graph') {
      dispatchScene({
        type: 'OPEN_TEMPORARY',
        kind: 'answer_graph',
        nodeIds: graphFocus?.nodeIds ?? [],
      })
    }
  }, [evidenceMode, graphFocus, dispatchScene])

  function handleCloseAnswerGraph() {
    dispatchScene({ type: 'CLOSE_TEMPORARY' })
    setEvidenceMode('investigation')
  }

  function handleGraphModeChange(nextMode: GraphMode) {
    setGraphMode(nextMode)
    if (nextMode === 'overview') {
      // Overview is the original curated graph, not a narrative workspace.
      // Reset hidden navigation so returning to Full starts from Story.
      setTopTab('story')
      setStoryMode('episode_overview')
      if (evidenceMode === 'answer_graph') handleCloseAnswerGraph()
    }
  }

  // 260814-viz: the Phase 10 visualization wiring (audit-gap closure).
  // activeView maps the four-tab hierarchy to projection view types; the DTO
  // fetch drives GraphCanvas's `visualization` prop; expansions merge their
  // delta DTOs into the base scene; Answer Graph swaps in the graphrag_focus
  // projection while open. All spoiler filtering stays backend-side (D-05).
  const activeView = useMemo<VisualizationViewType | null>(() => {
    if (graphMode === 'overview') return null
    // 260814-viz: Story keeps the legacy scene (user content lives in the
    // legacy GraphResponse — custom nodes/edges are never part of a
    // projection DTO); Advanced keeps the legacy full graph for the same
    // reason. Characters and Evidence render the narrative projections.
    switch (topTab) {
      case 'characters':
        return 'character_network'
      case 'evidence':
        return evidenceMode === 'answer_graph' ? 'graphrag_focus' : 'investigation'
      default:
        return null
    }
  }, [graphMode, topTab, evidenceMode])

  // The effective boundary the backend clamps to; falls back to episode 1
  // before progress resolves (the backend re-clamps anyway).
  const confirmedOrder = watchProgress.confirmedOrder ?? 1

  const [baseVisualization, setBaseVisualization] = useState<VisualizationDTO | null>(null)
  const [focusVisualization, setFocusVisualization] = useState<VisualizationDTO | null>(null)
  const [expansionRecords, setExpansionRecords] = useState<
    { anchorId: string; key: string; additionIds: string[]; dto: VisualizationDTO }[]
  >([])
  const [expandOpen, setExpandOpen] = useState(false)

  useEffect(() => {
    if (!activeView || activeView === 'graphrag_focus' || !watchProgress.seriesId) return
    let cancelled = false
    fetchVisualization(watchProgress.seriesId, activeView, confirmedOrder)
      .then((dto) => {
        if (!cancelled) setBaseVisualization(dto)
      })
      .catch((error: unknown) => {
        // Keep the prior scene (and the legacy backbone) on failure — never
        // blank the canvas; the last non-null DTO is held by GraphCanvas.
        console.error('visualization fetch failed', error)
      })
    return () => {
      cancelled = true
    }
  }, [activeView, watchProgress.seriesId, watchProgress.confirmedOrder])

  // Expansions belong to the active scene — reset when the view changes.
  useEffect(() => {
    setExpansionRecords([])
  }, [activeView])

  useEffect(() => {
    if (evidenceMode !== 'answer_graph' || !graphFocus?.nodeIds.length || !watchProgress.seriesId) {
      setFocusVisualization(null)
      return
    }
    let cancelled = false
    fetchVisualization(watchProgress.seriesId, 'graphrag_focus', confirmedOrder, graphFocus.nodeIds)
      .then((dto) => {
        if (!cancelled) setFocusVisualization(dto)
      })
      .catch((error: unknown) => {
        console.error('graphrag focus fetch failed', error)
      })
    return () => {
      cancelled = true
    }
  }, [evidenceMode, graphFocus, watchProgress.seriesId, watchProgress.confirmedOrder])

  const mergedVisualization = useMemo<VisualizationDTO | null>(() => {
    const base = activeView === 'graphrag_focus' ? focusVisualization : baseVisualization
    if (!base) return null
    if (expansionRecords.length === 0) return base
    const nodes = [...base.nodes]
    const edges = [...base.edges]
    const timeline = [...(base.timeline ?? [])]
    const seenNodes = new Set(nodes.map((n) => n.id))
    const seenEdges = new Set(edges.map((e) => e.id))
    const seenTimeline = new Set(timeline.map((t) => t.id))
    for (const record of expansionRecords) {
      for (const node of record.dto.nodes) {
        if (!seenNodes.has(node.id)) {
          seenNodes.add(node.id)
          nodes.push(node)
        }
      }
      for (const edge of record.dto.edges) {
        if (!seenEdges.has(edge.id)) {
          seenEdges.add(edge.id)
          edges.push(edge)
        }
      }
      for (const item of record.dto.timeline ?? []) {
        if (!seenTimeline.has(item.id)) {
          seenTimeline.add(item.id)
          timeline.push(item)
        }
      }
    }
    return { ...base, nodes, edges, timeline }
  }, [baseVisualization, focusVisualization, expansionRecords, activeView])

  async function handleExpand(key: string) {
    if (!selectedElement || selectedElement.kind !== 'node' || !watchProgress.seriesId) return
    try {
      const dto = await fetchExpansion(
        watchProgress.seriesId,
        selectedElement.id,
        key as ExpansionKey,
        confirmedOrder,
      )
      const record = {
        anchorId: selectedElement.id,
        key,
        additionIds: dto.nodes.map((n) => n.id),
        dto,
      }
      setExpansionRecords((prev) => [...prev, record])
      dispatchScene({
        type: 'ADD_EXPANSION',
        nodeIds: record.additionIds,
        record: { anchorId: record.anchorId, key: record.key, additionIds: record.additionIds },
      })
      setExpandOpen(false)
    } catch (error: unknown) {
      console.error('expansion failed', error)
    }
  }

  function handleUndoExpansion() {
    setExpansionRecords((prev) => prev.slice(0, -1))
    dispatchScene({ type: 'UNDO_EXPANSION' })
  }

  function handleCollapseExpansion(anchorId: string) {
    setExpansionRecords((prev) => prev.filter((r) => r.anchorId !== anchorId))
    dispatchScene({ type: 'COLLAPSE_EXPANSION', anchorId })
  }

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
      // create_relationship contributes nothing to the post-apply
      // highlight (unchanged pre-apply behavior): the relationship id is
      // not persisted until apply, and its endpoint nodes were already on
      // screen. Everything else rides the shared operationTargetRefs
      // mapping (PROB-09 #81) — claims/notes/custom nodes highlight as
      // nodes, relationships as edges.
      if (op.operation_type === 'create_relationship') continue
      for (const ref of operationTargetRefs(op)) {
        if (ref.kind === 'Relationship') edgeIds.push(ref.id)
        else nodeIds.push(ref.id)
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
  // FORWARD advance changes confirmedOrder, diff the node/edge
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
  // FEAT-02 (09-10) + 10-05 (D-38): a timeline row click converges on the
  // SAME shared selection as a canvas tap — it selects through the existing
  // onSelect path so the Inspector opens — but it never forces a view switch
  // or a graph focus (graph focus stays optional and camera-preserving) and
  // never unmounts/relayouts the canvas. The coordinated Story rail sits
  // next to the graph; the legacy full-screen timeline keeps its own
  // jump-to-graph handler (handleTimelineSelectAndShowGraph).
  const handleTimelineSelect = (selection: { id: string; label: string; nodeType: string }) => {
    setSelectedElement({ kind: 'node', id: selection.id, label: selection.label, nodeType: selection.nodeType })
  }

  // Legacy full-screen timeline (header toggle / palette): select through the
  // shared path, then switch to the graph view so the node is framed —
  // pre-10-05 behavior, kept for that surface only.
  const handleTimelineSelectAndShowGraph = (selection: { id: string; label: string; nodeType: string }) => {
    handleTimelineSelect(selection)
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
      {view === 'settings' ? (
        <SettingsPage onBack={() => setView('graph')} />
      ) : (
        <div className="flex h-full flex-col">
          {/* The Phase 10 narrative workspace belongs to Full mode. Overview
              intentionally remains the original curated graph without extra
              Story/Characters/Evidence/Advanced navigation. */}
          {graphMode === 'full' && (
          <Tabs value={topTab} onValueChange={(value) => setTopTab(value as StoryTab)} className="shrink-0">
            <TabsList className="w-full justify-start rounded-none border-b border-border bg-background px-2 max-sm:overflow-x-auto">
              <TabsTrigger value="story" className="max-sm:min-h-[44px] max-sm:flex-none">Story</TabsTrigger>
              <TabsTrigger value="characters" className="max-sm:min-h-[44px] max-sm:flex-none">Characters</TabsTrigger>
              <TabsTrigger value="evidence" className="max-sm:min-h-[44px] max-sm:flex-none">Evidence</TabsTrigger>
              <TabsTrigger value="advanced" className="max-sm:min-h-[44px] max-sm:flex-none">Advanced</TabsTrigger>
            </TabsList>
            <TabsContent value="story" className="shrink-0 border-b border-border px-3 py-1">
              <Tabs value={storyMode} onValueChange={(value) => setStoryMode(value as StoryMode)}>
                <TabsList variant="line" className="gap-1">
                  <TabsTrigger value="episode_overview" className="max-sm:min-h-[44px]">Episode Overview</TabsTrigger>
                  <TabsTrigger value="event_timeline" className="max-sm:min-h-[44px]">Event Timeline</TabsTrigger>
                </TabsList>
              </Tabs>
            </TabsContent>
            <TabsContent value="characters" className="shrink-0 border-b border-border px-3 py-1">
              <Tabs value={characterMode} onValueChange={(value) => setCharacterMode(value as CharacterMode)}>
                <TabsList variant="line" className="gap-1">
                  <TabsTrigger value="character_network" className="max-sm:min-h-[44px]">Character Network</TabsTrigger>
                  <TabsTrigger value="local_neighborhood" className="max-sm:min-h-[44px]">Local Neighborhood</TabsTrigger>
                </TabsList>
              </Tabs>
              {characterMode === 'local_neighborhood' && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Local Neighborhood shows the selected character&apos;s immediate connections in context.
                </p>
              )}
            </TabsContent>
            <TabsContent value="evidence" className="shrink-0 border-b border-border px-3 py-1">
              <Tabs value={evidenceMode} onValueChange={(value) => setEvidenceMode(value as EvidenceMode)}>
                <TabsList variant="line" className="gap-1">
                  <TabsTrigger value="investigation" className="max-sm:min-h-[44px]">Investigation</TabsTrigger>
                  <TabsTrigger value="evidence_chain" className="max-sm:min-h-[44px]">Evidence Chain</TabsTrigger>
                  <TabsTrigger value="answer_graph" className="max-sm:min-h-[44px]">Answer Graph</TabsTrigger>
                </TabsList>
              </Tabs>
              {evidenceMode === 'evidence_chain' && (
                graphState.status === 'success' ? (
                  <div className="mt-2">
                    <EvidenceChain
                      graph={graphState.data}
                      focusIds={[]}
                      onShowInGraph={(id) =>
                        handleJumpToNode({ id, label: id, nodeType: 'Claim' })
                      }
                    />
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Evidence Chain — a layered Claim → Evidence → Source path.
                  </p>
                )
              )}
              {evidenceMode === 'answer_graph' && (
                <div className="mt-2">
                  <AnswerGraph
                    nodeIds={scene.temporary?.nodeIds ?? []}
                    onClose={handleCloseAnswerGraph}
                  />
                </div>
              )}
            </TabsContent>
            <TabsContent value="advanced" className="shrink-0 border-b border-border px-3 py-1">
              <Tabs value={advancedMode} onValueChange={(value) => setAdvancedMode(value as AdvancedMode)}>
                <TabsList variant="line" className="gap-1">
                  <TabsTrigger value="full_graph" className="max-sm:min-h-[44px]">Full Graph</TabsTrigger>
                  <TabsTrigger value="debug" className="max-sm:min-h-[44px]">Debug</TabsTrigger>
                </TabsList>
              </Tabs>
              {advancedMode === 'debug' && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Debug — technical labels and raw relation names appear only here.
                </p>
              )}
            </TabsContent>
          </Tabs>
          )}
          {view === 'timeline' ? (
            <div className="min-h-0 flex-1">
        <TimelineView
          nodes={graphState.status === 'success' ? graphState.data.nodes : []}
          claims={graphState.status === 'success' ? graphState.data.claims : []}
          episodes={episodes}
          selectedId={selectedElement?.kind === 'node' ? selectedElement.id : null}
          onSelect={handleTimelineSelectAndShowGraph}
          filteredIds={timelineFilterIds}
          onToggleFilter={(id) =>
            setTimelineFilterIds((prev) =>
              prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
            )
          }
          onClearFilter={() => setTimelineFilterIds([])}
        />
            </div>
          ) : (
            <div className="relative flex min-h-0 flex-1">
              <div className="relative min-w-0 flex-1">
        <>
      {watchProgress.pendingChange && (
        <ConfirmAdvanceModal
          open
          direction={watchProgress.pendingChange.direction}
          episodeCode={pendingEpisode?.code ?? `order ${watchProgress.pendingChange.nextOrder}`}
          episodeOrder={watchProgress.pendingChange.nextOrder}
          visitor={isVisitor}
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
            mode={graphMode}
            onModeChange={handleGraphModeChange}
            visualization={activeView ? mergedVisualization : undefined}
          />

          {/* 260814-viz: semantic expansion — visible in projection views
              when a node is selected; menu offers the 7 allowlisted keys;
              Undo pops the newest record, Collapse removes an anchor's
              records. Local placement + no global relayout (D-23). */}
          {activeView && activeView !== 'graphrag_focus' && selectedElement?.kind === 'node' && (
            <div className="fixed top-20 left-4 z-[40] w-56">
              <Button
                variant="outline"
                size="sm"
                className="flex min-h-[44px] h-8 w-full items-center justify-between gap-1.5 rounded-lg bg-card/95 px-3 text-xs text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground backdrop-blur-sm"
                onClick={() => setExpandOpen((v) => !v)}
                aria-expanded={expandOpen}
              >
                <span className="truncate">Expand {selectedElement.label}</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-3.5 shrink-0" aria-hidden="true">
                  <path d="M5 12h14M12 5v14" />
                </svg>
              </Button>
              {expandOpen && (
                <div className="mt-2 rounded-lg border border-border bg-card p-2 shadow-md">
                  <div className="flex flex-col gap-1">
                    {EXPANSION_KEYS.map((key) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handleExpand(key)}
                        className="flex min-h-[44px] items-center rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                      >
                        {EXPANSION_KEY_LABELS[key]}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {expansionRecords.length > 0 && (
                <div className="mt-2 flex flex-col gap-1 rounded-lg border border-border bg-card p-2 shadow-md">
                  <button
                    type="button"
                    onClick={handleUndoExpansion}
                    className="flex min-h-[44px] items-center rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    Undo last expansion
                  </button>
                  {Array.from(new Set(expansionRecords.map((r) => r.anchorId))).map((anchorId) => (
                    <button
                      key={anchorId}
                      type="button"
                      onClick={() => handleCollapseExpansion(anchorId)}
                      className="flex min-h-[44px] items-center rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      Collapse expansions of {anchorId}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

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
              readOnly={isVisitor}
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
                episodes.find((episode) => episode.episode_order === confirmedOrder)?.code ?? null
              }
              onShowInGraph={handleShowInGraph}
              onOpenDetail={handleOpenDetail}
              onChangeSetApplied={handleChangeSetApplied}
            />
          )}
        </>
      )}
        </>
              </div>
              {/* 10-05 (D-17/D-38): Story's coordinated Event Timeline rail —
                  a right-side panel beside the dominant Cytoscape scene, only
                  in Story / Event Timeline mode, desktop/tablet only
                  (max-sm hidden keeps ONE primary region on narrow screens,
                  D-20). The graph canvas stays mounted behind it, so
                  switching modes never resets filters or camera (D-47). */}
              {graphMode === 'full' && topTab === 'story' && storyMode === 'event_timeline' && (
                <EventTimelineRail>
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
                    showHeading
                  />
                </EventTimelineRail>
              )}
            </div>
          )}
        </div>
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

const TIMELINE_MIN_WIDTH = 240
const TIMELINE_MAX_WIDTH = 640
const TIMELINE_WIDTH_STEP = 16

function clampTimelineWidth(width: number) {
  const viewportMax = typeof window === 'undefined' ? TIMELINE_MAX_WIDTH : window.innerWidth * 0.6
  return Math.max(TIMELINE_MIN_WIDTH, Math.min(Math.min(TIMELINE_MAX_WIDTH, viewportMax), width))
}

function EventTimelineRail({ children }: { children: ReactNode }) {
  const [timelineWidth, setTimelineWidth] = useState(320)
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef<{ x: number; width: number } | null>(null)

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault()
    try {
      event.currentTarget.setPointerCapture(event.pointerId)
    } catch {
      // jsdom does not implement pointer capture — drag still works via the
      // pointer events dispatched directly on the handle (ChatSheet.tsx:60-69).
    }
    dragStart.current = { x: event.clientX, width: timelineWidth }
    setDragging(true)
  }

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragStart.current) return
    setTimelineWidth(clampTimelineWidth(dragStart.current.width + (dragStart.current.x - event.clientX)))
  }

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    dragStart.current = null
    setDragging(false)
    try {
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId)
      }
    } catch {
      // jsdom (mirrors ChatSheet.tsx:81-86)
    }
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      setTimelineWidth((width) => clampTimelineWidth(width - TIMELINE_WIDTH_STEP))
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      setTimelineWidth((width) => clampTimelineWidth(width + TIMELINE_WIDTH_STEP))
    }
  }

  return (
    <aside
      aria-label="Event Timeline"
      style={{ width: timelineWidth }}
      className="hidden shrink-0 flex-col overflow-hidden border-l border-border lg:flex"
    >
      <div className="flex h-full min-h-0">
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize Event Timeline"
          aria-keyshortcuts="ArrowLeft ArrowRight"
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onKeyDown={onKeyDown}
          className="group flex w-11 shrink-0 cursor-ew-resize touch-none select-none items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            className={
              'h-12 w-0.5 rounded-full bg-border group-hover:bg-foreground/40' +
              (dragging ? ' bg-primary' : '')
            }
          />
        </div>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </aside>
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
