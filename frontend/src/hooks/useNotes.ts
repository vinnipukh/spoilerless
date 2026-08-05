import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import {
  getNotes, createNote as apiCreateNote,
  updateNote as apiUpdateNote, deleteNote as apiDeleteNote,
} from '../api/userContent'
import type { NoteResponse, NoteCreate, NoteUpdate } from '../types/userContent'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: NoteResponse[] }

type Props = {
  seriesId: string | null
  visibleUntilOrder: number | null
  targetType?: string
  targetId?: string
}

export function useNotes({ seriesId, visibleUntilOrder, targetType, targetId }: Props) {
  const [state, setState] = useState<State>(() =>
    seriesId && visibleUntilOrder != null ? { status: 'loading' } : { status: 'idle' },
  )

  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${targetType ?? ''}:${targetId ?? ''}`
  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setState(seriesId && visibleUntilOrder != null ? { status: 'loading' } : { status: 'idle' })
  }

  const fetchKeyRef = useRef(key)
  // Sync the ref from an effect, never from the render body: a render-time
  // write is a stale-ref correctness bug under React 19 double-render
  // (react-hooks/refs). Declared BEFORE the fetch effect below so the ref is
  // updated before a key-change fetch fires.
  useEffect(() => {
    fetchKeyRef.current = key
  }, [key])

  const fetchNotes = useCallback(() => {
    if (!seriesId || visibleUntilOrder == null) return
    getNotes(seriesId, visibleUntilOrder, targetType, targetId)
      .then((data) => {
        // Only apply if key hasn't changed since fetch started
        if (fetchKeyRef.current === key) {
          setState({ status: 'success', data })
        }
      })
      .catch((error) => {
        if (fetchKeyRef.current === key) {
          setState({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
  }, [seriesId, visibleUntilOrder, targetType, targetId, key])

  useEffect(() => {
    if (!seriesId || visibleUntilOrder == null) return
    fetchNotes()
  }, [fetchNotes, seriesId, visibleUntilOrder])

  const createNote = useCallback(async (body: NoteCreate): Promise<NoteResponse> => {
    if (!seriesId) throw new Error('No series selected')
    const result = await apiCreateNote(seriesId, body)
    fetchNotes()
    return result
  }, [seriesId, fetchNotes])

  const updateNote = useCallback(async (noteId: string, body: NoteUpdate): Promise<NoteResponse> => {
    if (!seriesId) throw new Error('No series selected')
    const result = await apiUpdateNote(seriesId, noteId, body)
    fetchNotes()
    return result
  }, [seriesId, fetchNotes])

  const deleteNote = useCallback(async (noteId: string): Promise<void> => {
    if (!seriesId) throw new Error('No series selected')
    await apiDeleteNote(seriesId, noteId)
    fetchNotes()
  }, [seriesId, fetchNotes])

  return { ...state, createNote, updateNote, deleteNote, refetch: fetchNotes }
}
