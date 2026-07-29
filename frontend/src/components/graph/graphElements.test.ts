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
})
