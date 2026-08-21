---
last_mapped: 2026-08-20
focus: tech
last_mapped_commit: 5ad68675e20b4c9b69e9b88335286b5e2f6f04fa
---

# Technology Stack

**Analysis Date:** 2026-08-20

## Languages

**Primary:**
- Python 3.13+ - FastAPI application, Neo4j repositories, domain models, graph seeding, spoiler filtering, retrieval, visualization projections, and LLM orchestration under `spoilerless/app/`; the requirement is declared in `pyproject.toml` and locked in `uv.lock`.
- TypeScript 6.0.3 - Browser application and tooling under `frontend/src/`; use strict, bundler-oriented ES modules configured by `frontend/tsconfig.app.json`.
- TSX / React JSX - React components, providers, hooks, and tests under `frontend/src/`; JSX uses the `react-jsx` transform from `frontend/tsconfig.app.json`.

**Secondary:**
- CSS - Tailwind v4 entry styles and application-specific styling in `frontend/src/index.css` and `frontend/src/App.css`.
- YAML - Graph ontology declarations in `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml`; seed/setup code loads them through `spoilerless/app/graph/ontology.py`.
- JSON - Dexter seed and metadata under `data/dexter/`, npm metadata in `frontend/package.json`, and UI generator configuration in `frontend/components.json`.
- Cypher - Embedded Neo4j queries live primarily in `spoilerless/app/repository/`, `spoilerless/app/retrieval/tools.py`, and `spoilerless/app/graph/`.

## Source Inventory

**Application and test source, excluding generated, vendor, planning, documentation, and data trees:**
- Python: 132 files / 40,200+ lines under `spoilerless/` (80 app, 52 tests, 1 script). New since 2026-08-14: `spoilerless/app/api/boundary.py` (shared fail-closed boundary resolver, D-01) and hardening across `spoilerless/app/cache/graph_cache.py`, `spoilerless/app/core/config.py`, `spoilerless/app/main.py`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/services/chat.py` (concurrency), `spoilerless/app/graph/candidates.py` (+ 316-line `spoilerless/tests/test_security_boundary.py`). No new dedicated Phase-11 module beyond `boundary.py`.
- TSX: 82 files / 15,200+ lines under `frontend/src/` (updated: `frontend/src/components/graph/GraphCanvas.tsx` now has controlled/uncontrolled mode seam; `frontend/src/App.tsx` wires `mode`/`onModeChange`).
- TypeScript: 72 files / 8,100+ lines under `frontend/src/` plus frontend configuration (newly promoted: `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines) + `frontend/src/components/graph/cytoscapeReconciler.test.ts` (91 lines) — reconciler is now tracked; `frontend/src/lib/visualizationAdapter.ts`, `frontend/src/hooks/useSceneState.ts` unchanged).
- CSS: 2 files / 174 lines under `frontend/src/` (updated: `frontend/src/components/graph/graphStylesheet.ts` + `relationshipStyles.ts` palette tweaks).

Use these counts as a scale baseline when estimating changes; do not count `frontend/node_modules/`, build output, or `.planning/` as product source.

## Runtime

**Environment:**
- CPython 3.13 or newer is required by `pyproject.toml`; `uv.lock` resolves for Python 3.13+.
- Node.js `^22.13.0 || >=24.0.0` is required by the locked Vite package in `frontend/package-lock.json`.
- Browser runtime targets ES2023 and DOM APIs through `frontend/tsconfig.app.json`.
- Neo4j Community is the only containerized runtime service; `docker-compose.yml` resolves to the single service `neo4j` using image `neo4j:2026.06.0-community`. An optional Upstash Redis instance (`REDIS_URL`) backs rate limiting and the graph/visualization cache.

**Package Manager:**
- uv manages Python environments and dependencies from `pyproject.toml`; exact resolution is committed in `uv.lock` (unchanged since 2026-08-14).
- npm manages frontend packages from `frontend/package.json`; exact resolution uses lockfile version 3 in `frontend/package-lock.json`.
- Docker Compose orchestrates local Neo4j only; run the Python backend and Vite frontend as host processes rather than expecting `docker-compose.yml` to start them.

## Frameworks

