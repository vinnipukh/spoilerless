import { describe, expect, it } from 'vitest'
import {
  DEXTER_NODE_ID,
  DEXTER_REPULSION,
  OVERVIEW_SPACING_SCALE,
  layoutOptionsFor,
  nodeRepulsionFor,
} from './layoutConfig'

describe('nodeRepulsionFor (08-06+ Dexter 7cm special case)', () => {
  it('gives Dexter Morgan the 7cm bubble repulsion', () => {
    // Cytoscape node objects expose `id()`; the helper also accepts
    // `data('id')` (jsdom-less unit shape).
    expect(nodeRepulsionFor({ id: () => DEXTER_NODE_ID })).toBe(DEXTER_REPULSION)
    expect(nodeRepulsionFor({ data: (k) => (k === 'id' ? DEXTER_NODE_ID : undefined) })).toBe(
      DEXTER_REPULSION,
    )
  })

  it('keeps the base repulsion for every other node', () => {
    expect(nodeRepulsionFor({ id: () => 'char_debra_morgan' })).toBe(833333)
  })

  it('keeps the higher repulsion for cluster parents', () => {
    expect(nodeRepulsionFor({ id: () => 'cluster:Ep #1', isParent: () => true })).toBe(1666667)
  })

  it('scales every repulsion by the overview spacing factor', () => {
    const scale = OVERVIEW_SPACING_SCALE
    expect(nodeRepulsionFor({ id: () => DEXTER_NODE_ID }, scale)).toBe(DEXTER_REPULSION * scale)
    expect(nodeRepulsionFor({ id: () => 'char_debra_morgan' }, scale)).toBe(833333 * scale)
    expect(nodeRepulsionFor({ id: () => 'cluster:Ep #1', isParent: () => true }, scale)).toBe(
      1666667 * scale,
    )
  })
})

describe('layoutOptionsFor overview spacing (08-06+)', () => {
  it('uses roomier constants in Overview mode, compact ones in Full', () => {
    type FcoSeSpacing = {
      idealEdgeLength: number
      gravity: number
      tilingPaddingVertical: number
      nodeRepulsion: (node: { id: () => string }) => number
    }
    const overview = layoutOptionsFor('fcose', false, 'overview') as FcoSeSpacing
    const full = layoutOptionsFor('fcose', false, 'full') as FcoSeSpacing

    expect(overview.idealEdgeLength).toBeGreaterThan(full.idealEdgeLength)
    expect(overview.gravity).toBeLessThan(full.gravity)
    expect(overview.tilingPaddingVertical).toBeGreaterThan(full.tilingPaddingVertical)
    // The repulsion function is mode-aware: same node repels harder in Overview.
    const probe = { id: () => 'char_debra_morgan' }
    expect(overview.nodeRepulsion(probe)).toBeGreaterThan(full.nodeRepulsion(probe))
  })

  it('accepts a fit flag (default true; false = interaction hold-view)', () => {
    expect(layoutOptionsFor('fcose', false, 'overview').fit).toBe(true)
    expect(layoutOptionsFor('fcose', false, 'overview', false).fit).toBe(false)
    expect(layoutOptionsFor('cose', false, 'full', false).fit).toBe(false)
  })
})
