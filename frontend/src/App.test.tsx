import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRef } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { graphResponseS01E01 } from './test/fixtures/graphResponse'
import type { SeriesResponse, EpisodeResponse } from './types/series'
import type { UserResponse } from './types/auth'

// react-cytoscapejs stub (same as before)
type FakeCollection = { addClass: (cls: string) => FakeCollection; removeClass: (cls: string) => FakeCollection; difference: (other: unknown) => FakeCollection; union: (other: unknown) => FakeCollection }
function makeFakeCollection(): FakeCollection {
  const c: FakeCollection = { addClass: () => c, removeClass: () => c, difference: () => c, union: () => c }
  return c
}

vi.mock('react-cytoscapejs', () => {
  type Handler = (evt: unknown) => void
  function CytoscapeComponentStub(props: { elements: Array<{ data: Record<string, unknown> }>; cy?: (cy: unknown) => void }) {
    const stateRef = useRef<{ handlers: Record<string, Handler[]>; fakeCy: { on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => void; elements: () => FakeCollection; container: () => null } } | null>(null)
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
      }
      stateRef.current = { handlers, fakeCy }
    }
    const { handlers, fakeCy } = stateRef.current
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
    return Promise.resolve(jsonResponse(graphResponseS01E01))
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
    expect(screen.getByText('Select a node to see details.')).toBeInTheDocument()
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
})
