---
last_mapped: 2026-08-26
focus: tech
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---

# Technology Stack

**Analysis Date:** 2026-08-26

## Languages

**Primary:**
- Python 3.13+ - FastAPI application, Neo4j repositories, domain models, graph seeding, spoiler filtering, retrieval, visualization projections, and LLM orchestration under `spoilerless/app/`; the requirement is declared in `pyproject.toml` and locked in `uv.lock`.
- TypeScript 6.0.3 - Browser application and tooling under `frontend/src/`; use strict, bundler-oriented ES modules configured by `frontend/tsconfig.app.json`.
- TSX / React JSX - React components, providers, hooks, and tests under `frontend/src/`; JSX uses the `react-jsx` transform from `frontend/tsconfig.app.json`.

**Secondary:**
- CSS - Tailwind v4 entry styles, theme tokens, and application-specific styling in `frontend/src/index.css` and `frontend/src/App.css`.
- YAML - Graph ontology declarations in `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml`; seed/setup code loads them through `spoilerless/app/graph/ontology.py`.
- JSON - Dexter seed and metadata under `data/dexter/`, npm metadata in `frontend/package.json`, and UI generator configuration in `frontend/components.json`.
- Cypher - Embedded Neo4j queries live primarily in `spoilerless/app/repository/`, `spoilerless/app/retrieval/tools.py`, `spoilerless/app/graph/`, and `spoilerless/app/spoiler/filter.py`.

## Source Inventory

**Application and test source, excluding generated, vendor, planning, documentation, and data trees:**
- Python: 146 files / 43,600+ lines under `spoilerless/` (93 app files / 20,207 lines, 53 test files / 23,441 lines). Phase 12 modularity changes: `spoilerless/app/services/visualization.py` decomposed into package `spoilerless/app/services/visualization/` (8 modules, 1,280 lines), `spoilerless/app/revisions/` split into `repository.py`, `service.py`, and `__init__.py`, `spoilerless/app/services/graph.py` facade, and `spoilerless/app/api/boundary.py` with `require_boundary` dependency.
- TSX: 91 files / 15,150+ lines under `frontend/src/` (Phase 12 decomposed `App.tsx` down to 291 lines, `GraphCanvas.tsx` to 426 lines, `DetailPanel.tsx` to 180 lines; added `tabs/OverviewTab.tsx`, `tabs/ClaimsTab.tsx`, `tabs/EvidenceTab.tsx`, `tabs/NotesTab.tsx`, `CharacterPortrait.tsx`, `dialogs/CreateCustomNodeDialog.tsx`, `dialogs/CreateRelationshipDialog.tsx`, `layout/AppIcons.tsx`, `layout/ResizableRail.tsx`).
- TypeScript: 75 files / 8,450+ lines under `frontend/src/` plus frontend configuration (newly added: `frontend/src/lib/tokens/graphTokens.ts`, `frontend/src/lib/graph/sceneElements.ts`, `frontend/src/lib/graph/positionCache.ts`, `frontend/src/components/graph/useCytoscapeLayout.ts`, `frontend/src/hooks/useWorkspaceScene.ts`, `frontend/src/hooks/useWorkspaceNavigation.ts`).
- CSS: 2 files / 176 lines under `frontend/src/` (centralized theme variables and graph token references).

Use these counts as a scale baseline when estimating changes; do not count `frontend/node_modules/`, build output, or `.planning/` as product source.

## Runtime

**Environment:**
- CPython 3.13 or newer is required by `pyproject.toml`; `uv.lock` resolves for Python 3.13+.
- Node.js `^22.13.0 || >=24.0.0` is required by the locked Vite package in `frontend/package-lock.json`.
- Browser runtime targets ES2023 and DOM APIs through `frontend/tsconfig.app.json`.
- Neo4j Community is the only containerized runtime service; `docker-compose.yml` resolves to the single service `neo4j` using image `neo4j:2026.06.0-community`. An optional Upstash Redis instance (`REDIS_URL`) backs rate limiting and the graph/visualization cache.

**Package Manager:**
- uv manages Python environments and dependencies from `pyproject.toml`; exact resolution is committed in `uv.lock`.
- npm manages frontend packages from `frontend/package.json`; exact resolution uses lockfile version 3 in `frontend/package-lock.json`.
- Docker Compose orchestrates local Neo4j only; run the Python backend and Vite frontend as host processes rather than expecting `docker-compose.yml` to start them.

## Frameworks

