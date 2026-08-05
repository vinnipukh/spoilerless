import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NodeSearch, type NodeSearchSelection } from './NodeSearch'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { NoteResponse } from '../../types/userContent'

function note(overrides: Partial<NoteResponse> = {}): NoteResponse {
  return {
    id: 'note_1',
    series_id: 'series_dexter',
    target_type: 'Character',
    target_id: 'char_dexter_morgan',
    content: 'Dexter keeps a meticulous ritual before every kill.',
    origin: 'user',
    visible_from_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const notes: NoteResponse[] = [note()]

function renderSearch(onSelect: (selection: NodeSearchSelection) => void = vi.fn()) {
  return render(<NodeSearch graph={graphResponseS01E01} notes={notes} onSelect={onSelect} />)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('NodeSearch (FEAT-01 nodes + FEAT-07 notes & claims)', () => {
  it('matches node labels by substring and shows node rows', async () => {
    const user = userEvent.setup()
    renderSearch()

    await user.type(screen.getByRole('textbox'), 'doakes')

    expect(screen.getByRole('button', { name: /James Doakes/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Dexter Morgan/ })).not.toBeInTheDocument()
  })

  it('groups claims and notes results under sticky headers in Notes & Claims mode', async () => {
    const user = userEvent.setup()
    renderSearch()

    await user.click(screen.getByRole('radio', { name: 'Notes & Claims' }))
    const input = screen.getByRole('textbox')

    // Claim rows grouped under the "Claims" header.
    await user.type(input, 'works')
    expect(screen.getByText('Claims')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /works at Miami Metro/ })).toBeInTheDocument()

    // Note rows grouped under the "Notes" header.
    await user.clear(input)
    await user.type(input, 'ritual')
    expect(screen.getByText('Notes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /meticulous ritual/ })).toBeInTheDocument()
    expect(screen.queryByText('Claims')).not.toBeInTheDocument()
  })

  it('selects the active row with Enter and calls onSelect with the node id', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderSearch(onSelect)

    await user.type(screen.getByRole('textbox'), 'doakes')
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith({
      id: 'char_james_doakes',
      label: 'James Doakes',
      nodeType: 'Character',
    })
  })

  it('selects a row on click through the same onSelect path', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderSearch(onSelect)

    await user.type(screen.getByRole('textbox'), 'doakes')
    await user.click(screen.getByRole('button', { name: /James Doakes/ }))

    expect(onSelect).toHaveBeenCalledWith({
      id: 'char_james_doakes',
      label: 'James Doakes',
      nodeType: 'Character',
    })
  })

  it('selecting a claim row routes to the claim subject node', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderSearch(onSelect)

    await user.click(screen.getByRole('radio', { name: 'Notes & Claims' }))
    await user.type(screen.getByRole('textbox'), 'works at miami')
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith({
      id: 'char_dexter_morgan',
      label: 'Dexter Morgan',
      nodeType: 'Character',
    })
  })

  it('renders the locked empty-state copy verbatim when nothing matches', async () => {
    const user = userEvent.setup()
    renderSearch()

    await user.type(screen.getByRole('textbox'), 'zzzz')

    expect(screen.getByText('No nodes match “zzzz”')).toBeInTheDocument()
    expect(screen.getByText('Try a different name, or search Notes & Claims.')).toBeInTheDocument()
  })

  it('closes the results dropdown on Escape', async () => {
    const user = userEvent.setup()
    renderSearch()

    const input = screen.getByRole('textbox')
    await user.type(input, 'doakes')
    expect(screen.getByRole('button', { name: /James Doakes/ })).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('button', { name: /James Doakes/ })).not.toBeInTheDocument()
  })

  it('never issues fetch calls — search is payload-local', async () => {
    const user = userEvent.setup()
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    renderSearch()

    await user.type(screen.getByRole('textbox'), 'doakes')
    await user.keyboard('{Enter}')
    await user.click(screen.getByRole('radio', { name: 'Notes & Claims' }))
    await user.type(screen.getByRole('textbox'), 'ritual')

    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
