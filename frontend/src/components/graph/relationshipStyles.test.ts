import { describe, expect, it } from 'vitest'
import { edgeColorFor } from './relationshipStyles'

describe('edgeColorFor', () => {
  it('returns #A78BFA for FAMILY_OF (violet family)', () => {
    expect(edgeColorFor('FAMILY_OF')).toBe('#A78BFA')
  })

  it('returns DEFAULT_HEX for PART_OF and PRECEDES (slate family)', () => {
    expect(edgeColorFor('PART_OF')).toBe('rgba(148,163,184,0.35)')
    expect(edgeColorFor('PRECEDES')).toBe('rgba(148,163,184,0.35)')
  })

  it('returns DEFAULT_HEX for an unmapped edge type', () => {
    expect(edgeColorFor('UNRECOGNIZED_TYPE')).toBe('rgba(148,163,184,0.35)')
  })
})
