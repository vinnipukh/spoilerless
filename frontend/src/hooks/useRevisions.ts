import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getRevisions } from '../api/revisions'
import type { RevisionResponse } from '../types/revision'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: RevisionResponse[] }

type Props = {
  seriesId: string | null
  visibleUntilOrder: number | null
  resourceType?: string
  resourceId?: string
}

export function useRevisions({ seriesId, visibleUntilOrder, resourceType, resourceId }: Props) {
  const [state, setState] = useState<State>(() =>
    seriesId && visibleUntilOrder != null ? { status: 'loading' } : { status: 'idle' },
  )

  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${resourceType ?? ''}:${resourceId ?? ''}`
  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setState(seriesId && visibleUntilOrder != null ? { status: 'loading' } : { status: 'idle' })
  }

  const fetchKeyRef = useRef(key)
  fetchKeyRef.current = key

  const fetchRevisions = useCallback(() => {
    if (!seriesId || visibleUntilOrder == null) return
    getRevisions(seriesId, visibleUntilOrder, resourceType, resourceId)
      .then((data) => {
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
  }, [seriesId, visibleUntilOrder, resourceType, resourceId, key])

  useEffect(() => {
    if (!seriesId || visibleUntilOrder == null) return
    fetchRevisions()
  }, [fetchRevisions, seriesId, visibleUntilOrder])

  return { ...state, refetch: fetchRevisions }
}
