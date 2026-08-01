import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChangeSetCard } from './ChangeSetCard'
import { confirmChangeSet, rejectChangeSet } from '../../api/changeSet'
import { ApiError } from '../../api/client'
import {
  createNodeOnlyChangeSet,
  createUpdateOnlyChangeSet,
  proposedChangeSetApplied,
  proposedChangeSetAwaitingConfirmation,
  proposedChangeSetFailed,
  proposedChangeSetRejected,
  protectedOverrideChangeSet,
  singleDeleteChangeSet,
  threeOperationChangeSetWithDelete,
  twoDeleteChangeSet,
  twoOperationChangeSet,
} from '../../test/fixtures/chatFixtures'
import type { ChangeSet } from '../../types/changeSet'

// T-06-05 (threat register): the card's own Confirm/Reject handlers are the
// ONLY UI path that calls confirmChangeSet/rejectChangeSet — these tests mock
// the api module and assert the card wires exclusively through it.
vi.mock('../../api/changeSet', () => ({
  confirmChangeSet: vi.fn(),
  rejectChangeSet: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ChangeSetCard', () => {
  it('renders "Proposed change" for exactly one operation and "Proposed changes (N)" for two or more', () => {
    // The singular/plural boundary is N=1 vs N>=2 — asserted here at exactly
    // N=1 (singleDeleteChangeSet) vs N=2 (twoOperationChangeSet), plus an
    // N=1 create_node-only set and N=3 as further confirmation the boundary
    // does not sit anywhere else.
    const { rerender } = render(<ChangeSetCard changeSet={singleDeleteChangeSet} seriesId="series_dexter" />)
    expect(screen.getByText('Proposed change')).toBeInTheDocument()
    expect(screen.queryByText(/Proposed changes/)).not.toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={createNodeOnlyChangeSet} seriesId="series_dexter" />)
    expect(screen.getByText('Proposed change')).toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={twoOperationChangeSet} seriesId="series_dexter" />)
    expect(screen.getByText('Proposed changes (2)')).toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={threeOperationChangeSetWithDelete} seriesId="series_dexter" />)
    expect(screen.getByText('Proposed changes (3)')).toBeInTheDocument()
  })

  it('renders Before/After rows only for update-type operations (create_node has no Before row)', () => {
    const { rerender } = render(
      <ChangeSetCard changeSet={createUpdateOnlyChangeSet} seriesId="series_dexter" />,
    )
    // update_node changed fields: Label + Description → exactly two rows.
    expect(screen.getAllByText('Before:')).toHaveLength(2)
    expect(screen.getAllByText('After:')).toHaveLength(2)
    expect(screen.getByText('Debra Morgan (detective)')).toBeInTheDocument()
    expect(screen.getByText('Now a detective.')).toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={createNodeOnlyChangeSet} seriesId="series_dexter" />)
    expect(screen.queryAllByText('Before:')).toHaveLength(0)
    expect(screen.queryAllByText('After:')).toHaveLength(0)
  })

  it('renders the destructive banner with correct pluralization only when a delete operation is present', () => {
    const { rerender } = render(<ChangeSetCard changeSet={singleDeleteChangeSet} seriesId="series_dexter" />)
    expect(screen.getByText('This will permanently delete 1 graph element.')).toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={twoDeleteChangeSet} seriesId="series_dexter" />)
    expect(screen.getByText('This will permanently delete 2 graph elements.')).toBeInTheDocument()

    // A delete among other operations still renders it (count = deletes only).
    rerender(<ChangeSetCard changeSet={threeOperationChangeSetWithDelete} seriesId="series_dexter" />)
    expect(screen.getByText('This will permanently delete 1 graph element.')).toBeInTheDocument()

    // Create/update-only sets never render it, regardless of operation count.
    rerender(<ChangeSetCard changeSet={createUpdateOnlyChangeSet} seriesId="series_dexter" />)
    expect(screen.queryByText(/permanently delete/)).not.toBeInTheDocument()
    rerender(<ChangeSetCard changeSet={createNodeOnlyChangeSet} seriesId="series_dexter" />)
    expect(screen.queryByText(/permanently delete/)).not.toBeInTheDocument()
  })

  it('keeps the Confirm label "Confirm changes" identical in both styles but re-skins to --destructive when any delete op is present', () => {
    const { rerender } = render(<ChangeSetCard changeSet={createUpdateOnlyChangeSet} seriesId="series_dexter" />)
    const primaryConfirm = screen.getByRole('button', { name: 'Confirm changes' })
    expect(primaryConfirm).toHaveTextContent('Confirm changes')
    expect(primaryConfirm.className).not.toContain('bg-destructive')

    rerender(<ChangeSetCard changeSet={threeOperationChangeSetWithDelete} seriesId="series_dexter" />)
    const destructiveConfirm = screen.getByRole('button', { name: 'Confirm changes' })
    expect(destructiveConfirm).toHaveTextContent('Confirm changes')
    expect(destructiveConfirm.className).toContain('bg-destructive')
  })

  it('calls confirmChangeSet on Confirm and swaps the controls for the Applied badge on success', async () => {
    vi.mocked(confirmChangeSet).mockResolvedValue(proposedChangeSetApplied)
    const onApplied = vi.fn()
    const user = userEvent.setup()
    render(
      <ChangeSetCard
        changeSet={proposedChangeSetAwaitingConfirmation}
        seriesId="series_dexter"
        onApplied={onApplied}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Confirm changes' }))

    expect(confirmChangeSet).toHaveBeenCalledTimes(1)
    expect(confirmChangeSet).toHaveBeenCalledWith('series_dexter', 'change_set_awaiting_confirmation')
    expect(await screen.findByText('Applied')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()
    expect(onApplied).toHaveBeenCalledWith(proposedChangeSetApplied)
  })

  it('calls rejectChangeSet on Reject and swaps the controls for the Rejected badge', async () => {
    vi.mocked(rejectChangeSet).mockResolvedValue(proposedChangeSetRejected)
    const user = userEvent.setup()
    render(<ChangeSetCard changeSet={proposedChangeSetAwaitingConfirmation} seriesId="series_dexter" />)

    await user.click(screen.getByRole('button', { name: 'Reject changes' }))

    expect(rejectChangeSet).toHaveBeenCalledTimes(1)
    expect(rejectChangeSet).toHaveBeenCalledWith('series_dexter', 'change_set_awaiting_confirmation')
    expect(await screen.findByText('Rejected')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()
  })

  it('renders the stale "no longer valid... ask again" banner instead of the controls when confirm returns changeset_stale', async () => {
    vi.mocked(confirmChangeSet).mockRejectedValue(
      new ApiError({ code: 'changeset_stale', message: 'Watch progress changed.' }),
    )
    const user = userEvent.setup()
    render(<ChangeSetCard changeSet={proposedChangeSetAwaitingConfirmation} seriesId="series_dexter" />)

    await user.click(screen.getByRole('button', { name: 'Confirm changes' }))

    expect(
      await screen.findByText(/no longer valid because your watch progress changed/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()
  })

  it('renders terminal Applied/Rejected/Failed cards as immutable records with zero Confirm/Reject controls', () => {
    const { rerender } = render(<ChangeSetCard changeSet={proposedChangeSetApplied} seriesId="series_dexter" />)
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={proposedChangeSetRejected} seriesId="series_dexter" />)
    expect(screen.getByText('Rejected')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()

    rerender(<ChangeSetCard changeSet={proposedChangeSetFailed} seriesId="series_dexter" />)
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm changes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject changes' })).not.toBeInTheDocument()
  })

  it('lists affected graph elements using the citation-chip visual style', () => {
    render(<ChangeSetCard changeSet={twoOperationChangeSet} seriesId="series_dexter" />)
    expect(screen.getByRole('button', { name: 'Character · char_dexter_morgan' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Node · char_debra_morgan' })).toBeInTheDocument()
  })

  it('renders the Protected badge (Lock, --destructive accent line) with "Propose a note instead" for a canonical-edit refusal, claiming no canonical modification', () => {
    render(<ChangeSetCard changeSet={protectedOverrideChangeSet} seriesId="series_dexter" />)

    const badge = screen.getByText('Protected')
    expect(badge).toBeInTheDocument()
    // --destructive accent line, not a full destructive fill (informational).
    expect(badge.className).toContain('border-l-2')
    expect(badge.className).toContain('border-destructive')
    expect(screen.getByText('Propose a note instead')).toBeInTheDocument()

    // The copy never claims the canonical record was changed (T-06-12): no
    // "updated"/"changed"/"modified" anywhere in the rendered card.
    expect(screen.queryByText(/updated|changed|modified/i)).not.toBeInTheDocument()
  })

  it('wraps (never truncates) an operation summary line with a very long entity label', () => {
    const longLabelChangeSet: ChangeSet = {
      ...createNodeOnlyChangeSet,
      operations: [
        {
          operation_type: 'create_node',
          node_type: 'Location',
          label: 'A'.repeat(400),
          episode_id: 'dexter_s01e01',
        },
      ],
    }
    render(<ChangeSetCard changeSet={longLabelChangeSet} seriesId="series_dexter" />)

    const line = screen.getByText(`Create Location: ${'A'.repeat(400)}`)
    expect(line.className).toContain('whitespace-pre-wrap')
    expect(line.className).toContain('break-words')
  })
})
