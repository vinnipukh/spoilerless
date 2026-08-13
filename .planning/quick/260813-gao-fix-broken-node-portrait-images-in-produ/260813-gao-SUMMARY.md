---
quick_id: 260813-gao
status: complete
key-files.created:
  - frontend/src/api/client.ts (new exported apiUrl(path) helper: prefixes only '/'-leading paths with VITE_API_BASE_URL, read at call time; null/undefined -> null; '' -> path unchanged; absolute http(s) URLs and bare relative segments untouched)
  - frontend/src/components/graph/graphElements.ts (Character portrait imageUrl data key now routed through apiUrl)
  - frontend/src/components/detail/DetailPanel.tsx (CharacterPortrait <img src> now routed through apiUrl)
  - frontend/src/components/graph/graphElements.test.ts (+3 tests: relative /api/static prefixed, absolute URL untouched, non-leading-slash passes through — first vi.stubEnv usage in the suite, vi.unstubAllEnvs() in afterEach)
  - frontend/src/components/detail/DetailPanel.test.tsx (+1 test: relative image_url renders prefixed <img src> via the defaultProps graph-injection harness)
---

# Summary

Production node portraits were 404ing because the backend serves `image_url` as a RELATIVE `/api/static/characters/<name>.webp` path: local dev worked through the Vite /api proxy, but on spoilerless.net the frontend origin resolved the path against itself. Added `apiUrl(path)` to `frontend/src/api/client.ts` — it prefixes ONLY '/'-leading paths with `VITE_API_BASE_URL`, reading the env at CALL time (not module scope, so `vi.stubEnv` works; no vi.stubEnv existed in the suite before) and returning `''`-base input unchanged — and routed both consumption sites through it: the Cytoscape `imageUrl` data key in `graphElements.ts:88` (background-image selector in graphStylesheet.ts untouched, per its intentional no-crossorigin note) and the DetailPanel portrait `<img src>` (`DetailPanel.tsx:78`). Absolute external fandom/wikia URLs and local-dev vite-proxy behavior are unchanged; `chat.ts`/`export.ts`/`image_source_url` deliberately untouched.

## Verification

- Task 1 verify: `npm run build` (tsc -b + vite) exit 0; targeted `NODE_ENV=test CI=1 npm run test -- src/components/graph/graphElements.test.ts src/components/detail/DetailPanel.test.tsx` → 2 files / 35 tests passed (existing tests unmodified).
- Task 2 verify: targeted same command → 2 files / 39 tests passed (35 existing + 4 new); full suite `NODE_ENV=test CI=1 npm run test` → 40 files / **342 tests passed**; `npm run build` → **exit 0**.
- Pre-existing dirty files (`.planning/config.json`, `.planning/tmp/docs-work-manifest.json`, untracked verification scripts, etc.) untouched — explicit `git add <paths>` only, no `.planning` files committed.

## Commits

- `73ed961` feat(quick-260813-gao): prefix relative image_url with VITE_API_BASE_URL at both portrait consumption sites (Task 1: client.ts, graphElements.ts, DetailPanel.tsx)
- `5f53e4f` test(quick-260813-gao): cover apiUrl prefixing of relative image_url in graph elements and detail panel (Task 2: graphElements.test.ts, DetailPanel.test.tsx)

## Self-check

- A Character node with a relative `/api/static/...` image_url renders its portrait in production: Cytoscape background-image resolves to `{VITE_API_BASE_URL}/api/static/...` and the DetailPanel `<img src>` carries the same prefixed URL (locked by 4 new tests; they fail if Task 1's wiring is reverted).
- Relative URLs are untouched when `VITE_API_BASE_URL` is `''` (local dev via vite proxy — default test env, all pre-existing tests green) and absolute external URLs are never prefixed.
- No stylesheet/backend changes; graphStylesheet.ts no-crossorigin behavior intentionally preserved; change is exactly 2 atomic commits / 5 files.
