import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRef } from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { graphResponseS01E01, graphResponseS01E03 } from './test/fixtures/graphResponse'
import {
  claimCitation,
  proposedChangeSetApplied,
  proposedChangeSetAwaitingConfirmation,
  protectedOverrideChangeSet,
} from './test/fixtures/chatFixtures'
import { useChatMessages } from './hooks/useChatMessages'
import { BYOK_STORAGE_KEY } from '@/lib/byok'
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
            connectedEdges: () => makeFakeCollection(),
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
  if (url.startsWith('/api/series/series_dexter/episodes')) return Promise.resolve(jsonResponse(episodesFixture))
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
  // Settings page (LLM provider configuration)
  if (url === '/api/settings/llm') {
    return Promise.resolve(
      jsonResponse({
        provider: 'gemini',
        model: 'gemini-2.5-flash',
        base_url: null,
        enabled: false,
        api_key_configured: false,
        api_key_masked: null,
      }),
    )
  }
  return Promise.resolve(notFoundResponse())
}

function graphFetchCalls() {
  return vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes('/graph'))
}

beforeEach(() => {
  currentAuthState = 'unauthenticated'
  sessionStorage.clear()
  localStorage.clear()
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
    expect(await screen.findByText('Spoilerless')).toBeInTheDocument()
    expect(screen.getByText(/spoiler-safe graph browser/i)).toBeInTheDocument()
  })

  it('enters read-only visitor (misafir) mode from the login page', async () => {
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Spoilerless')
    await user.click(screen.getByRole('button', { name: 'Continue as visitor' }))

    // Visitor badge replaces the account block…
    await waitFor(() => {
      expect(screen.getByText('Visitor')).toBeInTheDocument()
    })
    // …and chat is hidden entirely (chat is auth-gated and costs LLM tokens).
    expect(screen.queryByRole('button', { name: 'Open chat' })).not.toBeInTheDocument()
  })

  it('visitor detail inspector hides all note-adding and revision-history UI', async () => {
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Spoilerless')
    await user.click(screen.getByRole('button', { name: 'Continue as visitor' }))

    // Visitor badge replaces the account block…
    await waitFor(() => {
      expect(screen.getByText('Visitor')).toBeInTheDocument()
    })

    // Visitor entry seeds the first series at order 1 silently, so the graph
    // renders and the canvas stub exposes a clickable button per node.
    const nodeButton = await screen.findByTestId('graph-element-char_dexter_morgan')
    await user.click(nodeButton)
    await screen.findByRole('heading', { name: 'Dexter Morgan' })

    // The inspector stays browsable — no note-adding affordance (tab,
    // button, editor) and no revision history surface (tab, panel) exists.
    // Same assertion set as DetailPanel.test.tsx readOnly suite. Scoped to
    // the Inspector dialog: the new 10-05 top-level tab strip also carries
    // an "Evidence" tab, so unscoped role queries would be ambiguous.
    const inspector = within(screen.getByRole('dialog'))
    expect(inspector.queryByRole('tab', { name: 'Notes' })).not.toBeInTheDocument()
    expect(inspector.queryByRole('tab', { name: 'History' })).not.toBeInTheDocument()
    expect(inspector.queryByRole('button', { name: 'Add note' })).not.toBeInTheDocument()
    expect(inspector.queryByRole('button', { name: 'Create relationship' })).not.toBeInTheDocument()
    expect(inspector.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(inspector.getByRole('tab', { name: 'Claims' })).toBeInTheDocument()
    expect(inspector.getByRole('tab', { name: 'Evidence' })).toBeInTheDocument()
  })

  it('visitor navigating ABOVE the current boundary gets the spoiler warning modal (08-12 regression)', async () => {
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Spoilerless')
    await user.click(screen.getByRole('button', { name: 'Continue as visitor' }))
    await waitFor(() => {
      expect(screen.getByText('Visitor')).toBeInTheDocument()
    })

    // Visitor entry seeds the first series at order 1 silently (no boundary
    // existed yet to spoil) — the graph for order 1 loads without a modal.
    await waitFor(() => {
      expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=1'))).toBe(true)
    })

    // Forward navigation ABOVE the seeded boundary must warn BEFORE showing
    // anything — never a silent spoiler push (260805-te3 removed the modal
    // for visitors; restored 08-12 with visitor copy).
    await user.click(await screen.findByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E03/ }))

    expect(await screen.findByText('View S01E03?')).toBeInTheDocument()
    expect(screen.getByText(/may contain spoilers/i)).toBeInTheDocument()
    expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(false)

    await user.click(screen.getByRole('button', { name: 'View episode' }))
    await waitFor(() => {
      expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(true)
    })
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

  it('opens the LEFT inspector for a user-created edge, never the right-side card', async () => {
    currentAuthState = 'authenticated'
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('combobox', { name: 'Series' }))
    await user.click(await screen.findByRole('option', { name: 'Dexter' }))
    await user.click(await screen.findByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E01/ }))
    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))
    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()

    // A user-created relationship (claim_id null, origin 'user') must route to
    // the LEFT DetailPanel inspector (edge-type title + Overview tab), not the
    // right-side StructuralEdgeCard (regression: user edges used to match the
    // `claim_id == null` structural-edge condition and open on the right).
    await user.click(screen.getByTestId('graph-element-user-rel:test-1'))
    expect(await screen.findByRole('heading', { name: 'KNOWS' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    // The left panel shows the edge endpoints (the canvas button also carries
    // the node label, hence getAllByText).
    expect(screen.getAllByText('Dexter Morgan').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Debra Morgan').length).toBeGreaterThan(0)
  })

  it('restores confirmed state from sessionStorage on mount without opening confirmation modal', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

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
    sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Open chat' }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close chat' }))
    expect(screen.queryByRole('heading', { name: 'Chat' })).not.toBeInTheDocument()
  })

  it('toggles between the graph workspace and the settings page via the topBar button', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
    // BYOK (08-02): the settings form is populated from localStorage, not a
    // server GET - seed it so the stored model shows in the form.
    localStorage.setItem(
      BYOK_STORAGE_KEY,
      JSON.stringify({ provider: 'gemini', api_key: 'AIzaStoredKey', base_url: '', model: 'gemini-2.5-flash' }),
    )

    const user = userEvent.setup()
    render(<App />)

    // Graph workspace is the default view.
    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()

    // Open settings — the graph canvas unmounts, the settings form appears.
    await user.click(screen.getByRole('button', { name: 'Settings' }))
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('gemini-2.5-flash')).toBeInTheDocument()
    expect(screen.queryByTestId('graph-canvas-stub')).not.toBeInTheDocument()

    // The toggle flips to "Back to graph" while on the settings page (the
    // page itself also renders a "Back to graph" button — either returns to
    // the graph workspace).
    await user.click(screen.getAllByRole('button', { name: 'Back to graph' })[0])
    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Settings' })).not.toBeInTheDocument()
  })

  it('selecting a node while the chat sheet is open shows the node details AND keeps chat visible', async () => {
    currentAuthState = 'authenticated'
    sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Open chat' }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

    await user.click(await screen.findByTestId('graph-element-char_dexter_morgan'))

    // The two panels are independent sheets: the left inspector shows the
    // node's details while the right chat sheet stays open — both visible at
    // the same time (06-12 split, replacing the single-panel mode toggle).
    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeInTheDocument()
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
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation())

      const user = userEvent.setup()
      render(<App />)

      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

      // claimCitation: related_node_ids (2) + related_edge_ids (1) = 3.
      await user.click(screen.getByRole('button', { name: 'Show in graph' }))

      expect(await screen.findByText('Highlighting 3')).toBeInTheDocument()
      // "Show in graph" only sets the highlight — it never touches the chat
      // sheet (and never opens the inspector).
      expect(screen.getByRole('heading', { name: 'Chat' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Dexter Morgan' })).not.toBeInTheDocument()
    })

    it('clicking a citation chip body switches to Inspector mode and selects the referenced resource', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation())

      const user = userEvent.setup()
      render(<App />)

      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()

      // claimCitation's chip body: "{source_type} · {episode_code}".
      await user.click(screen.getByRole('button', { name: 'script · S01E01' }))

      expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()
      // Both panels coexist: the chip body opened the left inspector for the
      // referenced node while the right chat sheet stays open.
      expect(screen.getByRole('heading', { name: 'Chat' })).toBeInTheDocument()
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
      // 07-03 view-only model (PROG-01): selecting an already-watched episode
      // moves only the view boundary — no unlock confirmation modal appears.
      await user.click(await screen.findByRole('option', { name: /S01E01/ }))
    }

    it('clears an active graph focus that references a node hidden by the new (lower) boundary', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation(paulBennettCitation))

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(true))
      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      await user.click(await screen.findByRole('button', { name: 'Show in graph' }))
      expect(await screen.findByText('Highlighting 1')).toBeInTheDocument()

      await decreaseProgressToS01E01(user)

      await waitFor(() => expect(screen.queryByText(/Highlighting/)).not.toBeInTheDocument())
    })

    it('leaves a graph focus untouched when a progress decrease does not hide any of its referenced elements', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 3 }))
      // claimCitation references char_dexter_morgan/loc_miami_metro/edge_2 —
      // all present (by id) in both graphResponseS01E01 and graphResponseS01E03.
      vi.mocked(useChatMessages).mockReturnValue(chatMessagesWithCitation(claimCitation))

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=3'))).toBe(true))
      await user.click(await screen.findByRole('button', { name: 'Open chat' }))
      await user.click(await screen.findByRole('button', { name: 'Show in graph' }))
      expect(await screen.findByText('Highlighting 3')).toBeInTheDocument()

      await decreaseProgressToS01E01(user)

      await waitFor(() => expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=1'))).toBe(true))
      expect(screen.getByText('Highlighting 3')).toBeInTheDocument()
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
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
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
      expect(await screen.findByText('Highlighting 1')).toBeInTheDocument()

      // Regression: the graph still renders its elements after the refresh —
      // image/episode-filtering mapping (graphElements.ts) untouched.
      expect(await screen.findByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()
    })

    it('renders the Protected badge for a canonical-edit refusal in the full app, claiming no canonical modification', async () => {
      currentAuthState = 'authenticated'
      sessionStorage.setItem('spoilerless.watchProgress', JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }))
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

    it('renders fallback UI when ErrorBoundary catches a child render error', () => {
      const ThrowingChild = () => {
        throw new Error('Test crash')
      }
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      render(
        <ErrorBoundary fallbackTitle="Section error">
          <ThrowingChild />
        </ErrorBoundary>,
      )
      expect(screen.getByText('Section error')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Reload Section/i })).toBeInTheDocument()
      consoleSpy.mockRestore()
    })
  })

  describe('four-tab narrative hierarchy (10-05, D-16/D-17/D-38/D-47)', () => {
    async function renderGraphWorkspace() {
      currentAuthState = 'authenticated'
      sessionStorage.setItem(
        'spoilerless.watchProgress',
        JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }),
      )
      render(<App />)
      await screen.findByTestId('graph-canvas-stub')
    }

    it('renders four accessible top tabs with Story selected by default', async () => {
      await renderGraphWorkspace()

      expect(screen.getByRole('tab', { name: 'Story' })).toHaveAttribute('aria-selected', 'true')
      expect(screen.getByRole('tab', { name: 'Characters' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Evidence' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Advanced' })).toBeInTheDocument()
    })

    it('Story opens the bounded Episode Overview and reveals the coordinated Event Timeline rail', async () => {
      const user = userEvent.setup()
      await renderGraphWorkspace()

      // Episode Overview is the default nested mode: the graph workspace is
      // the primary region and no timeline rail is mounted yet.
      expect(screen.getByRole('tab', { name: 'Episode Overview' })).toHaveAttribute('aria-selected', 'true')
      expect(screen.queryByRole('complementary', { name: 'Event Timeline' })).not.toBeInTheDocument()

      // Event Timeline mode reveals the rail beside the STILL-MOUNTED canvas.
      await user.click(screen.getByRole('tab', { name: 'Event Timeline' }))
      const rail = await screen.findByRole('complementary', { name: 'Event Timeline' })
      expect(within(rail).getByRole('heading', { name: 'Event Timeline' })).toBeInTheDocument()
      expect(within(rail).getByRole('button', { name: /Dexter kills Mike Donovan/ })).toBeInTheDocument()
      // The graph never unmounts when the timeline opens.
      expect(screen.getByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()
    })

    it('exposes the nested responsibilities for Characters, Evidence, and Advanced', async () => {
      const user = userEvent.setup()
      await renderGraphWorkspace()

      await user.click(screen.getByRole('tab', { name: 'Characters' }))
      expect(screen.getByRole('tab', { name: 'Character Network' })).toHaveAttribute('aria-selected', 'true')
      expect(screen.getByRole('tab', { name: 'Local Neighborhood' })).toBeInTheDocument()

      await user.click(screen.getByRole('tab', { name: 'Evidence' }))
      expect(screen.getByRole('tab', { name: 'Investigation' })).toHaveAttribute('aria-selected', 'true')
      expect(screen.getByRole('tab', { name: 'Evidence Chain' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Answer Graph' })).toBeInTheDocument()

      await user.click(screen.getByRole('tab', { name: 'Advanced' }))
      expect(screen.getByRole('tab', { name: 'Full Graph' })).toHaveAttribute('aria-selected', 'true')
      expect(screen.getByRole('tab', { name: 'Debug' })).toBeInTheDocument()
    })

    it('Answer Graph nested mode renders the temporary-focus surface (UI-SPEC)', async () => {
      const user = userEvent.setup()
      await renderGraphWorkspace()

      await user.click(screen.getByRole('tab', { name: 'Evidence' }))
      await user.click(screen.getByRole('tab', { name: 'Answer Graph' }))

      // 10-07: the real AnswerGraph surface — empty focus shows the safe
      // empty copy, never a hidden total or an internal error.
      expect(
        await screen.findByText('No focus resources are visible at the current boundary.'),
      ).toBeInTheDocument()

      // Closing restores the Evidence tab's default Investigation mode.
      await user.click(screen.getByRole('button', { name: 'Close Answer Graph' }))
      expect(screen.getByRole('tab', { name: 'Investigation' })).toHaveAttribute(
        'aria-selected',
        'true',
      )
      expect(
        screen.queryByText('No focus resources are visible at the current boundary.'),
      ).not.toBeInTheDocument()
    })

    it('graph, timeline, and Inspector selections converge on one shared selection without layout calls', async () => {
      const user = userEvent.setup()
      await renderGraphWorkspace()
      // The initial canvas mount runs its layout; measure only what the
      // selection/tab interactions add.
      graphStubHooks.layoutRuns = 0

      // Canvas tap -> Inspector.
      await user.click(screen.getByTestId('graph-element-char_dexter_morgan'))
      expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()

      // Top-tab switches keep the canvas mounted, the selection, and the
      // Inspector open — no reset, no relayout (D-47/D-24).
      await user.click(screen.getByRole('tab', { name: 'Characters' }))
      await user.click(screen.getByRole('tab', { name: 'Story' }))
      expect(screen.getByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()

      // Timeline rail row -> the SAME shared selection (Inspector opens for
      // the event) while the canvas stays mounted and layout stays quiet.
      await user.click(screen.getByRole('tab', { name: 'Event Timeline' }))
      const rail = await screen.findByRole('complementary', { name: 'Event Timeline' })
      await user.click(within(rail).getByRole('button', { name: /Dexter kills Mike Donovan/ }))
      expect(await screen.findByRole('heading', { name: 'Dexter kills Mike Donovan' })).toBeInTheDocument()
      expect(screen.getByTestId('graph-element-char_dexter_morgan')).toBeInTheDocument()

      expect(graphStubHooks.layoutRuns).toBe(0)
    })
  })
})
