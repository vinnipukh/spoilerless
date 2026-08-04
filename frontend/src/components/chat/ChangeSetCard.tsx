import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Lock, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CitationChip } from './CitationChip'
import { confirmChangeSet, rejectChangeSet } from '../../api/changeSet'
import { ApiError } from '../../api/client'
import type { ChangeSet, ChangeSetOperation, ChangeSetStatus } from '../../types/changeSet'

// The propose-time preview + Confirm/Reject card (06-UI-SPEC.md "Proposed-
// ChangeSet card") — the ONE UI surface in this phase that ever calls
// confirmChangeSet/rejectChangeSet (T-06-05: no other UI event is wired to
// either function). A chat message is never treated as confirmation.

type Props = {
  changeSet: ChangeSet
  seriesId: string
  onApplied?: (changeSet: ChangeSet) => void
}

// A local-only UI state layered on top of the backend's own `ChangeSetStatus`
// — `'stale'` has no backend status value (RAG-14's staleness is a 409
// `changeset_stale` error at confirm-time, not a status the ChangeSet record
// itself ever carries), so it is tracked as a distinct local state that
// replaces the Confirm/Reject controls with the documented "no longer
// valid... ask again" banner instead of a generic error.
type LocalStatus = ChangeSetStatus | 'stale'

const DELETE_OPERATION_TYPES: ReadonlySet<ChangeSetOperation['operation_type']> = new Set([
  'delete_node',
  'delete_relationship',
  'delete_claim',
  'delete_note',
])

// Backend `_override_note_content()` (spoilerless/app/services/change_set.py)
// always emits this exact phrase when a direct canonical/candidate edit is
// transparently substituted with a create_note override proposal (06-05,
// RAG-13) — this is the only structural signal the frontend has for "this
// create_note is a protection substitution," since ChangeSetResponse carries
// no dedicated boolean flag for it.
const PROTECTED_OVERRIDE_PATTERN = /-origin content and stays exactly as it is/

const ENTITY_LABELS: Record<ChangeSetOperation['operation_type'], string> = {
  create_node: 'Node',
  update_node: 'Node',
  delete_node: 'Node',
  create_relationship: 'Relationship',
  update_relationship: 'Relationship',
  delete_relationship: 'Relationship',
  create_claim: 'Claim',
  update_claim: 'Claim',
  delete_claim: 'Claim',
  attach_evidence: 'Evidence',
  create_note: 'Note',
  update_note: 'Note',
  delete_note: 'Note',
}

function verbFor(operationType: ChangeSetOperation['operation_type']): string {
  if (operationType === 'attach_evidence') return 'Attach'
  if (operationType.startsWith('create_')) return 'Create'
  if (operationType.startsWith('update_')) return 'Update'
  return 'Delete'
}

// The identifying "label" shown on the operation's summary line. Most
// operation types only ever carry an existing resource's stable ID (no
// human-readable label is available client-side without a graph lookup this
// card doesn't have) — `create_node` is the sole exception, since it's the
// only operation that carries a human label field at all.
function labelFor(op: ChangeSetOperation): string {
  switch (op.operation_type) {
    case 'create_node':
      return op.label
    case 'update_node':
    case 'delete_node':
      return op.node_id
    case 'update_relationship':
    case 'delete_relationship':
      return op.relationship_id
    case 'create_claim':
      return `${op.subject_id} → ${op.predicate} → ${op.object_id}`
    case 'update_claim':
    case 'delete_claim':
    case 'attach_evidence':
      return op.claim_id
    case 'create_note':
      return op.target_id
    case 'update_note':
    case 'delete_note':
      return op.note_id
    case 'create_relationship':
      return `${op.source_id} → ${op.relationship_type} → ${op.target_id}`
  }
}

// "{Create/Update/Delete} {entity type}: {label}" (06-UI-SPEC.md Copywriting
// Contract) — `create_relationship` is a documented, deliberate exception
// ("Add relationship: ..."), matching the UI-SPEC's own worked example
// exactly rather than the generic template. `create_node` uses the
// operation's own `node_type` (e.g. "Create Location: Rita's House" per the
// UI-SPEC's example) rather than the generic "Node" fallback.
function summaryLineFor(op: ChangeSetOperation): string {
  if (op.operation_type === 'create_relationship') {
    return `Add relationship: ${labelFor(op)}`
  }
  const entityType = op.operation_type === 'create_node' ? op.node_type : ENTITY_LABELS[op.operation_type]
  return `${verbFor(op.operation_type)} ${entityType}: ${labelFor(op)}`
}

type FieldChange = { field: string; after: string }

