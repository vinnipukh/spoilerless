import { getRevisions } from '../api/revisions'
import type { RevisionResponse } from '../types/revision'
import { useFetchState } from './useFetchState'

type Props = {
  seriesId: string | null
  visibleUntilOrder: number | null
  resourceType?: string
  resourceId?: string
}

export function useRevisions({ seriesId, visibleUntilOrder, resourceType, resourceId }: Props) {
  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${resourceType ?? ''}:${resourceId ?? ''}`
  const enabled = Boolean(seriesId && visibleUntilOrder != null)

  return useFetchState<RevisionResponse[]>(
    key,
    enabled,
    () => getRevisions(seriesId!, visibleUntilOrder!, resourceType, resourceId),
  )
}
