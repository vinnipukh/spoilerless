// Neutral Cytoscape element adapter module (Plan 12-14).
//
// Unifies Cytoscape element conversion logic for both the GraphResponse (legacy/graph)
// and VisualizationDTO (Phase 10/visualization) paths.
//
// D-08 / D-36: The frontend owns these conversions; cluster policy is explicit and
// input-driven. Ungrouped visualization nodes NEVER receive episode bands.
// Threat model T10-LEAK-04: data key sets are strictly controlled per element type.

import type { ElementDefinition } from 'cytoscape'
import { apiUrl } from '../../api/client'
import { overviewProjection, type GraphMode } from '../../components/graph/overviewTiers'
import type {
  GraphEdge,
  GraphResponse,
  VisualizationDTO,
} from '../../types/graph'

const GROUP_PARENT_PREFIX = 'group:'

export type SceneElementDefinition = ElementDefinition

export type ToCytoscapeOptions = {
  /** Advanced/debug only (D-14): adds a `debugLabel` data key carrying the
   * technical node kind / edge relation class. Default false — technical
   * labels never reach the scene outside debug. */
  debugLabels?: boolean
}

// Documented data keys emitted per element kind. Exact-shape tests pin these
// sets; anything extra is a T10-LEAK-04 violation.
export const NODE_DATA_KEYS = [
  'id',
  'label',
  'nodeType',
  'displayTier',
  'order',
  'origin',
  'episodeId',
  'parent',
  'imageUrl',
  'debugLabel',
] as const

export const GROUP_DATA_KEYS = ['id', 'label', 'isCluster', 'groupId', 'debugLabel'] as const

export const EDGE_DATA_KEYS = [
  'id',
  'source',
  'target',
  'label',
  'relationClass',
  'order',
  'claimId',
  'origin',
  'debugLabel',
] as const

/**
 * Single explicit cluster policy:
 * - When `groups` is provided (visualization path): maps 1:1 to DTO group membership.
 *   Returns `{ id: 'group:groupId', label: group.label }` if node is in a group, else `null`.
 *   Policy rule: ungrouped visualization nodes receive NO compound parent (visual parity).
 * - When `groups` is null/undefined (graph path): maps to episode band `Ep #N` from
 *   `visible_from_order`, or fallback `Main`. Returns `{ id: 'cluster:Ep #N', label: 'Ep #N' }`.
 */
export function clusterFor(
  node: { id?: string; visible_from_order?: number | null },
  groups?: { id: string; label: string; node_ids?: string[] }[] | null,
): { id: string; label: string } | null {
  if (groups != null) {
    if (!node.id) return null
    for (const group of groups) {
      if (group.node_ids?.includes(node.id)) {
        return {
          id: `${GROUP_PARENT_PREFIX}${group.id}`,
          label: group.label,
        }
      }
    }
    return null
  }

  const clusterKey =
    node.visible_from_order != null
      ? `Ep #${node.visible_from_order}`
      : 'Main'
  return {
    id: `cluster:${clusterKey}`,
    label: clusterKey,
  }
}

/**
 * Shared internal enrichment helper that strips undefined values to enforce
 * exact-shape element data dictionaries.
 */
function enrich(raw: Record<string, unknown>): ElementDefinition {
  const data: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(raw)) {
    if (value !== undefined) {
      data[key] = value
    }
  }
  return { data }
}

/**
 * Convert a GraphResponse into Cytoscape ElementDefinition[].
 */
export function fromGraph(
  graph: GraphResponse,
  mode: GraphMode = 'full',
  opts?: ToCytoscapeOptions,
): SceneElementDefinition[] {
  let nodes = graph.nodes
  let edges: GraphEdge[] = graph.edges
  if (mode === 'overview') {
    const projection = overviewProjection(graph)
    nodes = graph.nodes.filter((n) => projection.keptNodeIds.has(n.id))
    edges = projection.keptEdges
  }

  const degree = new Map<string, number>()
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
  }

  const connected = new Set<string>()
  for (const edge of edges) {
    connected.add(edge.source)
    connected.add(edge.target)
  }

  const claimById = new Map(graph.claims.map((c) => [c.id, c]))
  const clusters = new Map<string, string>()

  const nodeElements: ElementDefinition[] = nodes
    .filter((node) => connected.has(node.id))
    .map((node) => {
      const imageUrl = node.type === 'Character' ? apiUrl(node.image_url) : null
      const simple = !imageUrl && (degree.get(node.id) ?? 0) < 3

      const cluster = clusterFor(node, undefined)
      if (cluster && !clusters.has(cluster.id)) {
        clusters.set(cluster.id, cluster.label)
      }

      return enrich({
        id: node.id,
        label: node.label,
        nodeType: node.type,
        origin: node.origin,
        parent: cluster?.id,
        simple: simple ? true : undefined,
        imageUrl: imageUrl ?? undefined,
        debugLabel: opts?.debugLabels ? node.type : undefined,
      })
    })

  const parentElements: ElementDefinition[] = Array.from(clusters.entries()).map(
    ([id, label]) =>
      enrich({
        id,
        label,
        isCluster: true,
        areaScale: mode === 'full' && label === 'Ep #1' ? 3 : undefined,
      }),
  )

  const edgeElements: ElementDefinition[] = edges.map((edge) => {
    const claim = edge.claim_id ? claimById.get(edge.claim_id) : undefined
    return enrich({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.type,
      edgeType: edge.type,
      origin: edge.origin,
      claimId: edge.claim_id,
      claimStatus: claim?.status,
      debugLabel: opts?.debugLabels ? edge.type : undefined,
    })
  })

  return [...parentElements, ...nodeElements, ...edgeElements]
}

/**
 * Convert a VisualizationDTO into Cytoscape ElementDefinition[].
 */
export function fromVisualization(
  dto: VisualizationDTO,
  options: ToCytoscapeOptions = {},
): SceneElementDefinition[] {
  const { debugLabels = false } = options

  const groupElements: ElementDefinition[] = dto.groups.map((group) =>
    enrich({
      id: `${GROUP_PARENT_PREFIX}${group.id}`,
      label: group.label,
      isCluster: true,
      groupId: group.id,
      debugLabel: debugLabels ? group.id : undefined,
    }),
  )

  const nodeElements: ElementDefinition[] = dto.nodes.map((node) => {
    const imageUrl = node.kind === 'Character' ? apiUrl(node.image_url) : null
    const cluster = clusterFor(node, dto.groups)

    return enrich({
      id: node.id,
      label: node.label,
      nodeType: node.kind,
      displayTier: node.display_tier,
      order: node.order,
      origin: node.origin,
      episodeId: node.episode_id,
      parent: cluster?.id,
      imageUrl: imageUrl ?? undefined,
      debugLabel: debugLabels ? node.kind : undefined,
    })
  })

  const edgeElements: ElementDefinition[] = dto.edges.map((edge) =>
    enrich({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relation_class,
      relationClass: edge.relation_class,
      order: edge.order,
      claimId: edge.claim_id,
      origin: edge.origin,
      debugLabel: debugLabels ? edge.relation_class : undefined,
    }),
  )

  return [...groupElements, ...nodeElements, ...edgeElements]
}
