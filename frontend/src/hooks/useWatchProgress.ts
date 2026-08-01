import { useEffect, useState } from 'react'
import { getProgress, updateProgress } from '../api/progress'

// D-01/D-02/D-03: sessionStorage-backed watch-progress state, now also
// backend-authoritative (RAG-01, 06-10-PLAN.md).
//
// Hydration on mount reads directly into the initial state via a lazy
// useState initializer — this never goes through requestChange/confirmChange,
// so restoring from sessionStorage can never open ConfirmAdvanceModal
// (RESEARCH.md Pitfall 5). Only a live call to requestChange() sets
// pendingChange, which the modal watches.
//
// Backend wiring (06-10): sessionStorage is now only ever a loading-state
// placeholder / optimistic cache, never the source of truth once a backend
// response has arrived. A mount-time effect fetches the authoritative
// getProgress() record for whatever seriesId sessionStorage hydrated (if
// any) and overrides confirmedOrder from it; confirmChange() awaits
// updateProgress() before committing local state, preferring the backend's
// own echoed value when the write succeeds.

const STORAGE_KEY = 'hdgraf.watchProgress'

type Stored = {
  seriesId: string
  visibleUntilOrder: number
}

export type WatchProgressDirection = 'forward' | 'backward'

export type PendingChange = {
  seriesId: string
  nextOrder: number
  direction: WatchProgressDirection
}

type State = {
  seriesId: string | null
  confirmedOrder: number | null
  pendingChange: PendingChange | null
}

function readStored(): Stored | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (
      typeof parsed?.seriesId !== 'string' ||
      parsed.seriesId.length === 0 ||
      !Number.isInteger(parsed?.visibleUntilOrder) ||
      parsed.visibleUntilOrder < 1
    ) {
      return null
    }
    return { seriesId: parsed.seriesId, visibleUntilOrder: parsed.visibleUntilOrder }
  } catch {
    return null
  }
}

function writeStored(seriesId: string, visibleUntilOrder: number) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId, visibleUntilOrder }))
}

function initialState(): State {
  const stored = readStored()
  return {
    seriesId: stored?.seriesId ?? null,
    confirmedOrder: stored?.visibleUntilOrder ?? null,
    pendingChange: null,
  }
}

export function useWatchProgress() {
  const [state, setState] = useState<State>(initialState)

  // Mount-time hydration reconciliation: if sessionStorage remembered a
  // seriesId, fetch the backend's authoritative progress record for it and
  // override confirmedOrder from that response — even if it disagrees with
  // whatever sessionStorage held (that value was only ever a loading-state
  // placeholder). Intentionally mount-only (the seriesId captured here is
  // read once, from the initial render's closure) — confirmChange's own
  // await already keeps subsequent changes backend-authoritative without
  // needing this effect to re-run on every seriesId change.
  useEffect(() => {
    const seriesId = state.seriesId
    if (!seriesId) return
    let cancelled = false
    getProgress(seriesId)
      .then((progress) => {
        if (cancelled) return
        writeStored(progress.series_id, progress.visible_until_order)
        setState((prev) => ({
          ...prev,
          seriesId: progress.series_id,
          confirmedOrder: progress.visible_until_order,
        }))
      })
      .catch(() => {
        // Backend fetch failed (network error/401/etc.) — the
        // sessionStorage-hydrated value already in state stands as a
        // loading-state placeholder only; it is never (re-)marked
        // authoritative by this catch branch.
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function requestChange(seriesId: string, nextOrder: number) {
    const currentOrder = state.seriesId === seriesId ? state.confirmedOrder : null
    const baseline = currentOrder ?? 0
    if (nextOrder === baseline) return
    const direction: WatchProgressDirection = nextOrder > baseline ? 'forward' : 'backward'
    setState((prev) => ({ ...prev, pendingChange: { seriesId, nextOrder, direction } }))
  }

  async function confirmChange() {
    const pending = state.pendingChange
    if (!pending) return
    const { seriesId, nextOrder } = pending

    // Await the backend write before committing local state (RAG-01) —
    // requestChange/confirmChange/cancelChange's own signatures/behavior
    // stay exactly as ConfirmAdvanceModal already expects. A failed backend
    // write (network error, transient 5xx) still commits the optimistic
    // local/sessionStorage value rather than leaving the modal's "Confirm"
    // action hung or reverted — ConfirmAdvanceModal's existing UX contract
    // (confirm always closes the modal and applies the change) must not
    // change because of this addition.
    try {
      const progress = await updateProgress(seriesId, nextOrder)
      writeStored(progress.series_id, progress.visible_until_order)
      setState((prev) =>
        prev.pendingChange
          ? { seriesId: progress.series_id, confirmedOrder: progress.visible_until_order, pendingChange: null }
          : prev,
      )
    } catch {
      writeStored(seriesId, nextOrder)
      setState((prev) => (prev.pendingChange ? { seriesId, confirmedOrder: nextOrder, pendingChange: null } : prev))
    }
  }

  function cancelChange() {
    setState((prev) => ({ ...prev, pendingChange: null }))
  }

  return {
    seriesId: state.seriesId,
    confirmedOrder: state.confirmedOrder,
    pendingChange: state.pendingChange,
    requestChange,
    confirmChange,
    cancelChange,
  }
}
