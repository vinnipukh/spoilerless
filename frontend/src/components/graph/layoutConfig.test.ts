import { describe, expect, it } from 'vitest'
import {
  DEXTER_NODE_ID,
  DEXTER_REPULSION,
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
})