**Core:**
- FastAPI 0.140.7 - ASGI REST API, dependency injection, OpenAPI, middleware, lifecycle, and SSE entry points in `spoilerless/app/main.py` and `spoilerless/app/api/`. `spoilerless/app/main.py` provides pure-ASGI `BodySizeLimitMiddleware` (413 on `max_body_size_bytes` overage), `TrustedHostMiddleware` with wildcard fallback support for `*.onrender.com`, CORS via `CORSMiddleware`, and docs-off in production (`environment == "production"` disables `/docs`, `/redoc`, `/openapi.json`).
- Pydantic 2.13.4 - strict request/response and domain models under `spoilerless/app/domain/`, including visualization DTOs in `spoilerless/app/domain/visualization.py`, `ProposeChangesetInput` in `spoilerless/app/domain/change_set.py`, and privacy-scrubbed user content models (`NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse` with `user_id: Optional[str] = None`).
- pydantic-settings 2.14.2 - environment-backed backend settings in `spoilerless/app/core/config.py` (209 lines). Settings include `environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`. Neo4j connection fields carry safe local defaults (`bolt://127.0.0.1:7687`, `neo4j`, `hdgraf-local-password`) while honoring `Aura*` aliases.
- React 19.2.8 and React DOM 19.2.8 - single-page browser UI rooted at `frontend/src/main.tsx` and decomposed `frontend/src/App.tsx` (now ~290 lines, coordinating `useWorkspaceScene`, `useWorkspaceNavigation`, `ResizableRail`, and tabbed layouts).
- Tailwind CSS 4.3.3 with `@tailwindcss/vite` 4.3.3 - styling pipeline registered in `frontend/vite.config.ts`.
- shadcn 4.16.0 / Radix UI 1.6.7 / Lucide React 1.28.0 - component conventions and primitives configured by `frontend/components.json` and implemented under `frontend/src/components/ui/`.
- Cytoscape.js 3.34.0, react-cytoscapejs 2.0.0, cytoscape-fcose 2.2.0 (default layout), cytoscape-dagre 4.0.0 (left-to-right layout for investigation view, registered via `cytoscape.use(dagre)` in `frontend/src/components/graph/layoutConfig.ts`), cose-bilkent 4.1.0 (fallback) - interactive graph rendering in `frontend/src/components/graph/GraphCanvas.tsx`. Layout orchestration is encapsulated in `frontend/src/components/graph/useCytoscapeLayout.ts`, scene adapter conversion in `frontend/src/lib/graph/sceneElements.ts`, and imperative diffing in `frontend/src/components/graph/cytoscapeReconciler.ts`.

**Testing:**
- pytest 9.1.1 and pytest-asyncio 1.4.0 - backend test runner configured in `pyproject.toml`; tests are under `spoilerless/tests/` (53 modules; new tests for revisions split, rate limiter lazy re-init, share API, and visualization cache).
- HTTPX 0.28.1 - FastAPI test/client support and injectable transport for LLM-provider tests; declared in dev dependency group.
- Vitest 4.1.10 with jsdom 30.0.1 - frontend tests configured in `frontend/vite.config.ts` and initialized by `frontend/src/test/setup.ts`. 438+ tests across 29 test files.
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
- redis 8.1.0 - async Redis client for rate limiting and graph/visualization caching in `spoilerless/app/cache/redis_client.py`.
- fastapi-limiter 0.2.0 (with pyrate-limiter) - Redis-backed request throttling in `spoilerless/app/services/rate_limit.py`. Supports resilient lazy re-initialization on startup connection blips (THERMO-P2-04), honors `rate_limit_fail_open == False` + `environment == "production"` to return 503 on Redis outage, and registers uppercase error code `RATE_LIMIT_UNAVAILABLE`.
- cytoscape-dagre 4.0.0 (exact pin) with `@types/cytoscape-dagre` 2.3.4 - dagre layout for investigation view.

**Infrastructure:**
- Neo4j stores canonical graph data, user-created graph data, revisions, users, sessions, progress, chat history, change sets, share tokens, and `AppSetting` nodes; access stays behind `spoilerless/app/repository/` and `spoilerless/app/graph/database.py`.
- Redis (optional, Upstash `rediss://`) backs rate limiting and cache-aside graph/visualization caching; all Redis access flows through `spoilerless/app/cache/`.
- FastAPI publishes OpenAPI automatically. Direct `app.openapi()` probe reports 39 path templates and 52 operations from `spoilerless/app/main.py`.
- FastAPI serves local static media through `app.mount("/api/static", StaticFiles(...))` in `spoilerless/app/main.py`; holds character portraits under `spoilerless/app/static/characters/`.
- Vite proxies `/api` to host FastAPI during development via `frontend/vite.config.ts`; production routing handles `/api` including `/api/static` and `Host` validation.

## Configuration

