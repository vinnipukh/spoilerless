import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import coseBilkent from 'cytoscape-cose-bilkent'
import type { GraphMode } from './overviewTiers'

// Register extensions with Cytoscape safely (no-op if already registered)
try {
  cytoscape.use(fcose)
} catch {
  // Extension already registered or register error fallback
}

try {
  cytoscape.use(coseBilkent)
} catch {
  // Extension already registered or register error fallback
}

export const DEXTER_NODE_ID = 'char_dexter_morgan'

type RepulsionNode = {
  isParent?: () => boolean
  data?: (key: string) => unknown
  id?: () => string
}

export const OVERVIEW_SPACING_SCALE = 1.6

/**
 * Per-node repulsion multiplier used by every layout.
 *
 * 08-06+ (product owner) special case: every node must sit at least ~7cm
 * (~265px @96dpi) from Dexter Morgan's node. fcose has no per-pair
 * min-gap parameter, so Dexter's node carries ~1.96x the base repulsion of
 * a normal node — pair separation scales with sqrt(repulsion product),
 * i.e. sqrt(1_633_333 / 833_333) = 1.4x the ~5cm base gap ≈ 7cm
 * center-to-center. Tunable via DEXTER_REPULSION.
 */
export const DEXTER_REPULSION = 1_633_333

export function nodeRepulsionFor(node: RepulsionNode, spacingScale: number = 1): number {
  const id =
    typeof node.id === 'function'
      ? node.id()
      : (node.data?.('id') as string | undefined)
  if (id === DEXTER_NODE_ID) return DEXTER_REPULSION * spacingScale
  return (node.isParent?.() ? 1666667 : 833333) * spacingScale
}

export function layoutOptionsFor(
  name: 'fcose' | 'cose-bilkent' | 'cose',
  prefersReducedMotion: boolean = false,
  mode: GraphMode = 'full',
) {
  const common = {
    fit: true,
    padding: 48,
    animate: prefersReducedMotion ? false : ('end' as const),
  }

  // 08-06+ (product owner): Overview mode gets extra spacing so the fewer,
  // curated clusters are easier to read — repulsion × OVERVIEW_SPACING_SCALE
  // (pair separation scales ~ sqrt(repulsion) ≈ 1.26x), longer ideal edges,
  // lower gravity, roomier cluster tiling. Full mode keeps the 5cm/7cm
  // constants tuned on the dense graph.
  const spacing = mode === 'overview' ? OVERVIEW_SPACING_SCALE : 1
  const edgeLength = mode === 'overview' ? 420 : 320
  const gravity = mode === 'overview' ? 0.015 : 0.02
  const tiling = mode === 'overview' ? 45 : 35

  if (name === 'fcose') {
    return {
      ...common,
      name: 'fcose',
      // 'proof' = high-quality mode: more iterations + better crossing
      // minimization (08-06: dense graph, long edges were colliding).
      quality: 'proof',
      randomize: false,
      // 08-06+ (product owner): nodes need ~5cm of clearance between them
      // (~189px at 96dpi; was ~3cm, raised 08-06+). fcose has no hard
      // min-gap parameter, so the gap is enforced via strong node repulsion
      // (all pairs) + long ideal edges (connected pairs); gravity is
      // lowered so clusters don't collapse back together. Tune these
      // constants if the live graph reads too tight or too loose.
      nodeRepulsion: (node: RepulsionNode) => nodeRepulsionFor(node, spacing),
      idealEdgeLength: edgeLength,
      // 08-06: stiffer springs make the pull between CONNECTED nodes
      // dominant (nodes are drawn toward their neighbours, not the canvas
      // centre); gravity is lowered to ~zero so the layout is edge-driven.
      edgeElasticity: 0.75,
      gravity,
      tilingPaddingVertical: tiling,
      tilingPaddingHorizontal: tiling,
    }
  }

  if (name === 'cose-bilkent') {
    return {
      ...common,
      name: 'cose-bilkent',
      nodeRepulsion: 160000 * spacing,
      idealEdgeLength: edgeLength,
      edgeElasticity: 0.4,
      gravity,
      tile: true,
    }
  }

  return {
    ...common,
    name: 'cose',
    nodeRepulsion: (node: RepulsionNode) => nodeRepulsionFor(node, spacing),
    idealEdgeLength: edgeLength,
    edgeElasticity: 0.4,
    gravity,
  }
}
