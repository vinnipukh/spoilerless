import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRef } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { graphResponseS01E01, graphResponseS01E03 } from './test/fixtures/graphResponse'
import {
  claimCitation,
  proposedChangeSetApplied,
  proposedChangeSetAwaitingConfirmation,
  protectedOverrideChangeSet,
} from './test/fixtures/chatFixtures'
import { useChatMessages } from './hooks/useChatMessages'
import type { SeriesResponse, EpisodeResponse } from './types/series'
import type { UserResponse } from './types/auth'
import type { Citation } from './types/chat'
import type { ChangeSet } from './types/changeSet'

// 06-10: citation-wiring tests (onShowInGraph/onOpenDetail -> App.tsx) mock
// useChatMessages directly rather than driving a real SSE turn end-to-end
// (already covered by CitationChip.test.tsx/MessageList.test.tsx at the
// props-firing level) — this only needs to prove the wiring from ChatPanel's
// rendered CitationChip up through DetailPanel into App.tsx's own
// graphFocus/selection state actually exists.
vi.mock('./hooks/useChatMessages', () => ({
  useChatMessages: vi.fn(),
}))

// 06-11: ChangeSetCard's Confirm/Reject handlers are the only UI path into
// the confirm/reject endpoints (T-06-05) — mock the api module so an App-level
// apply can be driven without a real POST, and assert the post-apply
// incremental-refresh wiring (graphState.refresh + setGraphFocus) fires.
vi.mock('./api/changeSet', () => ({
  confirmChangeSet: vi.fn(),
  rejectChangeSet: vi.fn(),
}))

import { confirmChangeSet } from './api/changeSet'

function defaultChatMessagesReturn() {
  return {
    status: 'idle' as const,
    messages: [],
    citations: [],
    graphFocus: { node_ids: [], edge_ids: [] },
    proposedChangeSet: null,
    sendMessage: vi.fn(),
    stop: vi.fn(),
  }
}

// react-cytoscapejs stub (same as before)
type FakeCollection = { addClass: (cls: string) => FakeCollection; removeClass: (cls: string) => FakeCollection; difference: (other: unknown) => FakeCollection; union: (other: unknown) => FakeCollection }
function makeFakeCollection(): FakeCollection {
  const c: FakeCollection = { addClass: () => c, removeClass: () => c, difference: () => c, union: () => c }
  return c
}

// 06-11: module-scoped counters the ChangeSet-apply tests read to prove the
// post-apply refresh neither remounts GraphCanvas (cy callback re-invoked)
// nor re-invokes the full layout (cy.layout re-called). Reset in beforeEach.
const graphStubHooks = vi.hoisted(() => ({ cyMounts: 0, layoutRuns: 0 }))

vi.mock('react-cytoscapejs', () => {
  type Handler = (evt: unknown) => void
  function CytoscapeComponentStub(props: { elements: Array<{ data: Record<string, unknown> }>; cy?: (cy: unknown) => void }) {
    const stateRef = useRef<{ handlers: Record<string, Handler[]>; fakeCy: { on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => void; elements: () => FakeCollection; container: () => null; layout: () => { run: () => void } } } | null>(null)
    if (!stateRef.current) {
      const handlers: Record<string, Handler[]> = {}
      const fakeCy = {
        on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => {
          const selector = typeof selectorOrHandler === 'string' ? selectorOrHandler : undefined
          const handler = (maybeHandler ?? selectorOrHandler) as Handler
          const key = selector ? `${event}:${selector}` : event
          handlers[key] = handlers[key] ?? []
          handlers[key].push(handler)
        },
        elements: () => makeFakeCollection(),
        container: () => null,
        // 06-11 spy: records whether the post-apply incremental refresh ever
        // re-invokes the full relayout path (it must not — only element-data
        // updates and the focus-driven fit are allowed).
        layout: () => {
          graphStubHooks.layoutRuns += 1
          return { run: () => {} }
        },
      }
      stateRef.current = { handlers, fakeCy }
    }
    const { handlers, fakeCy } = stateRef.current
    graphStubHooks.cyMounts += 1
    props.cy?.(fakeCy)
    return (
      <div data-testid="graph-canvas-stub">
        {props.elements.map((el) => {
          const isEdge = 'source' in el.data
          const key = isEdge ? 'tap:edge' : 'tap:node'
          const fakeTarget = {
            id: () => el.data.id as string,
            data: (field: string) => el.data[field],
            addClass: () => fakeTarget,
            removeClass: () => fakeTarget,
            closedNeighborhood: () => makeFakeCollection(),
            connectedNodes: () => makeFakeCollection(),
          }
          return (
            <button key={el.data.id as string} type="button" data-testid={`graph-element-${el.data.id}`}
              onClick={() => handlers[key]?.forEach((h) => h({ target: fakeTarget }))}>
              {el.data.label as string}
            </button>
          )
        })}
        <div data-testid="graph-canvas-background"
          onClick={() => handlers['tap']?.forEach((h) => h({ target: fakeCy }))} />
      </div>
    )
  }
  return { default: CytoscapeComponentStub }
})

