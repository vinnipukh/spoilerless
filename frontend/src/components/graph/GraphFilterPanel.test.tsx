import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { GraphFilterPanel } from './GraphFilterPanel'
import { initialFilterState } from './filterState'
import { NODE_TYPES } from '@/lib/nodeTypes'
import { EDGE_TYPE_TO_FAMILY } from './relationshipStyles'

const ALL_NODE_TYPES = NODE_TYPES.map((nt) => nt.type)
const ALL_EDGE_FAMILIES = Array.from(new Set(Object.values(EDGE_TYPE_TO_FAMILY)))

describe('GraphFilterPanel (settings-style, 260813)', () => {
  function renderPanel() {
    const filterState = initialFilterState(ALL_NODE_TYPES, ALL_EDGE_FAMILIES)
    const onToggleNodeType = vi.fn()
    const onToggleEdgeFamily = vi.fn()
    const onSetAll = vi.fn()
    render(
      <GraphFilterPanel
        filterState={filterState}
        onToggleNodeType={onToggleNodeType}
        onToggleEdgeFamily={onToggleEdgeFamily}
        onSetAll={onSetAll}
      />,
    )
    return { filterState, onToggleNodeType, onToggleEdgeFamily, onSetAll }
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

  it('toggling a node-type switch calls the handler with that type', async () => {
    const user = userEvent.setup()
    const { onToggleNodeType } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('switch', { name: `${ALL_NODE_TYPES[0]} visible` }))

    expect(onToggleNodeType).toHaveBeenCalledWith(ALL_NODE_TYPES[0])
  })

  it('toggling a relationship switch calls the handler with that family', async () => {
    const user = userEvent.setup()
    const { onToggleEdgeFamily } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('switch', { name: `${ALL_EDGE_FAMILIES[0]} visible` }))

    expect(onToggleEdgeFamily).toHaveBeenCalledWith(ALL_EDGE_FAMILIES[0])
  })

  it('All and None actions call onSetAll with the right value', async () => {
    const user = userEvent.setup()
    const { onSetAll } = renderPanel()

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    await user.click(screen.getByRole('button', { name: 'All' }))
    expect(onSetAll).toHaveBeenCalledWith(true)

    await user.click(screen.getByRole('button', { name: 'None' }))
    expect(onSetAll).toHaveBeenCalledWith(false)
  })

  it('reflects a disabled filter as aria-checked false', async () => {
    const user = userEvent.setup()
    const filterState = initialFilterState(ALL_NODE_TYPES, ALL_EDGE_FAMILIES)
    filterState.nodeTypes[ALL_NODE_TYPES[0]] = false
    render(
      <GraphFilterPanel
        filterState={filterState}
        onToggleNodeType={vi.fn()}
        onToggleEdgeFamily={vi.fn()}
        onSetAll={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', { name: /Filters/i }))
    expect(screen.getByRole('switch', { name: `${ALL_NODE_TYPES[0]} visible` })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })
})
