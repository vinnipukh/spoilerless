import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ShareView } from './ShareView'
import type { GraphResponse } from '@/types/graph'

vi.mock('@/api/share', () => ({
  getShareGraph: vi.fn(),
}))

vi.mock('@/components/graph/GraphCanvas', () => ({
  GraphCanvas: ({ readOnly }: { readOnly?: boolean }) => (
    <div data-testid="graph-canvas" data-readonly={readOnly ? 'true' : 'false'}>
      Mock Graph Canvas
    </div>
  ),
}))

import { getShareGraph } from '@/api/share'

const mockGraphResponse: GraphResponse = {
  series: { id: 'series_dexter', title: 'Dexter', slug: 'dexter' },
  visible_until_order: 3,
  effective_view_order: 1,
  nodes: [

    {
      id: 'dexter:character:dexter_morgan',
      type: 'Character',
      label: 'Dexter Morgan',
      visible_from_order: 1,
      origin: 'canonical',
      episode_id: null,
      image_url: null,
      image_source_url: null,
    },

  ],
  edges: [],
  claims: [],
  sources: [],
  evidence: [],
}

describe('ShareView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders read-only graph shell when token is valid', async () => {
    vi.mocked(getShareGraph).mockResolvedValue(mockGraphResponse)

    render(<ShareView token="valid_token_123" />)

    expect(screen.getByText('Loading snapshot...')).toBeTruthy()

    await waitFor(() => {
      expect(screen.getByText('Spoilerless')).toBeTruthy()
      expect(screen.getByText('Snapshot')).toBeTruthy()
      expect(screen.getByText('Open Spoilerless')).toBeTruthy()
      expect(screen.getByTestId('graph-canvas')).toBeTruthy()
      expect(screen.getByTestId('graph-canvas').getAttribute('data-readonly')).toBe('true')
      expect(
        screen.getByText('Snapshot created · visible through episode 3')
      ).toBeTruthy()
    })
  })

  it('renders error card when snapshot token is invalid, expired, or revoked', async () => {
    vi.mocked(getShareGraph).mockRejectedValue(
      new Error('Snapshot link is invalid, expired, or revoked.')
    )

    render(<ShareView token="invalid_token" />)

    await waitFor(() => {
      expect(
        screen.getByText('This snapshot link has expired or has been revoked.')
      ).toBeTruthy()
      expect(
        screen.getByText('Ask the person who shared it for a fresh link.')
      ).toBeTruthy()
      expect(screen.queryByTestId('graph-canvas')).toBeNull()
    })
  })
})
