# Graph canvas declutter — 08-05 (user-directed, VERIFIED live)

User complaint: graph is a hairball ("i cant understand anything"). Two asks:
1. More distance between nodes.
2. Pictureless nodes with < 3 edges → Obsidian-style simple dots.

All three files shipped + verified (vitest graph dir 37/37, `npm run build` exit 0).

## The .d.ts trap (user pointed at the WRONG file)

User asked to change `frontend/src/types/cytoscape-cose-bilkent.d.ts` to force
node spacing. That file is a **type-only shim** (6 lines:
`declare module 'cytoscape-cose-bilkent' { const ext: Ext }`) — editing it has
ZERO runtime effect. The real layout knobs live in
`GraphCanvas.tsx layoutOptionsFor()` (:52-64). Rule: when a user points at a
`*.d.ts` for behavioral change, check whether it declares runtime config or is
just a module shim — trace to the actual consumer (`rg "cose-bilkent" src`)
before editing. Don't touch the shim; explain and change the real site.

## Layout values that worked (cose-bilkent, shared with 'cose' fallback)

```
nodeRepulsion: 45000   // was 8000  — strong spread
idealEdgeLength: 240   // was 100   — longer ideal edges
edgeElasticity: 0.25   // was 0.45  — less edge tension
gravity: 0.08          // added     — weak center pull (default 0.25)
animate: prefersReducedMotion ? false : 'end'
```

Both `cose-bilkent` and the built-in `cose` fallback use the same key names,
so one `common` object works for both (same direction).

## `simple`-node pattern (Obsidian-style dots)

- **graphElements.ts**: degree map from the backend-filtered `graph.edges`
  list ONLY (satisfies the D-16 layout rule — filtered lists are allowed, hidden
  totals are not), then
  `const simple = !imageUrl && (degree.get(node.id) ?? 0) < 3` stamped as
  `data.simple: true`. Boundary test: exactly 3 edges is NOT simple.
- **graphStylesheet.ts** `node[simple]` block: `shape: ellipse, width/height: 13,
  background-color: #64748B (slate-500), border 1px rgba(255,255,255,0.12),
  color: #94A3B8, font-size: 9, text-margin-y: 4`.

### Cytoscape stylesheet specificity rules (durable, bite twice)

1. **Equal specificity → LATER stylesheet entry wins** (Cytoscape applies in
   order). `node[simple]` (spec 2) must be placed AFTER every per-type
   shape/color selector (`node[nodeType="Character"]` is also spec 2) or the
   type styles win.
2. **Attribute+class selectors are spec 3**: `node[nodeType="Character"].selected-dominant`
   (width 51) beats `node[simple]` (spec 2) — a selected simple Character would
   jump to 51px. Fix: add `node[simple].selected-dominant` (width 20) AFTER all
   per-type selected bumps (all spec 3, later wins).
3. The portrait selector `node[nodeType="Character"][imageUrl]` (spec 3) can
   never match a `simple` node because `simple` requires no imageUrl.

## D-16 media-rule deviation (user-directed, do NOT revert)

`graphElements.ts:15-20` D-16 forbade image PRESENCE from driving node sizing
(spoiler-inference: a masked above-boundary portrait could be inferred from a
smaller node). The product owner explicitly overrode this on 08-05. The
deviation is documented in the graphElements.ts comment (NOTE block). A future
executor citing D-16 to "fix" the simple-node sizing must NOT revert it — see
the main SKILL.md "Graph declutter" bullet.

## Proving full-suite reds are NOT yours (stash technique)

Full FE suite showed 20 reds (`DetailPanel.test.tsx` 16, `App.test.tsx` 4)
while my graph-dir tests passed 37/37. Proof they were pre-existing (sibling
Claude Code's in-flight work — `.planning/` + docs manifest dirty):

```
git stash push -m check -- frontend/src/components/graph/   # only MY files
NODE_ENV=test CI=1 npx vitest run src/App.test.tsx src/components/detail/DetailPanel.test.tsx
# → identical 20 failed | 13 passed on clean tree
git stash pop
```

Same-failure-count on the clean tree = pre-existing, not introduced. Don't
fix sibling's reds (out of scope); report the proof.

## Local run recipe (docker often down — Aura fallback works)

- `docker ps` failed (daemon down) — irrelevant: root `.env` points at AuraDB
  (`NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io`, `NEO4J_DATABASE=<dbid>`),
  backend connects directly.
- Backend: `unset PYTHONPATH && uv run python -m uvicorn spoilerless.app.main:app --host 127.0.0.1 --port 8000` (background).
- Frontend: `npm run dev` in `frontend/` (background) — vite serves `localhost:5173`,
  proxies `/api` → `127.0.0.1:8000` (vite.config.ts:17-19).
- Verify: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health` (200),
  then a REAL route through the proxy:
  `curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173/api/series/series_dexter/graph?visible_until_order=1"` (200).
  `/api/health` is NOT a route (404) — don't use it as the proxy check.
- User expectation: after frontend work, they want the app running + the
  localhost URL handed over (open the preview pane with `open_preview`).
- Curl on this MSYS host exits 23 on `-o /dev/null` pipelines — read the
  `-w` code, ignore the exit code.

## Killing the local servers (Windows orphaned-child trap, 08-05)

`process kill` on the background bash/npm wrapper **orphans the child**:
after killing vite's wrapper the port still answered 200 — `node.exe` kept
LISTENING. Verified kill sequence:

```
curl -s -o /dev/null --max-time 3 -w '%{http_code}' http://localhost:5173/   # 200 = survivor
netstat -ano | grep ':5173' | grep LISTEN                                     # last col = PID
powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"               # works
# taskkill //F //PID <pid> FAILS under MSYS: "Invalid argument/option - '//F'"
curl ... # re-verify → 000
```

Always re-verify the port is actually free after a kill; if not, netstat +
`Stop-Process`. (uvicorn's wrapper dies cleanly; vite's npm wrapper leaves
the node child.)

## Prod-readiness evidence pattern ("how close to prod?")

Fast one-shot status without deploy logs:
- `git rev-list --left-right --count origin/main...HEAD` → 0 left / N right =
  origin is a pure ancestor, N commits unpushed.
- `curl https://api.spoilerless.net/health` → the `service` field is emitted
  by app code (`main.py` title), so `hdgrafcehennemi-backend` = pre-rebrand
  (pre-09-01) code is live — a deploy-vintage sniff.
- `gh run list --limit 6` → CI staleness (last green date).
- Plan inventory: `ls .planning/phases/<phase>/*-PLAN.md` + `git log` (ROADMAP
  tracking lags — git log is ground truth).

## fcose caveat (09-14 PROB-32)

The layout values above are **cose-bilkent key names** (`nodeRepulsion`,
`idealEdgeLength`, `edgeElasticity`, `gravity`). 09-14's fcose swap replaces
cose-bilkent with a compound-parent cluster layout — different parameters,
different tuning. The `simple` dot styling survives, but re-validate the
spacing knobs under fcose before closing that plan.
