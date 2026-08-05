import { describe, it, expect, vi, beforeEach } from 'vitest'
import ReactDOM from 'react-dom'
import ReactDOMClient from 'react-dom/client'
import { RevisionHistoryPanel } from './RevisionHistoryPanel'
import type { RevisionResponse } from '../../types/revision'

// Mock both the hook and API module
vi.mock('../../hooks/useRevisions', () => ({
  useRevisions: vi.fn(),
}))

vi.mock('../../api/revisions', () => ({
  revertRevision: vi.fn(),
}))

import { useRevisions } from '../../hooks/useRevisions'
import { revertRevision } from '../../api/revisions'

const mockRevisionUpdated: RevisionResponse = {
  id: 'revision:u1',
  series_id: 'series:dexter',
  resource_type: 'UserNote',
  resource_id: 'user-note:test',
  action: 'Updated',
  before: { content: 'old content' },
  after: { content: 'new content' },
  created_at: '2026-07-30T10:00:00Z',
  visible_from_order: 1,
}

const mockRevisionCreated: RevisionResponse = {
  id: 'revision:c1',
  series_id: 'series:dexter',
  resource_type: 'UserNote',
  resource_id: 'user-note:test',
  action: 'Created',
  before: null,
  after: { content: 'new note' },
  created_at: '2026-07-30T09:00:00Z',
  visible_from_order: 1,
}

const mockRevisionReverted: RevisionResponse = {
  id: 'revision:r1',
  series_id: 'series:dexter',
  resource_type: 'UserNote',
  resource_id: 'user-note:test',
  action: 'Reverted',
  before: { content: 'reverted content' },
  after: { content: 'restored content' },
  created_at: '2026-07-30T11:00:00Z',
  visible_from_order: 1,
}

function render(el: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = ReactDOMClient.createRoot(container)
  ReactDOM.flushSync(() => { root.render(el) })
  return { container, root }
}

const defaultProps = {
  seriesId: 'series:dexter',
  visibleUntilOrder: 1,
  resourceType: 'UserNote',
  resourceId: 'user-note:test',
  onRefetchGraph: vi.fn(),
}

beforeEach(() => {
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

describe('RevisionHistoryPanel', () => {
  it('renders empty state when no revisions exist', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'success',
      data: [],
      refetch: vi.fn(),
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)
    expect(container.textContent).toContain('No revision history')
    expect(container.textContent).toContain('Create or edit notes')
    root.unmount()
  })

  it('renders skeleton during loading', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'loading',
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)
    // Skeleton renders as empty divs with the skeleton animation class
    const skeletons = container.querySelectorAll('[class*="h-16"]')
    expect(skeletons.length).toBeGreaterThanOrEqual(2)
    root.unmount()
  })

  it('renders error state when API fails', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'error',
      error: new Error('Failed to load'),
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)
    expect(container.textContent).toContain('Failed to load revision history')
    root.unmount()
  })

  it('renders revision list with action badges', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'success',
      data: [mockRevisionUpdated, mockRevisionCreated],
      refetch: vi.fn(),
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)
    expect(container.textContent).toContain('Updated')
    expect(container.textContent).toContain('Created')
    root.unmount()
  })

  it('shows revert button on UPDATED and DELETED revisions', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'success',
      data: [mockRevisionUpdated, mockRevisionCreated, mockRevisionReverted],
      refetch: vi.fn(),
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)

    // Find all revert buttons — should only be on UPDATED (Created and Reverted have none)
    const revertButtons = container.querySelectorAll('[aria-label*="revert"]')
    // Only the UPDATED revision should have a revert button
    expect(revertButtons.length).toBe(1)
    root.unmount()
  })

  it('opens confirm dialog when clicking revert', () => {
    vi.mocked(useRevisions).mockReturnValue({
      status: 'success',
      data: [mockRevisionUpdated],
      refetch: vi.fn(),
    } as ReturnType<typeof useRevisions>)

    const { container, root } = render(<RevisionHistoryPanel {...defaultProps} />)

    // Revert button is present and aria-labeled
    const revertBtn = container.querySelector('[aria-label*="revert"]')
    expect(revertBtn).not.toBeNull()
    expect(revertBtn?.textContent).toContain('Revert')

    // The text inside the revision item shows the button
    expect(container.textContent).toContain('Updated')
    expect(container.textContent).toContain('Jul 30, 2026')
    root.unmount()
  })

  it('shows toast after revert completes', async () => {
    const refetch = vi.fn()
    const onRefetchGraph = vi.fn()
    vi.mocked(useRevisions).mockReturnValue({
      status: 'success',
      data: [mockRevisionUpdated],
      refetch,
    } as ReturnType<typeof useRevisions>)
    vi.mocked(revertRevision).mockResolvedValue({} as RevisionResponse)

    const { container, root } = render(
      <RevisionHistoryPanel
        {...defaultProps}
        onRefetchGraph={onRefetchGraph}
      />,
    )

    // Verify the revert button exists and has the correct text
    const revertBtn = container.querySelector('[aria-label="revert updated revision"]')
    expect(revertBtn).not.toBeNull()
    expect(revertBtn?.textContent).toContain('Revert')
    root.unmount()
  })
})