**Core:**
- FastAPI 0.140.7 - ASGI REST API, dependency injection, OpenAPI, middleware, lifecycle, and SSE entry points in `spoilerless/app/main.py` and `spoilerless/app/api/`. Since 08-14, `spoilerless/app/main.py` adds pure-ASGI `BodySizeLimitMiddleware` (413 on `max_body_size_bytes` overage, D-08), `TrustedHostMiddleware` derived from `allowed_hosts` / `FRONTEND_ORIGINS`, CORS via `CORSMiddleware`, and docs-off in production (`environment == "production"` disables `/docs`, `/redoc`, `/openapi.json`).
- Pydantic 2.13.4 - strict request/response and domain models under `spoilerless/app/domain/`, including visualization DTOs in `spoilerless/app/domain/visualization.py` and hardened `ProposeChangesetInput` (`operations` now `max_length=20`, D-07).
- pydantic-settings 2.14.2 - environment-backed backend settings in `spoilerless/app/core/config.py` (now 209 lines). New fields since 08-14: `environment`, `rate_limit_fail_open` (D-05 fail-closed throttling), `allowed_hosts`, `max_body_size_bytes` (D-08), `llm_max_concurrent_generations` (D-07 semaphore), `llm_max_tool_calls_per_round` (D-07 per-round cap). Neo4j connection fields now carry safe local defaults (`bolt://127.0.0.1:7687`, `neo4j`, `hdgraf-local-password`) while still honoring `Aura*` aliases.
- React 19.2.8 and React DOM 19.2.8 - single-page browser UI rooted at `frontend/src/main.tsx` and `frontend/src/App.tsx` (now supports controlled mode seam `mode`/`onModeChange` forwarded to `GraphCanvas`).
- Tailwind CSS 4.3.3 with `@tailwindcss/vite` 4.3.3 - styling pipeline registered in `frontend/vite.config.ts`.
- shadcn 4.16.0 / Radix UI 1.6.7 / Lucide React 1.28.0 - component conventions and primitives configured by `frontend/components.json` and implemented under `frontend/src/components/ui/`.
- Cytoscape.js 3.34.0, react-cytoscapejs 2.0.0, cytoscape-fcose 2.2.0 (default layout), cytoscape-dagre 4.0.0 (left-to-right layout for investigation view, registered via `cytoscape.use(dagre)` in `frontend/src/components/graph/layoutConfig.ts`), cose-bilkent 4.1.0 (fallback) - interactive graph rendering in `frontend/src/components/graph/GraphCanvas.tsx`. `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines, fully tracked) now drives all scene updates via `reconcileCytoscapeElements()` inside `cy.batch()`. `frontend/src/lib/visualizationAdapter.ts` maps typed DTOs to Cytoscape elements.

**Testing:**
- pytest 9.1.1 and pytest-asyncio 1.4.0 - backend test runner configured in `pyproject.toml`; tests are under `spoilerless/tests/` (52 modules; new 316-line boundary suite `spoilerless/tests/test_security_boundary.py` covers D-01 fail-closed anonymous/progress cases).
- HTTPX 0.28.1 - FastAPI test/client support and injectable transport for LLM-provider tests; declared in dev dependency group.
- Vitest 4.1.10 with jsdom 30.0.1 - frontend tests configured in `frontend/vite.config.ts` and initialized by `frontend/src/test/setup.ts`. New: `frontend/src/components/graph/cytoscapeReconciler.test.ts` (91 lines, headless Cytoscape reconciler coverage).
- Testing Library React 16.3.2, jest-dom 7.0.0, user-event 14.6.1 - component interaction and DOM assertions.

**Build/Dev:**
- Uvicorn 0.51.0 - ASGI development/runtime server for `spoilerless.app.main:app`.
- Vite 8.1.5 and `@vitejs/plugin-react` 6.0.3 - frontend dev server and production bundle configured in `frontend/vite.config.ts`.
- TypeScript compiler 6.0.3 - `npm run build` performs `tsc -b` before `vite build`, as defined in `frontend/package.json`.
- ESLint 10.8.0 with typescript-eslint and React hook/refresh plugins - frontend static analysis configured in `frontend/eslint.config.js`.
- The `spoilerless-setup` console entry point maps to `spoilerless.app.graph.setup:main` in `pyproject.toml`; use it to create constraints and seed the graph after Neo4j is available.

## Key Dependencies

**Critical:**
- neo4j 6.2.0 - async Bolt driver; lifecycle in `spoilerless/app/graph/database.py`. Windows TLS fix stays: `neo4j+s://` normalized to `neo4j://` + `TrustCustomCAs(certifi.where())`.
- google-auth 2.56.2 with requests support - verifies Google ID tokens in `spoilerless/app/services/auth.py`.
- HTTPX 0.28.1 - async streaming HTTP transport for Gemini and OpenAI-compatible providers in `spoilerless/app/llm/provider.py`.
- PyYAML 6.0.3 - loads ontology and seed-support YAML through `spoilerless/app/graph/ontology.py`.
- python-dotenv 1.2.2 - supports local environment loading alongside pydantic-settings.
- redis 8.1.0 - async Redis client for rate limiting and graph/visualization caching in `spoilerless/app/cache/redis_client.py`. New cache guard: `_focus_capacity_allows` bounds per-series focus signatures to `FOCUS_SET_CAP=64` with 3600s TTL (`spoilerless/app/cache/graph_cache.py:54-75`).
- fastapi-limiter 0.2.0 (with pyrate-limiter) - Redis-backed request throttling in `spoilerless/app/services/rate_limit.py`. Now honors `rate_limit_fail_open == False` + `environment == "production"` to return 503 on Redis outage (SEC-DOS-001); local dev with empty `REDIS_URL` still degrades to no-op as before.
- cytoscape-dagre 4.0.0 (exact pin) with `@types/cytoscape-dagre` 2.3.4 - dagre layout for investigation view; no separate `dagre` package.

