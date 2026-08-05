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

// Wire-shape contract for the three progress payload shapes (PROB-23/#43,
// PROB-15): assertions are against the JSON-parsed body of the captured
// fetch call. The API client is NEVER vi.mock'd here — a client-module mock
// is exactly the pattern that enshrined the 08-01 chat-422 / 08-04
// progress-422 shipping-green bugs (Pitfall 4).
describe('updateProgress wire shape — parsed request body (no client mock)', () => {
  const progressUrl = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/series/series_dexter/progress`

  function parsedBody(): Record<string, number> {
    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(init?.body).toEqual(expect.any(String))
    return JSON.parse(init?.body as string) as Record<string, number>
  }

  it('forward confirm posts watched_through_order + view_as_of_order — visible_until_order ABSENT', async () => {
    mockFetchJson(200, { ...sampleProgress, watched_through_order: 4, view_as_of_order: 3 })

    await updateProgress('series_dexter', 4, { watchedThroughOrder: 4, viewAsOfOrder: 3 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      progressUrl,
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    const body = parsedBody()
    expect(body).toEqual({ watched_through_order: 4, view_as_of_order: 3 })
    expect(body).not.toHaveProperty('visible_until_order')
  })

  it('view-only posts view_as_of_order ALONE — visible_until_order and watched_through_order ABSENT', async () => {
    mockFetchJson(200, { ...sampleProgress, view_as_of_order: 2 })

    await updateProgress('series_dexter', 1, { viewAsOfOrder: 2 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      progressUrl,
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    const body = parsedBody()
    expect(body).toEqual({ view_as_of_order: 2 })
    expect(body).not.toHaveProperty('visible_until_order')
    expect(body).not.toHaveProperty('watched_through_order')
  })

  it('plain legacy confirm posts visible_until_order alone', async () => {
    mockFetchJson(200, { ...sampleProgress, visible_until_order: 5 })

    await updateProgress('series_dexter', 5)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      progressUrl,
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    const body = parsedBody()
    expect(body).toEqual({ visible_until_order: 5 })
    expect(body).not.toHaveProperty('watched_through_order')
    expect(body).not.toHaveProperty('view_as_of_order')
  })
})
