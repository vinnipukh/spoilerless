// Node-type metadata (D-24 table), shared between GraphLegend and the
// search/palette components (plan 09-09, UI-SPEC §10.3). Moved OUT of
// GraphLegend.tsx so that file stays components-only
// (react-refresh/only-export-components).

export type NodeTypeMeta = {
  type: string
  shape: 'ellipse' | 'round-rect' | 'diamond' | 'tag' | 'star' | 'rect'
  color: string
}

export const NODE_TYPES: NodeTypeMeta[] = [
  { type: 'Character', shape: 'ellipse', color: '#38BDF8' },
  { type: 'Event', shape: 'round-rect', color: '#2DD4BF' },
  { type: 'Location', shape: 'round-rect', color: '#60A5FA' },
  { type: 'Organization', shape: 'diamond', color: '#FB7185' },
  { type: 'Episode', shape: 'tag', color: '#FBBF24' },
  { type: 'Series', shape: 'star', color: '#131936' },
  { type: 'UserNote', shape: 'round-rect', color: '#131936' },
  { type: 'Object', shape: 'ellipse', color: '#131936' },
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
