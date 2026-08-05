import { describe, it, expect, vi, beforeEach } from 'vitest'
import { proposeChangeSet, confirmChangeSet, rejectChangeSet, revertChangeSet } from './changeSet'
import { ApiError } from './client'
import type { ChangeSetCreateRequest } from '../types/changeSet'

function mockFetchJson(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }) as unknown as typeof fetch
}

const sampleChangeSet = {
  id: 'change_set_1', user_id: 'user_1', series_id: 'series_dexter', chat_session_id: 'session_1',
  status: 'awaiting_confirmation', visible_until_order_snapshot: 1, summary: 'Add a note',
  operations: [{ operation_type: 'create_note', target_type: 'Character', target_id: 'char_1', content: 'note' }],
  created_at: '2026-01-01T00:00:00Z', confirmed_at: null, applied_at: null, revision_id: null,
  idempotency_key: null,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('changeSet api client', () => {
  it('proposeChangeSet posts the create request to /change-sets via apiFetch', async () => {
    mockFetchJson(201, sampleChangeSet)
    const body: ChangeSetCreateRequest = {
      series_id: 'series_dexter', chat_session_id: 'session_1', summary: 'Add a note',
      operations: [{ operation_type: 'create_note', target_type: 'Character', target_id: 'char_1', content: 'note' }],
    }

    const result = await proposeChangeSet('series_dexter', body)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/change-sets',
      expect.objectContaining({ method: 'POST', credentials: 'include', body: JSON.stringify(body) }),
    )
    expect(result).toEqual(sampleChangeSet)
  })

  it('confirmChangeSet posts to /change-sets/:id/confirm via apiFetch', async () => {
    mockFetchJson(200, { ...sampleChangeSet, status: 'applied' })

    await confirmChangeSet('series_dexter', 'change_set_1')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/change-sets/change_set_1/confirm',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('rejectChangeSet posts to /change-sets/:id/reject via apiFetch', async () => {
    mockFetchJson(200, { ...sampleChangeSet, status: 'rejected' })

    await rejectChangeSet('series_dexter', 'change_set_1')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/change-sets/change_set_1/reject',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('revertChangeSet posts to /change-sets/:id/revert via apiFetch', async () => {
    mockFetchJson(200, { ...sampleChangeSet, status: 'reverted' })

    await revertChangeSet('series_dexter', 'change_set_1')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/change-sets/change_set_1/revert',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('throws ApiError with the backend code/message intact on a non-2xx response', async () => {
    mockFetchJson(422, { detail: { code: 'INVALID_REQUEST', message: 'Request validation failed.' } })

    await expect(confirmChangeSet('series_dexter', 'change_set_1')).rejects.toMatchObject({
      code: 'INVALID_REQUEST',
      message: 'Request validation failed.',
    })
    await expect(confirmChangeSet('series_dexter', 'change_set_1')).rejects.toBeInstanceOf(ApiError)
  })
})
