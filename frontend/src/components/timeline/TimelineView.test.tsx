import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { GraphClaim, GraphNode } from '@/types/graph'
import type { EpisodeResponse } from '@/types/series'
import { TimelineView, type TimelineSelection } from './TimelineView'

const episodes: EpisodeResponse[] = [
  {
    id: 'dexter_s01e01',
    series_id: 'series_dexter',
    episode_order: 1,
    code: 'S01E01',
    title: 'Dexter',
    display_title: 'Dexter',
    is_unlocked: true,
    is_current_view: true,
    season_number: 1,
    episode_number: 1,
    visible_from_order: 1,
  },
  {
    id: 'dexter_s01e02',
    series_id: 'series_dexter',
    episode_order: 2,
    code: 'S01E02',
    title: 'Crocodile',
    display_title: 'Crocodile',
    is_unlocked: false,
    is_current_view: false,
    season_number: 1,
    episode_number: 2,
    visible_from_order: 2,
  },
]

const events: GraphNode[] = [
  {
    id: 'dexter:event:s01e02_flashback',
    type: 'Event',
    label: 'Buddy flashback',
    visible_from_order: 2,
    origin: 'canonical',
    episode_id: 'dexter_s01e02',
    image_url: null,
    image_source_url: null,
  },
  {
    id: 'dexter:event:s01e01_buddy_flashback',
    type: 'Event',
    label: 'Cops arrive',
    visible_from_order: 1,
    origin: 'canonical',
    episode_id: 'dexter_s01e01',
    image_url: null,
    image_source_url: null,
  },
  {
    id: 'dexter:location:miami_metro',
    type: 'Location',
    label: 'Miami Metro',
    visible_from_order: 1,
    origin: 'canonical',
    episode_id: 'dexter_s01e01',
    image_url: null,
    image_source_url: null,
  },
]

const claims: GraphClaim[] = [
  {
    id: 'dexter:claim:s01e01:cops_arrive',
    label: 'Dexter witnessed the scene',
    subject_id: 'dexter:event:s01e01_buddy_flashback',
    predicate: 'WITNESSED',
    object_id: 'dexter:character:dexter_morgan',
    claim_type: 'canonical',
    status: 'confirmed',
    confidence_level: 'high',
    relationship_effect: 1,
    visible_from_order: 1,
    valid_from_order: 1,
    valid_until_order: null,
    source_id: 'dexter:source:s01e01',
    evidence_ids: [],
    origin: 'canonical',
  },
]

function renderView(onSelect = vi.fn()) {
  return render(
    <TimelineView
      nodes={events}
      claims={claims}
      episodes={episodes}
      selectedId={null}
      onSelect={onSelect}
    />,
  )
}

describe('TimelineView', () => {
  it('sorts events chronologically and groups under episode headers', () => {
    renderView()
    // "S01E01" appears twice per episode (sticky group header + row badge).
    expect(screen.getAllByText('S01E01').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('S01E02').length).toBeGreaterThanOrEqual(2)
    // Only Event nodes render — the Location node is excluded.
    expect(screen.getByText('Cops arrive')).toBeTruthy()
    expect(screen.getByText('Buddy flashback')).toBeTruthy()
    expect(screen.queryByText('Miami Metro')).toBeNull()
    // Episode badge + claims count render.
    expect(screen.getByText('1 claim')).toBeTruthy()
  })

  it('row click selects the node through onSelect', () => {
    const onSelect = vi.fn()
    renderView(onSelect)
    fireEvent.click(screen.getByText('Cops arrive'))
    const selection: TimelineSelection = onSelect.mock.calls[0][0]
    expect(selection).toEqual({
      id: 'dexter:event:s01e01_buddy_flashback',
      label: 'Cops arrive',
      nodeType: 'Event',
    })
  })

  it('keyboard navigation: ArrowDown/ArrowUp/Enter', () => {
    const onSelect = vi.fn()
    renderView(onSelect)
    const container = screen.getByText('Cops arrive').closest('div')!.parentElement!
    fireEvent.keyDown(container, { key: 'ArrowDown' })
    fireEvent.keyDown(container, { key: 'Enter' })
    const selection: TimelineSelection = onSelect.mock.calls[0][0]
    expect(selection.id).toBe('dexter:event:s01e02_flashback')
  })

  it('renders the locked empty-state copy when there are no events', () => {
    render(
      <TimelineView
        nodes={events.filter((node) => node.type === 'Location')}
        claims={[]}
        episodes={episodes}
        selectedId={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('The timeline is empty')).toBeTruthy()
    expect(screen.getByText('Advance your watch progress to reveal more events.')).toBeTruthy()
  })

  describe('timeline graph filter (08-06)', () => {
    function renderFiltered(
      filteredIds: string[] = [],
      onToggleFilter = vi.fn(),
      onClearFilter = vi.fn(),
    ) {
      return render(
        <TimelineView
          nodes={events}
          claims={claims}
          episodes={episodes}
          selectedId={null}
          onSelect={vi.fn()}
          filteredIds={filteredIds}
          onToggleFilter={onToggleFilter}
          onClearFilter={onClearFilter}
        />,
      )
    }

    it('checkbox click toggles the event id through onToggleFilter', () => {
      const onToggleFilter = vi.fn()
      renderFiltered([], onToggleFilter)
      fireEvent.click(screen.getByLabelText('Filter graph by Cops arrive'))
      expect(onToggleFilter).toHaveBeenCalledWith('dexter:event:s01e01_buddy_flashback')
    })

    it('renders checked state + banner for active filter ids', () => {
      renderFiltered(['dexter:event:s01e01_buddy_flashback'])
      expect(screen.getByLabelText('Filter graph by Cops arrive')).toHaveAttribute(
        'aria-checked',
        'true',
      )
      expect(screen.getByLabelText('Filter graph by Buddy flashback')).toHaveAttribute(
        'aria-checked',
        'false',
      )
      expect(screen.getByText('Filtering the graph by 1 event')).toBeTruthy()
    })

    it('Clear button empties the filter through onClearFilter', () => {
      const onClearFilter = vi.fn()
      renderFiltered(['dexter:event:s01e01_buddy_flashback'], vi.fn(), onClearFilter)
      fireEvent.click(screen.getByText('Clear'))
      expect(onClearFilter).toHaveBeenCalled()
    })
  })
})
