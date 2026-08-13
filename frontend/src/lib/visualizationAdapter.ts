// Pure adapters from the neutral VisualizationDTO (D-08) to Cytoscape
// elements and timeline data. The frontend OWNS these conversions (D-08);
// the backend owns every spoiler decision (D-04/D-05).
//
// Safety contract (threat model T10-LEAK-04):
// - These functions consume ONLY serialized visible fields. They never
//   filter any node/edge by order, never infer hidden fields, counts,
//   degrees, or restoration hints, and never branch on anything the backend
//   did not serialize (D-06).
// - `toCytoscapeElements` emits a fixed, documented data-key set per element
//   kind; the exact-shape tests in visualizationAdapter.test.ts pin that set
//   so a hidden field sneaking into the DTO cannot silently flow through to
//   Cytoscape data (and from there into layout force, styling, or labels).
// - Technical labels (raw relation names / node-kind vocabulary) are hidden
//   outside explicit debug mode: `debugLabels: true` is the ONLY switch that
//   adds a `debugLabel` data key (consumed by the Advanced/debug stylesheet).
//   D-14: the backend serializes human `relation_class` wording, never raw
//   Neo4j names, so the default edge label is already human wording.
// - D-36: DTO `groups` are editorial plot threads — mapped 1:1 to compound
//   parents with visible membership only. No group is invented client-side.
// - Deterministic: same DTO in, same elements out (ids and order preserved).

import type { ElementDefinition } from 'cytoscape'
import { apiUrl } from '../api/client'
import type {
  VisualizationDTO,
  VisualizationTimelineItem,
} from '../types/graph'

// Node-kind vocabulary the existing stylesheet already understands
// (graphElements.ts uses `nodeType` for the same purpose). Group parents are
// prefixed so they can never collide with a real node id.
const GROUP_PARENT_PREFIX = 'group:'

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

export function toCytoscapeElements(
  dto: VisualizationDTO,
  options: ToCytoscapeOptions = {},
): ElementDefinition[] {
  const { debugLabels = false } = options

  // Group parents first (compound parents must precede their children in the
  // elements array so Cytoscape can resolve `parent`).
  const groupElements: ElementDefinition[] = dto.groups.map((group) => ({
    data: {
      id: `${GROUP_PARENT_PREFIX}${group.id}`,
      label: group.label,
      isCluster: true,
      groupId: group.id,
      ...(debugLabels ? { debugLabel: group.id } : {}),
    },
  }))

  const parentFor = new Map<string, string>()
  for (const group of dto.groups) {
    for (const nodeId of group.node_ids) {
      parentFor.set(nodeId, `${GROUP_PARENT_PREFIX}${group.id}`)
    }
  }

  const nodeElements: ElementDefinition[] = dto.nodes.map((node) => {
    const imageUrl = node.kind === 'Character' ? apiUrl(node.image_url) : null
    const parent = parentFor.get(node.id)
    return {
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.kind,
        displayTier: node.display_tier,
        order: node.order,
        origin: node.origin,
        episodeId: node.episode_id,
        ...(parent ? { parent } : {}),
        ...(imageUrl ? { imageUrl } : {}),
        ...(debugLabels ? { debugLabel: node.kind } : {}),
      },
    }
  })

  // Every DTO edge passes through — the adapter never filters. `label` is the
  // backend's human relation class; the stylesheet's label POLICY (never /
  // on_hover / on_select / on_path / medium_zoom / always, D-14) decides when
  // it is actually rendered.
  const edgeElements: ElementDefinition[] = dto.edges.map((edge) => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relation_class,
      relationClass: edge.relation_class,
      order: edge.order,
      claimId: edge.claim_id,
      origin: edge.origin,
      ...(debugLabels ? { debugLabel: edge.relation_class } : {}),
    },
  }))

  return [...groupElements, ...nodeElements, ...edgeElements]
}

export type TimelineEvent = VisualizationTimelineItem

// Pure pass-through of the serialized timeline fields (D-38). The timeline
// stays React/CSS (D-23); this adapter is the typed seam between the neutral
// DTO and TimelineView. Exact-shape tests pin the field set — no hidden
// field can ride along.
export function toTimelineEvents(dto: VisualizationDTO): TimelineEvent[] {
  return dto.timeline.map((item) => ({
    id: item.id,
    kind: item.kind,
    label: item.label,
    episode_id: item.episode_id,
    episode_order: item.episode_order,
    order: item.order,
    display_tier: item.display_tier,
    participant_ids: item.participant_ids,
    location_id: item.location_id,
    location_label: item.location_label,
  }))
}
