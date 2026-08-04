import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getProgress, updateProgress } from './progress'
import { ApiError } from './client'

function mockFetchJson(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }) as unknown as typeof fetch
}

const sampleProgress = {
  id: 'progress_1', user_id: 'user_1', series_id: 'series_dexter',
  visible_until_order: 2, updated_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('progress api client', () => {
  it('getProgress GETs /progress via apiFetch', async () => {
    mockFetchJson(200, sampleProgress)

    const result = await getProgress('series_dexter')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/progress',
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
    expect(result).toEqual(sampleProgress)
  })

  it('updateProgress posts { visible_until_order } to /progress via apiFetch', async () => {
    mockFetchJson(200, { ...sampleProgress, visible_until_order: 3 })

    const result = await updateProgress('series_dexter', 3)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/progress',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ visible_until_order: 3 }),
      }),
    )
    expect(result.visible_until_order).toBe(3)
  })

  it('forward confirm posts watched_through_order (never the legacy visible_until_order alias)', async () => {
    mockFetchJson(200, { ...sampleProgress, watched_through_order: 4, view_as_of_order: 4 })

    await updateProgress('series_dexter', 4, { watchedThroughOrder: 4, viewAsOfOrder: 4 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/progress',
      expect.objectContaining({
        body: JSON.stringify({ watched_through_order: 4, view_as_of_order: 4 }),
      }),
    )
  })

  it('view-only change posts view_as_of_order alone — no confirm alias (PROG-01)', async () => {
    mockFetchJson(200, { ...sampleProgress, view_as_of_order: 2 })

    await updateProgress('series_dexter', 2, { viewAsOfOrder: 2 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/progress',
      expect.objectContaining({
        body: JSON.stringify({ view_as_of_order: 2 }),
      }),
    )
  })

  it('throws ApiError with the backend code/message intact on a non-2xx response', async () => {
    mockFetchJson(404, { detail: { code: 'resource_not_found', message: 'Resource not found.' } })

    await expect(getProgress('series_dexter')).rejects.toMatchObject({
      code: 'resource_not_found',
      message: 'Resource not found.',
    })
    await expect(getProgress('series_dexter')).rejects.toBeInstanceOf(ApiError)
  })
})
