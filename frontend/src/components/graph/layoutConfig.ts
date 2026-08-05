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
      nodeRepulsion: (node: { isParent?: () => boolean }) =>
        node.isParent?.() ? 120000 : 55000,
      idealEdgeLength: 220,
      edgeElasticity: 0.35,
      gravity: 0.08,
      tilingPaddingVertical: 35,
      tilingPaddingHorizontal: 35,
    }
  }

  if (name === 'cose-bilkent') {
    return {
      ...common,
      name: 'cose-bilkent',
      nodeRepulsion: 45000,
      idealEdgeLength: 240,
      edgeElasticity: 0.25,
      gravity: 0.08,
      tile: true,
    }
  }

  return {
    ...common,
    name: 'cose',
    nodeRepulsion: (node: { isParent?: () => boolean }) =>
      node.isParent?.() ? 50000 : 45000,
    idealEdgeLength: 240,
    edgeElasticity: 0.25,
    gravity: 0.08,
  }
}
