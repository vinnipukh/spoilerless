// Edge-type → color-family mapping for the graph canvas.
//
// Each edge type resolves first to a "family" (EDGE_TYPE_TO_FAMILY) and then
// the family to a hex colour (FAMILY_HEX). Unmapped types fall through to a
// default muted slate. This two-level indirection lets multiple edge types
// share a single visual family without repeating hex values.

import { DEFAULT_EDGE_HEX, EDGE_FAMILY_COLORS } from '@/lib/tokens/graphTokens'

export type EdgeColorFamily =
  | 'violet'
  | 'slate'
  | 'amber'
  | 'teal'
  | 'cyan'
  | 'green'
  | 'red'

export const DEFAULT_HEX = DEFAULT_EDGE_HEX

export const EDGE_TYPE_TO_FAMILY: Record<string, EdgeColorFamily> = {
  FAMILY_OF: 'violet',
  PART_OF: 'slate',
  PRECEDES: 'slate',
  OCCURRED_IN: 'amber',
  LOCATED_IN: 'amber',
  PARTICIPATED_IN: 'teal',
  WITNESSED: 'teal',
  CAUSED: 'teal',
  AFFECTED: 'teal',
  TARGETED: 'teal',
  MENTIONED: 'teal',
  KNOWS: 'cyan',
  WORKS_WITH: 'cyan',
  TRUSTS: 'green',
  HELPS: 'green',
  DISTRUSTS: 'red',
  OPPOSES: 'red',
  THREATENS: 'red',
  ATTACKS: 'red',
  KILLS: 'red',
  CORRECTS: 'slate',
  SUPERSEDES: 'slate',
  REVERTS_TO: 'slate',
}

// VisualizationDTO intentionally exposes human semantic classes instead of
// raw relationship types. Keep their colors aligned with legacy edges while
// preserving that public contract.
const RELATION_CLASS_TO_FAMILY: Record<string, EdgeColorFamily> = {
  part_of: 'slate',
  precedes: 'slate',
  knows: 'cyan',
  family: 'violet',
  work: 'cyan',
  trusts: 'green',
  distrusts: 'red',
  helps: 'green',
  opposes: 'red',
  threatens: 'red',
  attacks: 'red',
  kills: 'red',
  participated_in: 'teal',
  occurred_in: 'amber',
  located_in: 'amber',
  witnessed: 'teal',
  caused: 'teal',
  affected: 'teal',
  targeted: 'teal',
  mentioned: 'teal',
  supported_by: 'teal',
  from_source: 'amber',
}

export const FAMILY_HEX: Record<EdgeColorFamily, string> = EDGE_FAMILY_COLORS

export function edgeColorFor(edgeType: string | undefined): string {
  const family = edgeType
    ? EDGE_TYPE_TO_FAMILY[edgeType] ?? RELATION_CLASS_TO_FAMILY[edgeType.toLowerCase()]
    : undefined
  if (!family) return DEFAULT_HEX
  return FAMILY_HEX[family]
}
