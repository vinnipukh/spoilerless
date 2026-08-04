import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createChatSession,
  listChatSessions,
  getChatSession,
  deleteChatSession,
  sendMessage,
  streamMessage,
} from './chat'
import { ApiError } from './client'
import { BYOK_STORAGE_KEY } from '@/lib/byok'
import type { MessageResponseEnvelope } from '../types/chat'

// Same expression chat.ts uses for the raw SSE fetch URL, so the expectation
// tracks whatever VITE_API_BASE_URL the test env resolves ('' by default).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const streamUrl = `${API_BASE}/api/series/series_dexter/chat/sessions/session_1/messages/stream`

function storeByokSettings(settings: {
  provider: string
  api_key: string
  base_url: string
  model: string
}) {
  localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(settings))
}

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

// Fakes a `res.body.getReader()` ReadableStream reader that yields the
// given raw SSE-text chunks (already `\n\n`-delimited) one at a time.
function mockStreamResponse(chunks: string[], status = 200) {
  let index = 0
  const encoder = new TextEncoder()
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => null,
    body: {
      getReader: () => ({
        read: async () => {
          if (index < chunks.length) {
            const value = encoder.encode(chunks[index])
            index += 1
            return { done: false, value }
          }
          return { done: true, value: undefined }
        },
      }),
    },
  }) as unknown as typeof fetch
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
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

describe('BYOK header attachment (D-06)', () => {
  const envelope: MessageResponseEnvelope = {
    message: {
      id: 'msg_1', role: 'assistant', content: 'Hi', created_at: '2026-01-01T00:00:00Z',
      visible_until_order_snapshot: 1,
    },
    citations: [],
    graph_focus: { node_ids: [], edge_ids: [] },
    proposed_change_set: null,
  }

  it('sendMessage attaches X-LLM-* headers when a key is stored', async () => {
    storeByokSettings({
      provider: 'openai_compatible',
      api_key: 'sk-browser-key',
      base_url: 'https://llm.example/v1',
      model: 'deepseek-chat',
    })
    mockFetchJson(200, envelope)

    await sendMessage('series_dexter', 'session_1', 'What happened?')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/chat/sessions/session_1/messages',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-LLM-Api-Key': 'sk-browser-key',
          'X-LLM-Base-URL': 'https://llm.example/v1',
          'X-LLM-Model': 'deepseek-chat',
        }),
      }),
    )
  })

  it('streamMessage attaches X-LLM-* headers when a key is stored', async () => {
    storeByokSettings({
      provider: 'openai_compatible',
      api_key: 'sk-browser-key',
      base_url: 'https://llm.example/v1',
      model: 'deepseek-chat',
    })
    mockStreamResponse([`event: done\ndata: ${JSON.stringify(envelope)}\n\n`])

    await streamMessage('series_dexter', 'session_1', 'Hi', { onDone: vi.fn() })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      streamUrl,
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-LLM-Api-Key': 'sk-browser-key',
          'X-LLM-Base-URL': 'https://llm.example/v1',
          'X-LLM-Model': 'deepseek-chat',
        }),
      }),
    )
  })

  it('sendMessage omits X-LLM-* headers when no key is stored', async () => {
    // localStorage is cleared in beforeEach - no BYOK key present.
    mockFetchJson(200, envelope)

    await sendMessage('series_dexter', 'session_1', 'Hi')

    const [, options] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(options.headers).not.toHaveProperty('X-LLM-Api-Key')
    expect(options.headers).not.toHaveProperty('X-LLM-Base-URL')
    expect(options.headers).not.toHaveProperty('X-LLM-Model')
  })

  it('streamMessage omits X-LLM-* headers when no key is stored', async () => {
    mockStreamResponse([`event: done\ndata: ${JSON.stringify(envelope)}\n\n`])

    await streamMessage('series_dexter', 'session_1', 'Hi', { onDone: vi.fn() })

    const [, options] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
  })

  it('treats a whitespace-only stored key as absent (no X-LLM-* headers)', async () => {
    storeByokSettings({ provider: 'gemini', api_key: '   ', base_url: '', model: '' })
    mockFetchJson(200, envelope)

    await sendMessage('series_dexter', 'session_1', 'Hi')

    const [, options] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(options.headers).not.toHaveProperty('X-LLM-Api-Key')
  })

  it('omits blank base_url/model headers but keeps the key header', async () => {
    storeByokSettings({ provider: 'gemini', api_key: 'sk-key-only', base_url: '', model: '' })
    mockFetchJson(200, envelope)

    await sendMessage('series_dexter', 'session_1', 'Hi')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json', 'X-LLM-Api-Key': 'sk-key-only' },
      }),
    )
  })
})

