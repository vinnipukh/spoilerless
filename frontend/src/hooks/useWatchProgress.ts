import { useEffect, useRef, useState } from 'react'
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
//
// PROB-31 / #56 (09-07): requestChange NEVER silently returns. A same-order
// click reconciles the view to the selector's displayed value (idempotent —
// never a bare `return`); the view-only branch AWAITS its POST and reports
// failure to the caller (App refetches the graph) so a failed persist never
// looks like "nothing happened"; and the mount-time hydration effect is
// serialized against user clicks (a late backend response can never clobber
// a just-committed click).

const STORAGE_KEY = 'spoilerless.watchProgress'

// Legacy sessionStorage key (pre-REBRAND-01). readStored falls back to it
// once when the new key is absent; writeStored removes it after writing the
// new key (T-09-01-02 migration spirit).
const LEGACY_STORAGE_KEY = 'hdgraf.watchProgress'

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
    const raw =
      sessionStorage.getItem(STORAGE_KEY) ?? sessionStorage.getItem(LEGACY_STORAGE_KEY)
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
  // One-time migration completion: drop the legacy key once the new key is written.
  sessionStorage.removeItem(LEGACY_STORAGE_KEY)
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

export function useWatchProgress(options?: { persist?: boolean }) {
  // Quick task 260805-te3: `persist: false` = read-only visitor (misafir)
  // mode. Progress writes are auth-gated (POST /progress → 401 anonymous),
  // so a visitor's boundary changes stay purely local: never POST, never
  // open the unlock modal, never touch the backend.
  const persist = options?.persist ?? true
  const [state, setState] = useState<State>(initialState)

  // Set by the first user-initiated interaction (requestChange/
  // confirmChange/cancelChange). The mount-time hydration response checks it
  // and SKIPS applying the backend record once the user has taken over —
  // serializing hydration against clicks so a late getProgress() response
  // can never clobber a just-committed click (PROB-31/#56 race). Written
  // only from event handlers/effects, never during render.
  const userInteractedRef = useRef(false)

  // Mount-time hydration reconciliation: if sessionStorage remembered a
  // seriesId, fetch the backend's authoritative progress record for it and
  // override the split fields from that response — even if it disagrees with
  // whatever sessionStorage held (that value was only ever a loading-state
  // placeholder). Intentionally mount-only (the seriesId captured here is
  // read once, from the initial render's closure) — confirmChange's own
  // await already keeps subsequent changes backend-authoritative without
  // needing this effect to re-run on every seriesId change. Skipped entirely
  // once the user has clicked (userInteractedRef) so hydration never rolls
  // back a committed selection (PROB-31).
  useEffect(() => {
    if (!persist) return // visitor mode: no backend progress to hydrate
    const seriesId = state.seriesId
    if (!seriesId) return
    let cancelled = false
    getProgress(seriesId)
      .then((progress) => {
        if (cancelled || userInteractedRef.current) return
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

  // Resolves true when the click's intent is surfaced (dialog opened, or the
  // view-only POST persisted); resolves false when a view-only POST failed —
  // the caller must refetch the graph so the UI never shows "nothing
  // happened" (PROB-31). Never silently returns.
  function requestChange(seriesId: string, nextOrder: number): Promise<boolean> {
    userInteractedRef.current = true

    // Visitor mode: purely local view switch — never POSTs. Forward moves
    // ABOVE the current view still open ConfirmAdvanceModal (spoiler
    // warning, visitor copy) so a visitor is never silently pushed into
    // future-episode content (260805-te3 originally skipped the modal
    // entirely — reverted 08-12: "no notification telling me I can see
    // spoilers"). First interaction (currentView null: entry seed,
    // series switch) never modals — there is no established boundary yet
    // to spoil, and the entry seed must not pop a dialog.
    if (!persist) {
      const currentView = state.seriesId === seriesId ? state.viewAsOfOrder : null
      if (currentView != null && nextOrder > currentView) {
        setState((prev) => ({
          ...prev,
          seriesId,
          pendingChange: { seriesId, nextOrder, direction: 'forward' },
        }))
        return Promise.resolve(true)
      }
      setState((prev) => ({ ...prev, seriesId, viewAsOfOrder: nextOrder }))
      return Promise.resolve(true)
    }

    const currentView = state.seriesId === seriesId ? state.viewAsOfOrder : null
    const watched = state.seriesId === seriesId ? state.watchedThroughOrder : null

    // Same-order click (PROB-31): reconcile the view to the selector's
    // displayed value — an idempotent write, never a silent return. When the
    // clicked episode is already-watched this also re-affirms it to the
    // backend with the awaited view-only POST so state, selector and backend
    // agree.
    if (nextOrder === currentView) {
      setState((prev) => ({ ...prev, viewAsOfOrder: nextOrder }))
      if (watched != null && nextOrder <= watched) {
        return updateProgress(seriesId, nextOrder, { viewAsOfOrder: nextOrder })
          .then(() => true)
          .catch(() => false)
      }
      return Promise.resolve(true)
    }

    // Already-watched selection = view-only change (PROG-01, D-06): update
    // the temporary boundary immediately, persist with a view-only POST, and
    // never open the unlock confirmation. Never lowers watchedThroughOrder.
    // The POST is AWAITED and failure is surfaced to the caller (App refetches
    // the graph) — a failed persist must never look like a silent no-op
    // (PROB-31/#56).
    if (watched != null && nextOrder <= watched) {
      setState((prev) => ({ ...prev, viewAsOfOrder: nextOrder }))
      return updateProgress(seriesId, nextOrder, { viewAsOfOrder: nextOrder })
        .then(() => true)
        .catch(() => false)
    }

    // Above watchedThroughOrder (or no progress record yet) = the unlock
    // flow: a forward locked-episode click ALWAYS opens ConfirmAdvanceModal
    // (PROB-31).
    const baseline = currentView ?? 0
    const direction: WatchProgressDirection = nextOrder > baseline ? 'forward' : 'backward'
    setState((prev) => ({ ...prev, pendingChange: { seriesId, nextOrder, direction } }))
    return Promise.resolve(true)
  }

  async function confirmChange() {
    userInteractedRef.current = true
    const pending = state.pendingChange
    if (!pending) return
    const { seriesId, nextOrder } = pending

    // Visitor mode: the modal is a pure spoiler warning — confirm applies
    // the view locally (mirrors the auth catch branch) and never POSTs.
    if (!persist) {
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
      return
    }

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
    userInteractedRef.current = true
    setState((prev) => ({ ...prev, pendingChange: null }))
  }

  // PROB-09/#61: navigation-only series switch — the dropdown/dashboard
  // "Open series" must move the graph to the new series IMMEDIATELY (a
  // stale old-series graph otherwise stays on screen until an episode
  // click). This is NOT a watch action: never opens ConfirmAdvanceModal,
  // resets the boundary to the fail-closed NULL (same empty state as the
  // mount-time initial render — no reveal until the user picks an episode,
  // which then goes through the normal unlock flow), leaves nothing watched,
  // and cancels any in-flight pending change. Setting viewAsOfOrder=1 here
  // would pre-select S01E01 in the episode selector, and Radix Select does
  // not fire onValueChange for a re-selected value — the first unlock click
  // would be swallowed entirely.
  function switchSeries(seriesId: string) {
    userInteractedRef.current = true
    writeStored(seriesId, 1)
    setState((prev) =>
      prev.seriesId === seriesId
        ? prev
        : {
            seriesId,
            watchedThroughOrder: null,
            viewAsOfOrder: null,
            pendingChange: null,
          },
    )
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
    switchSeries,
  }
}
