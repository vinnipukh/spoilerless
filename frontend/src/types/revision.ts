// Mirrors backend/app/domain/revision.py RevisionAction + RevisionResponse

export type RevisionAction = 'Created' | 'Updated' | 'Deleted' | 'Reverted'

export type RevisionResponse = {
  id: string
  series_id: string
  resource_type: string
  resource_id: string
  action: RevisionAction
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  created_at: string  // ISO 8601 datetime
  visible_from_order: number
}
