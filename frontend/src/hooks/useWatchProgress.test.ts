import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useWatchProgress } from './useWatchProgress'
import { getProgress, updateProgress } from '../api/progress'

const STORAGE_KEY = 'hdgraf.watchProgress'

vi.mock('../api/progress', () => ({
  getProgress: vi.fn(),
  updateProgress: vi.fn(),
}))

const mockedGetProgress = vi.mocked(getProgress)
const mockedUpdateProgress = vi.mocked(updateProgress)

function progressRecord(seriesId: string, visibleUntilOrder: number) {
  return {
    id: 'progress_1',
    user_id: 'user_1',
    series_id: seriesId,
    visible_until_order: visibleUntilOrder,
    watched_through_order: visibleUntilOrder,
    view_as_of_order: visibleUntilOrder,
    effective_view_order: visibleUntilOrder,
    updated_at: '2026-01-01T00:00:00Z',
  }
}

beforeEach(() => {
  sessionStorage.clear()
  vi.clearAllMocks()
  // Default: pending forever — existing sync-assertion tests below never
  // await anything, so a never-resolving promise keeps this mount-time
  // hydration effect from mutating state (or logging act() warnings) during
  // tests that don't care about it. Tests exercising hydration explicitly
  // override this with mockResolvedValueOnce/mockRejectedValueOnce.
  mockedGetProgress.mockImplementation(() => new Promise(() => {}))
  mockedUpdateProgress.mockImplementation((seriesId: string, visibleUntilOrder: number) =>
    Promise.resolve(progressRecord(seriesId, visibleUntilOrder)),
  )
})

describe('useWatchProgress', () => {
  it('hydrates confirmedSeriesId/confirmedOrder from a valid sessionStorage entry without opening the modal', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.confirmedOrder).toBe(2)
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state without throwing when sessionStorage holds invalid JSON', () => {
    sessionStorage.setItem(STORAGE_KEY, 'not-valid-json{')

    expect(() => renderHook(() => useWatchProgress())).not.toThrow()

    const { result } = renderHook(() => useWatchProgress())
    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state when visibleUntilOrder is 0 (fails the shape guard)', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 0 }),
    )

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state when visibleUntilOrder is negative', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: -1 }),
    )

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state when visibleUntilOrder is a non-integer', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1.5 }),
    )

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state when visibleUntilOrder is missing', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter' }))

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('falls back to the empty state when seriesId is an empty string', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: '', visibleUntilOrder: 1 }))

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.seriesId).toBeNull()
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()
  })

  it('does not set pendingChange when requestChange is called with the already-confirmed order (same-episode no-op)', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.confirmedOrder).toBe(2)

    act(() => {
      result.current.requestChange('series_dexter', 2)
    })

    expect(result.current.pendingChange).toBeNull()
    expect(result.current.confirmedOrder).toBe(2)
  })

  it('confirmChange awaits updateProgress before committing local state, then persists the backend value to sessionStorage', async () => {
    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      result.current.requestChange('series_dexter', 3)
    })
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 3,
      direction: 'forward',
    })

    await act(async () => {
      await result.current.confirmChange()
    })

    expect(mockedUpdateProgress).toHaveBeenCalledWith('series_dexter', 3, {
      watchedThroughOrder: 3,
      viewAsOfOrder: 3,
    })
    expect(result.current.confirmedOrder).toBe(3)
    expect(result.current.watchedThroughOrder).toBe(3)
    expect(result.current.viewAsOfOrder).toBe(3)
    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.pendingChange).toBeNull()
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? '{}')).toEqual({
      seriesId: 'series_dexter',
      visibleUntilOrder: 3,
    })
  })

  it('requestChange/cancelChange behavior is unchanged: cancelChange clears pendingChange without calling the backend', () => {
    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      result.current.requestChange('series_dexter', 2)
    })
    expect(result.current.pendingChange).not.toBeNull()

    act(() => {
      result.current.cancelChange()
    })

    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })

  it('selecting an already-watched episode is a view-only change: no modal, watched progress unchanged, view-only POST (PROG-01)', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))

    const { result } = renderHook(() => useWatchProgress())
    expect(result.current.watchedThroughOrder).toBe(3)
    expect(result.current.viewAsOfOrder).toBe(3)

    act(() => {
      result.current.requestChange('series_dexter', 1)
    })

    // View moved down, watched untouched, no confirmation flow.
    expect(result.current.viewAsOfOrder).toBe(1)
    expect(result.current.confirmedOrder).toBe(1)
    expect(result.current.watchedThroughOrder).toBe(3)
    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).toHaveBeenCalledWith('series_dexter', 1, { viewAsOfOrder: 1 })
  })

  it('selecting above watchedThroughOrder still opens the unlock confirmation (D-06)', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))

    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      result.current.requestChange('series_dexter', 4)
    })

    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 4,
      direction: 'forward',
    })
    expect(result.current.viewAsOfOrder).toBe(3) // unchanged until confirm
  })

  it('on initial mount, prefers the backend getProgress() value over a conflicting sessionStorage value', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    mockedGetProgress.mockResolvedValueOnce(progressRecord('series_dexter', 5))

    const { result } = renderHook(() => useWatchProgress())

    expect(result.current.confirmedOrder).toBe(2) // sessionStorage placeholder, pre-resolution

    await waitFor(() => expect(result.current.confirmedOrder).toBe(5))
    expect(mockedGetProgress).toHaveBeenCalledWith('series_dexter')
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? '{}')).toEqual({
      seriesId: 'series_dexter',
      visibleUntilOrder: 5,
    })
  })

  it('falls back to sessionStorage as a loading placeholder (never re-marked authoritative) when getProgress rejects', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    mockedGetProgress.mockRejectedValueOnce(new Error('network error'))

    const { result } = renderHook(() => useWatchProgress())

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(result.current.confirmedOrder).toBe(2)
    expect(result.current.seriesId).toBe('series_dexter')
  })
})
