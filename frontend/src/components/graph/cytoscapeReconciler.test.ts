import cytoscape, { type ElementDefinition } from 'cytoscape'
import { describe, expect, it } from 'vitest'
import { reconcileCytoscapeElements } from './cytoscapeReconciler'

const dexterId = 'dexter:character:dexter_morgan'
const camillaId = 'dexter:character:camilla_figg'
const edgeId = 'dexter:claim:s01e01:camilla_works_dexter:edge'

const legacyOverview: ElementDefinition[] = [
  { data: { id: 'cluster:Ep #1', isCluster: true } },
  { data: { id: dexterId, label: 'Dexter Morgan', parent: 'cluster:Ep #1' } },
]

const characterNetwork: ElementDefinition[] = [
  { data: { id: dexterId, label: 'Dexter Morgan' } },
  { data: { id: camillaId, label: 'Camilla Figg' } },
  { data: { id: edgeId, source: camillaId, target: dexterId, relationClass: 'work' } },
]

function ids(cy: cytoscape.Core) {
  return cy.elements().map((element) => element.id()).sort()
}

describe('reconcileCytoscapeElements', () => {
  it('moves shared children out of stale compounds before removal', () => {
    const cy = cytoscape({ headless: true, styleEnabled: false, elements: legacyOverview })
    const dexter = cy.getElementById(dexterId)
    const identity = dexter[0]
    dexter.position({ x: 42, y: 84 })
    dexter.addClass('selected-dominant')
    dexter.select()
    cy.zoom(1.4)
    cy.pan({ x: 12, y: 18 })

    expect(() => reconcileCytoscapeElements(cy, characterNetwork)).not.toThrow()
    expect(ids(cy)).toEqual(characterNetwork.map((element) => String(element.data.id)).sort())
    expect(cy.getElementById(dexterId)[0]).toBe(identity)
    expect(cy.getElementById(dexterId).parent().length).toBe(0)
    expect(cy.getElementById(dexterId).position()).toEqual({ x: 42, y: 84 })
    expect(cy.getElementById(dexterId).hasClass('selected-dominant')).toBe(true)
    expect(cy.getElementById(dexterId).selected()).toBe(true)
    expect(cy.zoom()).toBe(1.4)
    expect(cy.pan()).toEqual({ x: 12, y: 18 })
    expect(cy.getElementById(edgeId).source().id()).toBe(camillaId)
    expect(cy.getElementById(edgeId).target().id()).toBe(dexterId)
    cy.destroy()
  })

  it('rewires a shared edge before removing its old-only endpoint', () => {
    const replacementId = 'dexter:character:debra_morgan'
    const oldScene: ElementDefinition[] = [
      { data: { id: dexterId } },
      { data: { id: camillaId } },
      { data: { id: edgeId, source: camillaId, target: dexterId } },
    ]
    const nextScene: ElementDefinition[] = [
      { data: { id: dexterId } },
      { data: { id: replacementId } },
      { data: { id: edgeId, source: replacementId, target: dexterId } },
    ]
    const cy = cytoscape({ headless: true, styleEnabled: false, elements: oldScene })

    reconcileCytoscapeElements(cy, nextScene)

    expect(ids(cy)).toEqual(nextScene.map((element) => String(element.data.id)).sort())
    expect(cy.getElementById(edgeId).source().id()).toBe(replacementId)
    expect(cy.getElementById(edgeId).target().id()).toBe(dexterId)
    cy.destroy()
  })

  it('adds and removes expansion deltas without changing viewport', () => {
    const cy = cytoscape({ headless: true, styleEnabled: false, elements: characterNetwork })
    cy.zoom(1.2)
    cy.pan({ x: -7, y: 15 })
    const clueId = 'dexter:evidence:clue'
    const expanded = [
      ...characterNetwork,
      { data: { id: clueId, label: 'Clue' } },
      { data: { id: 'edge:clue', source: dexterId, target: clueId, relationClass: 'supported_by' } },
    ] satisfies ElementDefinition[]

    reconcileCytoscapeElements(cy, expanded)
    expect(ids(cy)).toEqual(expanded.map((element) => String(element.data.id)).sort())
    reconcileCytoscapeElements(cy, characterNetwork)

    expect(ids(cy)).toEqual(characterNetwork.map((element) => String(element.data.id)).sort())
    expect(cy.zoom()).toBe(1.2)
    expect(cy.pan()).toEqual({ x: -7, y: 15 })
    cy.destroy()
  })
})
