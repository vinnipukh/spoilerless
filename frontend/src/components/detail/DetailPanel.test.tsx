import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DetailPanel } from './DetailPanel'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { SelectedElement } from '../graph/GraphCanvas'

const graph = graphResponseS01E01

describe('DetailPanel', () => {
  it('renders the locked no-selection placeholder with no Tabs', () => {
    render(<DetailPanel selected={null} graph={graph} />)

    expect(screen.getByText('Select a node to see details.')).toBeInTheDocument()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
  })

  it('renders all three tabs for a node with claims/evidence, including the exact evidence copy', async () => {
    const user = userEvent.setup()
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} graph={graph} />)

    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Claims' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Evidence' })).toBeInTheDocument()

    // Overview tab is the default.
    expect(await screen.findByText('Type: Character')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Claims' }))
    expect(await screen.findByText('Dexter works at Miami Metro')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Evidence' }))
    expect(await screen.findByText('Source: S01E01 script - 00:03:12')).toBeInTheDocument()
  })

  it('renders the claim-backed edge Overview tab with claim fields and its single evidence entry', async () => {
    const user = userEvent.setup()
    // edge_2: OCCURRED_IN, claim_id 'claim_1' (Dexter works at Miami Metro).
    const selected: SelectedElement = {
      kind: 'edge',
      id: 'edge_2',
      edgeType: 'OCCURRED_IN',
      source: 'char_dexter_morgan',
      target: 'loc_miami_metro',
    }
    render(<DetailPanel selected={selected} graph={graph} />)

    expect(await screen.findByRole('heading', { name: 'Dexter works at Miami Metro' })).toBeInTheDocument()
    expect(await screen.findByText('Predicate: works_at')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Evidence' }))
    expect(await screen.findByText('Source: S01E01 script - 00:03:12')).toBeInTheDocument()
  })

  it('renders the "No claims recorded" empty sub-state for a node with zero linked claims', async () => {
    const user = userEvent.setup()
    const selected: SelectedElement = {
      kind: 'node',
      id: 'char_ice_truck_killer',
      label: 'The Ice Truck Killer',
      nodeType: 'Character',
    }
    render(<DetailPanel selected={selected} graph={graph} />)

    await user.click(screen.getByRole('tab', { name: 'Claims' }))
    expect(await screen.findByText('No claims recorded for this node yet')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Evidence' }))
    expect(await screen.findByText('No evidence recorded for this claim yet')).toBeInTheDocument()
  })

  it('shows a portrait linking to image_source_url for a Character with image_url', async () => {
    // char_dexter_morgan carries a seeded image_url/image_source_url pair
    // (test/fixtures/graphResponse.ts).
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} graph={graph} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    expect(portrait).toBeInTheDocument()
    expect(portrait.tagName).toBe('IMG')

    const link = screen.getByRole('link', { name: 'Open Dexter Morgan on Fandom' })
    expect(link).toHaveAttribute('href', 'https://dexter.fandom.com/wiki/Dexter_Morgan')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows an initials fallback avatar for a Character with no image_url, with no <img>', async () => {
    // char_debra_morgan has image_url: null in the fixture.
    const selected: SelectedElement = { kind: 'node', id: 'char_debra_morgan', label: 'Debra Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} graph={graph} />)

    expect(await screen.findByRole('heading', { name: 'Debra Morgan' })).toBeInTheDocument()
    expect(screen.getByText('DM')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open .* on Fandom/ })).not.toBeInTheDocument()
  })

  it('falls back to the initials avatar when the portrait image fails to load', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} graph={graph} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    portrait.dispatchEvent(new Event('error'))

    expect(await screen.findByText('DM')).toBeInTheDocument()
    expect(screen.queryByAltText('Dexter Morgan')).not.toBeInTheDocument()
  })

  it('shows no portrait or avatar for non-Character selections', async () => {
    const selected: SelectedElement = {
      kind: 'edge',
      id: 'edge_2',
      edgeType: 'OCCURRED_IN',
      source: 'char_dexter_morgan',
      target: 'loc_miami_metro',
    }
    render(<DetailPanel selected={selected} graph={graph} />)

    expect(await screen.findByRole('heading', { name: 'Dexter works at Miami Metro' })).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