const seriesFixture: SeriesResponse[] = [{ id: 'series_dexter', title: 'Dexter', slug: 'dexter' }]
const episodesFixture: EpisodeResponse[] = [
  { id: 'dexter_s01e01', series_id: 'series_dexter', season_number: 1, episode_number: 1, episode_order: 1, code: 'S01E01', title: 'Dexter', visible_from_order: 1 },
  { id: 'dexter_s01e02', series_id: 'series_dexter', season_number: 1, episode_number: 2, episode_order: 2, code: 'S01E02', title: 'Crocodile', visible_from_order: 2 },
  { id: 'dexter_s01e03', series_id: 'series_dexter', season_number: 1, episode_number: 3, episode_order: 3, code: 'S01E03', title: 'Popping Cherry', visible_from_order: 3 },
]

const mockUser: UserResponse = {
  user: { id: 'user:1', email: 'test@example.com', display_name: 'Test User', avatar_url: '', created_at: '2025-01-01T00:00:00+00:00', updated_at: '2025-01-01T00:00:00+00:00' },
}

function jsonResponse(data: unknown): Response {
  return { ok: true, json: async () => data } as Response
}

function notFoundResponse(): Response {
  return { ok: false, status: 401, json: async () => ({ detail: { code: 'AUTH_UNAUTHENTICATED', message: 'Unauthenticated' } }) } as Response
}

let currentAuthState: 'authenticated' | 'unauthenticated' = 'unauthenticated'

function fetchStub(input: RequestInfo | URL): Promise<Response> {
  const url = String(input)
  // Auth endpoints
  if (url === '/api/auth/me') {
    if (currentAuthState === 'authenticated') {
      return Promise.resolve(jsonResponse(mockUser))
    }
    return Promise.resolve(notFoundResponse())
  }
  if (url === '/api/auth/google') {
    return Promise.resolve(jsonResponse(mockUser))
  }
  if (url === '/api/auth/logout') {
    return Promise.resolve({ ok: true, status: 204, json: async () => undefined } as Response)
  }
  // App endpoints
  if (url === '/api/series') return Promise.resolve(jsonResponse(seriesFixture))
  if (url === '/api/series/series_dexter/episodes') return Promise.resolve(jsonResponse(episodesFixture))
  if (url.startsWith('/api/series/series_dexter/graph')) {
    // 06-10: routed by boundary order — most tests only ever confirm order 1
    // (graphResponseS01E01), but the progress-decrease-clears-stale-focus
    // tests need a real order-3-vs-order-1 node-set difference to exercise.
    if (url.includes('visible_until_order=3')) return Promise.resolve(jsonResponse(graphResponseS01E03))
    return Promise.resolve(jsonResponse(graphResponseS01E01))
  }
  // ChatPanel (mounted only once the panel switches to Chat mode) fetches
  // the session list on mount — an empty list keeps these App-level
  // integration tests focused on the mode-toggle wiring itself, not chat
  // session content (covered by ChatPanel.test.tsx/SessionPicker.test.tsx).
  if (url.startsWith('/api/series/series_dexter/chat/sessions')) {
    return Promise.resolve(jsonResponse([]))
  }
  return Promise.resolve(notFoundResponse())
}

