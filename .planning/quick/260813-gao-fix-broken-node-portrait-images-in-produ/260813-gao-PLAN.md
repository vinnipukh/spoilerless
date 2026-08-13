---
quick_id: 260813-gao
description: "Fix broken node portrait images in production: backend image_url is relative (/api/static/...), frontend must prefix with VITE_API_BASE_URL (works locally via vite proxy, 404 on spoilerless.net)"
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/api/client.ts
  - frontend/src/components/graph/graphElements.ts
  - frontend/src/components/detail/DetailPanel.tsx
  - frontend/src/components/graph/graphElements.test.ts
  - frontend/src/components/detail/DetailPanel.test.tsx
autonomous: true

estimate:
  tokens: 14000
  raw_tokens: 10000
  tasks: 2
  confidence: high

must_haves:
  truths:
    - A Character node whose image_url starts with '/' renders its portrait in production: Cytoscape background-image resolves to {VITE_API_BASE_URL}/api/static/... and the DetailPanel <img src> carries the same prefixed URL.
    - Relative image_url values are untouched when VITE_API_BASE_URL is '' (local dev via vite proxy) and absolute image_url values (external fandom/wikia) are never prefixed.
  artifacts:
    - frontend/src/api/client.ts exports an apiUrl(path) helper (prefixes only '/'-leading paths)
    - frontend/src/components/graph/graphElements.ts and frontend/src/components/detail/DetailPanel.tsx consume apiUrl for image_url
  key_links:
    - client.ts apiUrl (apiBase at client.ts:46) -> graphElements.ts:88 imageUrl -> data.imageUrl (graphElements.ts:114) -> graphStylesheet.ts:115-117 background-image: data(imageUrl)
    - client.ts apiUrl -> DetailPanel.tsx:78 <img src>
---

<objective>
Fix broken character portrait images in production by prefixing the backend's relative image_url (/api/static/characters/*.webp) with VITE_API_BASE_URL at both frontend consumption sites.

Purpose: The backend (data/dexter/seed/characters.json) serves image_url as a RELATIVE path. Locally this works because Vite proxies /api to the backend (vite.config.ts:17-18); in production the frontend origin (spoilerless.net on Vercel) resolves /api/static/... against itself → 404 → broken portraits. apiFetch already solves this exact problem for API calls via the internal apiBase (frontend/src/api/client.ts:46, '' when unset), but image_url bypasses apiFetch entirely.

Output: exported apiUrl() helper in client.ts; graphElements.ts and DetailPanel.tsx prefix image_url through it (only when the path starts with '/'); new tests proving the prefixed behavior under a stubbed VITE_API_BASE_URL; existing tests stay green.
</objective>

<context>
Diagnosis verified against current source (2026-08-13):

- `const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''` — frontend/src/api/client.ts:46, module-private, used only by apiFetch (client.ts:50). `''` preserves relative-URL local-dev behavior through the Vite proxy.
- Backend seed data is relative: `"image_url": "/api/static/characters/dexter_morgan.webp"` (data/dexter/seed/characters.json).
- Production code consumes node.image_url in EXACTLY two places (grep-confirmed, no other consumers):
  1. frontend/src/components/graph/graphElements.ts:88 — `const imageUrl = node.type === 'Character' ? node.image_url : null`, set into Cytoscape data at graphElements.ts:114 (`...(imageUrl ? { imageUrl } : {})`) and rendered by graphStylesheet.ts:115-117 (`node[nodeType = "Character"][imageUrl]` → `background-image: 'data(imageUrl)'`).
  2. frontend/src/components/detail/DetailPanel.tsx:65 (`showImage = Boolean(node?.image_url) && !failed`) and :78 (`src={node.image_url ?? undefined}`) inside CharacterPortrait.
