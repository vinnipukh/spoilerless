// Mirrors spoilerless/app/domain/change_set.py field-for-field.
//
// `ChangeSetOperation` is a discriminated union on `operation_type`, matching
// the backend's closed 13-type Pydantic discriminated union exactly — no
// operation type is ever declared here beyond the 13 the backend accepts,
// and no operation ever carries `origin`/`visible_from_order`/`id` as a
// settable field (those stay server-derived on every mutation path).

export type ChangeSetStatus =
  | 'draft'
  | 'awaiting_confirmation'
  | 'applied'
  | 'rejected'
  | 'failed'
  | 'reverted'

export type ClaimType =
  | 'explicit_fact'
  | 'observed_event'
  | 'inferred_state'
  | 'external_interpretation'
  | 'user_authored'

export type ConfidenceLevel = 'low' | 'medium' | 'high' | 'verified'

// Mirrors backend NoteTargetType (spoilerless/app/domain/user_content.py):
// the five custom node labels plus Claim. Extending this union keeps note
// creation on Location/Event/Organization/Object nodes type-safe end to end.
export type NoteTargetType =
  | 'Character'
  | 'Event'
  | 'Location'
  | 'Organization'
  | 'Object'
  | 'Claim'

// Only `description` is ever accepted inside an operation's `properties`
// dict — matches backend `ALLOWED_OPERATION_PROPERTY_KEYS`.
export type OperationProperties = { description?: string } | null

export type CreateNodeOperation = {
  operation_type: 'create_node'
  node_type: string
  label: string
  episode_id: string
  properties?: OperationProperties
}

export type UpdateNodeOperation = {
  operation_type: 'update_node'
  node_id: string
  label?: string | null
  properties?: OperationProperties
}

export type DeleteNodeOperation = {
  operation_type: 'delete_node'
  node_id: string
}

export type CreateRelationshipOperation = {
  operation_type: 'create_relationship'
  source_id: string
  target_id: string
  relationship_type: string
  episode_id: string
  properties?: OperationProperties
}

export type UpdateRelationshipOperation = {
  operation_type: 'update_relationship'
  relationship_id: string
  relationship_type?: string | null
  properties?: OperationProperties
}

export type DeleteRelationshipOperation = {
  operation_type: 'delete_relationship'
  relationship_id: string
}

export type CreateClaimOperation = {
  operation_type: 'create_claim'
  subject_id: string
  object_id: string
  predicate: string
  claim_type: ClaimType
  confidence_level: ConfidenceLevel
  episode_id: string
  properties?: OperationProperties
}

export type UpdateClaimOperation = {
  operation_type: 'update_claim'
  claim_id: string
  predicate?: string | null
  confidence_level?: ConfidenceLevel | null
  properties?: OperationProperties
}

export type DeleteClaimOperation = {
  operation_type: 'delete_claim'
  claim_id: string
}

export type AttachEvidenceOperation = {
  operation_type: 'attach_evidence'
  claim_id: string
  source_id: string
  episode_id: string
  locator: string
  text: string
}

export type CreateNoteOperation = {
  operation_type: 'create_note'
  target_type: NoteTargetType
  target_id: string
  content: string
}

export type UpdateNoteOperation = {
  operation_type: 'update_note'
  note_id: string
  content: string
}

export type DeleteNoteOperation = {
  operation_type: 'delete_note'
  note_id: string
}

// The full closed set of 13 operation types — matches backend
// `ChangeSetOperation` Annotated[Union[...], Field(discriminator=...)]
// exactly. An `operation_type` outside this set does not type-check here,
// mirroring the backend's discriminator-level rejection.
export type ChangeSetOperation =
  | CreateNodeOperation
  | UpdateNodeOperation
  | DeleteNodeOperation
  | CreateRelationshipOperation
  | UpdateRelationshipOperation
  | DeleteRelationshipOperation
  | CreateClaimOperation
  | UpdateClaimOperation
  | DeleteClaimOperation
  | AttachEvidenceOperation
  | CreateNoteOperation
  | UpdateNoteOperation
  | DeleteNoteOperation

export type ChangeSetCreateRequest = {
  series_id: string
  chat_session_id: string
  summary: string
  operations: ChangeSetOperation[]
}

export type ChangeSet = {
  id: string
  user_id: string
  series_id: string
  chat_session_id: string
  status: ChangeSetStatus
  visible_until_order_snapshot: number
  summary: string
  operations: ChangeSetOperation[]
  created_at: string
  confirmed_at: string | null
  applied_at: string | null
  revision_id: string | null
  // THERMO-P1-05: revert-time Revision id (PROB-27, #51) — set when the
  // ChangeSet is reverted, absent/null otherwise. Optional so locally built
  // ChangeSet literals (tests/fixtures) pre-dating the field stay assignable.
  revert_revision_id?: string | null
  idempotency_key: string | null
}

// One operation → already-existing-target-ids mapping, shared by every
// consumer that needs the graph elements an operation touches
// (ChangeSetCard's affected-elements list, App's post-apply focus
// highlight — was two hand-rolled switches in two files, PROB-09 #81).
// `create_node`/`create_claim` carry no persisted id at propose/apply
// time, so they contribute nothing; `create_relationship` contributes its
// endpoint nodes (the relationship id itself is not persisted until apply).
export type OperationRef = { id: string; kind: string }

export function operationTargetRefs(op: ChangeSetOperation): OperationRef[] {
  switch (op.operation_type) {
    case 'update_node':
    case 'delete_node':
      return [{ id: op.node_id, kind: 'Node' }]
    case 'create_relationship':
      return [
        { id: op.source_id, kind: 'Node' },
        { id: op.target_id, kind: 'Node' },
      ]
    case 'update_relationship':
    case 'delete_relationship':
      return [{ id: op.relationship_id, kind: 'Relationship' }]
    case 'update_claim':
    case 'delete_claim':
    case 'attach_evidence':
      return [{ id: op.claim_id, kind: 'Claim' }]
    case 'create_note':
      return [{ id: op.target_id, kind: op.target_type }]
    case 'update_note':
    case 'delete_note':
      return [{ id: op.note_id, kind: 'Note' }]
    default:
      return []
  }
}