// Before/After rows are only rendered for update-type operations. The
// backend's `ChangeSetOperation` payload never carries a "before" snapshot
// value (confirmed against spoilerless/app/domain/change_set.py) — only the
// proposed *new* value is ever present — so "Before" is honestly rendered as
// "Not shown" rather than fabricating a prior value this card was never
// given.
function changedFieldsFor(op: ChangeSetOperation): FieldChange[] {
  switch (op.operation_type) {
    case 'update_node': {
      const fields: FieldChange[] = []
      if (op.label != null) fields.push({ field: 'Label', after: op.label })
      if (op.properties?.description != null) {
        fields.push({ field: 'Description', after: op.properties.description })
      }
      return fields
    }
    case 'update_relationship': {
      const fields: FieldChange[] = []
      if (op.relationship_type != null) fields.push({ field: 'Type', after: op.relationship_type })
      if (op.properties?.description != null) {
        fields.push({ field: 'Description', after: op.properties.description })
      }
      return fields
    }
    case 'update_claim': {
      const fields: FieldChange[] = []
      if (op.predicate != null) fields.push({ field: 'Predicate', after: op.predicate })
      if (op.confidence_level != null) fields.push({ field: 'Confidence', after: op.confidence_level })
      if (op.properties?.description != null) {
        fields.push({ field: 'Description', after: op.properties.description })
      }
      return fields
    }
    default:
      return []
  }
}

type AffectedRef = { id: string; kind: string }

// The affected-graph-elements list — every operation's already-existing
// target resource (create_node/create_claim carry no persisted id yet at
// propose time, so they contribute nothing here).
function affectedRefsFor(operations: ChangeSetOperation[]): AffectedRef[] {
  const refs: AffectedRef[] = []
  for (const op of operations) {
    switch (op.operation_type) {
      case 'update_node':
      case 'delete_node':
        refs.push({ id: op.node_id, kind: 'Node' })
        break
      case 'create_relationship':
        refs.push({ id: op.source_id, kind: 'Node' }, { id: op.target_id, kind: 'Node' })
        break
      case 'update_relationship':
      case 'delete_relationship':
        refs.push({ id: op.relationship_id, kind: 'Relationship' })
        break
      case 'update_claim':
      case 'delete_claim':
      case 'attach_evidence':
        refs.push({ id: op.claim_id, kind: 'Claim' })
        break
      case 'create_note':
        refs.push({ id: op.target_id, kind: op.target_type })
        break
      case 'update_note':
      case 'delete_note':
        refs.push({ id: op.note_id, kind: 'Note' })
        break
      default:
        break
    }
  }
  return refs
}

// Warnings are rendered defensively via an optional extension — the current
// backend ChangeSetResponse (06-05/06-06) has no `warnings` field at all, so
// this always resolves to an empty array today. Implemented ahead of time so
// the row is ready the moment the backend adds one, per 06-UI-SPEC.md's
// documented (if not yet backend-populated) "warnings row" structure.
function warningsFor(changeSet: ChangeSet): string[] {
  return (changeSet as ChangeSet & { warnings?: string[] }).warnings ?? []
}

function protectedOverrideOperation(operations: ChangeSetOperation[]) {
  return operations.find(
    (op) => op.operation_type === 'create_note' && PROTECTED_OVERRIDE_PATTERN.test(op.content),
  )
}

function StatusBadge({ status }: { status: ChangeSetStatus }) {
  if (status === 'applied') {
    return (
      <span className="inline-flex w-fit items-center gap-1.5 rounded-md bg-success/10 px-2 py-1 text-xs font-semibold text-success">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        Applied
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex w-fit items-center gap-1.5 rounded-md bg-destructive/10 px-2 py-1 text-xs font-semibold text-destructive">
        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
        Failed
      </span>
    )
  }
  if (status === 'rejected' || status === 'reverted') {
    return (
      <span className="inline-flex w-fit items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground">
        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
        {status === 'reverted' ? 'Reverted' : 'Rejected'}
      </span>
    )
  }
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-md bg-warning/10 px-2 py-1 text-xs font-semibold text-warning">
      Awaiting confirmation
    </span>
  )
}