- graphStylesheet.ts:100-113 comment: no `background-image-crossorigin` is INTENTIONAL (anonymous mode makes Cytoscape draw a broken-image glyph on cross-origin opaque responses) — do not touch the stylesheet. The prefixed URL will be cross-origin in production; the existing no-crossorigin behavior renders it correctly.
- graphElements.ts is a pure GraphResponse→ElementDefinition mapper (D-16 media rule: the imageUrl key feeds ONLY the background-image selector, never layout/sizing — prefixing changes the URL value, not presence, so D-16/D-14 invariants hold).
- Do NOT touch frontend/src/api/chat.ts:82 or frontend/src/api/export.ts:3 — they already prefix their own API request URLs with VITE_API_BASE_URL. Do NOT touch image_source_url (DetailPanel.tsx:98-100 renders it as an absolute external fandom link — apiUrl's '/'-only rule passes it through untouched).
- Existing tests and prefixing safety (all fixtures use ABSOLUTE wikia URLs or null, so no current test exercises a relative image_url):
  - graphElements.test.ts:6-11 asserts `dexter?.data.imageUrl` equals the fixture's absolute wikia URL verbatim → stays green because absolute paths are not prefixed. Imported function name is `graphToElements` (graphElements.test.ts:2).
  - DetailPanel.test.tsx:123-139 asserts alt text + the image_source_url link href, never the <img> src → stays green. DetailPanel test harness injects the graph as a prop: `const graph = graphResponseS01E01; const defaultProps = { graph, ... }` (DetailPanel.test.tsx:47-54) — a new test can pass a cloned graph with a relative image_url.
  - export.test.ts:21,31 uses image_url: null → unaffected.
- Env handling in tests TODAY: no vi.stubEnv anywhere; tests read `import.meta.env.VITE_API_BASE_URL` directly (chat.test.ts:16, progress.test.ts:94) and vitest resolves it as '' by default. Vitest keeps import.meta.env live (vi.stubEnv is documented to affect import.meta.env), so the NEW helper must read the env var INSIDE the function body (call time), not capture it in a module-scope const at import time — otherwise vi.stubEnv after import would not take effect. Use `vi.stubEnv('VITE_API_BASE_URL', 'https://api.spoilerless.net')` + `vi.unstubAllEnvs()` in afterEach.
- Conventions: atomic commits with explicit `git add <paths>` only (never `git add -A`), code commit and test commit separate, never commit .planning files. No DaisyUI; inline Tailwind (no styling changes in this task anyway).

@frontend/src/api/client.ts
@frontend/src/components/graph/graphElements.ts
@frontend/src/components/detail/DetailPanel.tsx
@frontend/src/components/graph/graphElements.test.ts
@frontend/src/components/detail/DetailPanel.test.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Export apiUrl() from client.ts and prefix image_url at both consumption sites</name>
  <files>frontend/src/api/client.ts, frontend/src/components/graph/graphElements.ts, frontend/src/components/detail/DetailPanel.tsx</files>
  <action>
    frontend/src/api/client.ts — add ONE exported helper next to apiBase (line 46), reusing the existing module-private const:

    `export function apiUrl(path: string | null): string | null` — return null for null/undefined input; return path unchanged when it does NOT start with '/'; otherwise return `${apiBase}${path}` (apiBase = import.meta.env.VITE_API_BASE_URL ?? '', read INSIDE the function body at call time — do NOT capture it in a new module-scope const — so vi.stubEnv works against it in tests). Do NOT change apiFetch, do NOT export apiBase itself, do NOT touch the ApiError class.

    frontend/src/components/graph/graphElements.ts — at line 88, replace `node.image_url` with the helper: `const imageUrl = node.type === 'Character' ? apiUrl(node.image_url) : null` (import `apiUrl` from '../../api/client'). Keep the surrounding logic byte-identical: the `[imageUrl]` presence gate at line 114 and the `simple` derivation at line 89 must not change (D-16: presence semantics and layout must stay untouched — only the URL value changes).

    frontend/src/components/detail/DetailPanel.tsx — at line 78, replace `src={node.image_url ?? undefined}` with `src={apiUrl(node.image_url) ?? undefined}` (import `apiUrl` from '../../api/client'). Keep `showImage` (line 65), the onError fallback, referrerPolicy, and the image_source_url link (lines 94-100) exactly as they are — the fandom link must NOT go through any prefixing.

    Do NOT modify graphStylesheet.ts (its no-crossorigin comment at lines 100-113 is intentional and the prefixed cross-origin URL renders correctly without it), chat.ts, or export.ts. Commit atomically (code-only) with explicit `git add frontend/src/api/client.ts frontend/src/components/graph/graphElements.ts frontend/src/components/detail/DetailPanel.tsx` — never `git add -A`, never stage .planning files.
  </action>
  <verify>
    <automated>cd frontend && npm run build && NODE_ENV=test CI=1 npm run test -- src/components/graph/graphElements.test.ts src/components/detail/DetailPanel.test.tsx</automated>
  </verify>
  <done>
    apiUrl exported from client.ts; with apiBase '' (default) a relative '/api/static/...' image_url maps to itself (local dev unchanged); graphElements.ts and DetailPanel.tsx both route image_url through apiUrl; tsc -b (npm run build) clean; graphElements.test.ts and DetailPanel.test.tsx pass unmodified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add prefixed-URL coverage for graphElements and DetailPanel</name>
  <files>frontend/src/components/graph/graphElements.test.ts, frontend/src/components/detail/DetailPanel.test.tsx</files>
  <action>
    Add tests proving the '/'→prefix rule, using `vi.stubEnv('VITE_API_BASE_URL', 'https://api.spoilerless.net')` with `vi.unstubAllEnvs()` in afterEach (first use of stubEnv in this suite — vitest keeps import.meta.env live, and the helper reads env at call time, so no vi.resetModules/dynamic import is needed):

    frontend/src/components/graph/graphElements.test.ts — extend the existing describe (do not modify the three existing tests at lines 6-28):
    1. Relative path IS prefixed: build a minimal inline GraphData (follow the inline-node pattern already used at graphElements.test.ts:138-148) whose Character node has image_url '/api/static/characters/dexter_morgan.webp'; stubEnv VITE_API_BASE_URL; call graphToElements; expect `el.data.imageUrl` === 'https://api.spoilerless.net/api/static/characters/dexter_morgan.webp'.
    2. Absolute path is NOT prefixed: same shape with image_url 'https://static.wikia.nocookie.net/...' (or reuse graphResponseS01E01's existing absolute fixture); expect imageUrl equals the input verbatim.
    3. Non-'/' edge: image_url 'api/static/...' (no leading slash) passes through unchanged.

    frontend/src/components/detail/DetailPanel.test.tsx — add one test using the existing renderPanel + defaultProps harness (DetailPanel.test.tsx:47-54): pass a cloned graph (`{ ...graph, nodes: graph.nodes.map((n) => n.id === 'char_dexter_morgan' ? { ...n, image_url: '/api/static/characters/dexter_morgan.webp' } : n) }`) with stubEnv VITE_API_BASE_URL; select char_dexter_morgan; expect `screen.getByAltText('Dexter Morgan')` to have `src` === 'https://api.spoilerless.net/api/static/characters/dexter_morgan.webp'. Do not touch the existing portrait tests (123-175) — they use absolute fixture URLs and must keep passing.

    Test-only commit, atomic: explicit `git add frontend/src/components/graph/graphElements.test.ts frontend/src/components/detail/DetailPanel.test.tsx` — never `git add -A`, never stage .planning files. No production files in this commit.
  </action>
  <verify>
    <automated>cd frontend && NODE_ENV=test CI=1 npm run test -- src/components/graph/graphElements.test.ts src/components/detail/DetailPanel.test.tsx && NODE_ENV=test CI=1 npm run test && npm run build</automated>
  </verify>
  <done>
    New tests pass; they fail (RED) if Task 1's apiUrl wiring is reverted, proving regression coverage; the FULL frontend suite (NODE_ENV=test CI=1 npm run test) and typecheck/build (npm run build) are green; no existing test was modified.
  </done>
</task>

</tasks>

<verification>
- cd frontend && npm run build — tsc -b typecheck gate (Task 1 + Task 2)
- cd frontend && NODE_ENV=test CI=1 npm run test — full frontend suite (Task 2)
- Manual spot check (optional, after deploy): open spoilerless.net with VITE_API_BASE_URL=https://api.spoilerless.net baked in — graph Character nodes and DetailPanel portraits load; dev server (no env var) still shows portraits via the /api proxy.
</verification>

<success_criteria>
- Production graph node portraits and DetailPanel portraits load from {VITE_API_BASE_URL}/api/static/characters/*.webp; local dev (apiBase '') and absolute external URLs behave exactly as before.
- Change is 2 atomic commits (code, tests), 5 files touched, no stylesheet/backend changes, existing suite untouched and green.
</success_criteria>
