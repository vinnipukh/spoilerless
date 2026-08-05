import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import coseBilkent from 'cytoscape-cose-bilkent'

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

/**
 * Per-node repulsion multiplier used by every layout.
 *
 * 08-06 (product owner) special case: every node must sit at least ~5cm
 * (~190px @96dpi) from Dexter Morgan's node. fcose has no per-pair
 * min-gap parameter, so Dexter's node carries ~5.5x the base repulsion of
 * a normal node — pair separation scales with sqrt(repulsion product),
 * i.e. sqrt(1_200_000 / 220_000) ≈ 2.3x the ~95px base gap ≈ 220px ≈ 5.8cm
 * center-to-center. Tunable via DEXTER_REPULSION.
 */
export const DEXTER_REPULSION = 1_200_000

export function nodeRepulsionFor(node: RepulsionNode): number {
  const id =
    typeof node.id === 'function'
      ? node.id()
      : (node.data?.('id') as string | undefined)
  if (id === DEXTER_NODE_ID) return DEXTER_REPULSION
  return node.isParent?.() ? 600000 : 300000
}

export function layoutOptionsFor(
  name: 'fcose' | 'cose-bilkent' | 'cose',
  prefersReducedMotion: boolean = false,
) {
  const common = {
    fit: true,
    padding: 48,
    animate: prefersReducedMotion ? false : ('end' as const),
  }

  if (name === 'fcose') {
    return {
      ...common,
      name: 'fcose',
      // 'proof' = high-quality mode: more iterations + better crossing
      // minimization (08-06: dense graph, long edges were colliding).
      quality: 'proof',
      randomize: false,
      // 08-06 (product owner): nodes need ~3cm of clearance between them
      // (~113px at 96dpi; was ~2.5cm, raised 08-06). fcose has no hard
      // min-gap parameter, so the gap is enforced via strong node repulsion
      // (all pairs) + long ideal edges (connected pairs); gravity is
      // lowered so clusters don't collapse back together. Tune these
      // constants if the live graph reads too tight or too loose.
      nodeRepulsion: nodeRepulsionFor,
      idealEdgeLength: 320,
      // 08-06: stiffer springs make the pull between CONNECTED nodes
      // dominant (nodes are drawn toward their neighbours, not the canvas
      // centre); gravity is lowered to ~zero so the layout is edge-driven.
      edgeElasticity: 0.75,
      gravity: 0.02,
      tilingPaddingVertical: 35,
      tilingPaddingHorizontal: 35,
    }
  }

  if (name === 'cose-bilkent') {
    return {
      ...common,
      name: 'cose-bilkent',
      nodeRepulsion: 160000,
      idealEdgeLength: 320,
      edgeElasticity: 0.4,
      gravity: 0.03,
      tile: true,
    }
  }

  return {
    ...common,
    name: 'cose',
    nodeRepulsion: nodeRepulsionFor,
    idealEdgeLength: 320,
    edgeElasticity: 0.4,
    gravity: 0.03,
  }
}
