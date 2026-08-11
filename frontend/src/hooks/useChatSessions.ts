import { listChatSessions } from '../api/chat'
import type { ChatSession } from '../types/chat'
import { useFetchState } from './useFetchState'

export function useChatSessions(seriesId: string | null) {
  const { refetch, ...state } = useFetchState<ChatSession[]>(
    seriesId ?? '',
    Boolean(seriesId),
    () => listChatSessions(seriesId!),
  )

  return {
    status: state.status,
    sessions: state.status === 'success' ? state.data : [],
    error: state.status === 'error' ? state.error : null,
    refetch,
  }
}
