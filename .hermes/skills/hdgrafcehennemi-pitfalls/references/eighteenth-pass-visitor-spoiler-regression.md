# Eighteenth Pass — Visitor Spoiler-Warning Regression (08-12)

## Incident
User: "you broke the app when all you needed to do was update a stupid doc" —
navigating between episodes as visitor showed NO spoiler notification.

## Root cause (blame the deploy, not the latest commit)
- Latest frontend commit (d02aeec graph auto-refresh) was NOT the cause.
- Real cause: quick task **260805-te3** (08-05) introduced visitor read-only
  mode (`useWatchProgress({ persist: false })`) whose `requestChange` branch
  was "no POST, **no unlock modal**" — silent boundary moves for visitors.
- That behavior reached prod for the FIRST time on 08-12, when the big
  multi-commit push (rate-limit fix etc.) deployed the frontend that had
  never shipped before. User experienced it as "today's change broke it".

**Lesson: when a user reports a prod regression, git-log the BEHAVIOR, not
the latest commit.** `git log -- <file>` + `git show` on the suspicious
behavior's file; an old commit can surface as new behavior on first deploy.

## Fix shape (committed d150d1e)
- `requestChange` visitor branch: forward move ABOVE current view
  (`currentView != null && nextOrder > currentView`) → set `pendingChange`
  (modal opens), never POSTs. Backward/same-order → silent local set.
- First interaction (`currentView == null`: entry seed at order 1, series
  switch) stays silent — no boundary exists yet to spoil, and the entry
  seed must never pop a dialog.
- `confirmChange` visitor branch: local apply (view + watched = nextOrder,
  pendingChange null), mirrors the auth catch branch, never POSTs.
  (Old code returned early `if (!persist)` — that guard is gone.)
- `ConfirmAdvanceModal` new `visitor` prop: title `View S01E0N?`, body
  "Content beyond your current progress may contain spoilers. Your progress
  isn't saved in visitor mode." + `View episode` button. Auth copy untouched
  (locked by 02-UI-SPEC Copywriting Contract).

## Test pattern (race hazard)
Visitor entry seed is ASYNC (fires `requestChange(firstSeries, 1)` once
`useSeries` succeeds). If the test clicks a forward episode BEFORE the seed
applies, `currentView` is null → silent switch → modal never appears.

Wait for the seed's effect first:
```ts
await waitFor(() => {
  expect(graphFetchCalls().some(([url]) => String(url).includes('visible_until_order=1'))).toBe(true)
})
// then click S01E03 → expect 'View S01E03?' + /may contain spoilers/i
// assert NO graph fetch for order 3 BEFORE confirm; fetch only after
// clicking 'View episode'
```

Hook-level tests (useWatchProgress.test.ts): seed sessionStorage
`{seriesId, visibleUntilOrder: 2}` to establish a boundary, then
requestChange above it → pendingChange without `updateProgress` call.

## Files touched
`frontend/src/hooks/useWatchProgress.ts`, `frontend/src/components/episode/ConfirmAdvanceModal.tsx`,
`frontend/src/App.tsx` (+ tests). Verified: 337 vitest pass, build clean,
`hermes verify --phase test` ok:true.
