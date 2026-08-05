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
      quality: 'default',
      randomize: false,
      // 08-06 (product owner): nodes need ~2.5cm of clearance between them
      // (~95px at 96dpi). fcose has no hard min-gap parameter, so the gap is
      // enforced via strong node repulsion (all pairs) + long ideal edges
      // (connected pairs); gravity is lowered so clusters don't collapse
      // back together. Tune these constants if the live graph reads too
      // tight or too loose.
      nodeRepulsion: (node: { isParent?: () => boolean }) =>
        node.isParent?.() ? 450000 : 220000,
      idealEdgeLength: 320,
      edgeElasticity: 0.35,
      gravity: 0.04,
      tilingPaddingVertical: 35,
      tilingPaddingHorizontal: 35,
    }
  }

  if (name === 'cose-bilkent') {
    return {
      ...common,
      name: 'cose-bilkent',
      nodeRepulsion: 120000,
      idealEdgeLength: 320,
      edgeElasticity: 0.25,
      gravity: 0.04,
      tile: true,
    }
  }

  return {
    ...common,
    name: 'cose',
    nodeRepulsion: (node: { isParent?: () => boolean }) =>
      node.isParent?.() ? 150000 : 120000,
    idealEdgeLength: 320,
    edgeElasticity: 0.25,
    gravity: 0.04,
  }
}
