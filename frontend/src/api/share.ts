import { apiFetch } from './client'
import type { GraphResponse } from '../types/graph'
import type { ShareTokenCreateResponse, ShareTokenItem } from '../types/share'

export async function createShareLink(
  seriesId: string,
  visibleUntilOrder: number
): Promise<ShareTokenCreateResponse> {
  return apiFetch<ShareTokenCreateResponse>('/api/share', {
    method: 'POST',
    body: {
      series_id: seriesId,
      visible_until_order: visibleUntilOrder,
    },
  })
}

export async function getShareGraph(token: string): Promise<GraphResponse> {
  return apiFetch<GraphResponse>(`/api/share/${token}/graph`)
}

export async function listShareLinks(): Promise<ShareTokenItem[]> {
  return apiFetch<ShareTokenItem[]>('/api/share')
}

export async function revokeShareLink(token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/share/${token}`, {
    method: 'DELETE',
  })
}
