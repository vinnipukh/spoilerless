# Frontend API base URL, node portrait images (image_url), and GSD quick-plan authoring

Verified against source 2026-08-13 (quick task 260813-gao).

## VITE_API_BASE_URL usage map
- `frontend/src/api/client.ts:46` — `const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''` (module-private, used by apiFetch at :50). `''` → relative URLs through the Vite proxy (`vite.config.ts:17-18`, `/api` → backend).
- Same per-module const is duplicated at `chat.ts:82` and `export.ts:3`. This duplication is the ESTABLISHED pattern — do not "fix" it by importing from client.ts unless the task explicitly asks.
- No `vi.stubEnv` anywhere in the suite; tests read `import.meta.env.VITE_API_BASE_URL` directly (chat.test.ts:16, progress.test.ts:94) and vitest resolves it as `''` by default.

## vi.stubEnv pitfall (vitest)
- vitest keeps `import.meta.env` live, so `vi.stubEnv('VITE_API_BASE_URL', url)` DOES affect `import.meta.env` reads — but only reads executed at CALL time. A helper that captures env into a module-scope const at import time ignores `vi.stubEnv` called after import (this suite uses no vi.resetModules/dynamic-import dance).
- Rule: any helper that must be testable via stubEnv reads `import.meta.env` inside the function body, not at module scope. Cleanup with `vi.unstubAllEnvs()` in afterEach.

## image_url (node portraits) — consumption map
- Backend seed data is RELATIVE: `"image_url": "/api/static/characters/<name>.webp"` (data/dexter/seed/characters.json). Local dev works via the vite proxy; prod (Vercel frontend + api.spoilerless.net backend) 404s unless prefixed.
- EXACTLY two prod consumers (grep-confirmed):
  1. `frontend/src/components/graph/graphElements.ts:88` — `const imageUrl = node.type === 'Character' ? node.image_url : null` → `data.imageUrl` (:114) → `graphStylesheet.ts:115-117` `background-image: 'data(imageUrl)'`. The no-`background-image-crossorigin` comment (graphStylesheet.ts:100-113) is INTENTIONAL (anonymous mode makes Cytoscape draw a broken-image glyph) — never add it.
  2. `frontend/src/components/detail/DetailPanel.tsx:65/78` — CharacterPortrait `<img src={...}>` with onError → initials avatar. `image_source_url` (external fandom link, :94-100) must NOT be prefixed.
- Fix pattern (260813-gao): export `apiUrl(path: string | null): string | null` from client.ts — null passthrough; return unchanged unless path starts with `/`; else `` `${apiBase}${path}` `` (env read at call time). The `/`-only rule keeps absolute fixture URLs (static.wikia.nocookie.net) untouched, so existing tests stay green.
- Fixture note: `test/fixtures/graphResponse.ts` uses absolute wikia URLs or null — no existing test exercises a relative image_url. To test prefixing: clone the fixture graph in the test (DetailPanel harness injects graph via `defaultProps` at DetailPanel.test.tsx:47-54; graphElements.test.ts uses inline-node patterns at :138-148).

## GSD quick-plan authoring (this repo)
- `C:\Users\arhan\AppData\Local\hermes\gsd-core\templates\plan.md` does NOT exist even though gsd-planner.md references it. Quick-mode format = `gsd-core/workflows/quick.md` constraints (1-3 atomic tasks; each task MUST have files/action/verify/done; must_haves in frontmatter) + the most recent committed `.planning/quick/*/PLAN.md` as the concrete format reference. Current convention: 260813-ftl-PLAN.md style — full frontmatter (`quick_id`, `description`, `type`, `wave`, `depends_on`, `files_modified`, `autonomous`, `estimate`, `must_haves`) + `<objective>` + `<context>` (verified facts + @file refs) + `<tasks>` + `<verification>` + `<success_criteria>`.
- Naming: `.planning/quick/YYYYMMDD-{slug}/` containing `{quick_id}-PLAN.md` where `quick_id` = `YYMMDD-{short}` (e.g. `260813-gao`). If the orchestrator supplies the directory path, use it verbatim even when the slug looks truncated.
- Planning-only sessions: do NOT modify source; never commit .planning files; keep per-task verify commands runnable and under a minute where possible.

## Frontend-only verification gates (validated 260813-gao execution)
- `cd frontend && npm run build` (tsc -b + vite; typechecks src incl. test files) — exit 0.
- `cd frontend && NODE_ENV=test CI=1 npm run test` (full vitest suite) or targeted `NODE_ENV=test CI=1 npm run test -- <paths>`.
- `hermes verify` on this repo detects the BACKEND FastAPI recipe (`uv sync` → `pytest` → `uvicorn main:app` port 8000, needs live AuraDB Neo4j) — confirmed via `hermes verify --detect-only --json` (2026-08-13). It is NOT the gate for frontend-only changes (its start phase is environmentally blocked and pytest covers untouched `spoilerless/` code); state this concretely when the verification harness pushes pytest/full-boot.
- Windows tooling quirk (2026-08-13): `search_files` fails on this host with absolute paths — both `C:\...` and `C:/...` forms throw an MSYS "path not found" IO error. Use `terminal` grep/ls or relative paths from repo root; `read_file` accepts Windows paths fine.

## Test-construction gotchas (260813-gao tests, all green)
- Inline minimal GraphData for `graphToElements` must keep the portrait Character node CONNECTED (at least one edge) or isolated-node pruning drops it and `el.data.imageUrl` is undefined.
- `vi.stubEnv` tests: put `vi.unstubAllEnvs()` in `afterEach` inside the describe (no-op when nothing stubbed); import `afterEach` from vitest alongside `vi`.
- Prefix-rule coverage shape that worked: relative `/api/static/...` → prefixed; absolute wikia URL → verbatim; bare `api/static/...` → unchanged (3 graphElements tests) + 1 DetailPanel test asserting `<img src>` via the defaultProps graph clone.
- Commit split that worked: `feat(quick-260813-gao): ...` (3 source files) then `test(quick-260813-gao): ...` (2 test files), explicit `git add <paths>` only; SUMMARY.md left untracked for the orchestrator.
