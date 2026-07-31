import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useChatMessages } from './useChatMessages'
import type { ChatSessionDetail, MessageResponseEnvelope } from '../types/chat'

vi.mock('../api/chat', () => ({
  getChatSession: vi.fn(),
  streamMessage: vi.fn(),
}))

import { getChatSession, streamMessage } from '../api/chat'

type StreamCallbacks = {
  onTextDelta?: (delta: string) => void
  onDone: (envelope: MessageResponseEnvelope) => void
  onError?: (error: { code: string; message: string }) => void
}

const detail: ChatSessionDetail = {
  session: {
    id: 'session_1', series_id: 'series_dexter', title: 'Chat',
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  },
  messages: [],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getChatSession).mockResolvedValue(detail)
})

describe('useChatMessages', () => {
  it('starts idle when seriesId/sessionId are null', () => {
    const { result } = renderHook(() => useChatMessages(null, null))
    expect(result.current.status).toBe('idle')
  })

  it('loads the session detail into a success state', async () => {
    const { result } = renderHook(() => useChatMessages('series_dexter', 'session_1'))
    expect(result.current.status).toBe('loading')

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.messages).toEqual([])
  })

  it('transitions to streaming, accumulates text-delta chunks, then success on done', async () => {
    let captured: StreamCallbacks | null = null
    vi.mocked(streamMessage).mockImplementation(async (_s, _sid, _c, callbacks) => {
      captured = callbacks as StreamCallbacks
    })

    const { result } = renderHook(() => useChatMessages('series_dexter', 'session_1'))
    await waitFor(() => expect(result.current.status).toBe('success'))

    act(() => {
      result.current.sendMessage('What happened?')
    })

    expect(result.current.status).toBe('streaming')

    act(() => {
      captured?.onTextDelta?.('Hel')
      captured?.onTextDelta?.('lo')
    })

    expect(result.current.status).toBe('streaming')
    expect((result.current as { streamingText?: string }).streamingText).toBe('Hello')

    const envelope: MessageResponseEnvelope = {
      message: {
        id: 'msg_1', role: 'assistant', content: 'Hello', created_at: '2026-01-01T00:00:00Z',
        visible_until_order_snapshot: 1,
      },
      citations: [{
        claim_id: 'claim_1', evidence_id: null, source_id: 'source_1', source_label: 'S01E01 script',
        source_type: 'script', episode_code: 'S01E01', locator: '00:03:12', excerpt: null,
        related_node_ids: [], related_edge_ids: [],
      }],
      graph_focus: { node_ids: ['char_dexter_morgan'], edge_ids: [] },
      proposed_change_set: null,
    }

    act(() => {
      captured?.onDone(envelope)
    })

    expect(result.current.status).toBe('success')
    expect(result.current.messages).toContainEqual(envelope.message)
    expect(result.current.citations).toEqual(envelope.citations)
    expect(result.current.graphFocus).toEqual(envelope.graph_focus)
  })

  it('stop() aborts the in-flight stream via AbortController without an unhandled rejection', async () => {
    let capturedSignal: AbortSignal | undefined
    vi.mocked(streamMessage).mockImplementation((_s, _sid, _c, _callbacks, signal) => {
      capturedSignal = signal
      return new Promise((_resolve, reject) => {
        signal?.addEventListener('abort', () => {
          const err = new Error('The operation was aborted.')
          err.name = 'AbortError'
          reject(err)
        })
      })
    })

    const { result } = renderHook(() => useChatMessages('series_dexter', 'session_1'))
    await waitFor(() => expect(result.current.status).toBe('success'))

    act(() => {
      result.current.sendMessage('Hi')
    })
    expect(result.current.status).toBe('streaming')

    await act(async () => {
      result.current.stop()
      // Flush the microtask queue so the aborted promise's .catch() handler runs.
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(capturedSignal?.aborted).toBe(true)
  })

  it('transitions to error when the initial session-detail fetch fails', async () => {
    vi.mocked(getChatSession).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useChatMessages('series_dexter', 'session_1'))

    await waitFor(() => expect(result.current.status).toBe('error'))
  })
})
