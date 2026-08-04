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
  relationship_effect: number
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
  content_hash: string
  visible_from_order: number
  origin: string
}

export type GraphResponse = {
  series: SeriesResponse
  visible_until_order: number
  nodes: GraphNode[]
  edges: GraphEdge[]
  claims: GraphClaim[]
  sources: GraphSource[]
  evidence: GraphEvidence[]
}
