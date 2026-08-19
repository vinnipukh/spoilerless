# Frontend: launch auto-refresh = exact Refresh-button action (0ff3829, replaces d02aeec)

## Pattern that survived (product owner, 08-12)
User requirement: at app launch, do exactly what the Refresh graph button does
(force re-layout + re-fit via `runLayout(cy, seriesId, visible_until_order,
true, mode)` — NOT a data refetch).

GraphCanvas mount-time effect, ref-guarded, runs once:

```tsx
const launchRefreshedRef = useRef(false)
useEffect(() => {
  const cy = cyInstanceRef.current
  if (!cy || launchRefreshedRef.current) return
  launchRefreshedRef.current = true
  runLayout(cy, seriesId, graph.visible_until_order, true, mode)
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

The Refresh button handler is literally
`onReset={() => { const cy = cyInstanceRef.current; if (cy) runLayout(cy, seriesId, graph.visible_until_order, true, mode) }}`
— the mount effect IS that call. Canvas only mounts when the app enters the
graph (cold load, login, visitor entry), so mount covers every launch path.
StrictMode dev double-mount is harmless (second run is a no-op via ref).

## Pitfall: first implementation was rejected (d02aeec, reverted in 0ff3829)
Original: App.tsx auth-transition signal machinery — `authRefreshSignal` state
+ `lastAuthStatusRef` + `authEntrySeenRef` + two effects + `refreshSignal`
prop + a `react-hooks/set-state-in-effect` lint warning. User: "auto refresh
graph thing still doesnt work. all you have to do is call what happens when
user presses refresh graph button at the launch of the app." It also never
fired on cold launch (status already `authenticated` → no transition).

**Lesson (product-owner style): "run handler X once at launch/entry" = a
mount-time effect calling X. No state machines, no cross-component signal
props, no transition detection. When the user prescribes the implementation,
implement literally that.** If a feature can be expressed as "mount → call the
existing handler", it can and should be.

## TS/React pitfalls hit while wiring the original (still valid)
1. **TDZ ordering**: an effect referencing a `const` declared LATER in the
   component body crashes (used-before-declaration). Place effects after the
   hooks/consts they read.
2. **Union narrowing does NOT apply inside the deps array**:
   `[graphState.status, graphState.data]` errors TS2339 even when the body
   narrows first — the deps expression is type-checked outside the guard.
   Fix: hoist `const graphData = graphState.status === 'success' ? graphState.data : null`
   and depend on `[graphData]`.
3. `react-hooks/set-state-in-effect` fires on setState-in-effect — if your
   design needs it, that is a smell: prefer the mount-effect-calls-handler
   shape above (lint stayed 0 warnings after the rewrite).

## hermes verify recipe quirks (repo, updated 08-12)
- **NODE_ENV=production persists in the session env** (terminal tool
  re-injects it; `unset` does NOT stick across calls). npm treats
  NODE_ENV=production as `omit=dev` → `hermes verify` bootstrap
  `npm install` PRUNES devDependencies (vitest, @testing-library/react
  vanish → build fails with TS2307/TS2882). Restore with
  `env -u NODE_ENV npm install`; run verify as
  `env -u NODE_ENV CI=1 hermes verify --phase test --json`.
- **Full `hermes verify --json` (no --phase) hangs**: recipe's
  `npm run test` = vitest watch mode without CI=1. Use `--phase test`
  (test + lint) — real recorded evidence, exits cleanly.
- Repo ROOT: detected recipe is generic FastAPI and wrong (`test: ["pytest"]`
  — bare pytest not on PATH; `start: uvicorn main:app` wrong entrypoint; real
  `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`).
  Fixing requires writing `.hermes/environment.json` (may be blocked). Don't
  trust failing root verify as evidence.
- FRONTEND dir: Vite recipe works. `hermes verify --phase test --json` from
  `frontend/` = recorded ok:true evidence (337 tests + eslint, 0 warnings
  after the rewrite).

## Docs-update note (GSD docs-update, SEVENTEENTH)
Stale claims to refresh when behavior changes: docs/CONFIGURATION.md §Rate
limiting & Redis cache ("can fail startup"), docs/ARCHITECTURE.md D-11 +
§7.14 ("not caught locally and can propagate"), docs/ops/runbook.md (sweep
driver key) — all fixed to degrade-not-fail semantics. CRLF files patch
cleanly (git normalizes; `git diff --stat` shows only real insertions).
