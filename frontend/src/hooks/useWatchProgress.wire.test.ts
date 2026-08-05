import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useWatchProgress } from './useWatchProgress'

// PROB-31/#56 wire-shape regressions (RESEARCH.md Pitfall 4 / NO-WIRE-MOCK):
// these tests stub globalThis.fetch at the transport level and never
// vi.mock the progress API client, so the asserted payloads and behaviors
// cannot enshrine a contract bug. The payload builder itself is already
// locked by src/api/progress.test.ts (09-02); these tests lock the HOOK's
// requestChange behavior against a failing view-only POST.

const STORAGE_KEY = 'spoilerless.watchProgress'

function progressRecord(seriesId: string, watchedThroughOrder: number, viewAsOfOrder: number) {
  return {
    id: 'progress_1',
    user_id: 'user_1',
    series_id: seriesId,
    visible_until_order: viewAsOfOrder,
    watched_through_order: watchedThroughOrder,
    view_as_of_order: viewAsOfOrder,
    effective_view_order: viewAsOfOrder,
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function jsonResponse(data: unknown): Response {
  return { ok: true, status: 200, json: async () => data } as Response
}

function failingResponse(): Response {
  return {
    ok: false,
    status: 401,
    json: async () => ({ detail: { code: 'AUTH_UNAUTHENTICATED', message: 'Unauthenticated' } }),
  } as Response
}

// Number of consecutive POST failures to serve before POSTs succeed again.
let postFailuresRemaining = 0
// Captured POST payloads (parsed) for wire-shape assertions.
let capturedPostBodies: Array<Record<string, number>> = []

beforeEach(() => {
  sessionStorage.clear()
  postFailuresRemaining = 0
  capturedPostBodies = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (init?.method === 'POST' && url.includes('/progress')) {
        const body = JSON.parse(String(init.body)) as Record<string, number>
        capturedPostBodies.push(body)
        if (postFailuresRemaining > 0) {
          postFailuresRemaining -= 1
          return Promise.resolve(failingResponse())
        }
        const order = body.watched_through_order ?? body.view_as_of_order ?? 1
        return Promise.resolve(jsonResponse(progressRecord('series_dexter', order, order)))
      }
      if (url.includes('/progress')) {
        // Mount hydration: the backend holds watched=3 while the user is
        // currently viewing episode 1 — the PROB-31 scenario where a
        // below-watched click is view-only.
        return Promise.resolve(jsonResponse(progressRecord('series_dexter', 3, 1)))
      }
      return Promise.resolve(failingResponse())
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useWatchProgress wire regressions (PROB-31/#56)', () => {
  it('clicking a locked episode above watchedThroughOrder with a failing view-only POST still opens the unlock dialog', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
    postFailuresRemaining = 1

    const { result } = renderHook(() => useWatchProgress())
    // Let the mount hydration land (backend: watched=3, view=1).
    await waitFor(() => expect(result.current.watchedThroughOrder).toBe(3))

    // View-only click below the watched boundary: the POST fails, the click
    // is surfaced (resolves false) and the episode still loads locally.
    let persisted = true
    await act(async () => {
      persisted = await result.current.requestChange('series_dexter', 2)
    })
    expect(persisted).toBe(false)
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(result.current.pendingChange).toBeNull()
    // Wire shape: the view-only POST carried ONLY view_as_of_order — never
    // the legacy confirm alias (PROG-01/09-02 contract).
    expect(capturedPostBodies).toEqual([{ view_as_of_order: 2 }])

    // The locked-episode click ABOVE watchedThroughOrder STILL opens the
    // unlock dialog — a failed view-only POST never blocks the modal.
    act(() => {
      void result.current.requestChange('series_dexter', 4)
    })
    expect(result.current.pendingChange).toEqual({
      seriesId: 'series_dexter',
      nextOrder: 4,
      direction: 'forward',
    })
  })

  it('clicking a locked episode below watchedThroughOrder loads the episode and reports the POST failure so the graph refetches', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
    // TWO consecutive view-only POST failures: the same-order reaffirm click
    // (order 1) consumes the first, the below-watched click (order 2) the
    // second — both must surface failure (PROB-31: never a silent no-op).
    postFailuresRemaining = 2

    const { result } = renderHook(() => useWatchProgress())
    await waitFor(() => expect(result.current.watchedThroughOrder).toBe(3))

    // Same-order click on the currently-viewed episode is reconciled (never
    // silently dropped) and re-affirmed with a view-only POST.
    let persisted = true
    await act(async () => {
      persisted = await result.current.requestChange('series_dexter', 1)
    })
    expect(result.current.viewAsOfOrder).toBe(1)
    expect(persisted).toBe(false)
    expect(capturedPostBodies).toEqual([{ view_as_of_order: 1 }])

    // Now the below-watched click: loads the episode AND reports failure so
    // the App refetches the graph (never "nothing happened").
    persisted = true
    await act(async () => {
      persisted = await result.current.requestChange('series_dexter', 2)
    })
    expect(result.current.viewAsOfOrder).toBe(2)
    expect(result.current.pendingChange).toBeNull()
    expect(persisted).toBe(false)
  })

  it('a same-order click on the current view is never a silent no-op and never touches watchedThroughOrder', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    const { result } = renderHook(() => useWatchProgress())
    await waitFor(() => expect(result.current.watchedThroughOrder).toBe(3))

    // POST succeeds on this path (postFailuresRemaining = 0).
    let persisted = false
    await act(async () => {
      persisted = await result.current.requestChange('series_dexter', 1)
    })
    expect(persisted).toBe(true)
    expect(result.current.viewAsOfOrder).toBe(1)
    // View-only: watched progress is NEVER lowered or touched.
    expect(result.current.watchedThroughOrder).toBe(3)
    expect(result.current.pendingChange).toBeNull()
    expect(capturedPostBodies).toEqual([{ view_as_of_order: 1 }])
  })
})
