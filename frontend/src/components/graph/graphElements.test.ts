import { describe, expect, it } from 'vitest'
import { graphToElements } from './graphElements'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'

describe('graphToElements', () => {
  it('sets imageUrl for a Character node that has image_url', () => {
    const elements = graphToElements(graphResponseS01E01)
    const dexter = elements.find((el) => el.data.id === 'char_dexter_morgan')

    expect(dexter?.data.imageUrl).toBe(
      'https://static.wikia.nocookie.net/dexter/images/example/dexter_morgan.jpg',
    )
  })

  it('omits imageUrl entirely for a Character node with no image_url', () => {
    const elements = graphToElements(graphResponseS01E01)
    const debra = elements.find((el) => el.data.id === 'char_debra_morgan')

    expect(debra?.data).not.toHaveProperty('imageUrl')
  })

  it('never sets imageUrl for non-Character node types', () => {
    const elements = graphToElements(graphResponseS01E01)
    const nonCharacter = elements.filter(
      (el) => el.data.nodeType && el.data.nodeType !== 'Character',
    )

    expect(nonCharacter.every((el) => !('imageUrl' in el.data))).toBe(true)
  })

  describe('simple flag (08-05 Obsidian-style declutter)', () => {
    const find = (id: string) =>
      graphToElements(graphResponseS01E01).find((el) => el.data.id === id)

    it('marks pictureless nodes with < 3 edges as simple', () => {
      // char_angel_batista: no portrait, degree 1 → simple dot
      expect(find('char_angel_batista')?.data.simple).toBe(true)
      // char_ice_truck_killer: no portrait, degree 0 → simple dot
      expect(find('char_ice_truck_killer')?.data.simple).toBe(true)
      // series_dexter / dexter_s01e01: degree 1 → simple dot
      expect(find('series_dexter')?.data.simple).toBe(true)
    })

    it('does NOT mark a pictureless node with exactly 3 edges as simple', () => {
      // char_debra_morgan: no portrait, degree 3 (edge_4 + edge_5 +
      // user-rel:test-1) → stays a full-size node
      expect(find('char_debra_morgan')?.data).not.toHaveProperty('simple')
    })

    it('never marks a node with a portrait as simple', () => {
      // char_dexter_morgan: has imageUrl (degree 5) → portrait node
      expect(find('char_dexter_morgan')?.data).not.toHaveProperty('simple')
    })
  })
})
