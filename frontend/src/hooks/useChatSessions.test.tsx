import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useChatSessions } from './useChatSessions'
import type { ChatSession } from '../types/chat'

vi.mock('../api/chat', () => ({
  listChatSessions: vi.fn(),
}))

import { listChatSessions } from '../api/chat'

const mockSession: ChatSession = {
  id: 'session_1', series_id: 'series_dexter', title: 'Chat',
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listChatSessions).mockResolvedValue([])
})

describe('useChatSessions', () => {
  it('starts idle when seriesId is null', () => {
    const { result } = renderHook(() => useChatSessions(null))
    expect(result.current.status).toBe('idle')
    expect(result.current.sessions).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('starts loading when seriesId is set', () => {
    const { result } = renderHook(() => useChatSessions('series_dexter'))
    expect(result.current.status).toBe('loading')
  })

  it('transitions to success with the fetched sessions', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([mockSession])

    const { result } = renderHook(() => useChatSessions('series_dexter'))

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.sessions).toEqual([mockSession])
    expect(result.current.error).toBeNull()
  })

  it('transitions to error on fetch failure', async () => {
    vi.mocked(listChatSessions).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useChatSessions('series_dexter'))

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error?.message).toBe('Request failed.')
    expect(result.current.sessions).toEqual([])
  })

  it('refetches when seriesId changes', async () => {
    vi.mocked(listChatSessions)
      .mockResolvedValueOnce([mockSession])
      .mockResolvedValueOnce([{ ...mockSession, id: 'session_2' }])

    const { result, rerender } = renderHook(({ sid }) => useChatSessions(sid), {
      initialProps: { sid: 'series_dexter' },
    })

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.sessions).toEqual([mockSession])

    rerender({ sid: 'series_other' })
    expect(result.current.status).toBe('loading')

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.sessions).toEqual([{ ...mockSession, id: 'session_2' }])
    expect(listChatSessions).toHaveBeenCalledTimes(2)
  })

  it('refetch() re-fetches without resetting to loading', async () => {
    vi.mocked(listChatSessions)
      .mockResolvedValueOnce([mockSession])
      .mockResolvedValueOnce([{ ...mockSession, id: 'session_2' }])

    const { result } = renderHook(() => useChatSessions('series_dexter'))

    await waitFor(() => expect(result.current.status).toBe('success'))

    result.current.refetch()

    await waitFor(() => expect(result.current.sessions).toEqual([{ ...mockSession, id: 'session_2' }]))
  })
})
