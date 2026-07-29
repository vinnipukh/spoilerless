import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmAdvanceModal } from './ConfirmAdvanceModal'

describe('ConfirmAdvanceModal', () => {
  it('renders the locked forward-direction copy when direction is "forward"', () => {
    render(
      <ConfirmAdvanceModal
        open
        direction="forward"
        episodeCode="S01E02"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByText('Unlock S01E02?')).toBeInTheDocument()
    expect(
      screen.getByText(
        "You're about to see new characters, events, and relationships from S01E02. This can't be undone. Continue?",
      ),
    ).toBeInTheDocument()
  })

  it('renders the backward-direction copy when direction is "backward"', () => {
    render(
      <ConfirmAdvanceModal
        open
        direction="backward"
        episodeCode="S01E01"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByText('Rewatch S01E01?')).toBeInTheDocument()
    expect(
      screen.getByText("You're about to move your watch progress back to S01E01. Continue?"),
    ).toBeInTheDocument()
  })

  it('calls onCancel when Cancel is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <ConfirmAdvanceModal
        open
        direction="forward"
        episodeCode="S01E02"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onConfirm when "Yes, unlock episode" is clicked', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <ConfirmAdvanceModal
        open
        direction="forward"
        episodeCode="S01E02"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
