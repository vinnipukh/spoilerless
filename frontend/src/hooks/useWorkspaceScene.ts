import { useEffect, useMemo, useState } from 'react'
import type { FocusedElementIds } from '../components/graph/GraphCanvas'
import type { VisualizationDTO, VisualizationViewType } from '../types/graph'
import type { GraphResponse } from '../types/graph'
import type { ExpansionKey } from '../api/graph'
import { fetchVisualization, fetchExpansion } from '../api/graph'

// 12-08 (THERMO-P0-02): the visualization scene layer extracted from App.tsx.
// Owns: active view resolution (topTab + evidenceMode -> VisualizationViewType),
// base/focus DTO loading, expansion records with the in-flight race guard
// (THERMO-P2-07), and the mergedVisualization derivation. All state changes
// happen in effects/handlers — never during render.

type SceneArgs = {
  topTab: string
  graphMode: string
  evidenceMode: string
  seriesId: string | null
  confirmedOrder: number
  graphFocus: FocusedElementIds | null
}

export type ExpansionRecord = {
  anchorId: string
  key: string
  additionIds: string[]
  dto: VisualizationDTO
}

export function useWorkspaceScene({ topTab, graphMode, evidenceMode, seriesId, confirmedOrder, graphFocus }: SceneArgs) {
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

  const [baseVisualization, setBaseVisualization] = useState<VisualizationDTO | null>(null)
  const [focusVisualization, setFocusVisualization] = useState<VisualizationDTO | null>(null)
  const [expansionRecords, setExpansionRecords] = useState<ExpansionRecord[]>([])

  useEffect(() => {
    if (!activeView || activeView === 'graphrag_focus' || !seriesId) return
    let cancelled = false
    fetchVisualization(seriesId, activeView, confirmedOrder)
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
  }, [activeView, seriesId, confirmedOrder])

  // Expansions belong to the active scene — reset when the view changes.
  useEffect(() => {
    setExpansionRecords([])
  }, [activeView])

  useEffect(() => {
    if (evidenceMode !== 'answer_graph' || !graphFocus?.nodeIds.length || !seriesId) {
      setFocusVisualization(null)
      return
    }
    let cancelled = false
    fetchVisualization(seriesId, 'graphrag_focus', confirmedOrder, graphFocus.nodeIds)
      .then((dto) => {
        if (!cancelled) setFocusVisualization(dto)
      })
      .catch((error: unknown) => {
        console.error('graphrag focus fetch failed', error)
      })
    return () => {
      cancelled = true
    }
  }, [evidenceMode, graphFocus, seriesId, confirmedOrder])

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

  // THERMO-P2-07 in-flight race guard: an expansion response is only applied
  // when its anchor node is still selected AND the series/boundary it was
  // fetched for still matches the current ones. Rapid navigation can no
  // longer append records into the wrong scene.
  async function handleExpand(
    key: string,
    selectedNodeId: string | null,
    onDone?: () => void,
  ) {
    if (!selectedNodeId || !seriesId) return
    const requestSeriesId = seriesId
    const requestOrder = confirmedOrder
    try {
      const dto = await fetchExpansion(requestSeriesId, selectedNodeId, key as ExpansionKey, requestOrder)
      // Race guard — drop stale responses after view/boundary/series change.
      if (seriesId !== requestSeriesId || confirmedOrder !== requestOrder || selectedNodeId == null) {
        return
      }
      const record: ExpansionRecord = {
        anchorId: selectedNodeId,
        key,
        additionIds: dto.nodes.map((n) => n.id),
        dto,
      }
      setExpansionRecords((prev) => [...prev, record])
      onDone?.()
    } catch (error: unknown) {
      console.error('expansion failed', error)
    }
  }

  function undoLastExpansion() {
    setExpansionRecords((prev) => prev.slice(0, -1))
  }

  function collapseExpansions(anchorId: string) {
    setExpansionRecords((prev) => prev.filter((r) => r.anchorId !== anchorId))
  }

  return {
    activeView,
    mergedVisualization,
    expansionRecords,
    handleExpand,
    undoLastExpansion,
    collapseExpansions,
  }
}

// FEAT-03 (09-07): newly-revealed highlight on episode forward advance,
// extracted from App.tsx verbatim (guarded render-time adjustment retained).
export function useNewlyRevealed(
  graphState: { status: string; data: GraphResponse | null },
  confirmedOrder: number | null,
): FocusedElementIds | null {
  const [prevGraphSnapshot, setPrevGraphSnapshot] = useState<{
    payload: GraphResponse | null
    order: number | null
  } | null>(null)
  const [newlyRevealedIds, setNewlyRevealedIds] = useState<FocusedElementIds | null>(null)
  if (graphState.status === 'success' && graphState.data !== prevGraphSnapshot?.payload) {
    const prevOrder = prevGraphSnapshot?.order ?? null
    const nextOrder = confirmedOrder
    const prevPayload = prevGraphSnapshot?.payload ?? null
    const advancedForward =
      prevPayload != null && prevOrder !== nextOrder && (nextOrder ?? 0) > (prevOrder ?? 0)
    if (advancedForward && graphState.data) {
      const prevNodeIds = new Set(prevPayload!.nodes.map((node) => node.id))
      const prevEdgeIds = new Set(prevPayload!.edges.map((edge) => edge.id))
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
  return newlyRevealedIds
}
