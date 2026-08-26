// Mirrors spoilerless/app/domain/chat.py field-for-field. The public response
// shape is `{message, citations, graph_focus, proposed_change_set}` exactly
// as documented in 06-CONTEXT.md's "Suggested public response shape" and
// implemented by MessageResponseEnvelope — no field is renamed or dropped.
//
// T-06-12 (threat register): these types only expose the public envelope
// shape — no field for raw tool calls, chain-of-thought, or provider
// diagnostics is declared here, matching the backend's StrictModel which
// never emits them either.

import type { ChangeSet } from './changeSet'

export type Citation = {
  claim_id: string | null
  evidence_id: string | null
  source_id: string | null
  source_label: string
  source_type: string
  episode_code: string
  locator: string
  excerpt: string | null
  related_node_ids: string[]
  related_edge_ids: string[]
}

export type GraphFocus = {
  node_ids: string[]
  edge_ids: string[]
}

export type ChatMessage = {
  id: string
  role: string
  content: string
  created_at: string
  visible_until_order_snapshot: number
  // THERMO-P1-05: backend MessageStatus ('pending' | 'completed' | 'failed',
  // default 'completed'). Optional so locally-constructed optimistic messages
  // and cached envelopes predating PROB-13/#35 stay assignable.
  status?: 'pending' | 'completed' | 'failed'
}

export type ChatSession = {
  id: string
  series_id: string
  title: string
  created_at: string
  updated_at: string
}

export type ChatSessionDetail = {
  session: ChatSession
  messages: ChatMessage[]
}

// `proposed_change_set` is always `null` on the backend's current
// MessageResponseEnvelope (Stage 2 ChangeSet-proposal-from-chat wiring is
// not part of this plan), but is typed as `ChangeSet | null` here — not
// `null` alone — so later plans (06-09..11) that wire ChangeSet proposals
// into the chat response do not need a breaking type change.
export type MessageResponseEnvelope = {
  message: ChatMessage
  citations: Citation[]
  graph_focus: GraphFocus
  proposed_change_set: ChangeSet | null
}
