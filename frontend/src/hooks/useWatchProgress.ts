import { useState } from 'react'

// D-01/D-02/D-03: sessionStorage-backed watch-progress state.
//
// Hydration on mount reads directly into the initial state via a lazy
// useState initializer — this never goes through requestChange/confirmChange,
// so restoring from sessionStorage can never open ConfirmAdvanceModal
// (RESEARCH.md Pitfall 5). Only a live call to requestChange() sets
// pendingChange, which the modal watches.

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

  function requestChange(seriesId: string, nextOrder: number) {
    const currentOrder = state.seriesId === seriesId ? state.confirmedOrder : null
    const baseline = currentOrder ?? 0
    if (nextOrder === baseline) return
    const direction: WatchProgressDirection = nextOrder > baseline ? 'forward' : 'backward'
    setState((prev) => ({ ...prev, pendingChange: { seriesId, nextOrder, direction } }))
  }

  function confirmChange() {
    setState((prev) => {
      if (!prev.pendingChange) return prev
      const { seriesId, nextOrder } = prev.pendingChange
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ seriesId, visibleUntilOrder: nextOrder }))
      return { seriesId, confirmedOrder: nextOrder, pendingChange: null }
    })
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
