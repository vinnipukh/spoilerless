import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useWatchProgress } from './useWatchProgress'
import { getProgress, updateProgress } from '../api/progress'

const STORAGE_KEY = 'spoilerless.watchProgress'

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

  it('switchSeries moves to the new series at a NULL boundary without opening the modal (PROB-09/#61)', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))

    const { result } = renderHook(() => useWatchProgress())
    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.confirmedOrder).toBe(3)

    act(() => {
      result.current.switchSeries('series_other')
    })

    expect(result.current.seriesId).toBe('series_other')
    // Fail-closed: nothing revealed for the new series until the user picks
    // an episode — viewAsOfOrder=1 would pre-select S01E01 and Radix Select
    // swallows re-selected values, killing the first unlock click.
    expect(result.current.confirmedOrder).toBeNull()
    expect(result.current.viewAsOfOrder).toBeNull()
    // Navigation-only: never a watch action, so no pending confirmation.
    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? '{}')).toEqual({
      seriesId: 'series_other',
      visibleUntilOrder: 1,
    })
  })

  it('switchSeries to the already-current series is a no-op', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))

    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      result.current.switchSeries('series_dexter')
    })

    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.confirmedOrder).toBe(2)
  })

  it('after switchSeries, the first episode click still surfaces the unlock dialog (PROB-09/#61 regression)', () => {
    // switchSeries leaves the boundary NULL; clicking S01E01 must open the
    // confirm flow (currentView null → unlock path), never be swallowed.
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_other', visibleUntilOrder: 1 }))

    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      result.current.switchSeries('series_dexter')
    })
    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.viewAsOfOrder).toBeNull()
    expect(result.current.pendingChange).toBeNull()

    act(() => {
      result.current.requestChange('series_dexter', 1)
    })

    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 1,
      direction: 'forward',
    })
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
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

  it('a confirm committed during mount hydration is not clobbered by the late hydration response (PROB-31 race)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
    // Hold the mount-time getProgress open so hydration is still in flight
    // when the user clicks + confirms.
    let resolveHydration!: (record: ReturnType<typeof progressRecord>) => void
    mockedGetProgress.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveHydration = resolve
      }),
    )

    const { result } = renderHook(() => useWatchProgress())

    // User clicks a locked episode and confirms while hydration is pending.
    act(() => {
      void result.current.requestChange('series_dexter', 2)
    })
    await act(async () => {
      await result.current.confirmChange()
    })
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(result.current.watchedThroughOrder).toBe(2)

    // The backend record (older boundary) resolves LATE — it must NOT roll
    // back the just-committed click.
    await act(async () => {
      resolveHydration(progressRecord('series_dexter', 1))
    })

    expect(result.current.viewAsOfOrder).toBe(2)
    expect(result.current.watchedThroughOrder).toBe(2)
    expect(result.current.pendingChange).toBeNull()
  })

  it('a modal opened during mount hydration survives a late hydration response (PROB-31 race)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
    let resolveHydration!: (record: ReturnType<typeof progressRecord>) => void
    mockedGetProgress.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveHydration = resolve
      }),
    )

    const { result } = renderHook(() => useWatchProgress())

    act(() => {
      void result.current.requestChange('series_dexter', 2)
    })
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 2,
      direction: 'forward',
    })

    await act(async () => {
      resolveHydration(progressRecord('series_dexter', 1))
    })

    // The unlock dialog is still open — the late hydration never swallowed
    // the click.
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 2,
      direction: 'forward',
    })
  })

  it('a same-order re-click is reconciled, never silently dropped: view-only POST re-affirms the current episode (PROB-31)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))

    const { result } = renderHook(() => useWatchProgress())
    expect(result.current.confirmedOrder).toBe(2)

    act(() => {
      void result.current.requestChange('series_dexter', 2)
    })

    // No modal, view unchanged — but the click was NOT swallowed: it
    // re-affirmed the current view with an awaited view-only POST.
    expect(result.current.pendingChange).toBeNull()
    expect(result.current.confirmedOrder).toBe(2)
    expect(mockedUpdateProgress).toHaveBeenCalledWith('series_dexter', 2, { viewAsOfOrder: 2 })
  })

  it('a view-only POST failure is surfaced to the caller (resolves false) so the graph can refetch (PROB-31)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
    mockedUpdateProgress.mockRejectedValueOnce(new Error('network error'))

    const { result } = renderHook(() => useWatchProgress())

    let persisted = true
    await act(async () => {
      persisted = await result.current.requestChange('series_dexter', 1)
    })

    // The episode still loads locally (optimistic view move)...
    expect(result.current.viewAsOfOrder).toBe(1)
    expect(result.current.pendingChange).toBeNull()
    // ...but the caller is told the persist failed so it can refetch.
    expect(persisted).toBe(false)
  })

  it('a locked-episode click above watchedThroughOrder still opens the unlock dialog after a failing view-only POST (PROB-31 regression)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
    // First: a view-only click below the watched boundary fires a POST that
    // fails (network error) — the click is NOT swallowed.
    mockedUpdateProgress.mockRejectedValueOnce(new Error('network error'))

    const { result } = renderHook(() => useWatchProgress())

    await act(async () => {
      await expect(result.current.requestChange('series_dexter', 2)).resolves.toBe(false)
    })
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(result.current.pendingChange).toBeNull()

    // Then: the locked-episode click ABOVE watchedThroughOrder ALWAYS opens
    // the unlock dialog — a failed view-only POST never blocks the modal.
    act(() => {
      void result.current.requestChange('series_dexter', 4)
    })
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 4,
      direction: 'forward',
    })
  })
})

