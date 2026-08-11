import { apiFetch } from './client'
import type {
  NoteResponse, NoteCreate, NoteUpdate,
  CustomNodeCreate, CustomNodeResponse,
  CustomRelationshipCreate, CustomRelationshipResponse,
} from '../types/userContent'

// ── Notes ──

export function getNotes(
  seriesId: string,
  visibleUntilOrder: number,
  targetType?: string,
  targetId?: string,
): Promise<NoteResponse[]> {
  let url = `/api/series/${seriesId}/notes?visible_until_order=${visibleUntilOrder}`
  if (targetType && targetId) {
    url += `&target_type=${encodeURIComponent(targetType)}&target_id=${encodeURIComponent(targetId)}`
  }
  return apiFetch(url)
}

export function createNote(seriesId: string, body: NoteCreate): Promise<NoteResponse> {
  return apiFetch(`/api/series/${seriesId}/notes`, {
    method: 'POST',
    body,
  })
}

export function updateNote(seriesId: string, noteId: string, body: NoteUpdate): Promise<NoteResponse> {
  return apiFetch(`/api/series/${seriesId}/notes/${encodeURIComponent(noteId)}`, {
    method: 'PATCH',
    body,
  })
}

export function deleteNote(seriesId: string, noteId: string): Promise<void> {
  return apiFetch(`/api/series/${seriesId}/notes/${encodeURIComponent(noteId)}`, {
    method: 'DELETE',
  })
}

// ── Custom Nodes ──

export function createCustomNode(seriesId: string, body: CustomNodeCreate): Promise<CustomNodeResponse> {
  return apiFetch(`/api/series/${seriesId}/custom-nodes`, {
    method: 'POST',
    body,
  })
}

// ── Custom Relationships ──

export function createCustomRelationship(
  seriesId: string,
  body: CustomRelationshipCreate,
): Promise<CustomRelationshipResponse> {
  return apiFetch(`/api/series/${seriesId}/custom-relationships`, {
    method: 'POST',
    body,
  })
}
