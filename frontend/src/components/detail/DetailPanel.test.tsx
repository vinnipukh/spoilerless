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
})
