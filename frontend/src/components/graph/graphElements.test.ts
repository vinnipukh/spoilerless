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

  it('flags the Episode-1 cluster with areaScale 3 (3x area expansion)', () => {
    const elements = graphToElements(graphResponseS01E01)
    const ep1 = elements.find((el) => el.data.id === 'cluster:Ep #1')

    expect(ep1?.data.isCluster).toBe(true)
    expect(ep1?.data.areaScale).toBe(3)
  })

  describe('overview mode (08-06+ presentation declutter)', () => {
    const overviewIds = () =>
      new Set(graphToElements(graphResponseS01E01, 'overview').map((el) => el.data.id))

    it('renders only the curated tier-1 + structural nodes', () => {
      const present = overviewIds()
      for (const id of ['char_dexter_morgan', 'char_debra_morgan', 'char_angel_batista', 'loc_miami_metro', 'dexter_s01e01', 'series_dexter']) {
        expect(present.has(id)).toBe(true)
      }
    })

    it('hides tier-3 nodes and edges touching them', () => {
      const present = overviewIds()
      for (const id of ['char_rita_bennett', 'char_james_doakes', 'char_ice_truck_killer', 'loc_dexters_apartment', 'event_first_kill']) {
        expect(present.has(id)).toBe(false)
      }
      // edge_6 (dexter -> event_first_kill) and edge_2's target... edge_2 is
      // dexter->miami_metro (both kept). The dropped event kills its edge.
      expect(present.has('edge_6')).toBe(false)
    })

    it('keeps user-origin edges between kept nodes', () => {
      expect(overviewIds().has('user-rel:test-1')).toBe(true)
    })

    it('keeps full mode behavior with mode="full" (default)', () => {
      const full = new Set(graphToElements(graphResponseS01E01, 'full').map((el) => el.data.id))
      const connected = new Set<string>()
      for (const e of graphResponseS01E01.edges) {
        connected.add(e.source)
        connected.add(e.target)
      }
      expect(
        graphResponseS01E01.nodes
          .filter((n) => connected.has(n.id))
          .every((n) => full.has(n.id)),
      ).toBe(true)
    })
  })

  describe('isolated-node pruning (08-06)', () => {
    const ids = () =>
      new Set(graphToElements(graphResponseS01E01).map((el) => el.data.id))

    it('drops nodes with zero edges', () => {
      const present = ids()
      // Degree 0 in the fixture: james_doakes, rita_bennett,
      // ice_truck_killer, loc_dexters_apartment
      expect(present.has('char_james_doakes')).toBe(false)
      expect(present.has('char_rita_bennett')).toBe(false)
      expect(present.has('char_ice_truck_killer')).toBe(false)
      expect(present.has('loc_dexters_apartment')).toBe(false)
    })

    it('keeps nodes with at least one edge', () => {
      const present = ids()
      expect(present.has('char_dexter_morgan')).toBe(true)
      expect(present.has('char_debra_morgan')).toBe(true)
      expect(present.has('loc_miami_metro')).toBe(true)
      expect(present.has('event_first_kill')).toBe(true)
    })

    it('drops a cluster whose members are all isolated', () => {
      const elements = graphToElements({
        series: { id: 's', title: 'S', slug: 's' },
        nodes: [
          {
            id: 'a', type: 'Character', label: 'A', visible_from_order: 1,
            origin: 'canonical', episode_id: null, image_url: null,
            image_source_url: null,
          },
          {
            id: 'b', type: 'Character', label: 'B', visible_from_order: 1,
            origin: 'canonical', episode_id: null, image_url: null,
            image_source_url: null,
          },
          {
            id: 'loner', type: 'Character', label: 'Loner', visible_from_order: 2,
            origin: 'canonical', episode_id: null, image_url: null,
            image_source_url: null,
          },
        ],
        edges: [
          {
            id: 'e1', source: 'a', target: 'b', type: 'KNOWS',
            visible_from_order: 1, origin: 'canonical', claim_id: null,
          },
        ],
        claims: [],
        visible_until_order: 1,
        sources: [],
        evidence: [],
      })

      const present = new Set(elements.map((el) => el.data.id))
      expect(present.has('cluster:Ep #1')).toBe(true)
      expect(present.has('cluster:Ep #2')).toBe(false)
      expect(present.has('loner')).toBe(false)
      expect(present.has('a')).toBe(true)
      expect(present.has('b')).toBe(true)
    })
  })
})