export function ChangeSetCard({ changeSet, seriesId, onApplied }: Props) {
  const [current, setCurrent] = useState<ChangeSet>(changeSet)
  const [localStatus, setLocalStatus] = useState<LocalStatus>(changeSet.status)
  const [submitting, setSubmitting] = useState(false)

  // Reset local state if a genuinely different ChangeSet arrives (adjust
  // state during render, comparing a state copy of the previous id — the
  // codebase's established pattern, 06-PATTERNS.md — rather than an
  // effect + setState).
  const [prevId, setPrevId] = useState(changeSet.id)
  if (prevId !== changeSet.id) {
    setPrevId(changeSet.id)
    setCurrent(changeSet)
    setLocalStatus(changeSet.status)
  }

  async function handleConfirm() {
    setSubmitting(true)
    try {
      const updated = await confirmChangeSet(seriesId, current.id)
      setCurrent(updated)
      setLocalStatus(updated.status)
      if (updated.status === 'applied') onApplied?.(updated)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'changeset_stale') {
        setLocalStatus('stale')
      }
      // Any other error leaves the card awaiting confirmation so the user
      // can retry — no dedicated error banner is specified for this case.
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReject() {
    setSubmitting(true)
    try {
      const updated = await rejectChangeSet(seriesId, current.id)
      setCurrent(updated)
      setLocalStatus(updated.status)
    } catch {
      // Leave the card awaiting confirmation so the user can retry.
    } finally {
      setSubmitting(false)
    }
  }

  const operationCount = current.operations.length
  const title = operationCount === 1 ? 'Proposed change' : `Proposed changes (${operationCount})`
  const deleteCount = current.operations.filter((op) => DELETE_OPERATION_TYPES.has(op.operation_type)).length
  const isDestructive = deleteCount > 0
  const warnings = warningsFor(current)
  const affectedRefs = affectedRefsFor(current.operations)
  const protectedOp = protectedOverrideOperation(current.operations)
  const isAwaiting = localStatus === 'awaiting_confirmation' || localStatus === 'draft'

  return (
    <Card className="w-full max-w-[85%] border border-border bg-card">
      <CardHeader>
        <CardTitle className="font-heading text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {protectedOp && (
          <div className="flex flex-col gap-1">
            <span className="inline-flex w-fit items-center gap-1.5 border-l-2 border-destructive pl-2 text-xs font-semibold text-destructive">
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              Protected
            </span>
            <p className="text-xs text-muted-foreground">Propose a note instead</p>
          </div>
        )}

        <ul className="flex flex-col gap-2 text-sm">
          {current.operations.map((op, index) => (
            <li key={index} className="flex flex-col gap-1">
              <span className="whitespace-pre-wrap break-words">{summaryLineFor(op)}</span>
              {(op.operation_type === 'create_note' || op.operation_type === 'update_note') && (
                <p className="text-xs whitespace-pre-wrap break-words text-muted-foreground">{op.content}</p>
              )}
              {changedFieldsFor(op).map((change) => (
                <div
                  key={change.field}
                  className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground"
                >
                  <span className="font-semibold">{change.field}</span>
                  <span>
                    <span className="font-semibold">Before:</span> Not shown
                  </span>
                  <span aria-hidden="true">→</span>
                  <span>
                    <span className="font-semibold">After:</span> {change.after}
                  </span>
                </div>
              ))}
            </li>
          ))}
        </ul>

        {affectedRefs.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {affectedRefs.map((ref, index) => (
              <CitationChip
                key={`${ref.kind}-${ref.id}-${index}`}
                citation={{
                  claim_id: null,
                  evidence_id: null,
                  source_id: null,
                  source_label: ref.id,
                  source_type: ref.kind,
                  episode_code: ref.id,
                  locator: '',
                  excerpt: null,
                  related_node_ids: [],
                  related_edge_ids: [],
                }}
              />
            ))}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="flex flex-col gap-1">
            {warnings.map((warning, index) => (
              <div key={index} className="flex items-start gap-2 text-xs text-warning">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>{warning}</span>
              </div>
            ))}
          </div>
        )}

        {isDestructive && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>
              This will permanently delete {deleteCount} graph element{deleteCount === 1 ? '' : 's'}.
            </span>
          </div>
        )}

        {localStatus === 'stale' && (
          <div className="rounded-md border border-warning/30 bg-warning/5 p-2 text-xs text-foreground">
            This proposal is no longer valid because your watch progress changed. Ask again to get an
            updated proposal.
          </div>
        )}

        {isAwaiting && (
          <div className="flex items-center justify-end gap-2">
            <Button variant="outline" onClick={handleReject} disabled={submitting}>
              Reject changes
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={submitting}
              className={
                isDestructive ? 'bg-destructive text-destructive-foreground hover:bg-destructive/80' : ''
              }
            >
              Confirm changes
            </Button>
          </div>
        )}

        {!isAwaiting && localStatus !== 'stale' && <StatusBadge status={localStatus as ChangeSetStatus} />}
      </CardContent>
    </Card>
  )
}
