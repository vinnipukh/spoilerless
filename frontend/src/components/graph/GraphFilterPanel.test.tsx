import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { GraphFilterPanel } from './GraphFilterPanel'
import { NODE_TYPES } from '@/lib/nodeTypes'
import { EDGE_TYPE_TO_FAMILY } from './relationshipStyles'

const ALL_NODE_TYPES = NODE_TYPES.map((nt) => nt.type)
const ALL_EDGE_FAMILIES = Array.from(new Set(Object.values(EDGE_TYPE_TO_FAMILY)))

describe('GraphFilterPanel (settings-style, 260813)', () => {
  function renderPanel(overrides?: {
    nodeKindFilters?: Record<string, boolean>
    edgeClassFilters?: Record<string, boolean>
  }) {
    const nodeKindFilters = overrides?.nodeKindFilters ?? Object.fromEntries(ALL_NODE_TYPES.map((t) => [t, true]))
    const edgeClassFilters = overrides?.edgeClassFilters ?? Object.fromEntries(ALL_EDGE_FAMILIES.map((f) => [f, true]))
    const dispatchScene = vi.fn()
    render(
      <GraphFilterPanel
        nodeKindFilters={nodeKindFilters}
        edgeClassFilters={edgeClassFilters}
        dispatchScene={dispatchScene}
      />,
    )
    return { nodeKindFilters, edgeClassFilters, dispatchScene }
  }

  it('opens to a settings-style panel with a heading and per-type switches', async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))

    expect(screen.getByRole('heading', { name: 'Graph Filters' })).toBeInTheDocument()
    // One switch per node type, all on by default.
    for (const type of ALL_NODE_TYPES) {
      expect(screen.getByRole('switch', { name: `${type} visible` })).toHaveAttribute(
        'aria-checked',
        'true',
      )
    }
    for (const family of ALL_EDGE_FAMILIES) {
      expect(screen.getByRole('switch', { name: `${family} visible` })).toHaveAttribute(
        'aria-checked',
        'true',
      )
    }
  })

  it('toggling a node-type switch dispatches SET_NODE_KIND_FILTER', async () => {
    const user = userEvent.setup()
    const { dispatchScene } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('switch', { name: `${ALL_NODE_TYPES[0]} visible` }))

    expect(dispatchScene).toHaveBeenCalledWith({
      type: 'SET_NODE_KIND_FILTER',
      kind: ALL_NODE_TYPES[0],
      visible: false,
    })
  })

  it('toggling a relationship switch dispatches SET_EDGE_CLASS_FILTER', async () => {
    const user = userEvent.setup()
    const { dispatchScene } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('switch', { name: `${ALL_EDGE_FAMILIES[0]} visible` }))

    expect(dispatchScene).toHaveBeenCalledWith({
      type: 'SET_EDGE_CLASS_FILTER',
      edgeClass: ALL_EDGE_FAMILIES[0],
      visible: false,
    })
  })

  it('All and None actions dispatch SET_ALL_FILTERS', async () => {
    const user = userEvent.setup()
    const { dispatchScene } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('button', { name: 'All' }))
    expect(dispatchScene).toHaveBeenCalledWith({ type: 'SET_ALL_FILTERS', visible: true })

    await user.click(screen.getByRole('button', { name: 'None' }))
    expect(dispatchScene).toHaveBeenCalledWith({ type: 'SET_ALL_FILTERS', visible: false })
  })

  it('reflects a disabled filter as aria-checked false', async () => {
    const user = userEvent.setup()
    const nodeKindFilters = Object.fromEntries(ALL_NODE_TYPES.map((t) => [t, true]))
    nodeKindFilters[ALL_NODE_TYPES[0]] = false
    renderPanel({ nodeKindFilters })

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    expect(screen.getByRole('switch', { name: `${ALL_NODE_TYPES[0]} visible` })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })
})