function graphFetchCalls() {
  return vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes('/graph'))
}

beforeEach(() => {
  currentAuthState = 'unauthenticated'
  sessionStorage.clear()
  vi.stubGlobal('fetch', vi.fn(fetchStub))
  vi.mocked(useChatMessages).mockReturnValue(defaultChatMessagesReturn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows login screen when unauthenticated', async () => {
    render(<App />)

    // Should show the login page (title)
    expect(await screen.findByText('HD Graf Cehennemi')).toBeInTheDocument()
    expect(screen.getByText(/spoiler-safe graph browser/i)).toBeInTheDocument()
  })

  it('shows loading then transitions from login to graph when authenticated', async () => {
    // Start unauthenticated, then after a brief delay become authenticated
    currentAuthState = 'authenticated'

    render(<App />)

    // Should transition to the app - we need to wait for the auth check
    await waitFor(() => {
      // The app should load and show the graph area
      expect(screen.getByText('Nothing revealed yet')).toBeInTheDocument()
    })
  })

  it('shows empty state and fires no /graph request until series confirmed', async () => {
    currentAuthState = 'authenticated'

    render(<App />)

    expect(await screen.findByText('Nothing revealed yet')).toBeInTheDocument()
    expect(screen.getByText('Advance your watch progress to unlock the story.')).toBeInTheDocument()
    expect(graphFetchCalls()).toHaveLength(0)
  })

  it('runs select -> confirm -> fetch -> render -> inspect end-to-end', async () => {
    currentAuthState = 'authenticated'

    const user = userEvent.setup()
    render(<App />)

    // The user bar should show the authenticated user
    expect(await screen.findByText('Test User')).toBeInTheDocument()

    await user.click(await screen.findByRole('combobox', { name: 'Series' }))
    await user.click(await screen.findByRole('option', { name: 'Dexter' }))

    await user.click(await screen.findByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E01/ }))

    expect(await screen.findByText('Unlock S01E01?')).toBeInTheDocument()
    expect(graphFetchCalls()).toHaveLength(0)

    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))

    await waitFor(() => expect(graphFetchCalls()).toHaveLength(1))
    expect(graphFetchCalls()[0]?.[0]).toBe('/api/series/series_dexter/graph?visible_until_order=1')

    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
    // 06-09: DetailPanel's Sheet now defaults closed until either a node is
    // selected or chat is opened this session — it is no longer permanently
    // visible with the "Select a node..." placeholder the instant a graph
    // loads (the highest-risk, deliberate behavior change this phase makes).
    expect(screen.queryByText('Select a node to see details.')).not.toBeInTheDocument()

    await user.click(await screen.findByTestId('graph-element-char_dexter_morgan'))
    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
  })

  it('restores confirmed state from sessionStorage on mount without opening confirmation modal', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    render(<App />)

    await waitFor(() =>
      expect(graphFetchCalls().some(([url]) => url === '/api/series/series_dexter/graph?visible_until_order=1')).toBe(true),
    )
    expect(screen.queryByText(/Unlock S01E0/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Rewatch S01E0/)).not.toBeInTheDocument()
    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
  })

  it('ChatLauncher opens the panel in Chat mode, and clicking it again while already in Chat mode collapses the panel', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Open chat' }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Chat' })).toHaveAttribute('aria-checked', 'true')

    await user.click(screen.getByRole('button', { name: 'Close chat' }))
    expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()
  })

  it('selecting a node while the panel is in Chat mode force-switches it to Inspector and shows the node details', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Open chat' }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

    await user.click(await screen.findByTestId('graph-element-char_dexter_morgan'))

    // A canvas tap is an explicit request to see the element's details — the
    // panel switches to Inspector and shows the node, replacing Chat content.
    // (Reverted from 06-09's sticky-Chat behavior per user feedback: "clicking
    // a node shows nothing on the right".)
    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Inspector' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()
  })

  describe('citation graph-focus wiring (06-10, RAG-17)', () => {
    function chatMessagesWithCitation() {
      return {
        ...defaultChatMessagesReturn(),
        status: 'success' as const,
        messages: [
          {
            id: 'message_assistant_1',
            role: 'assistant',
            content: 'Dexter works at Miami Metro.',
            created_at: '2026-01-01T00:01:05Z',
            visible_until_order_snapshot: 1,
          },
        ],
        citations: [claimCitation],
      }
    }

    it('clicking a citation chip\'s "Show in graph" icon updates the graph focus without leaving Chat mode', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation())

      const user = userEvent.setup()
      render(<App />)

      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

      // claimCitation: related_node_ids (2) + related_edge_ids (1) = 3.
      await user.click(screen.getByRole('button', { name: 'Show in graph' }))

      expect(await screen.findByText('Highlighting 3 from chat')).toBeInTheDocument()
      // Still Chat mode — "Show in graph" must never switch panel content.
      expect(screen.getByRole('heading', { name: 'Chat' })).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: 'Chat' })).toHaveAttribute('aria-checked', 'true')
    })

    it('clicking a citation chip body switches to Inspector mode and selects the referenced resource', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation())

      const user = userEvent.setup()
      render(<App />)

      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

      // claimCitation's chip body: "{source_type} · {episode_code}".
      await user.click(screen.getByRole('button', { name: 'script · S01E01' }))

      expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: 'Inspector' })).toHaveAttribute('aria-checked', 'true')
      expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()
    })
  })

  describe('progress-decrease clears stale graph focus (06-10 Task 3)', () => {
    // char_paul_bennett only exists in graphResponseS01E03 (visible_from_order
    // 3) — absent from graphResponseS01E01, so a focus referencing it must be
    // cleared once progress decreases to order 1.
    const paulBennettCitation: Citation = {
      claim_id: 'claim_7',
      evidence_id: null,
      source_id: 'source_1',
      source_label: 'S01E03 script',
      source_type: 'script',
      episode_code: 'S01E03',
      locator: '00:10:00',
      excerpt: 'Paul Bennett appears.',
      related_node_ids: ['char_paul_bennett'],
      related_edge_ids: [],
    }

    function chatMessagesWithCitation(citation: Citation) {
      return {
        ...defaultChatMessagesReturn(),
        status: 'success' as const,
        messages: [
          {
            id: 'message_assistant_1',
            role: 'assistant',
            content: 'Answer text.',
            created_at: '2026-01-01T00:01:05Z',
            visible_until_order_snapshot: 3,
          },
        ],
        citations: [citation],
      }
    }

    async function decreaseProgressToS01E01(user: ReturnType<typeof userEvent.setup>) {
      await user.click(await screen.findByRole('combobox', { name: 'Watch progress' }))
      await user.click(await screen.findByRole('option', { name: /S01E01/ }))
      await user.click(await screen.findByRole('button', { name: 'Yes, unlock episode' }))
    }

    it('clears an active graph focus that references a node hidden by the new (lower) boundary', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation(paulBennettCitation))

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(true))
      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      await user.click(await screen.findByRole('button', { name: 'Show in graph' }))
      expect(await screen.findByText('Highlighting 1 from chat')).toBeInTheDocument()

      await decreaseProgressToS01E01(user)

      await waitFor(() => expect(screen.queryByText(/Highlighting/)).not.toBeInTheDocument())
    })

    it('leaves a graph focus untouched when a progress decrease does not hide any of its referenced elements', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
      // claimCitation references char_dexter_morgan/loc_miami_metro/edge_2 —
      // all present (by id) in both graphResponseS01E01 and graphResponseS01E03.
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation(claimCitation))

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(true))
      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      await user.click(await screen.findByRole('button', { name: 'Show in graph' }))
      expect(await screen.findByText('Highlighting 3 from chat')).toBeInTheDocument()

      await decreaseProgressToS01E01(user)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=1'))).toBe(true))
      expect(screen.getByText('Highlighting 3 from chat')).toBeInTheDocument()
    })
  })

  describe('ChangeSet-apply incremental refresh (06-11, RAG-14/RAG-17)', () => {
    function chatMessagesWithProposedChangeSet(changeSet: ChangeSet) {
      return {
        ...defaultChatMessagesReturn(),
        status: 'success' as const,
        messages: [
          {
            id: 'message_assistant_cs',
            role: 'assistant',
            content: 'Here is a proposal.',
            created_at: '2026-01-01T00:01:05Z',
            visible_until_order_snapshot: 1,
          },
        ],
        proposedChangeSet: changeSet,
      }
    }

    async function openChatAndConfirm(user: ReturnType<typeof userEvent.setup>) {
      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      await user.click(await screen.findByRole('button', { name: 'Confirm changes' }))
    }

    it('applying a ChangeSet refreshes the graph incrementally — no full relayout, no GraphCanvas remount, focus moved to the new resource', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithProposedChangeSet(proposedChangeSetAwaitingConfirmation))
      vi.mocked(confirmChangeSet).mockResolvedValue(proposedChangeSetApplied)

      const user = userEvent.setup()
      render(<App />)

      // Initial graph load settles, then reset the spies so only the
      // post-apply refresh's behavior is measured.
      await screen.findByTestId('graph-element-char_dexter_morgan')
      const fetchesBeforeApply = graphFetchCalls().length
      graphStubHooks.cyMounts = 0
      graphStubHooks.layoutRuns = 0

      await openChatAndConfirm(user)

      // Terminal Applied badge replaces the controls (immutable record).
      expect(await screen.findByText('Applied')).toBeInTheDocument()
      // T-06-05: the only write path is the card's own Confirm button — it
      // fired exactly once, no other UI event triggered apply.
      expect(confirmChangeSet).toHaveBeenCalledTimes(1)

      // Incremental refresh: useGraph re-issued its own fetch (no loading
      // flash — GraphCanvas never unmounts), and the full relayout path was
      // NOT re-invoked. cyMounts counts stub re-renders (not remounts), so
      // the mount-stability proof is: the graph element never leaves the DOM
      // and no GraphLoadingState appears during the refresh.
      await waitFor(() => expect(graphFetchCalls().length).toBeGreaterThan(fetchesBeforeApply))
      expect(screen.getByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
      expect(graphStubHooks.layoutRuns).toBe(0)

      // 06-10 focus mechanism reused: the created resource (create_note →
      // char_dexter_morgan) gets the selected-dominant focus treatment.
      expect(await screen.findByText('Highlighting 1 from chat')).toBeInTheDocument()

      // Regression: the graph still renders its elements after the refresh —
      // image/episode-filtering mapping (graphElements.ts) untouched.
      expect(await screen.findByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()
    })

    it('renders the Protected badge for a canonical-edit refusal in the full app, claiming no canonical modification', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('hdgraf.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithProposedChangeSet(protectedOverrideChangeSet))

      const user = userEvent.setup()
      render(<App />)

      await user.click(await screen.findByRole('button', { name: 'Open chat' }))

      expect(await screen.findByText('Protected')).toBeInTheDocument()
      expect(screen.getByText('Propose a note instead')).toBeInTheDocument()
      // The card stays confirmable (the proposal is a linked note annotation,
      // not a canonical edit — the badge is informational), but no copy claims
      // the canonical record was changed (T-06-12).
      expect(screen.getByRole('button', { name: 'Confirm changes' })).toBeInTheDocument()
      expect(screen.queryByText(/canonical record.*(updated|changed|modified)/i)).not.toBeInTheDocument()
    })
  })
})
