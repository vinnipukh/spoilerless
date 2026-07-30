// Use the `/vitest` subpath so jest-dom's matcher types augment Vitest's
// `Assertion`/`AsymmetricMatchersContaining` interfaces (the bare
// `@testing-library/jest-dom` entry only augments Jest's global namespace,
// which leaves `expect(...).toBeInTheDocument()` untyped under `tsc -b`).
import '@testing-library/jest-dom/vitest'

// Polyfill for React 19 canary (19.2.x) which doesn't export `React.act`.
// react-dom/test-utils expects it; without it all tests that touch React
// throw "React.act is not a function". We keep the import after the
// jest-dom import so vitest's module graph processes it correctly.
import React from 'react'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
if (typeof (React as any).act !== 'function') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(React as any).act = (fn: () => void) => fn()
}

// jsdom does not implement these browser APIs; the shadcn/Radix primitives
// used throughout this component tree (Select, Dialog, Sheet) call them
// during open/close and viewport-measurement logic. Without these stubs,
// interacting with those primitives under jsdom throws.
Element.prototype.hasPointerCapture = () => false
Element.prototype.setPointerCapture = () => {}
Element.prototype.releasePointerCapture = () => {}
Element.prototype.scrollIntoView = () => {}

globalThis.ResizeObserver =
  globalThis.ResizeObserver ??
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

// MatchMedia polyfill — GraphCanvas.tsx calls window.matchMedia at module scope
// to detect prefers-reduced-motion. jsdom doesn't implement it.
console.log('[SETUP] before matchMedia polyfill, typeof:', typeof window.matchMedia)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})
