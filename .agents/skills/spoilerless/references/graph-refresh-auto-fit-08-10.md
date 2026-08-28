# Graph auto-refresh on open — StrictMode double-mount layout skip (08-10, fix `ef91fee`)

## Symptom (user report)
Every app open (after login or visitor entry) showed the graph "diagonal" / bad
positions at the default zoom-1 origin. Pressing the Reset zoom button always
fixed it — the user had to click it every time.

## Root cause (dev/StrictMode only — prod single-mount is immune)
- `frontend/src/main.tsx` wraps the app in `<StrictMode>` → React's dev build
  double-mounts every component (mount → simulated unmount → remount).
- The layout effect in GraphCanvas.tsx (`useEffect` deps
  `[graph, focusedElementIds, revealTarget, seriesId, mode]`) dedupes with refs
  `lastLayoutGraphRef` / `lastLayoutModeRef`. **Refs survive the StrictMode
  remount (same fiber), but react-cytoscapejs creates a NEW cytoscape instance**
  (class component: componentDidMount → destroy → componentDidMount).
- On the second (LIVE) cy: `graphChanged = lastLayoutGraphRef.current !== graph`
  computed FALSE (the ref was already set by the first effect run on the dead
  cy#1) → early return → `runLayout` (the ONLY fit:true authority) never ran on
  the live instance.
- Result: only the declarative `layout` prop applied —
  `layoutOptionsFor(..., fit=false)` (fit deliberately false per the 08-06
  comment: the declarative prop must not zoom out on remount) → nodes laid out
  at the default zoom-1 pan-0 origin → the "diagonal" view.
- The Reset zoom button fixed it because `onReset` calls
  `runLayout(..., forceRelayout=true)` which bypasses the guard entirely.

## Fix (`ef91fee`)
- The dedupe guard is keyed to the cy INSTANCE: added `lastLayoutCyRef`.
  `cyChanged = lastLayoutCyRef.current !== cy` (ref updated every effect run);
  `graphChanged = lastLayoutGraphRef.current !== graph || cyChanged`;
  `runLayout(..., modeChanged || cyChanged, ...)`.
- Any new cy (StrictMode's live instance, the destructive-loading remount on
  refetch, episode switch) now forces a fresh fcose layout + fit + Overview
  zoom floor — exactly the Refresh action, automatically. In-place graph
  changes (same cy, e.g. `onRefreshGraph` edits) keep the cached-position
  restore + 20s auto-zoom-hold semantics (hold still protects non-remount
  graph-change layouts).
- Button renamed "Reset zoom" → "Refresh graph" (GraphControls.tsx aria-label +
  tooltip). RotateCcw icon kept. Nothing in the FE suite referenced the old
  label (rg gate clean).

## Test-stub accuracy rule (GraphCanvas.test.tsx)
- The old stub created a NEW fakeCy object on EVERY render. Real
  react-cytoscapejs hands the SAME cy instance to `props.cy` on every update
  and a NEW one on remount (StrictMode double-mount included). Any per-cy
  logic (like this guard) can only be tested with an accurate stub:
  `const fakeCy = useMemo(() => makeFakeCy(), [])` — new per mount, stable
  across plain rerenders.
- `makeFakeCy()` must build the object as `const fakeCy = {...}` then
  `return fakeCy` — a `return { layout: () => uses fakeCy }` form is a
  ReferenceError at layout() call time (the binding is the caller's variable).

## Regression test
- Render `<StrictMode><GraphCanvas .../></StrictMode>` in vitest — NODE_ENV=test
  keeps React in dev mode, so StrictMode double-mount actually happens.
- The layout spy records the cy instance: `layoutCalls.push({ fit, cy: fakeCy })`.
  Assert `layoutCalls.at(-1).fit === true && layoutCalls.at(-1).cy ===
  capturedCy` — the LIVE instance must have received the fit layout. RED on the
  old guard (the last call is on the dead cy#1), GREEN on the fix.

## Pre-existing-flake proof nuance
The 3 full-suite failures (App.test e2e ×2 + SettingsPage "trims whitespace")
reproduce with AND without the change — proven by stashing the 3 changed files
and running the FULL suite both ways. Running only the failing files in
isolation passes on BOTH trees, so an isolation-only comparison is NOT proof
for full-suite-only flakes. (See "Pre-existing-reds proof technique" in the
main skill — run the full suite on the clean tree, not just the failing files.)

## Verification (all post-edit)
- GraphCanvas.test.tsx 25/25 (incl. the new StrictMode test, 0 act warnings —
  the 2-3 act warnings in full runs are pre-existing).
- Changed-surface vitest (GraphCanvas + App + SettingsPage) 49/49.
- `npm run build` BUILD_EXIT=0.
- DB-free pytest `uv run pytest spoilerless/tests/test_user_content_models.py`
  23/23 — remember `unset PYTHONPATH` first (hermes venv shadows pydantic_core).
