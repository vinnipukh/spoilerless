import { useEffect, useState } from 'react'
import { getProgress, updateProgress } from '../api/progress'

// D-01/D-02/D-03: sessionStorage-backed watch-progress state, now also
// backend-authoritative (RAG-01, 06-10-PLAN.md). Since the D-05 split
// (07-02) the model separates the highest contiguous confirmed order
// (`watchedThroughOrder`) from the temporary spoiler boundary
// (`viewAsOfOrder`); `confirmedOrder` is kept as the alias of the CURRENT
// VIEW (effective) so all existing consumers (graph boundary, badge,
// selector value) stay semantically correct without renames.
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
// any) and overrides the split fields from it; confirmChange() awaits
// updateProgress() before committing local state, preferring the backend's
// own echoed values when the write succeeds.
//
// PROG-01 / D-06 (07-03): selecting an already-watched episode is a
// VIEW-ONLY change — it updates viewAsOfOrder locally (and persists it with
// a view-only POST) WITHOUT opening the unlock confirmation and never lowers
// watchedThroughOrder. Only selecting ABOVE watchedThroughOrder goes through
// the pendingChange/confirmChange modal flow, whose copy states Episodes
// 1 through N will be considered watched.

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
  // Highest contiguous confirmed-watched order (D-05).
  watchedThroughOrder: number | null
  // Temporary spoiler boundary — what the graph/chat currently show.
  viewAsOfOrder: number | null
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

// The stored shape stays {seriesId, visibleUntilOrder} (visibleUntilOrder =
// the effective view) — backward compatible with the pre-split format; the
// D-07 migration initializes watched = view = the stored value.
function writeStored(seriesId: string, visibleUntilOrder: number) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId, visibleUntilOrder }))
}

function initialState(): State {
  const stored = readStored()
  return {
    seriesId: stored?.seriesId ?? null,
    watchedThroughOrder: stored?.visibleUntilOrder ?? null,
    viewAsOfOrder: stored?.visibleUntilOrder ?? null,
    pendingChange: null,
  }
}

export function useWatchProgress() {
  const [state, setState] = useState<State>(initialState)

  // Mount-time hydration reconciliation: if sessionStorage remembered a
  // seriesId, fetch the backend's authoritative progress record for it and
  // override the split fields from that response — even if it disagrees with
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
        writeStored(progress.series_id, progress.effective_view_order)
        setState((prev) => ({
          ...prev,
          seriesId: progress.series_id,
          watchedThroughOrder: progress.watched_through_order,
          viewAsOfOrder: progress.view_as_of_order,
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
    const currentView = state.seriesId === seriesId ? state.viewAsOfOrder : null
    if (nextOrder === currentView) return
    const watched = state.seriesId === seriesId ? state.watchedThroughOrder : null

    // Already-watched selection = view-only change (PROG-01, D-06): update
    // the temporary boundary immediately, persist with a view-only POST, and
    // never open the unlock confirmation. Never lowers watchedThroughOrder.
    if (watched != null && nextOrder <= watched) {
      setState((prev) => ({ ...prev, viewAsOfOrder: nextOrder }))
      updateProgress(seriesId, nextOrder, { viewAsOfOrder: nextOrder }).catch(() => {
        // View-only persistence failed (network error) — the local boundary
        // stays; the next forward confirm re-syncs from the backend.
      })
      return
    }

    const baseline = currentView ?? 0
    const direction: WatchProgressDirection = nextOrder > baseline ? 'forward' : 'backward'
    setState((prev) => ({ ...prev, pendingChange: { seriesId, nextOrder, direction } }))
  }

  async function confirmChange() {
    const pending = state.pendingChange
    if (!pending) return
    const { seriesId, nextOrder } = pending

    // Forward confirm marks Episodes 1..N watched AND views them (D-06):
    // watched_through_order = view_as_of_order = N. Await the backend write
    // before committing local state (RAG-01). A failed backend write still
    // commits the optimistic local/sessionStorage value — ConfirmAdvanceModal's
    // existing UX contract (confirm always closes the modal and applies the
    // change) must not change.
    try {
      const progress = await updateProgress(seriesId, nextOrder, {
        watchedThroughOrder: nextOrder,
        viewAsOfOrder: nextOrder,
      })
      writeStored(progress.series_id, progress.effective_view_order)
      setState((prev) =>
        prev.pendingChange
          ? {
              seriesId: progress.series_id,
              watchedThroughOrder: progress.watched_through_order,
              viewAsOfOrder: progress.view_as_of_order,
              pendingChange: null,
            }
          : prev,
      )
    } catch {
      writeStored(seriesId, nextOrder)
      setState((prev) =>
        prev.pendingChange
          ? {
              seriesId,
              watchedThroughOrder: nextOrder,
              viewAsOfOrder: nextOrder,
              pendingChange: null,
            }
          : prev,
      )
    }
  }

  function cancelChange() {
    setState((prev) => ({ ...prev, pendingChange: null }))
  }

  return {
    seriesId: state.seriesId,
    // Current view (effective boundary) — kept under the legacy name so App
    // wiring (graph boundary, episode badge, selector value) stays correct.
    confirmedOrder: state.viewAsOfOrder,
    watchedThroughOrder: state.watchedThroughOrder,
    viewAsOfOrder: state.viewAsOfOrder,
    pendingChange: state.pendingChange,
    requestChange,
    confirmChange,
    cancelChange,
  }
}
