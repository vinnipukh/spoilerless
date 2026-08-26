// Mirrors spoilerless/app/domain/graph.py field-for-field.
//
// NOTE: `origin` is typed as `string`, not a union, because the wire value in
// this project is literally `'canonical'` (never `'curated'`) — see
// 02-RESEARCH.md Pitfall 1. Do not branch on `'curated'` anywhere.

import type { SeriesResponse } from './series'

export type GraphNode = {
  id: string
  type: string
  label: string
  visible_from_order: number
  origin: string
  episode_id: string | null
  image_url: string | null
  image_source_url: string | null
}

export type GraphEdge = {
  id: string
  source: string
  target: string
  type: string
  visible_from_order: number
  origin: string
  claim_id: string | null
}

export type GraphClaim = {
  id: string
  label: string
  subject_id: string
  predicate: string
  object_id: string
  claim_type: string
  status: string
  confidence_level: string
  // THERMO-P1-05: mirrors backend `str | float | None` — seed claims carry a
  // float strength, candidate-origin claims the RelationshipEffect string.
  relationship_effect: string | number | null
  visible_from_order: number
  valid_from_order: number | null
  valid_until_order: number | null
  source_id: string
  evidence_ids: string[]
  origin: string
}

export type GraphSource = {
  id: string
  label: string
  episode_id: string
  source_type: string
  locator: string
  retrieved_at: string
  visible_from_order: number
  origin: string
}

export type GraphEvidence = {
  id: string
  label: string
  episode_id: string
  source_id: string
  text: string
  locator: string
  // THERMO-P1-05: optional content hash for dedup — backend allows None and
  // legacy evidence rows may not carry it at all.
  content_hash?: string | null
  visible_from_order: number
  origin: string
}

export type GraphResponse = {
  series: SeriesResponse
  visible_until_order: number
  // THERMO-P1-05: mandatory on the backend Pydantic model (always serialized),
  // so required here despite being absent from pre-fix responses in flight.
  effective_view_order: number
  nodes: GraphNode[]
  edges: GraphEdge[]
  claims: GraphClaim[]
  sources: GraphSource[]
  evidence: GraphEvidence[]
}

// FEAT-06 (09-11): shortest-path response from POST /graph/path.
export type PathResponse = {
  found: boolean
  path: string[]
  edges: string[]
  hops: number
}

// ── Phase 10 neutral VisualizationDTO wire types (D-08) ─────────────────────
// Mirrors spoilerless/app/domain/visualization.py field-for-field. This is the
// library-neutral presentation contract produced ONLY by the backend from
// spoiler-safe graph detail; the frontend never filters or infers hidden
// fields (D-04/D-05/D-06, T10-LEAK-04).

// D-29: the exact view vocabulary of
// GET /api/series/{series_id}/graph/visualization.
export const VISUALIZATION_VIEW_TYPES = [
  'episode_overview',
  'character_network',
  'plot_threads',
  'investigation',
  'full',
  'graphrag_focus',
] as const

export type VisualizationViewType = (typeof VISUALIZATION_VIEW_TYPES)[number]

export type VisualizationMetadata = {
  projection_version: string
  view_type: string
  series_id: string
  series_title: string
  episode_order: number
  visible_until_order: number
  effective_view_order: number
}

// `origin` is `string | null` (the backend serializes Origin | None); the
// wire value in this project is `'canonical'` (never `'curated'`) — see
// 02-RESEARCH.md Pitfall 1. Do not branch on `'curated'` anywhere.
export type VisualizationNode = {
  id: string
  kind: string
  label: string
  display_tier: number
  order: number
  episode_id: string | null
  image_url: string | null
  image_source_url: string | null
  origin: string | null
}

// D-14: `relation_class` is human semantic wording (never a raw Neo4j
// relation name) — the backend guarantees this at projection time.
export type VisualizationEdge = {
  id: string
  source: string
  target: string
  relation_class: string
  order: number
  claim_id: string | null
  origin: string | null
}

// D-36: editorial plot-thread group; membership lists VISIBLE node ids only
// and carries no count/total field.
export type VisualizationGroup = {
  id: string
  label: string
  node_ids: string[]
}

// D-38: one first-class timeline entry ordered by safe reveal order.
export type VisualizationTimelineItem = {
  id: string
  kind: 'event'
  label: string
  episode_id: string
  episode_order: number
  order: number
  display_tier: number
  participant_ids: string[]
  location_id: string | null
  location_label: string | null
}

// T10-FOCUS-02: a focus may only reference a node present in the DTO; the
// backend validator rejects hidden/unknown focus IDs before serialization.
export type VisualizationFocus = {
  node_id: string
}

export type VisualizationDTO = {
  metadata: VisualizationMetadata
  nodes: VisualizationNode[]
  edges: VisualizationEdge[]
  groups: VisualizationGroup[]
  timeline: VisualizationTimelineItem[]
  focus: VisualizationFocus | null
}
