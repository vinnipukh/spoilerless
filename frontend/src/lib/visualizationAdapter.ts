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
import type {
  VisualizationDTO,
  VisualizationTimelineItem,
} from '../types/graph'
import {
  fromVisualization,
  EDGE_DATA_KEYS,
  GROUP_DATA_KEYS,
  NODE_DATA_KEYS,
  type ToCytoscapeOptions,
} from './graph/sceneElements'

export type { ToCytoscapeOptions }
export { NODE_DATA_KEYS, GROUP_DATA_KEYS, EDGE_DATA_KEYS }

export function toCytoscapeElements(
  dto: VisualizationDTO,
  options: ToCytoscapeOptions = {},
): ElementDefinition[] {
  return fromVisualization(dto, options)
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
