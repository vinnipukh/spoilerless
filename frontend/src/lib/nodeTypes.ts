// Node-type metadata (D-24 table), shared between GraphLegend and the
// search/palette components (plan 09-09, UI-SPEC §10.3). Moved OUT of
// GraphLegend.tsx so that file stays components-only
// (react-refresh/only-export-components).

import { NODE_TYPE_COLORS } from '@/lib/tokens/graphTokens'

export type NodeTypeMeta = {
  type: string
  shape: 'ellipse' | 'round-rect' | 'diamond' | 'tag' | 'star' | 'rect'
  color: string
}

export const NODE_TYPES: NodeTypeMeta[] = [
  { type: 'Character', shape: 'ellipse', color: NODE_TYPE_COLORS.Character },
  { type: 'Event', shape: 'round-rect', color: NODE_TYPE_COLORS.Event },
  { type: 'Location', shape: 'round-rect', color: NODE_TYPE_COLORS.Location },
  { type: 'Organization', shape: 'diamond', color: NODE_TYPE_COLORS.Organization },
  { type: 'Episode', shape: 'tag', color: NODE_TYPE_COLORS.Episode },
  { type: 'Series', shape: 'star', color: NODE_TYPE_COLORS.Series },
  { type: 'UserNote', shape: 'round-rect', color: NODE_TYPE_COLORS.UserNote },
  { type: 'Object', shape: 'ellipse', color: NODE_TYPE_COLORS.Object },
]

// The closed set of types the custom-node dialog may create — mirrors the
// backend's CustomNodeType enum (types/userContent re-exports this).
// Derived registries below (ALLOWED_NODE_TYPES, GraphCanvas's filter
// list) build from NODE_TYPES so a new node type lands in one place
// (PROB-09 #81).
export const CUSTOM_NODE_TYPE_NAMES = [
  'Character',
  'Event',
  'Location',
  'Organization',
  'Object',
] as const

export type CustomNodeType = (typeof CUSTOM_NODE_TYPE_NAMES)[number]

export const ALLOWED_NODE_TYPES: { value: CustomNodeType; label: string }[] = NODE_TYPES.filter(
  (nt) => (CUSTOM_NODE_TYPE_NAMES as readonly string[]).includes(nt.type),
).map((nt) => ({ value: nt.type as CustomNodeType, label: nt.type }))
