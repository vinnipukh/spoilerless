import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DetailPanel } from './DetailPanel'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { SelectedElement } from '../graph/GraphCanvas'

// ChatPanel (mounted only when mode === 'chat') calls the real chat API
// client on mount via useChatSessions — stub it so mode-toggle tests that
// switch into Chat mode don't hit a real/undefined `fetch`.
vi.mock('../../api/chat', () => ({
  listChatSessions: vi.fn().mockResolvedValue([]),
  getChatSession: vi.fn(),
  createChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  streamMessage: vi.fn(),
}))

const graph = graphResponseS01E01
const defaultProps = {
  graph,
  seriesId: 'series:dexter' as const,
  visibleUntilOrder: 1,
  episodes: [],
  open: true,
  onDeselect: vi.fn(),
}

describe('DetailPanel', () => {
  it('renders the locked no-selection placeholder with no Tabs', async () => {
    render(<DetailPanel selected={null} {...defaultProps} />)

    expect(await screen.findByText('Select a node to see details.')).toBeInTheDocument()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
  })

  it('renders all three tabs for a node with claims/evidence, including the exact evidence copy', async () => {
    const user = userEvent.setup()
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Claims' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Evidence' })).toBeInTheDocument()

    // Overview tab is the default.
    expect(await screen.findByText('Node Type')).toBeInTheDocument()
    expect(await screen.findByText('Character')).toBeInTheDocument()

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
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Dexter works at Miami Metro' })).toBeInTheDocument()
    expect(await screen.findByText('Relationship')).toBeInTheDocument()
    expect(await screen.findByText('works_at')).toBeInTheDocument()

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
    render(<DetailPanel selected={selected} {...defaultProps} />)

    await user.click(await screen.findByRole('tab', { name: 'Claims' }))
    expect(await screen.findByText('No claims recorded for this node yet')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Evidence' }))
    expect(await screen.findByText('No evidence recorded for this claim yet')).toBeInTheDocument()
  })

  it('shows a portrait linking to image_source_url for a Character with image_url', async () => {
    // char_dexter_morgan carries a seeded image_url/image_source_url pair
    // (test/fixtures/graphResponse.ts).
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} />)

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
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Debra Morgan' })).toBeInTheDocument()
    expect(screen.getByText('DM')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open .* on Fandom/ })).not.toBeInTheDocument()
  })

  it('falls back to the initials avatar when the portrait image fails to load', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} />)

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
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Dexter works at Miami Metro' })).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('shows the Notes tab when a Character node is selected', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('tab', { name: 'Notes' })).toBeInTheDocument()
  })

  it('shows the User origin badge for a user-origin node', async () => {
    const graphWithUserNode = {
      ...graphResponseS01E01,
      nodes: graphResponseS01E01.nodes.map((n) =>
        n.id === 'char_ice_truck_killer' ? { ...n, origin: 'user' as const } : n,
      ),
    }
    const selected: SelectedElement = { kind: 'node', id: 'char_ice_truck_killer', label: 'The Ice Truck Killer', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} graph={graphWithUserNode} />)

    expect(await screen.findByText('User')).toBeInTheDocument()
    // The badge should have dashed border styling
    const badge = screen.getByText('User').closest('span')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('border-dashed')
  })

  it('shows canonical origin text (not badge) for a canonical node', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    render(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByText('canonical')).toBeInTheDocument()
  })

  describe('collapsible left inspector Sheet (06-09/06-12)', () => {
    it('renders no Sheet content at all when open is false', () => {
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      render(<DetailPanel selected={selected} {...defaultProps} open={false} />)

      expect(screen.queryByRole('heading', { name: 'Dexter Morgan' })).not.toBeInTheDocument()
      expect(screen.queryByText('Select a node to see details.')).not.toBeInTheDocument()
      expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    })

    it('renders the inspector content (never the chat surface) when open', async () => {
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      render(<DetailPanel selected={selected} {...defaultProps} />)

      expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
      // The chat surface lives in its own right-side sheet (ChatSheet) — this
      // panel is inspector-only, so no chat content can appear here.
      expect(screen.queryByRole('heading', { name: 'Ask about Dexter' })).not.toBeInTheDocument()
    })
  })
})
