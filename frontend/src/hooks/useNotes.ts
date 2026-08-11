import { useCallback } from 'react'
import {
  getNotes, createNote as apiCreateNote,
  updateNote as apiUpdateNote, deleteNote as apiDeleteNote,
} from '../api/userContent'
import type { NoteResponse, NoteCreate, NoteUpdate } from '../types/userContent'
import { useFetchState } from './useFetchState'

type Props = {
  seriesId: string | null
  visibleUntilOrder: number | null
  targetType?: string
  targetId?: string
}

export function useNotes({ seriesId, visibleUntilOrder, targetType, targetId }: Props) {
  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${targetType ?? ''}:${targetId ?? ''}`
  const enabled = Boolean(seriesId && visibleUntilOrder != null)

  const { refetch, ...state } = useFetchState<NoteResponse[]>(
    key,
    enabled,
    () => getNotes(seriesId!, visibleUntilOrder!, targetType, targetId),
  )

  const createNote = useCallback(async (body: NoteCreate): Promise<NoteResponse> => {
    if (!seriesId) throw new Error('No series selected')
    const result = await apiCreateNote(seriesId, body)
    refetch()
    return result
  }, [seriesId, refetch])

  const updateNote = useCallback(async (noteId: string, body: NoteUpdate): Promise<NoteResponse> => {
    if (!seriesId) throw new Error('No series selected')
    const result = await apiUpdateNote(seriesId, noteId, body)
    refetch()
    return result
  }, [seriesId, refetch])

  const deleteNote = useCallback(async (noteId: string): Promise<void> => {
    if (!seriesId) throw new Error('No series selected')
    await apiDeleteNote(seriesId, noteId)
    refetch()
  }, [seriesId, refetch])

  return { ...state, createNote, updateNote, deleteNote, refetch }
}
