// Hand-written chat/ChangeSet fixtures mirroring test/fixtures/graphResponse.ts's
// structure: exported fixture objects for every downstream frontend chat
// plan's (06-09..11) component tests to import, type-checked against
// types/chat.ts/types/changeSet.ts.

import type {
  ChatMessage,
  ChatSessionDetail,
  Citation,
  MessageResponseEnvelope,
} from '../../types/chat'
import type { ChangeSet, ChangeSetStatus } from '../../types/changeSet'

// ── Sessions ──

// An empty session — no messages yet (the "start chatting" empty state).
export const emptyChatSession: ChatSessionDetail = {
  session: {
    id: 'session_empty',
    series_id: 'series_dexter',
    title: 'New chat',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  messages: [],
}

const userMessage: ChatMessage = {
  id: 'message_user_1',
  role: 'user',
  content: 'Who is Dexter?',
  created_at: '2026-01-01T00:01:00Z',
  visible_until_order_snapshot: 1,
}

const assistantMessage: ChatMessage = {
  id: 'message_assistant_1',
  role: 'assistant',
  content: 'Dexter Morgan works at Miami Metro Police Department.',
  created_at: '2026-01-01T00:01:05Z',
  visible_until_order_snapshot: 1,
}

// A session with exactly one visible user/assistant exchange.
export const chatSessionWithOneMessage: ChatSessionDetail = {
  session: {
    id: 'session_1',
    series_id: 'series_dexter',
    title: 'About Dexter',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:01:05Z',
  },
  messages: [userMessage, assistantMessage],
}

// ── Citations ──
//
// Claim/evidence citations use the same S01E01 fixture data as
// test/fixtures/graphResponse.ts (claim_1/evidence_1/source_1) — mirrors the
// claim-accent vs. evidence-accent citation-chip distinction DetailPanel.tsx
// already establishes (CLAIM_ACCENT_COLOR/EVIDENCE_ACCENT_COLOR), though
// this fixture module only needs the underlying data shape, not the colors.

export const claimCitation: Citation = {
  claim_id: 'claim_1',
  evidence_id: null,
  source_id: 'source_1',
  source_label: 'S01E01 script',
  source_type: 'script',
  episode_code: 'S01E01',
  locator: '00:03:12',
  excerpt: 'Dexter works at Miami Metro.',
  related_node_ids: ['char_dexter_morgan', 'loc_miami_metro'],
  related_edge_ids: ['edge_2'],
}

export const evidenceCitation: Citation = {
  claim_id: null,
  evidence_id: 'evidence_1',
  source_id: 'source_1',
  source_label: 'S01E01 script',
  source_type: 'script',
  episode_code: 'S01E01',
  locator: '00:03:12',
  excerpt: 'Dexter narrates his ritual before the kill.',
  related_node_ids: ['char_dexter_morgan'],
  related_edge_ids: [],
}

// A message envelope whose only citation is a claim citation.
export const messageEnvelopeWithClaimCitation: MessageResponseEnvelope = {
  message: assistantMessage,
  citations: [claimCitation],
  graph_focus: { node_ids: ['char_dexter_morgan', 'loc_miami_metro'], edge_ids: ['edge_2'] },
  proposed_change_set: null,
}

// A message envelope whose only citation is an evidence citation.
export const messageEnvelopeWithEvidenceCitation: MessageResponseEnvelope = {
  message: assistantMessage,
  citations: [evidenceCitation],
  graph_focus: { node_ids: ['char_dexter_morgan'], edge_ids: [] },
  proposed_change_set: null,
}

// ── ChangeSets (one per status) ──

function makeChangeSet(status: ChangeSetStatus): ChangeSet {
  return {
    id: `change_set_${status}`,
    user_id: 'user_1',
    series_id: 'series_dexter',
    chat_session_id: 'session_1',
    status,
    visible_until_order_snapshot: 1,
    summary: 'Add a personal note on Dexter Morgan',
    operations: [
      {
        operation_type: 'create_note',
        target_type: 'Character',
        target_id: 'char_dexter_morgan',
        content: 'This is likely foreshadowing.',
      },
    ],
    created_at: '2026-01-01T00:01:05Z',
    confirmed_at: status === 'draft' || status === 'awaiting_confirmation' ? null : '2026-01-01T00:02:00Z',
    applied_at: status === 'applied' || status === 'reverted' ? '2026-01-01T00:02:05Z' : null,
    revision_id: status === 'applied' || status === 'reverted' ? 'revision_1' : null,
    idempotency_key: null,
  }
}

export const proposedChangeSetAwaitingConfirmation: ChangeSet = makeChangeSet('awaiting_confirmation')
export const proposedChangeSetApplied: ChangeSet = makeChangeSet('applied')
export const proposedChangeSetRejected: ChangeSet = makeChangeSet('rejected')
export const proposedChangeSetFailed: ChangeSet = makeChangeSet('failed')
export const proposedChangeSetReverted: ChangeSet = makeChangeSet('reverted')

// A message envelope carrying a proposed (awaiting_confirmation) ChangeSet —
// the shape ChatPanel/ChangeSetCard (06-09..11) render for a graph-editing
// proposal.
export const messageEnvelopeWithProposedChangeSet: MessageResponseEnvelope = {
  message: assistantMessage,
  citations: [],
  graph_focus: { node_ids: [], edge_ids: [] },
  proposed_change_set: proposedChangeSetAwaitingConfirmation,
}

// ── Streaming-in-progress state ──
//
// Mirrors the `{status: 'streaming', streamingText}` shape useChatMessages.ts
// returns mid-stream, before the final `done` event has arrived.
export const streamingInProgressState = {
  status: 'streaming' as const,
  streamingText: 'Dexter Morgan work',
}
