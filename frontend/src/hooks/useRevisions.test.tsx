import { describe, it, expect, vi, beforeEach } from 'vitest'
import ReactDOM from 'react-dom'
import ReactDOMClient from 'react-dom/client'
import { useRevisions } from './useRevisions'
import type { RevisionResponse } from '../types/revision'

// Mock the API module before any imports that use it
vi.mock('../api/revisions', () => ({
  getRevisions: vi.fn(),
}))

import { getRevisions } from '../api/revisions'

const mockRevision: RevisionResponse = {
  id: 'revision:test-1',
  series_id: 'series:dexter',
  resource_type: 'UserNote',
  resource_id: 'user-note:test',
  action: 'Updated',
  before: { content: 'old content' },
  after: { content: 'new content' },
  created_at: '2026-07-30T10:00:00Z',
  visible_from_order: 1,
}

function render(ui: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = ReactDOMClient.createRoot(container)
  ReactDOM.flushSync(() => { root.render(ui) })
  return { container, root }
}

beforeEach(() => {
  document.body.innerHTML = ''
  vi.clearAllMocks()
  // Default mock so tests that trigger async effects don't crash
  vi.mocked(getRevisions).mockResolvedValue([])
})

describe('useRevisions', () => {
  it('starts in idle state when seriesId is null', () => {
    let captured: any = null
    function TestComp() {
      captured = useRevisions({ seriesId: null, visibleUntilOrder: null })
      return null
    }
    const { root } = render(<TestComp />)
    expect(captured.status).toBe('idle')
    root.unmount()
  })

  it('starts in loading state when seriesId and visibleUntilOrder are set', () => {
    let captured: any = null
    function TestComp() {
      captured = useRevisions({ seriesId: 'series:dexter', visibleUntilOrder: 1 })
      return null
    }
    const { root } = render(<TestComp />)
    expect(captured.status).toBe('loading')
    root.unmount()
  })

  it('transitions to success state after fetch resolves', async () => {
    vi.mocked(getRevisions).mockResolvedValue([mockRevision])

    let captured: any = null
    function TestComp() {
      captured = useRevisions({ seriesId: 'series:dexter', visibleUntilOrder: 1 })
      return null
    }
    const { root } = render(<TestComp />)
    expect(captured.status).toBe('loading')

    // Let the async effect settle
    await vi.waitFor(() => {
      expect(captured.status).toBe('success')
    })

    expect(captured.data).toEqual([mockRevision])
    root.unmount()
  })

  it('transitions to error state on fetch failure', async () => {
    vi.mocked(getRevisions).mockRejectedValue(new Error('Network error'))

    let captured: any = null
    function TestComp() {
      captured = useRevisions({ seriesId: 'series:dexter', visibleUntilOrder: 1 })
      return null
    }
    const { root } = render(<TestComp />)
    expect(captured.status).toBe('loading')

    await vi.waitFor(() => {
      expect(captured.status).toBe('error')
    })

    expect(captured.error.message).toBe('Request failed.')
    root.unmount()
  })

  it('resets to loading when key changes', async () => {
    vi.mocked(getRevisions).mockResolvedValue([mockRevision])

    let captured: any = null
    function TestComp({ sid }: { sid: string | null }) {
      captured = useRevisions({ seriesId: sid, visibleUntilOrder: 1 })
      return null
    }

    const { root } = render(<TestComp sid="series:dexter" />)

    // Wait for success
    await vi.waitFor(() => {
      expect(captured.status).toBe('success')
    })

    // Re-render with different seriesId
    ReactDOM.flushSync(() => { root.render(<TestComp sid="series:other" />) })
    expect(captured.status).toBe('loading')
    root.unmount()
  })

  it('refetch re-fetches and updates data', async () => {
    const updatedRevision = { ...mockRevision, id: 'revision:test-2' }
    vi.mocked(getRevisions)
      .mockResolvedValueOnce([mockRevision])
      .mockResolvedValueOnce([updatedRevision])

    let captured: any = null
    function TestComp() {
      captured = useRevisions({ seriesId: 'series:dexter', visibleUntilOrder: 1 })
      return null
    }

    const { root } = render(<TestComp />)

    // Wait for initial fetch
    await vi.waitFor(() => {
      expect(captured.status).toBe('success')
    })
    expect(captured.data).toEqual([mockRevision])

    // Call refetch — doesn't set loading (matches useNotes pattern)
    ReactDOM.flushSync(() => { captured.refetch() })

    // Data should update after refetch resolves
    await vi.waitFor(() => {
      expect(captured.data).toEqual([updatedRevision])
    })
    root.unmount()
  })
})
