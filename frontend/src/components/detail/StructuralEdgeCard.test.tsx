import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StructuralEdgeCard } from './StructuralEdgeCard'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { SelectedEdge } from '../graph/GraphCanvas'

describe('StructuralEdgeCard', () => {
  it('renders the relationship type and both connected node labels for a PART_OF edge', () => {
    // edge_1: PART_OF, dexter_s01e01 -> series_dexter, claim_id: null.
    const selected: SelectedEdge = {
      kind: 'edge',
      id: 'edge_1',
      edgeType: 'PART_OF',
      source: 'dexter_s01e01',
      target: 'series_dexter',
    }
    render(<StructuralEdgeCard selected={selected} nodes={graphResponseS01E01.nodes} />)

    expect(screen.getByRole('heading', { name: 'PART_OF' })).toBeInTheDocument()
    expect(screen.getByText(/S01E01 — Dexter/)).toBeInTheDocument()
    expect(screen.getByText(/Dexter/)).toBeInTheDocument()
  })

  it('renders no TabsList/TabsTrigger elements', () => {
    const selected: SelectedEdge = {
      kind: 'edge',
      id: 'edge_1',
      edgeType: 'PART_OF',
      source: 'dexter_s01e01',
      target: 'series_dexter',
    }
    render(<StructuralEdgeCard selected={selected} nodes={graphResponseS01E01.nodes} />)

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
  })
})
