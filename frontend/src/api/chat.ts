import { apiFetch } from './client'
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
    { method: 'POST', body: { question: content } },
  )
}
