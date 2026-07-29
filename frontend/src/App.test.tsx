import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRef } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { graphResponseS01E01 } from './test/fixtures/graphResponse'
import type { SeriesResponse, EpisodeResponse } from './types/series'

// react-cytoscapejs renders to a <canvas>, which is not individually
// queryable/clickable per-node under jsdom (no real canvas 2D context, no
// hit-testing). Stub it with a DOM representation that still exercises
// GraphCanvas's real `cy.on('tap', ...)` wiring: it captures the handlers
// GraphCanvas registers via the `cy` callback prop, then invokes them from
// plain clickable elements standing in for "a rendered node/edge" and "an
// empty patch of canvas".
//
// react-cytoscapejs's real implementation invokes the `cy` prop on every
// componentDidUpdate (not just mount) — GraphCanvas relies on this and
// guards its own `cy.on(...)` registration with a ref so listeners are only
// attached once. To exercise that real guard correctly, this stub must keep
// the same `fakeCy`/`handlers` identity across re-renders too (via useRef),
// not recreate them on every render.
// A trivial chainable stand-in for a Cytoscape collection (`.elements()`,
// `.closedNeighborhood()`, `.connectedNodes()`, `.difference()`, `.union()`)
// — GraphCanvas.tsx's tap-driven highlight/fade wiring (Plan 02) calls these
// on every node/edge tap. The stub doesn't need real graph-traversal
// semantics (this test only asserts DetailPanel content, not fade/dominant
// classes), it just needs to not throw when the real production code calls
// through the chain.
type FakeCollection = {
  addClass: (cls: string) => FakeCollection
  removeClass: (cls: string) => FakeCollection
  difference: (other: unknown) => FakeCollection
  union: (other: unknown) => FakeCollection
}

function makeFakeCollection(): FakeCollection {
  const collection: FakeCollection = {
    addClass: () => collection,
    removeClass: () => collection,
    difference: () => collection,
    union: () => collection,
  }
  return collection
}

vi.mock('react-cytoscapejs', () => {
  function CytoscapeComponentStub(props: {
    elements: Array<{ data: Record<string, unknown> }>
    cy?: (cy: unknown) => void
  }) {
    type Handler = (evt: unknown) => void
    const stateRef = useRef<{
      handlers: Record<string, Handler[]>
      fakeCy: {
        on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => void
        elements: () => FakeCollection
        container: () => null
      }
    } | null>(null)

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
            <button
              key={el.data.id as string}
              type="button"
              data-testid={`graph-element-${el.data.id}`}
              onClick={() => handlers[key]?.forEach((handler) => handler({ target: fakeTarget }))}
            >
              {el.data.label as string}
            </button>
          )
        })}
        <div
          data-testid="graph-canvas-background"
          onClick={() => handlers['tap']?.forEach((handler) => handler({ target: fakeCy }))}
        />
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

function jsonResponse(data: unknown): Response {
  return { ok: true, json: async () => data } as Response
}

function notFoundResponse(): Response {
  return {
    ok: false,
    json: async () => ({ detail: { code: 'unknown_error', message: 'not found' } }),
  } as Response
}

function fetchStub(input: RequestInfo | URL): Promise<Response> {
  const url = String(input)
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
  sessionStorage.clear()
  vi.stubGlobal('fetch', vi.fn(fetchStub))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the empty state and fires no /graph request until a series and episode are confirmed', async () => {
    render(<App />)

    expect(await screen.findByText('Nothing revealed yet')).toBeInTheDocument()
    expect(screen.getByText('Advance your watch progress to unlock the story.')).toBeInTheDocument()
    expect(graphFetchCalls()).toHaveLength(0)
  })

  it('runs select -> confirm -> fetch -> render -> inspect end-to-end, and gates cancel/forward/backward changes', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('combobox', { name: 'Series' }))
    await user.click(await screen.findByRole('option', { name: 'Dexter' }))

    await user.click(await screen.findByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E01/ }))

    // Confirmation modal appears before any /graph fetch fires.
    expect(await screen.findByText('Unlock S01E01?')).toBeInTheDocument()
    expect(graphFetchCalls()).toHaveLength(0)

    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))

    await waitFor(() => expect(graphFetchCalls()).toHaveLength(1))
    expect(graphFetchCalls()[0]?.[0]).toBe('/api/series/series_dexter/graph?visible_until_order=1')

    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
    expect(screen.getByText('Select a node to see details.')).toBeInTheDocument()

    // Click a rendered node -> DetailPanel shows its label.
    await user.click(screen.getByTestId('graph-element-char_dexter_morgan'))
    expect(await screen.findByRole('heading', { name: 'Dexter Morgan' })).toBeInTheDocument()

    // Click empty canvas -> DetailPanel returns to the placeholder.
    await user.click(screen.getByTestId('graph-canvas-background'))
    expect(await screen.findByText('Select a node to see details.')).toBeInTheDocument()

    // Forward change to S01E02 opens the modal before any new fetch; cancel fires none.
    await user.click(screen.getByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E02/ }))
    expect(await screen.findByText('Unlock S01E02?')).toBeInTheDocument()
    const callsBeforeCancel = graphFetchCalls().length

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByText('Unlock S01E02?')).not.toBeInTheDocument())
    expect(graphFetchCalls()).toHaveLength(callsBeforeCancel)

    // Re-select S01E02 and confirm this time.
    await user.click(screen.getByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E02/ }))
    expect(await screen.findByText('Unlock S01E02?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))
    await waitFor(() =>
      expect(graphFetchCalls().some(([url]) => url === '/api/series/series_dexter/graph?visible_until_order=2')).toBe(
        true,
      ),
    )

    // Backward change to S01E01 opens the "Rewatch" copy variant, not "Unlock".
    await user.click(screen.getByRole('combobox', { name: 'Watch progress' }))
    await user.click(await screen.findByRole('option', { name: /S01E01/ }))
    expect(await screen.findByText('Rewatch S01E01?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Yes, unlock episode' }))
    await waitFor(() =>
      expect(
        graphFetchCalls().filter(([url]) => url === '/api/series/series_dexter/graph?visible_until_order=1').length,
      ).toBe(2),
    )
  })

  it('restores confirmed state from sessionStorage on mount without opening the confirmation modal', async () => {
    sessionStorage.setItem(
      'hdgraf.watchProgress',
      JSON.stringify({ seriesId: 'series_dexter', visibleUntilOrder: 1 }),
    )

    render(<App />)

    await waitFor(() =>
      expect(graphFetchCalls().some(([url]) => url === '/api/series/series_dexter/graph?visible_until_order=1')).toBe(
        true,
      ),
    )
    expect(screen.queryByText(/Unlock S01E0/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Rewatch S01E0/)).not.toBeInTheDocument()
    expect(await screen.findByTestId('graph-canvas-stub')).toBeInTheDocument()
  })
})