**Infrastructure:**
- Neo4j stores canonical graph data, user-created graph data, revisions, users, sessions, progress, chat history, change sets, share tokens, and `AppSetting` nodes; access stays behind `spoilerless/app/repository/` and `spoilerless/app/graph/database.py`.
- Redis (optional, Upstash `rediss://`) backs rate limiting and cache-aside graph/visualization caching; all Redis access flows through `spoilerless/app/cache/`.
- FastAPI publishes OpenAPI automatically. Direct `app.openapi()` probe still reports 39 path templates and 52 operations from `spoilerless/app/main.py` (boundary factoring is internal; no new path template since 08-14).
- FastAPI serves local static media through `app.mount("/api/static", StaticFiles(...))` in `spoilerless/app/main.py` (363 lines); holds character portraits under `spoilerless/app/static/characters/`.
- Vite proxies `/api` to host FastAPI during development via `frontend/vite.config.ts`; production routing must handle `/api` including `/api/static` and `Host` validation.

## Configuration

**Environment:**
- Backend configuration uses `Settings` in `spoilerless/app/core/config.py` (209 lines): process environment overrides root `.env`, defaults fill optional fields, unknown variables ignored, `get_settings()` caches one instance.
- A root `.env` file is present and sensitive; note existence only and never read, quote, or commit it. Use `.env.example` for variable-name templates.
- Required database variable names are `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` (now with safe local defaults but no default on Aura-style deploy); optional `NEO4J_DATABASE`.
- Authentication uses `GOOGLE_CLIENT_ID`, `SESSION_COOKIE_NAME`, `SESSION_TTL_SECONDS`, `SESSION_COOKIE_SECURE`, `FRONTEND_ORIGINS`; plus `ENVIRONMENT`, `ALLOWED_HOSTS`, `MAX_BODY_SIZE_BYTES`, `RATE_LIMIT_FAIL_OPEN` (see `spoilerless/app/core/config.py:80-105`).
- Optional rate-limit/cache uses `REDIS_URL` in `spoilerless/app/core/config.py`; empty disables both. In production, `RATE_LIMIT_FAIL_OPEN=false` makes Redis outage surface as 503 on gated routes.
- Optional chat config uses the `LLM_*` fields; now includes `LLM_MAX_CONCURRENT_GENERATIONS` (default 4, semaphore in `spoilerless/app/services/chat.py`) and `LLM_MAX_TOOL_CALLS_PER_ROUND` (default 8, cap in `spoilerless/app/retrieval/pipeline.py`). Runtime overrides via `spoilerless/app/services/settings.py` / `ChatService`.
- Frontend build-time configuration is templated in `frontend/.env.example`. `VITE_GOOGLE_CLIENT_ID` consumed by `frontend/src/components/auth/LoginPage.tsx`. `VITE_API_BASE_URL` prefixes every `apiFetch` request and `apiUrl()` image URLs at call time (`frontend/src/api/client.ts`).

