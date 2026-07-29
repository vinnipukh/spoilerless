// Use the `/vitest` subpath so jest-dom's matcher types augment Vitest's
// `Assertion`/`AsymmetricMatchersContaining` interfaces (the bare
// `@testing-library/jest-dom` entry only augments Jest's global namespace,
// which leaves `expect(...).toBeInTheDocument()` untyped under `tsc -b`).
import '@testing-library/jest-dom/vitest'

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
