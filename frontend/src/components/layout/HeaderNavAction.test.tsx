import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HeaderNavAction } from './HeaderNavAction'

function TestIcon() {
  return <svg data-testid="nav-icon" aria-hidden="true" />
}

// Base size/typography/geometry classes every HeaderNavAction instance must
// carry — the shared visual contract between Chat and Settings. Asserted as
// individual substrings (not one full className string) so the tests survive
// reordering of Tailwind utilities.
const BASE_CONTRACT_CLASSES = [
  'h-11', // identical height (44px touch target)
  'min-w-11',
  'rounded-md', // identical radius
  'px-2.5', // identical horizontal padding
  'gap-1.5', // identical icon-to-label gap
  'text-sm', // identical typography
  'font-medium',
]

describe('HeaderNavAction', () => {
  it('renders icon, label, and accessible name; click fires onClick', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <HeaderNavAction icon={<TestIcon />} label="Chat" ariaLabel="Open chat" active={false} onClick={onClick} />
    )

    const button = screen.getByRole('button', { name: 'Open chat' })
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByTestId('nav-icon')).toBeInTheDocument()
    await user.click(button)

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('exposes the active state via aria-pressed', () => {
    const { rerender } = render(
      <HeaderNavAction icon={<TestIcon />} label="Chat" ariaLabel="Open chat" active={false} onClick={vi.fn()} />
    )
    expect(screen.getByRole('button', { name: 'Open chat' })).toHaveAttribute('aria-pressed', 'false')

    rerender(
      <HeaderNavAction icon={<TestIcon />} label="Chat" ariaLabel="Open chat" active onClick={vi.fn()} />
    )
    expect(screen.getByRole('button', { name: 'Open chat' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('active and inactive share the base visual contract and differ only in state styling', () => {
    const { rerender } = render(
      <HeaderNavAction icon={<TestIcon />} label="Chat" ariaLabel="Open chat" active={false} onClick={vi.fn()} />
    )
    const inactiveClass = screen.getByRole('button', { name: 'Open chat' }).className

    for (const cls of BASE_CONTRACT_CLASSES) {
      expect(inactiveClass).toContain(cls)
    }
    // Inactive: transparent/subdued — no accent background.
    expect(inactiveClass).not.toContain('bg-accent')

    rerender(<HeaderNavAction icon={<TestIcon />} label="Chat" ariaLabel="Open chat" active onClick={vi.fn()} />)
    const activeClass = screen.getByRole('button', { name: 'Open chat' }).className

    for (const cls of BASE_CONTRACT_CLASSES) {
      expect(activeClass).toContain(cls)
    }
    // Active: emphasized with the app's accent treatment.
    expect(activeClass).toContain('bg-accent')
    expect(activeClass).toContain('text-accent-foreground')
  })
})
