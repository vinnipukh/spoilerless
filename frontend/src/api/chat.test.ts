import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createChatSession,
  listChatSessions,
  getChatSession,
  deleteChatSession,
  sendMessage,
} from './chat'
import { ApiError } from './client'

function mockFetchJson(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }) as unknown as typeof fetch
}

function mockFetchNoContent() {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 204,
    json: async () => null,
  }) as unknown as typeof fetch
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('chat api client', () => {
  it('createChatSession posts the title to /sessions via apiFetch', async () => {
    const session = {
      id: 'session_1', series_id: 'series_dexter', title: 'Chat',
      created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    }
    mockFetchJson(201, session)

    const result = await createChatSession('series_dexter', 'Chat')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ title: 'Chat' }),
      }),
    )
    expect(result).toEqual(session)
  })

  it('listChatSessions GETs /sessions via apiFetch', async () => {
    mockFetchJson(200, [])

    await listChatSessions('series_dexter')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions',
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it('getChatSession GETs /sessions/:id via apiFetch', async () => {
    mockFetchJson(200, { session: {}, messages: [] })

    await getChatSession('series_dexter', 'session_1')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions/session_1',
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it('deleteChatSession DELETEs /sessions/:id via apiFetch', async () => {
    mockFetchNoContent()

    await deleteChatSession('series_dexter', 'session_1')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions/session_1',
      expect.objectContaining({ method: 'DELETE', credentials: 'include' }),
    )
  })

  it('sendMessage posts { question } to /messages via apiFetch', async () => {
    const envelope = {
      message: {
        id: 'msg_1', role: 'assistant', content: 'Hi', created_at: '2026-01-01T00:00:00Z',
        visible_until_order_snapshot: 1,
      },
      citations: [],
      graph_focus: { node_ids: [], edge_ids: [] },
      proposed_change_set: null,
    }
    mockFetchJson(200, envelope)

    const result = await sendMessage('series_dexter', 'session_1', 'What happened?')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions/session_1/messages',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ question: 'What happened?' }),
      }),
    )
    expect(result).toEqual(envelope)
  })

  it('throws ApiError with the backend code/message intact on a non-2xx response', async () => {
    mockFetchJson(404, { detail: { code: 'resource_not_found', message: 'Resource not found.' } })

    await expect(listChatSessions('series_dexter')).rejects.toMatchObject({
      code: 'resource_not_found',
      message: 'Resource not found.',
    })
    await expect(listChatSessions('series_dexter')).rejects.toBeInstanceOf(ApiError)
  })
})
