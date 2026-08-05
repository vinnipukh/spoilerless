import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, renderHook } from '@testing-library/react'
import { useHotkey } from './useHotkey'

function dispatchKey(key: string, init: KeyboardEventInit = {}) {
  fireEvent.keyDown(window, { key, ...init })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useHotkey', () => {
  it('fires mod+k for Ctrl+K', () => {
    const handler = vi.fn()
    renderHook(() => useHotkey('mod+k', handler))

    dispatchKey('k', { ctrlKey: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('fires mod+k for Meta+K (⌘K)', () => {
    const handler = vi.fn()
    renderHook(() => useHotkey('mod+k', handler))

    dispatchKey('k', { metaKey: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not fire mod+k for a bare k', () => {
    const handler = vi.fn()
    renderHook(() => useHotkey('mod+k', handler))

    dispatchKey('k')
    expect(handler).not.toHaveBeenCalled()
  })

  it("does not fire the bare '/' combo while a modifier is held", () => {
    const handler = vi.fn()
    renderHook(() => useHotkey('/', handler))

    dispatchKey('/', { ctrlKey: true })
    expect(handler).not.toHaveBeenCalled()
  })

  it("skips '/' while an input is focused (T-09-09-03 — never hijack typing)", () => {
    const handler = vi.fn()
    renderHook(() => useHotkey('/', handler, { skipWhenInputFocused: true }))

    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()

    fireEvent.keyDown(input, { key: '/' })
    expect(handler).not.toHaveBeenCalled()

    // Same combo fires when nothing editable is focused.
    dispatchKey('/')
    expect(handler).toHaveBeenCalledTimes(1)

    input.remove()
  })

  it('removes the listener on unmount', () => {
    const handler = vi.fn()
    const { unmount } = renderHook(() => useHotkey('escape', handler))

    unmount()
    dispatchKey('Escape')
    expect(handler).not.toHaveBeenCalled()
  })

  it('keeps the latest handler without re-registering (ref pattern)', () => {
    const first = vi.fn()
    const second = vi.fn()
    const { rerender } = renderHook(({ handler }) => useHotkey('mod+k', handler), {
      initialProps: { handler: first },
    })

    rerender({ handler: second })
    dispatchKey('k', { ctrlKey: true })

    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
  })
})
