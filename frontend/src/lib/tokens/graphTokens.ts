/**
 * Authoritative visual design tokens for graph visualization, entity node types,
 * relationship families, highlight glows, and claim/evidence badges.
 * Centralized to eliminate design token drift across canvas, stylesheets, and detail drawers.
 */

export const NODE_TYPE_COLORS = {
  Character: '#38BDF8',
  Event: '#2DD4BF',
  Location: '#60A5FA',
  Organization: '#FB7185',
  Episode: '#FBBF24',
  Series: '#131936',
  UserNote: '#131936',
  Object: '#131936',
  Claim: '#D946EF',
  Evidence: '#FB923C',
} as const

export const CLAIM_ACCENT_COLOR = NODE_TYPE_COLORS.Claim
export const EVIDENCE_ACCENT_COLOR = NODE_TYPE_COLORS.Evidence

export const EDGE_FAMILY_COLORS = {
  violet: '#A78BFA',
  slate: 'rgba(148,163,184,0.35)',
  amber: '#D97706',
  teal: '#2DD4BF',
  cyan: '#38BDF8',
  green: '#34D399',
  red: '#EF4444',
} as const

export const DEFAULT_EDGE_HEX = EDGE_FAMILY_COLORS.slate

export const GRAPH_CANVAS_TOKENS = {
  background: '#0F172A',
  card: '#192134',
  elevated: '#1E2740',
  muted: '#131936',
  mutedForeground: '#94A3B8',
  border: 'rgba(255, 255, 255, 0.08)',
  borderLight: 'rgba(255, 255, 255, 0.12)',
  accent: '#7C3AED',
  clusterBorder: '#334155',
  edgeLabelBg: '#0B1120',
  simpleDot: '#64748B',
  edgeDefaultText: '#E2E8F0',
  nodeLabelText: '#FFFFFF',
} as const

export const SELECTION_GLOW_TOKENS = {
  selectedOverlayColor: '#7C3AED',
  selectedOverlayOpacity: 0.35,
  hoverOverlayOpacity: 0.15,
  revealedOverlayOpacity: 0.45,
  pathOverlayOpacity: 0.3,
} as const
