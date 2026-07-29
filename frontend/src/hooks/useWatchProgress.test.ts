import { beforeEach, describe, expect, it } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useWatchProgress } from './useWatchProgress'

const STORAGE_KEY = 'hdgraf.watchProgress'

beforeEach(() => {
  sessionStorage.clear()
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
})
