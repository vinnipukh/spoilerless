import { apiFetch, ApiError } from './client'
import { getLLMHeaders } from '@/lib/byok'
import type { ChatSession, ChatSessionDetail, MessageResponseEnvelope } from '../types/chat'

// ── Sessions ──

export function createChatSession(seriesId: string, title: string): Promise<ChatSession> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/chat/sessions`, {
    method: 'POST',
    body: { title },
  })
}

export function listChatSessions(seriesId: string): Promise<ChatSession[]> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/chat/sessions`)
}

export function getChatSession(seriesId: string, sessionId: string): Promise<ChatSessionDetail> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/chat/sessions/${encodeURIComponent(sessionId)}`,
  )
}

export function deleteChatSession(seriesId: string, sessionId: string): Promise<void> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/chat/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  )
}

// ── Messages (non-streaming) ──

export function sendMessage(
  seriesId: string,
  sessionId: string,
  content: string,
): Promise<MessageResponseEnvelope> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
    // BYOK (D-06): browser-held key/base_url/model ride as X-LLM-* headers.
    { method: 'POST', body: { question: content }, headers: getLLMHeaders() },
  )
}

// ── Messages (streaming) ──
//
// The one call `apiFetch<T>` cannot serve: it awaits/parses a single JSON
// body, but this endpoint returns `text/event-stream`. `credentials:
// 'include'` is preserved manually here since `apiFetch` isn't used.
// `EventSource` is not viable — it cannot POST a body/custom headers with
// cookies portably (06-PATTERNS.md).

export type StreamMessageCallbacks = {
  onTextDelta?: (delta: string) => void
  onDone: (envelope: MessageResponseEnvelope) => void
  onError?: (error: { code: string; message: string }) => void
}

/**
 * Reads the `/messages/stream` SSE response body incrementally, parsing
 * `data: {...}\n\n` chunks (`{type: 'text_delta', text}`) and the final
 * `event: done\ndata: {...}\n\n` chunk (a full `MessageResponseEnvelope`).
 * A concurrency rejection after headers are sent arrives as a structured
 * `event: error\ndata: {code, message}\n\n` chunk instead of an HTTP status.
 *
 * Malformed/unparseable chunks are skipped defensively rather than thrown —
 * the streaming fetch response is server-controlled but must never crash the
 * UI on a partial or corrupted chunk (threat model: "Streaming fetch
 * response -> client parser").
 */
export async function streamMessage(
  seriesId: string,
  sessionId: string,
  content: string,
  callbacks: StreamMessageCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  // BYOK (D-06): this raw SSE fetch carries the X-LLM-* headers like any
  // other chat request, and VITE_API_BASE_URL ('' by default) prefixes the
  // URL so a hosted frontend can reach a backend on another origin. The
  // shared apiFetch cannot serve this call (it awaits a JSON body).
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
  const res = await fetch(
    `${apiBase}/api/series/${encodeURIComponent(seriesId)}/chat/sessions/${encodeURIComponent(sessionId)}/messages/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getLLMHeaders() },
      body: JSON.stringify({ question: content }),
      credentials: 'include',
      signal,
    },
  )

  if (!res.ok || !res.body) {
    const responseBody = await res.json().catch(() => null)
    throw new ApiError(responseBody?.detail ?? { code: 'unknown_error', message: 'Request failed.' })
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  // A terminal event (`done` or `error`) must always arrive: if the server
  // closes the stream without one (proxy death, mid-stream provider failure
  // that the backend could not frame as `event: error`), the caller would
  // otherwise stay in its streaming state forever — the Stop button never
  // goes away and no answer ever appears.
  let gotTerminal = false

  function processEvent(rawEvent: string): void {
    const lines = rawEvent.split('\n')
    let eventType = 'message'
    let dataLine = ''
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice('event:'.length).trim()
      } else if (line.startsWith('data:')) {
        dataLine = line.slice('data:'.length).trim()
      }
    }
    if (!dataLine) return

    let parsed: unknown
    try {
      parsed = JSON.parse(dataLine)
    } catch {
      // Defensive: a malformed chunk must not crash the UI.
      return
    }

    if (eventType === 'done') {
      gotTerminal = true
      callbacks.onDone(parsed as MessageResponseEnvelope)
    } else if (eventType === 'error') {
      gotTerminal = true
      callbacks.onError?.(parsed as { code: string; message: string })
    } else {
      const chunk = parsed as { type?: string; text?: string }
      if (chunk.type === 'text_delta' && typeof chunk.text === 'string') {
        callbacks.onTextDelta?.(chunk.text)
      }
    }
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      processEvent(rawEvent)
      boundary = buffer.indexOf('\n\n')
    }
  }

  if (!gotTerminal) {
    callbacks.onError?.({
      code: 'stream_ended',
      message: 'The response ended unexpectedly. Please try again.',
    })
  }
}
