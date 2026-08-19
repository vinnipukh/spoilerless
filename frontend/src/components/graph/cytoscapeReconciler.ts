import type cytoscape from 'cytoscape'
import type { Core, ElementDefinition, SingularElementReturnValue } from 'cytoscape'

type ElementData = Record<string, unknown> & {
  id: string
  source?: string
  target?: string
  parent?: string
}

type RuntimeSnapshot = {
  classes: string[]
  selected: boolean
  position?: cytoscape.Position
}

const TOPOLOGY_KEYS = new Set(['id', 'source', 'target', 'parent'])

function dataOf(definition: ElementDefinition): ElementData {
  return definition.data as ElementData
}

function isEdgeDefinition(definition: ElementDefinition): boolean {
  const data = dataOf(definition)
  return data.source !== undefined || data.target !== undefined
}

function patchData(element: SingularElementReturnValue, next: ElementData) {
  const current = element.data() as Record<string, unknown>
  for (const key of Object.keys(current)) {
    if (!TOPOLOGY_KEYS.has(key) && !(key in next)) element.removeData(key)
  }
  for (const [key, value] of Object.entries(next)) {
    if (!TOPOLOGY_KEYS.has(key) && !Object.is(current[key], value)) {
      element.data(key, value)
    }
  }
}

/**
 * Reconcile a complete element scene without letting removal of an obsolete
 * compound parent cascade-delete shared children and edges.
 *
 * react-cytoscapejs plans updates from declared ids, then removes old-only
 * elements first. Cytoscape compound removal recursively removes descendants,
 * invalidating that id plan. This reconciler adds target nodes, detaches or
 * reparents shared nodes, rewires shared edges, then removes stale topology.
 * Shared element identity, runtime classes/selection, positions, zoom, and pan
 * remain intact.
 */
export function reconcileCytoscapeElements(
  cy: Core,
  nextDefinitions: ElementDefinition[],
): void {
  const nextById = new Map(nextDefinitions.map((definition) => [String(dataOf(definition).id), definition]))
  const nextIds = new Set(nextById.keys())
  const currentIds = new Set(cy.elements().map((element) => element.id()))
  const nextNodes = nextDefinitions.filter((definition) => !isEdgeDefinition(definition))
  const nextEdges = nextDefinitions.filter(isEdgeDefinition)

  const runtime = new Map<string, RuntimeSnapshot>()
  for (const id of nextIds) {
    if (!currentIds.has(id)) continue
    const element = cy.getElementById(id)
    if (element.length === 0) continue
    runtime.set(id, {
      classes: element.classes(),
      selected: element.selected(),
      ...(element.isNode() ? { position: { ...element.position() } } : {}),
    })
  }

  cy.batch(() => {
    const incomingNodes = nextNodes.filter((definition) => !currentIds.has(String(dataOf(definition).id)))
    if (incomingNodes.length > 0) cy.add(incomingNodes)

    for (const definition of nextNodes) {
      const next = dataOf(definition)
      if (!currentIds.has(String(next.id))) continue
      const node = cy.getElementById(String(next.id))
      if (node.length === 0) continue
      const currentParent = node.parent()[0]?.id() ?? null
      const nextParent = next.parent == null ? null : String(next.parent)
      if (currentParent !== nextParent) node.move({ parent: nextParent })
    }

    for (const definition of nextEdges) {
      const next = dataOf(definition)
      if (!currentIds.has(String(next.id))) continue
      const edge = cy.getElementById(String(next.id))
      if (edge.length === 0) continue
      const source = String(next.source)
      const target = String(next.target)
      if (edge.source().id() !== source || edge.target().id() !== target) {
        edge.move({ source, target })
      }
    }

    const staleEdges = cy.edges().filter((edge) => !nextIds.has(edge.id()))
    if (staleEdges.length > 0) cy.remove(staleEdges)

    // Shared children have already been detached/reparented, so removing the
    // stale node collection (children and parents together) cannot cascade
    // into any id retained by the target scene.
    const staleNodes = cy.nodes().filter((node) => !nextIds.has(node.id()))
    if (staleNodes.length > 0) cy.remove(staleNodes)

    const incomingEdges = nextEdges.filter((definition) => !currentIds.has(String(dataOf(definition).id)))
    if (incomingEdges.length > 0) cy.add(incomingEdges)

    for (const definition of nextDefinitions) {
      const next = dataOf(definition)
      if (!currentIds.has(String(next.id))) continue
      const element = cy.getElementById(String(next.id))
      if (element.length > 0) patchData(element, next)
    }

    for (const [id, snapshot] of runtime) {
      const element = cy.getElementById(id)
      if (element.length === 0) continue
      element.classes(snapshot.classes)
      if (snapshot.position && element.isNode()) element.position(snapshot.position)
      if (snapshot.selected) element.select()
    }
  })
}
