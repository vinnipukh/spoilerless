// Global keyboard-shortcut hook (FEAT-08, plan 09-09). Registers one
// window keydown listener per combo with proper cleanup, and keeps the
// latest handler in a ref so inline-arrow handlers never re-register the
// listener on every render.
//
// Combos: 'mod+k' (⌘K / Ctrl+K), '/' , 'escape', 'ctrl+k', 'shift+?' …
// `mod` means metaKey OR ctrlKey (platform-agnostic).
//
// T-09-09-03 ('/' must not hijack typing): pass
// `{ skipWhenInputFocused: true }` so the combo is ignored while an
// input/textarea/select/contenteditable is focused.

import { useEffect, useRef } from 'react'

// Module-scope platform capture — the same pattern GraphCanvas.tsx uses for
// prefers-reduced-motion (:29-31): read once at module load, never per
// render, so kbd hints are stable and SSR-safe.
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform ?? '')

/** '⌘' on macOS, 'Ctrl' elsewhere — for kbd hints (palette trigger). */
export function modLabel(): string {
  return isMac ? '⌘' : 'Ctrl'
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable
}

function matchesCombo(combo: string, event: KeyboardEvent): boolean {
  const parts = combo.toLowerCase().split('+')
  const key = parts[parts.length - 1]
  const wantsMod = parts.includes('mod')
  const wantsCtrl = parts.includes('ctrl')
  const wantsShift = parts.includes('shift')
  const wantsAlt = parts.includes('alt')

  if (event.key.toLowerCase() !== key) return false
  if (wantsMod && !(event.metaKey || event.ctrlKey)) return false
  // Bare combos ('/', 'escape') must not fire while a modifier is held.
  if (!wantsMod && !wantsCtrl && (event.metaKey || event.ctrlKey)) return false
  if (wantsCtrl && !event.ctrlKey) return false
  if (wantsShift && !event.shiftKey) return false
  if (wantsAlt && !event.altKey) return false
  return true
}

export type UseHotkeyOptions = {
  /** Ignore the combo while an input/textarea/select/contenteditable is
   * focused (T-09-09-03 — '/' must never hijack typing). */
  skipWhenInputFocused?: boolean
}

export function useHotkey(
  combo: string,
  handler: (event: KeyboardEvent) => void,
  options: UseHotkeyOptions = {},
) {
  const { skipWhenInputFocused = false } = options

  // Latest-handler ref (written in an effect, the documented
  // react-hooks/refs-safe pattern) so the window listener below registers
  // once per combo, not once per render.
  const handlerRef = useRef(handler)
  useEffect(() => {
    handlerRef.current = handler
  })

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (!matchesCombo(combo, event)) return
      if (skipWhenInputFocused && isEditableTarget(event.target)) return
      handlerRef.current(event)
    }
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
  }, [combo, skipWhenInputFocused])
}
