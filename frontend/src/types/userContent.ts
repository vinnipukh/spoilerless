// Mirrors spoilerless/app/domain/user_content.py field-for-field

// CustomNodeType is defined in lib/nodeTypes.ts (single registry with
// NODE_TYPES + ALLOWED_NODE_TYPES, PROB-09 #81) and re-exported here so
// existing importers keep `types/userContent` as their entry point.
import type { CustomNodeType } from '../lib/nodeTypes'
export type { CustomNodeType } from '../lib/nodeTypes'
import type { NoteTargetType } from './changeSet'
export type { NoteTargetType } from './changeSet'

export type NoteResponse = {
  id: string
  series_id: string
  target_type: NoteTargetType
  target_id: string
  content: string
  origin: string
  visible_from_order: number
  created_at: string
  updated_at: string
}

export type NoteCreate = {
  target_type: NoteTargetType
  target_id: string
  content: string
}

export type NoteUpdate = {
  content: string
}

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
