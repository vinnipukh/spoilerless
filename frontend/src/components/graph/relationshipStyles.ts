// Edge-type → color-family mapping for the graph canvas.
//
// Each edge type resolves first to a "family" (EDGE_TYPE_TO_FAMILY) and then
// the family to a hex colour (FAMILY_HEX). Unmapped types fall through to a
// default muted slate. This two-level indirection lets multiple edge types
// share a single visual family without repeating hex values.

export type EdgeColorFamily =
  | 'violet'
  | 'slate'
  | 'amber'
  | 'teal'
  | 'cyan'
  | 'green'
  | 'red'

export const DEFAULT_HEX = 'rgba(148,163,184,0.35)' // --muted-foreground, slate

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

export const FAMILY_HEX: Record<EdgeColorFamily, string> = {
  violet: '#A78BFA',
  slate: DEFAULT_HEX,
  amber: '#D97706',
  teal: '#2DD4BF',
  cyan: '#38BDF8',
  green: '#34D399',
  red: '#EF4444',
}

export function edgeColorFor(edgeType: string | undefined): string {
  const family = edgeType
    ? EDGE_TYPE_TO_FAMILY[edgeType] ?? RELATION_CLASS_TO_FAMILY[edgeType.toLowerCase()]
    : undefined
  if (!family) return DEFAULT_HEX
  return FAMILY_HEX[family]
}