describe('useWatchProgress persist:false (visitor / misafir read-only mode)', () => {
  it('first interaction (no established boundary yet) applies locally — never POSTs, never opens the modal', async () => {
    // Fresh visitor: currentView null (entry seed / series switch) — there
    // is no boundary yet to spoil, so the first selection is silent.
    const { result } = renderHook(() => useWatchProgress({ persist: false }))

    await act(async () => {
      const ok = await result.current.requestChange('series_dexter', 3)
      expect(ok).toBe(true)
    })

    expect(result.current.seriesId).toBe('series_dexter')
    expect(result.current.viewAsOfOrder).toBe(3)
    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })

  it('never calls the backend hydration GET on mount', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))

    renderHook(() => useWatchProgress({ persist: false }))

    expect(mockedGetProgress).not.toHaveBeenCalled()
  })

  it('forward move ABOVE the current view opens the spoiler modal without POSTing (08-12 regression)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    const { result } = renderHook(() => useWatchProgress({ persist: false }))
    expect(result.current.viewAsOfOrder).toBe(2)

    await act(async () => {
      const ok = await result.current.requestChange('series_dexter', 4)
      expect(ok).toBe(true)
    })

    // The warning surfaces; the view is NOT moved until confirm.
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 4,
      direction: 'forward',
    })
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })

  it('backward / same-order moves stay silent (view-only, nothing spoiled)', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    const { result } = renderHook(() => useWatchProgress({ persist: false }))

    await act(async () => {
      await result.current.requestChange('series_dexter', 1)
    })
    expect(result.current.viewAsOfOrder).toBe(1)
    expect(result.current.pendingChange).toBeNull()

    await act(async () => {
      await result.current.requestChange('series_dexter', 1)
    })
    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })

  it('visitor confirmChange applies the view locally and never POSTs', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    const { result } = renderHook(() => useWatchProgress({ persist: false }))

    act(() => {
      void result.current.requestChange('series_dexter', 4)
    })
    expect(result.current.pendingChange).not.toBeNull()

    await act(async () => {
      await result.current.confirmChange()
    })

    expect(result.current.viewAsOfOrder).toBe(4)
    expect(result.current.watchedThroughOrder).toBe(4)
    expect(result.current.pendingChange).toBeNull()
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })

  it('visitor cancelChange clears the spoiler modal without moving the view', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 2 }))
    const { result } = renderHook(() => useWatchProgress({ persist: false }))

    act(() => {
      void result.current.requestChange('series_dexter', 4)
    })
    expect(result.current.pendingChange).not.toBeNull()

    act(() => {
      result.current.cancelChange()
    })

    expect(result.current.pendingChange).toBeNull()
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(mockedUpdateProgress).not.toHaveBeenCalled()
  })
})