**Environment:**
- Backend configuration uses `Settings` in `spoilerless/app/core/config.py`: process environment overrides root `.env`, defaults fill optional fields, unknown variables ignored, `get_settings()` caches one instance.
- Required database variable names are `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`; optional `NEO4J_DATABASE`.
- Authentication uses `GOOGLE_CLIENT_ID`, `SESSION_COOKIE_NAME`, `SESSION_TTL_SECONDS`, `SESSION_COOKIE_SECURE`, `FRONTEND_ORIGINS`; plus `ENVIRONMENT`, `ALLOWED_HOSTS`, `MAX_BODY_SIZE_BYTES`, `RATE_LIMIT_FAIL_OPEN`.
- Optional rate-limit/cache uses `REDIS_URL` in `spoilerless/app/core/config.py`; empty disables both. In production, `RATE_LIMIT_FAIL_OPEN=false` makes Redis outage surface as 503 on gated routes.
- Optional chat config uses `LLM_*` fields; includes `LLM_MAX_CONCURRENT_GENERATIONS` (default 4) and `LLM_MAX_TOOL_CALLS_PER_ROUND` (default 8). Runtime overrides via `spoilerless/app/services/settings.py` / `ChatService`.
- Frontend build-time configuration is templated in `frontend/.env.example`. `VITE_GOOGLE_CLIENT_ID` consumed by `frontend/src/components/auth/LoginPage.tsx`. `VITE_API_BASE_URL` prefixes every `apiFetch` request and `apiUrl()` image URLs at call time (`frontend/src/api/client.ts`).

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **Frontend Architectural Decomposition (Phase 12):**
  - `frontend/src/App.tsx` decomposed from ~900 lines to 291 lines; extracted `useWorkspaceScene.ts` (217 lines), `useWorkspaceNavigation.ts` (50 lines), `layout/AppIcons.tsx` (74 lines), and `layout/ResizableRail.tsx` (143 lines).
  - `frontend/src/components/graph/GraphCanvas.tsx` decomposed from ~700 lines to 426 lines; extracted `useCytoscapeLayout.ts` (197 lines) and `dialogs/CreateCustomNodeDialog.tsx` (130 lines).
  - `frontend/src/components/detail/DetailPanel.tsx` decomposed from ~750 lines to 180 lines; extracted `tabs/OverviewTab.tsx` (152 lines), `tabs/ClaimsTab.tsx` (49 lines), `tabs/EvidenceTab.tsx` (45 lines), `tabs/NotesTab.tsx` (235 lines), `CharacterPortrait.tsx` (78 lines), and `dialogs/CreateRelationshipDialog.tsx` (167 lines).
  - `frontend/src/lib/graph/sceneElements.ts` (242 lines) unifies Cytoscape node/edge conversion logic across all views and projections.
  - `frontend/src/lib/tokens/graphTokens.ts` (57 lines) centralizes graph design tokens, node sizes, colors, and 44px touch targets.
  - `frontend/src/lib/graph/positionCache.ts` (37 lines) maintains layout coordinates across scene switches.
- **Backend Modularization & Decomposition (Phase 12):**
  - Monolithic `spoilerless/app/services/visualization.py` (1,173 lines) replaced by package `spoilerless/app/services/visualization/` containing `boundary.py` (121 lines), `constants.py` (95 lines), `expansion.py` (275 lines), `focus.py` (149 lines), `node_builders.py` (64 lines), `service.py` (180 lines), `views.py` (306 lines), and `__init__.py` (19 lines).
  - `spoilerless/app/revisions/__init__.py` (341 lines) split into `repository.py` (141 lines), `service.py` (203 lines), and clean facade `__init__.py`.
  - `spoilerless/app/services/graph.py` provides `GraphService` facade consolidating visible graph reads and cache invalidations (`read_visible_graph`, `invalidate_series_caches`).
  - `spoilerless/app/api/boundary.py` enhanced with `require_boundary` dependency and typed resolvers.
  - `spoilerless/app/domain/change_set.py` now hosts `ProposeChangesetInput` directly.
  - `spoilerless/app/services/auth.py` now hosts `warn_if_open_signup`.
- **Security & Reliability Hardening (Phase 12):**
  - Privacy-scrubbed reads: `NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse` have `user_id: Optional[str] = None` in `spoilerless/app/domain/user_content.py` preventing 500 `ValidationError` on non-owner/anonymous reads.
  - Candidate ingest Cypher consolidation: single Cypher roundtrip in `spoilerless/app/graph/candidates.py` eliminating 3x query amplification.
  - SSRF DNS timeout: 1.0s timeout bounded with `asyncio.wait_for` in `spoilerless/app/domain/settings.py`.
  - Rate limiter lazy re-initialization: `RateLimiter` recovers from startup Redis blips in `spoilerless/app/services/rate_limit.py`, with registered uppercase error codes (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`).
  - Production CSP & TrustedHost: `vercel.json` and `index.html` allow `https://api.spoilerless.net` and `https://*.onrender.com` in `connect-src`; `_trusted_hosts` supports Render wildcard fallback.

---

*Stack analysis: 2026-08-26*
