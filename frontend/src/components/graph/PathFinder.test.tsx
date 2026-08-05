import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PathFinder } from './PathFinder'
import * as apiGraph from '@/api/graph'

vi.mock('@/api/graph', () => ({
  findPath: vi.fn(),
}))

describe('PathFinder component', () => {
  const mockCy = {
    elements: vi.fn().mockReturnThis(),
    removeClass: vi.fn().mockReturnThis(),
    addClass: vi.fn().mockReturnThis(),
    difference: vi.fn().mockReturnThis(),
    fit: vi.fn(),
    getElementById: vi.fn().mockReturnValue({
      length: 1,
      addClass: vi.fn(),
    }),
    collection: vi.fn().mockReturnValue({
      length: 1,
      merge: vi.fn(),
      addClass: vi.fn(),
    }),
  }

  const cyRef = { current: mockCy as any }
  const onExit = vi.fn()
  let registeredPickHandler: ((pick: { id: string; label: string }) => void) | null = null
  const registerPickHandler = vi.fn((handler) => {
    registeredPickHandler = handler
  })

  beforeEach(() => {
    vi.clearAllMocks()
    registeredPickHandler = null
  })

  it('renders initial mode copy "Select first node…"', () => {
    render(
      <PathFinder
        cyRef={cyRef}
        seriesId="series_dexter"
        onExit={onExit}
        registerPickHandler={registerPickHandler}
      />
    )

    expect(screen.getByText('Select first node…')).toBeInTheDocument()
    expect(registerPickHandler).toHaveBeenCalledWith(expect.any(Function))
  })

  it('transitions copy on first pick to "Select second node…"', () => {
    render(
      <PathFinder
        cyRef={cyRef}
        seriesId="series_dexter"
        onExit={onExit}
        registerPickHandler={registerPickHandler}
      />
    )

    expect(registeredPickHandler).not.toBeNull()
    act(() => {
      registeredPickHandler!({ id: 'node1', label: 'Dexter Morgan' })
    })

    expect(screen.getByText('Select second node…')).toBeInTheDocument()
  })

  it('triggers findPath on second pick and renders result chip', async () => {
    vi.mocked(apiGraph.findPath).mockResolvedValueOnce({
      found: true,
      path: ['node1', 'node2'],
      edges: ['edge1'],
      hops: 1,
    })

    render(
      <PathFinder
        cyRef={cyRef}
        seriesId="series_dexter"
        onExit={onExit}
        registerPickHandler={registerPickHandler}
      />
    )

    act(() => {
      registeredPickHandler!({ id: 'node1', label: 'Dexter Morgan' })
    })
    act(() => {
      registeredPickHandler!({ id: 'node2', label: 'Debra Morgan' })
    })

    await waitFor(() => {
      expect(apiGraph.findPath).toHaveBeenCalledWith('series_dexter', {
        source_entity_id: 'node1',
        target_entity_id: 'node2',
        max_hops: 4,
      })
      expect(screen.getByText('1 hops · 2 nodes')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: 'Clear path' })).toBeInTheDocument()
  })

  it('renders error alert when path is not found', async () => {
    vi.mocked(apiGraph.findPath).mockResolvedValueOnce({
      found: false,
      path: [],
      edges: [],
      hops: 0,
    })

    render(
      <PathFinder
        cyRef={cyRef}
        seriesId="series_dexter"
        onExit={onExit}
        registerPickHandler={registerPickHandler}
      />
    )

    act(() => {
      registeredPickHandler!({ id: 'node1', label: 'Dexter Morgan' })
    })
    act(() => {
      registeredPickHandler!({ id: 'node2', label: 'Rudy Cooper' })
    })

    await waitFor(() => {
      expect(screen.getByText('No path found')).toBeInTheDocument()
    })
  })

  it('exits mode on Exit button click', () => {
    render(
      <PathFinder
        cyRef={cyRef}
        seriesId="series_dexter"
        onExit={onExit}
        registerPickHandler={registerPickHandler}
      />
    )

    const exitBtn = screen.getByRole('button', { name: 'Exit path finder' })
    act(() => {
      exitBtn.click()
    })

    expect(onExit).toHaveBeenCalled()
  })
})
