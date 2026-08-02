import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatLauncher } from './ChatLauncher'

describe('ChatLauncher', () => {
  it('shows aria-label "Open chat" when inactive and calls onClick', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<ChatLauncher active={false} onClick={onClick} />)

    const button = screen.getByRole('button', { name: 'Open chat' })
    await user.click(button)

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('shows aria-label "Close chat" when active', () => {
    render(<ChatLauncher active onClick={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Close chat' })).toBeInTheDocument()
  })
})