**Build:**
- Frontend build and test plugins, `@` alias, `/api` proxy, and jsdom setup are in `frontend/vite.config.ts`.
- TypeScript project references are in `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`.
- Tailwind/shadcn aliases and CSS-variable conventions are in `frontend/components.json`; entry point is `frontend/src/index.css`.
- Python dependency and pytest config is centralized in `pyproject.toml`; preserve `uv.lock` on any resolution change.

## Platform Requirements

**Development:**
- Install Python 3.13+, uv, Node.js satisfying Vite 8, npm, Docker, Docker Compose; authoritative manifests are `pyproject.toml`, `uv.lock`, `frontend/package.json`, `frontend/package-lock.json`.
- Start only Neo4j with `docker-compose.yml`, then run setup, backend, frontend separately.
- Keep Neo4j available for backend integration tests: `spoilerless/tests/conftest.py` and repositories are designed around a real graph.
- Preserve spoiler boundary in backend data access; frontend filtering is not a substitute for `spoilerless/app/spoiler/`, `spoilerless/app/repository/`, and `spoilerless/app/retrieval/` filtering. `VisualizationProjectionService` still consumes only safe `GraphResponse` detail and enforces boundary-before-projection (D-05).
- Verification scripts `run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, `verify_arch.py` are stdlib-only claim checkers (untracked, hard-coded repo root).

**Production:**
- Render deployment is defined by `render.yaml`: free-tier `spoilerless-api` web service (`uv sync --frozen`, `uv run uvicorn spoilerless.app.main:app`) that auto-deploys on push. Frontend `frontend/vercel.json` now carries explicit security headers: `Content-Security-Policy` (default-src 'self', script-src self + accounts.google.com, img-src self data: https:, connect-src self accounts.google.com, frame-src accounts.google.com), `Strict-Transport-Security` (31536000 includeSubDomains), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
- Backend production hardens at `spoilerless/app/main.py`: `BodySizeLimitMiddleware` rejects bodies > `MAX_BODY_SIZE_BYTES` (default 1 MiB) with `{"detail":{"code":"payload_too_large"}}` and 413 (header pre-check + streaming chunk count, D-08); `TrustedHostMiddleware` allowlist derives from `ALLOWED_HOSTS` or `FRONTEND_ORIGINS` hosts + `localhost`/`127.0.0.1`/`testserver`; docs are disabled when `ENVIRONMENT=production`; `warn_if_open_signup` emits loud startup warning on open signup (11-05 wiring).
- CI is GitHub Actions in `.github/workflows/ci.yml` plus `release.yml`.
- Production must provide HTTPS, secure cookie behavior, route `/api` (including `/api/static`) to FastAPI, host built frontend, and supply external Neo4j, optional Upstash Redis, and provider configuration.
- `LICENSE` is present (MIT, Spoilerless Team); README demo disclaimer in `README.md` remains.

## Map Delta (2026-08-20 vs 2026-08-14 / 5bd1641)

- **No dependency change:** `pyproject.toml` / `uv.lock` / `frontend/package.json` / `frontend/package-lock.json` unchanged since 08-14 — Phase-11 is middleware/config/pipeline hardening, not new packages. `frontend/package-lock.json` still only owes `cytoscape-dagre` 4.0.0 from the 08-12 map.
- **New backend module:** `spoilerless/app/api/boundary.py` (66 lines) — single shared `resolve_effective_boundary()` (D-01, SEC-BE-001) replacing ad-hoc graph/series/path boundary clamps; consumes `spoilerless/app/spoiler/policy.py:effective_view_order` + `ProgressService`.
- **Hardened core modules (no new files, behavioral delta):**
  - `spoilerless/app/main.py` (363 lines, +128): adds `BodySizeLimitMiddleware` (D-08, 413 envelope), `TrustedHostMiddleware` via `_trusted_hosts()`, production docs-off, `warn_if_open_signup()` startup call, and `_docs_kwargs` gating.
  - `spoilerless/app/core/config.py` (209 lines, +40): adds `environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes` (ge=1024, default 1 MiB), `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`; Neo4j defaults now `bolt://127.0.0.1:7687` / `neo4j` / `hdgraf-local-password` with `Aura*` aliases retained.
  - `spoilerless/app/cache/graph_cache.py` (286 lines, +27): adds `FOCUS_SET_CAP=64` + `FOCUS_SET_TTL_SECONDS=3600` + `_focus_capacity_allows()` to bound per-series focus-signature cardinality (D-12) before `set_cached_visualization` stores.
  - `spoilerless/app/retrieval/pipeline.py` (+67/-unknown): adds `_neutralize_answer_delimiters()` (escapes exact `<CONTEXT_SECTIONS>` tags in answers), caps `ProposeChangesetInput.operations` at 20, and delegates `propose_changeset` to `ChangeSetService.propose_via_tool` (QUAL-02 thin delegation).
  - `spoilerless/app/core/errors.py` (+17): aligns error envelope with new 413 code `payload_too_large`.
  - `spoilerless/app/domain/settings.py` (+83): validates base URLs (http/https + host), exposes masked suffix, allows loopback/private hosts for compatible servers.
  - `spoilerless/app/services/rate_limit.py` (+68): fail-closed path when `rate_limit_fail_open is False` and `environment == "production"` (503 on Redis outage).
  - `spoilerless/app/services/chat.py` (+28): adds process-wide `asyncio.Semaphore` bound by `llm_max_concurrent_generations` (D-07) alongside per-user slot.
  - `spoilerless/app/graph/candidates.py` (+99) and `spoilerless/app/domain/extraction.py` (+8): candidate ingest hardening (progress scoping, series_id filtering).
  - `spoilerless/app/retrieval/context.py` (+26), `spoilerless/app/revisions/__init__.py` (+36), `spoilerless/app/services/change_set.py` (+41): delimiter neutralization, revision wiring, `propose_via_tool` extraction.
