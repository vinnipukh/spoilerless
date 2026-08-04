// Mirrors spoilerless/app/domain/user_content.py field-for-field

export type NoteResponse = {
  id: string
  series_id: string
  target_type: 'Character' | 'Claim'
  target_id: string
  content: string
  origin: string
  visible_from_order: number
  created_at: string
  updated_at: string
}

export type NoteCreate = {
  target_type: 'Character' | 'Claim'
  target_id: string
  content: string
}

export type NoteUpdate = {
  content: string
}

export type CustomNodeType = 'Character' | 'Event' | 'Location' | 'Organization' | 'Object'

export type CustomNodeCreate = {
  node_type: CustomNodeType
  label: string
  episode_id: string
}

export type CustomNodeResponse = {
  id: string
  series_id: string
  label: string
  node_type: string
  episode_id: string
  visible_from_order: number
  origin: string
  created_at: string
  updated_at: string
}

export type CustomNodeUpdate = {
  label: string
}

export type CustomRelationshipCreate = {
  source_id: string
  target_id: string
  predicate: string
  episode_id: string
}

export type CustomRelationshipUpdate = {
  predicate: string
}

export type CustomRelationshipResponse = {
  id: string
  series_id: string
  source: string
  target: string
  type: string
  visible_from_order: number
  origin: string
  episode_id: string
  created_at: string
  updated_at: string
}
