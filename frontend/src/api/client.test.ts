// Wire-shape tests for the shared fetch client (spoilerless/app/core/errors.py
// envelope mirror). PROB-09/#20: every synthesized/normalized code follows the
// backend's canonical UPPERCASE convention — no legacy lowercase aliases.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './client'

describe('ApiError normalization (PROB-09 uppercase convention)', () => {
  it('passes envelope codes through as-is (uppercase canonical)', () => {
    const err = new ApiError({ code: 'RESOURCE_NOT_FOUND', message: 'Not found.' })
    expect(err.code).toBe('RESOURCE_NOT_FOUND')
    expect(err.message).toBe('Not found.')
    expect(err.name).toBe('ApiError')
  })

  it('normalizes the FastAPI validation-error array shape to INVALID_REQUEST', () => {
    const err = new ApiError([{ loc: ['body', 'count'], msg: 'Input should be greater than 0', type: 'greater_than' }])
    expect(err.code).toBe('INVALID_REQUEST')
    expect(err.message).toBe('Input should be greater than 0')
  })

  it('falls back to a real message for an empty validation array', () => {
    const err = new ApiError([])
    expect(err.code).toBe('INVALID_REQUEST')
    expect(err.message).toBe('Request failed.')
  })

  it('accepts uppercase auth/LLM codes without rewriting them', () => {
    const err = new ApiError({ code: 'AUTH_EMAIL_NOT_ALLOWED', message: 'nope' })
    expect(err.code).toBe('AUTH_EMAIL_NOT_ALLOWED')
  })
})

describe('apiFetch', () => {
  const fetchStub = vi.fn()

  beforeEach(() => {
    fetchStub.mockReset()
    vi.stubGlobal('fetch', fetchStub)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the parsed JSON body on 2xx', async () => {
    fetchStub.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ count: 1 }),
    })
    await expect(apiFetch<{ count: number }>('/api/series')).resolves.toEqual({ count: 1 })
  })

  it('returns undefined on 204 No Content', async () => {
    fetchStub.mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => {
        throw new Error('no body')
      },
    })
    await expect(apiFetch('/api/series/x/progress', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('throws ApiError with the envelope code on a non-2xx envelope response', async () => {
    fetchStub.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: { code: 'RESOURCE_NOT_FOUND', message: 'Not found.' } }),
    })
    const err = await apiFetch('/api/series/nope').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('RESOURCE_NOT_FOUND')
  })

  it('synthesizes UNKNOWN_ERROR when the error body is not JSON', async () => {
    fetchStub.mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('Unexpected token')
      },
    })
    const err = await apiFetch('/api/series/x').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('UNKNOWN_ERROR')
  })

  it('sends credentials include and a JSON content type with the body', async () => {
    fetchStub.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    })
    await apiFetch('/api/series', { method: 'POST', body: { a: 1 } })
    expect(fetchStub).toHaveBeenCalledWith(
      expect.stringContaining('/api/series'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})