- **API factoring:** `spoilerless/app/api/graph.py` (-92 lines) deletes the inline `_resolve_effective_boundary` (previously 69 lines) and re-exports the shared `spoilerless/app/api/boundary.py` resolver via `_resolve_effective_boundary = resolve_effective_boundary` for backward compat of visualization/expand/path/export call sites.
- **Frontend promoted + new hardening:**
  - `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines) + `frontend/src/components/graph/cytoscapeReconciler.test.ts` (91 lines) — reconciler is now fully tracked (was untracked on 08-14); `GraphCanvas.tsx` (50-line delta) adds controlled/uncontrolled mode seam (`mode`/`onModeChange`), stabilizes `initialElementsRef`/`initialLayoutRef` to stop react-cytoscapejs uncontrolled relayout, and exposes `useImperativeReconcileRef` guard.
  - `frontend/src/api/client.ts` (2-line delta) — call-site prefix handling unchanged, retained for `VITE_API_BASE_URL`.
  - `frontend/src/components/graph/graphStylesheet.ts` + `relationshipStyles.ts` palette tweaks (4+34 lines).
  - `frontend/vercel.json` (14-line delta) — now carries full security-header block (CSP, HSTS, nosniff, DENY, referrer-policy) instead of sole rewrites entry.
  - `frontend/index.html` adds GIS CSP alignment (`https://accounts.google.com` already present); `frontend/src/App.tsx` threads controlled mode; `frontend/src/hooks/useWatchProgress.ts` narrows storage handling.
- **Tests:** New `spoilerless/tests/test_security_boundary.py` (316 lines) exercises shared boundary (anonymous fixed at 1, no-progress fail-closed, clamped min(...)), plus deltas in `test_candidate_ingest.py` (+86), `test_candidate_review.py` (+31), `test_visualization_cache.py` (+18 covering focus-cap), plus minor `test_auth.py`/`test_revisions.py`/`test_user_content_api.py`.
- **Untracked artifacts unchanged in status:** `.hermes/` (now 181 skill files), and the four stdlib-only verification scripts at repo root remain untracked.

---

*Stack analysis: 2026-08-20*