describe('streamMessage', () => {
  it('reads text_delta chunks incrementally and invokes onTextDelta per chunk', async () => {
    const envelope: MessageResponseEnvelope = {
      message: {
        id: 'msg_1', role: 'assistant', content: 'Hello', created_at: '2026-01-01T00:00:00Z',
        visible_until_order_snapshot: 1,
      },
      citations: [],
      graph_focus: { node_ids: [], edge_ids: [] },
      proposed_change_set: null,
    }
    mockStreamResponse([
      'data: {"type":"text_delta","text":"Hel"}\n\n',
      'data: {"type":"text_delta","text":"lo"}\n\n',
      `event: done\ndata: ${JSON.stringify(envelope)}\n\n`,
    ])

    const onTextDelta = vi.fn()
    const onDone = vi.fn()

    await streamMessage('series_dexter', 'session_1', 'Hi', { onTextDelta, onDone })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      streamUrl,
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ question: 'Hi' }),
      }),
    )
    expect(onTextDelta).toHaveBeenNthCalledWith(1, 'Hel')
    expect(onTextDelta).toHaveBeenNthCalledWith(2, 'lo')
    expect(onDone).toHaveBeenCalledWith(envelope)
  })

  it('invokes onError for a structured event: error chunk (concurrency rejection)', async () => {
    mockStreamResponse([
      'event: error\ndata: {"code":"too_many_requests","message":"Too many concurrent requests."}\n\n',
    ])

    const onDone = vi.fn()
    const onError = vi.fn()
    await streamMessage('series_dexter', 'session_1', 'Hi', { onDone, onError })

    expect(onError).toHaveBeenCalledWith({ code: 'too_many_requests', message: 'Too many concurrent requests.' })
    expect(onDone).not.toHaveBeenCalled()
  })

  it('ends the streaming state when the server closes without a terminal event', async () => {
    // Server closed the connection mid-stream with no `event: done` and no
    // `event: error` (e.g. a provider failure the backend could not frame) —
    // the caller must still leave its streaming state, or the Stop button
    // would stay visible forever.
    mockStreamResponse([
      'data: {"type":"text_delta","text":"Based"}\n\n',
    ])

    const onDone = vi.fn()
    const onError = vi.fn()
    await streamMessage('series_dexter', 'session_1', 'Hi', { onDone, onError })

    expect(onDone).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledWith({
      code: 'stream_ended',
      message: 'The response ended unexpectedly. Please try again.',
    })
  })

  it('skips a malformed chunk defensively instead of throwing', async () => {
    const envelope: MessageResponseEnvelope = {
      message: {
        id: 'msg_2', role: 'assistant', content: 'ok', created_at: '2026-01-01T00:00:00Z',
        visible_until_order_snapshot: 1,
      },
      citations: [],
      graph_focus: { node_ids: [], edge_ids: [] },
      proposed_change_set: null,
    }
    mockStreamResponse([
      'data: {not valid json\n\n',
      `event: done\ndata: ${JSON.stringify(envelope)}\n\n`,
    ])

    const onTextDelta = vi.fn()
    const onDone = vi.fn()
    await expect(
      streamMessage('series_dexter', 'session_1', 'Hi', { onTextDelta, onDone }),
    ).resolves.toBeUndefined()

    expect(onDone).toHaveBeenCalledWith(envelope)
  })

  it('throws ApiError with the backend code/message intact when the stream request itself fails', async () => {
    mockStreamResponse(['irrelevant'], 503)
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: { code: 'llm_provider_unavailable', message: 'LLM provider unavailable.' } }),
      body: null,
    }) as unknown as typeof fetch

    await expect(
      streamMessage('series_dexter', 'session_1', 'Hi', { onDone: vi.fn() }),
    ).rejects.toMatchObject({ code: 'llm_provider_unavailable', message: 'LLM provider unavailable.' })
  })

  it('preserves an AbortSignal passed through to fetch for cancellation', async () => {
    mockStreamResponse([`event: done\ndata: ${JSON.stringify({
      message: { id: 'm', role: 'assistant', content: '', created_at: 'x', visible_until_order_snapshot: 1 },
      citations: [], graph_focus: { node_ids: [], edge_ids: [] }, proposed_change_set: null,
    })}\n\n`])

    const controller = new AbortController()
    await streamMessage('series_dexter', 'session_1', 'Hi', { onDone: vi.fn() }, controller.signal)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: controller.signal }),
    )
  })
})
