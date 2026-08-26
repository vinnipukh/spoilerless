import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactElement } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DetailPanel } from './DetailPanel'
import { TooltipProvider } from '@/components/ui/tooltip'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { SelectedElement } from '../graph/GraphCanvas'

// The panel header carries a Tooltip (Export Markdown, FEAT-05) that renders
// whenever a node is selected — every selected-node render must sit inside a
// TooltipProvider or Radix throws "Tooltip must be used within
// TooltipProvider" (root cause of the 2026-08-05 DetailPanel test reds).
function renderPanel(ui: ReactElement) {
  return render(<TooltipProvider>{ui}</TooltipProvider>)
}

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

vi.mock('../../api/userContent', () => ({
  createCustomRelationship: vi.fn().mockResolvedValue({
    id: 'user-rel:test',
    source_id: 'dexter:character:dexter_morgan',
    target_id: 'dexter:character:debra_morgan',
    predicate: 'KNOWS',
    origin: 'user',
  }),
  // useNotes (Notes tab) also imports from this module — stub it so the
  // module-level mock doesn't break the Notes tab's initial load.
  getNotes: vi.fn().mockResolvedValue([]),
  createNote: vi.fn(),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
}))

import { createCustomRelationship } from '../../api/userContent'

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
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('renders the locked no-selection placeholder with no Tabs', async () => {
    renderPanel(<DetailPanel selected={null} {...defaultProps} />)

    expect(await screen.findByText('Select a node to see details.')).toBeInTheDocument()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
  })

  it('renders all three tabs for a node with claims/evidence, including the exact evidence copy', async () => {
    const user = userEvent.setup()
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

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
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

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
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    await user.click(await screen.findByRole('tab', { name: 'Claims' }))
    expect(await screen.findByText('No claims recorded for this node yet')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Evidence' }))
    expect(await screen.findByText('No evidence recorded for this claim yet')).toBeInTheDocument()
  })

  it('shows a portrait linking to image_source_url for a Character with image_url', async () => {
    // char_dexter_morgan carries a seeded image_url/image_source_url pair
    // (test/fixtures/graphResponse.ts).
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    expect(portrait).toBeInTheDocument()
    expect(portrait.tagName).toBe('IMG')

    // The source link's accessible label is the generic "Image source" —
    // never the URL, never a filename (D-14).
    const link = screen.getByRole('link', { name: 'Image source' })
    expect(link).toHaveAttribute('href', 'https://dexter.fandom.com/wiki/Dexter_Morgan')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.queryByText(/dexter\.fandom\.com|wikia\.nocookie/)).not.toBeInTheDocument()
  })

  it('prefixes a relative /api/static image_url with VITE_API_BASE_URL (quick-260813-gao)', async () => {
    const graphWithRelativeImage = {
      ...graphResponseS01E01,
      nodes: graphResponseS01E01.nodes.map((n) =>
        n.id === 'char_dexter_morgan'
          ? { ...n, image_url: '/api/static/characters/dexter_morgan.webp' }
          : n,
      ),
    }
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.spoilerless.net')
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} graph={graphWithRelativeImage} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    expect(portrait).toHaveAttribute(
      'src',
      'https://api.spoilerless.net/api/static/characters/dexter_morgan.webp',
    )
  })

  it('shows an initials fallback avatar for a Character with no image_url, with no <img>', async () => {
    // char_debra_morgan has image_url: null in the fixture.
    const selected: SelectedElement = { kind: 'node', id: 'char_debra_morgan', label: 'Debra Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Debra Morgan' })).toBeInTheDocument()
    expect(screen.getByText('DM')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open .* on Fandom/ })).not.toBeInTheDocument()
  })

  it('falls back to the initials avatar when the portrait image fails to load', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    portrait.dispatchEvent(new Event('error'))

    expect(await screen.findByText('DM')).toBeInTheDocument()
    expect(screen.queryByAltText('Dexter Morgan')).not.toBeInTheDocument()
  })

  it('renders the identical initials placeholder for null and failed images (D-14)', async () => {
    // Missing image: image_url null -> initials placeholder.
    const nullSelected: SelectedElement = { kind: 'node', id: 'char_debra_morgan', label: 'Debra Morgan', nodeType: 'Character' }
    const { unmount } = renderPanel(<DetailPanel selected={nullSelected} {...defaultProps} />)
    const nullPlaceholder = await screen.findByTestId('character-avatar')
    expect(nullPlaceholder).toBeInTheDocument()
    const nullDom = nullPlaceholder.outerHTML
    unmount()

    // Failed image: same node portrait errors out -> must render the SAME
    // placeholder DOM (identical testid + classes), no distinct error UI,
    // no retry affordance, no presence inference.
    const failSelected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={failSelected} {...defaultProps} />)
    const portrait = await screen.findByAltText('Dexter Morgan')
    portrait.dispatchEvent(new Event('error'))

    const failedPlaceholder = await screen.findByTestId('character-avatar')
    expect(failedPlaceholder.outerHTML).toBe(nullDom)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByText(/failed|error|retry|try again/i)).not.toBeInTheDocument()
  })

  it('uses the safe visible label as alt text, never a filename or URL (D-14)', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    const portrait = await screen.findByAltText('Dexter Morgan')
    const alt = portrait.getAttribute('alt')
    expect(alt).toBe('Dexter Morgan')
    expect(alt).not.toMatch(/https?:\/\//)
    expect(alt).not.toMatch(/\.(png|jpe?g|webp|gif|svg)/i)
    // No filename or URL rendered as user-visible text anywhere.
    expect(screen.queryByText(/wikia\.nocookie\.net|dexter\.fandom\.com|\.png|\.jpe?g/i)).not.toBeInTheDocument()
  })

  it('never renders the image source link for a node hidden at the current boundary (D-14 defensive guard)', async () => {
    // The backend nulls image_source_url above the boundary; this proves the
    // frontend ALSO guards against a non-null value defensively — a regression
    // must never surface a URL as text or as a link.
    const graphWithHiddenImage = {
      ...graphResponseS01E01,
      nodes: graphResponseS01E01.nodes.map((n) =>
        n.id === 'char_dexter_morgan'
          ? { ...n, visible_from_order: 2, image_url: null, image_source_url: 'https://dexter.fandom.com/wiki/Dexter_Morgan' }
          : n,
      ),
    }
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    // defaultProps visibleUntilOrder is 1; the node is visible_from_order 2.
    renderPanel(<DetailPanel selected={selected} {...defaultProps} graph={graphWithHiddenImage} />)

    expect(await screen.findByTestId('character-avatar')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Image source' })).not.toBeInTheDocument()
    expect(screen.queryByText(/dexter\.fandom\.com/)).not.toBeInTheDocument()
  })

  it('renders the image source link only when the boundary is known (D-14 fail closed)', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    // An unknown/null boundary must fail closed — no source link, even though
    // the backend would have returned a valid URL for this visible node.
    renderPanel(<DetailPanel selected={selected} {...defaultProps} visibleUntilOrder={null} />)

    expect(await screen.findByAltText('Dexter Morgan')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Image source' })).not.toBeInTheDocument()
  })

  it('shows no portrait or avatar for non-Character selections', async () => {
    const selected: SelectedElement = {
      kind: 'edge',
      id: 'edge_2',
      edgeType: 'OCCURRED_IN',
      source: 'char_dexter_morgan',
      target: 'loc_miami_metro',
    }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Dexter works at Miami Metro' })).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('shows the Notes tab when a Character node is selected', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

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
    renderPanel(<DetailPanel selected={selected} {...defaultProps} graph={graphWithUserNode} />)

    expect(await screen.findByText('User')).toBeInTheDocument()
    // The badge should have dashed border styling
    const badge = screen.getByText('User').closest('span')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('border-dashed')
  })

  it('shows canonical origin text (not badge) for a canonical node', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

    // 12-08: claims/evidence resolve synchronously now (no setTimeout gate),
    // so the Overview origin <dd> is no longer the only "canonical" text on
    // screen — claim cards in the Claims tab render theirs too. Scope to the
    // Origin row via its accessible dt label (getByRole('definition') pairs
    // with the preceding term inside the Overview grid).
    const originTerm = screen.getByText('Origin')
    expect(originTerm.nextElementSibling).not.toBeNull()
    expect(originTerm.nextElementSibling).toHaveTextContent('canonical')
  })

  describe('collapsible left inspector Sheet (06-09/06-12)', () => {
    it('renders no Sheet content at all when open is false', () => {
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      renderPanel(<DetailPanel selected={selected} {...defaultProps} open={false} />)

      expect(screen.queryByRole('heading', { name: 'Dexter Morgan' })).not.toBeInTheDocument()
      expect(screen.queryByText('Select a node to see details.')).not.toBeInTheDocument()
      expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    })

    it('renders the inspector content (never the chat surface) when open', async () => {
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

      expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
      // The chat surface lives in its own right-side sheet (ChatSheet) — this
      // panel is inspector-only, so no chat content can appear here.
      expect(screen.queryByRole('heading', { name: 'Ask about Dexter' })).not.toBeInTheDocument()
    })

    // --- 10-05 (D-20/D-42): mobile Inspector sheet behavior ---

    it('toggles the mobile sheet between half and full height via the drag handle', async () => {
      const user = userEvent.setup()
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      renderPanel(<DetailPanel selected={selected} {...defaultProps} />)

      const handle = screen.getByRole('button', { name: 'Toggle Inspector height' })
      expect(handle).toHaveAttribute('aria-expanded', 'false')

      await user.click(handle)
      expect(screen.getByRole('button', { name: 'Toggle Inspector height' })).toHaveAttribute('aria-expanded', 'true')

      await user.click(handle)
      expect(screen.getByRole('button', { name: 'Toggle Inspector height' })).toHaveAttribute('aria-expanded', 'false')
    })

    it('closes via the explicit Close Inspector button and via Escape', async () => {
      const user = userEvent.setup()
      const onDeselect = vi.fn()
      const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
      const { rerender } = renderPanel(
        <DetailPanel selected={selected} {...defaultProps} onDeselect={onDeselect} />,
      )

      // Explicit close button (accessible name per UI-SPEC).
      await user.click(screen.getByRole('button', { name: 'Close Inspector' }))
      expect(onDeselect).toHaveBeenCalledTimes(1)

      // Escape funnels through the same onDeselect path (D-42).
      rerender(<DetailPanel selected={selected} {...defaultProps} onDeselect={onDeselect} />)
      await user.keyboard('{Escape}')
      expect(onDeselect).toHaveBeenCalledTimes(2)
    })

  it('refreshes the graph in place after creating a relationship', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    const onRefreshGraph = vi.fn()
    const user = userEvent.setup()
    renderPanel(
      <DetailPanel
        selected={selected}
        {...defaultProps}
        episodes={[{ id: 'dexter_s01e01', code: 'S01E01', title: 'Dexter', episode_order: 1 }]}
        onRefreshGraph={onRefreshGraph}
      />,
    )

    await user.click(await screen.findByRole('button', { name: 'Create relationship' }))
    await user.selectOptions(await screen.findByLabelText('To'), 'char_debra_morgan')
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createCustomRelationship).toHaveBeenCalledWith(
      'series:dexter',
      expect.objectContaining({
        source_id: 'char_dexter_morgan',
        target_id: 'char_debra_morgan',
        predicate: 'KNOWS',
      }),
    )
    // The success path must reload the graph data in place so the new edge
    // appears without a manual reload (and without a destructive remount).
    expect(onRefreshGraph).toHaveBeenCalledTimes(1)
  })
  })
})

describe('DetailPanel readOnly (visitor / misafir read-only mode)', () => {
  it('hides the Create Relationship action', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} readOnly />)

    await screen.findByRole('heading', { name: 'Dexter Morgan' })
    expect(screen.queryByRole('button', { name: 'Create relationship' })).not.toBeInTheDocument()
  })

  it('hides the Notes and History tabs entirely (auth-gated surfaces)', async () => {
    const selected: SelectedElement = { kind: 'node', id: 'char_dexter_morgan', label: 'Dexter Morgan', nodeType: 'Character' }
    renderPanel(<DetailPanel selected={selected} {...defaultProps} readOnly />)

    await screen.findByRole('heading', { name: 'Dexter Morgan' })
    expect(screen.queryByRole('tab', { name: 'Notes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'History' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add note' })).not.toBeInTheDocument()
    // Browsable tabs remain for guests
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Backlinks' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Claims' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Evidence' })).toBeInTheDocument()
  })
})
