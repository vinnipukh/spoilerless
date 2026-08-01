import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CitationChip } from './CitationChip'
import { CLAIM_ACCENT_COLOR, EVIDENCE_ACCENT_COLOR } from '../detail/DetailPanel'
import { claimCitation, evidenceCitation } from '../../test/fixtures/chatFixtures'
import type { Citation } from '../../types/chat'

const sourceOnlyCitation: Citation = {
  claim_id: null,
  evidence_id: null,
  source_id: 'source_1',
  source_label: 'S01E01 script',
  source_type: 'script',
  episode_code: 'S01E01',
  locator: '00:01:00',
  excerpt: null,
  related_node_ids: [],
  related_edge_ids: [],
}

// jsdom normalizes a hex color assigned via the `style` object to its
// rgb() functional-notation equivalent when read back — this asserts the
// *value* still traces to the imported constant, not a re-typed literal.
function hexToRgb(hex: string): string {
  const value = hex.replace('#', '')
  const r = parseInt(value.slice(0, 2), 16)
  const g = parseInt(value.slice(2, 4), 16)
  const b = parseInt(value.slice(4, 6), 16)
  return `rgb(${r}, ${g}, ${b})`
}

describe('CitationChip', () => {
  it('uses CLAIM_ACCENT_COLOR for a claim citation', () => {
    const { container } = render(<CitationChip citation={claimCitation} />)
    const chip = container.firstElementChild as HTMLElement
    expect(chip.style.borderLeft).toContain(hexToRgb(CLAIM_ACCENT_COLOR))
  })

  it('uses EVIDENCE_ACCENT_COLOR for an evidence citation', () => {
    const { container } = render(<CitationChip citation={evidenceCitation} />)
    const chip = container.firstElementChild as HTMLElement
    expect(chip.style.borderLeft).toContain(hexToRgb(EVIDENCE_ACCENT_COLOR))
  })

  it('renders a muted border with no color accent for a source-only citation', () => {
    const { container } = render(<CitationChip citation={sourceOnlyCitation} />)
    const chip = container.firstElementChild as HTMLElement
    expect(chip.style.borderLeft).toBe('')
  })

  it('renders the "Show in graph" Eye action only when related IDs are non-empty', () => {
    render(<CitationChip citation={claimCitation} />)
    expect(screen.getByRole('button', { name: 'Show in graph' })).toBeInTheDocument()
  })

  it('renders zero "Show in graph" actions when related_node_ids and related_edge_ids are both empty', () => {
    render(<CitationChip citation={sourceOnlyCitation} />)
    expect(screen.queryByRole('button', { name: 'Show in graph' })).not.toBeInTheDocument()
  })

  it('renders the "{source_type} · {episode_code}" label', () => {
    render(<CitationChip citation={claimCitation} />)
    expect(screen.getByText('script · S01E01')).toBeInTheDocument()
  })

  it('invokes onOpenDetail when the chip body (not the icon) is clicked', async () => {
    const user = userEvent.setup()
    const onOpenDetail = vi.fn()
    render(<CitationChip citation={claimCitation} onOpenDetail={onOpenDetail} />)

    await user.click(screen.getByText('script · S01E01'))
    expect(onOpenDetail).toHaveBeenCalledWith(claimCitation)
  })

  it('invokes onShowInGraph when the Eye icon is clicked', async () => {
    const user = userEvent.setup()
    const onShowInGraph = vi.fn()
    render(<CitationChip citation={claimCitation} onShowInGraph={onShowInGraph} />)

    await user.click(screen.getByRole('button', { name: 'Show in graph' }))
    expect(onShowInGraph).toHaveBeenCalledWith(claimCitation)
  })
})
