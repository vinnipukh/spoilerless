---
last_mapped: 2026-08-14
focus: tech
last_mapped_commit: 5bd1641d7a9c44d693669d356ea602a23aa3664f
---

# Technology Stack

**Analysis Date:** 2026-08-14

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
- Python: 131 files / 39,364 lines under `spoilerless/` (78 app, 52 tests, 1 script). New since the 2026-08-12 map: `spoilerless/app/services/visualization.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/api/exceptions.py`, and six visualization/phase-10 test modules under `spoilerless/tests/`.
- TSX: 82 files / 15,061 lines under `frontend/src/` (new: `frontend/src/components/graph/AnswerGraph.tsx`, `frontend/src/components/evidence/EvidenceChain.tsx`, `frontend/src/components/graph/GraphFilterPanel.test.tsx`).
- TypeScript: 71 files / 7,955 lines under `frontend/src/` plus frontend configuration (new: `frontend/src/lib/visualizationAdapter.ts`, `frontend/src/hooks/useSceneState.ts`, `frontend/src/components/graph/cytoscapeReconciler.ts`, and their tests — the reconciler is currently untracked in the working tree).
- CSS: 2 files / 174 lines under `frontend/src/` (unchanged).

Use these counts as a scale baseline when estimating changes; do not count `frontend/node_modules/`, build output, or `.planning/` as product source.

## Runtime

**Environment:**
- CPython 3.13 or newer is required by `pyproject.toml`; `uv.lock` resolves for Python 3.13+.
- Node.js `^22.13.0 || >=24.0.0` is required by the locked Vite package in `frontend/package-lock.json`.
- Browser runtime targets ES2023 and DOM APIs through `frontend/tsconfig.app.json`.
- Neo4j Community is the only containerized runtime service; `docker-compose.yml` resolves to the single service `neo4j` using image `neo4j:2026.06.0-community`. An optional Upstash Redis instance (`REDIS_URL`) backs rate limiting and the graph/visualization cache.

**Package Manager:**
- uv manages Python environments and dependencies from `pyproject.toml`; exact resolution is committed in `uv.lock` (unchanged since the 2026-08-12 map).
- npm manages frontend packages from `frontend/package.json`; exact resolution uses lockfile version 3 in `frontend/package-lock.json`.
- Docker Compose orchestrates local Neo4j only; run the Python backend and Vite frontend as host processes rather than expecting `docker-compose.yml` to start them.

## Frameworks

**Core:**
- FastAPI 0.140.7 - ASGI REST API, dependency injection, OpenAPI, middleware, lifecycle, and SSE entry points in `spoilerless/app/main.py` and `spoilerless/app/api/`.
- Pydantic 2.13.4 - strict request/response and domain models under `spoilerless/app/domain/`, including the visualization DTOs in `spoilerless/app/domain/visualization.py`.
- pydantic-settings 2.14.2 - environment-backed backend settings in `spoilerless/app/core/config.py`.
- React 19.2.8 and React DOM 19.2.8 - single-page browser UI rooted at `frontend/src/main.tsx` and `frontend/src/App.tsx`.
- Tailwind CSS 4.3.3 with `@tailwindcss/vite` 4.3.3 - styling pipeline registered in `frontend/vite.config.ts`.
- shadcn 4.16.0 / Radix UI 1.6.7 / Lucide React 1.28.0 - component conventions and primitives configured by `frontend/components.json` and implemented under `frontend/src/components/ui/`.
- Cytoscape.js 3.34.0, react-cytoscapejs 2.0.0, cytoscape-fcose 2.2.0 (default layout), cytoscape-dagre 4.0.0 (left-to-right layout for the investigation view, registered via `cytoscape.use(dagre)` in `frontend/src/components/graph/layoutConfig.ts`), and cose-bilkent 4.1.0 (runtime fallback) - interactive graph rendering and layout in `frontend/src/components/graph/GraphCanvas.tsx` and `frontend/src/components/graph/layoutConfig.ts`. Layout engine selection is task-driven: `view === 'investigation'` selects dagre with `rankDir: 'LR'`, everything else stays fcose (D-25). `frontend/src/lib/visualizationAdapter.ts` maps the typed visualization DTO into Cytoscape `ElementDefinition`s for these renderers.

**Testing:**
- pytest 9.1.1 and pytest-asyncio 1.4.0 - backend test runner configured in `pyproject.toml`; tests are under `spoilerless/tests/`.
- HTTPX 0.28.1 - FastAPI test/client support and injectable transport for LLM-provider tests; declared in the dev dependency group in `pyproject.toml`.
- Vitest 4.1.10 with jsdom 30.0.1 - frontend tests configured in `frontend/vite.config.ts` and initialized by `frontend/src/test/setup.ts`.
- Testing Library React 16.3.2, jest-dom 7.0.0, and user-event 14.6.1 - component interaction and DOM assertions declared in `frontend/package.json`.

**Build/Dev:**
- Uvicorn 0.51.0 - ASGI development/runtime server for `spoilerless.app.main:app`, declared in `pyproject.toml`.
- Vite 8.1.5 and `@vitejs/plugin-react` 6.0.3 - frontend development server and production bundle configured in `frontend/vite.config.ts`.
- TypeScript compiler 6.0.3 - `npm run build` performs `tsc -b` before `vite build`, as defined in `frontend/package.json`.
- ESLint 10.8.0 with typescript-eslint and React hook/refresh plugins - frontend static analysis configured in `frontend/eslint.config.js`.
- The `spoilerless-setup` console entry point maps to `spoilerless.app.graph.setup:main` in `pyproject.toml`; use it to create constraints and seed the graph after Neo4j is available.

## Key Dependencies

**Critical:**
- neo4j 6.2.0 - async Bolt driver; application-owned lifecycle and query helpers are implemented in `spoilerless/app/graph/database.py`.
- google-auth 2.56.2 with requests support - verifies Google ID tokens in `spoilerless/app/services/auth.py`.
- HTTPX 0.28.1 - asynchronous streaming HTTP transport for Gemini and OpenAI-compatible providers in `spoilerless/app/llm/provider.py`.
- PyYAML 6.0.3 - loads ontology and seed-support YAML through `spoilerless/app/graph/ontology.py`.
- python-dotenv 1.2.2 - supports local environment loading alongside pydantic-settings, declared in `pyproject.toml`.
- redis 8.1.0 - async Redis client for rate limiting and graph/visualization caching in `spoilerless/app/cache/redis_client.py`.
- fastapi-limiter 0.2.0 (with pyrate-limiter) - Redis-backed request throttling in `spoilerless/app/services/rate_limit.py`.
- cytoscape-dagre 4.0.0 (exact pin) with `@types/cytoscape-dagre` 2.3.4 - dagre layout for the investigation visualization view; the `dagre` implementation is bundled by `cytoscape-dagre` (no separate `dagre` package appears in `frontend/package-lock.json`). Added to `frontend/package.json` since the 2026-08-12 map; no Python dependencies changed.

**Infrastructure:**
- Neo4j stores canonical graph data, user-created graph data, revisions, users, sessions, progress, chat history, change sets, share tokens, and runtime `AppSetting` configuration; access stays behind `spoilerless/app/repository/` and `spoilerless/app/graph/database.py`.
- Redis (optional, Upstash `rediss://`) backs rate limiting and cache-aside graph/visualization caching; all Redis access flows through `spoilerless/app/cache/`.
- FastAPI publishes OpenAPI automatically. A direct `app.openapi()` probe at this commit reports 39 path templates and 52 method/path operations from `spoilerless/app/main.py` (up from 37/50; the new `/api/series/{series_id}/graph/visualization` projection route is included).
- FastAPI serves local static media through `app.mount("/api/static", StaticFiles(...))` in `spoilerless/app/main.py`; the mounted directory `spoilerless/app/static/` currently holds character portrait `.webp` files under `spoilerless/app/static/characters/`.
- Vite proxies `/api` to the host FastAPI server during development via `frontend/vite.config.ts`; this proxy is a development facility, not a production reverse proxy.

## Configuration

**Environment:**
- Backend configuration uses `Settings` in `spoilerless/app/core/config.py`: process environment overrides root `.env`, defaults fill optional fields, unknown variables are ignored, and `get_settings()` caches one process-wide instance.
- A root `.env` file is present and sensitive; note existence only and never read, quote, or commit it. Use the safe variable-name template `.env.example` when documenting setup.
- Required database variable names are `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`; optional database selection uses `NEO4J_DATABASE`. Keep values out of code and documentation.
- Authentication configuration uses `GOOGLE_CLIENT_ID`, `SESSION_COOKIE_NAME`, `SESSION_TTL_SECONDS`, `SESSION_COOKIE_SECURE`, and `FRONTEND_ORIGINS`; definitions and defaults live in `spoilerless/app/core/config.py`.
- Optional rate-limit/cache configuration uses `REDIS_URL` (Upstash `rediss://` connection string) in `spoilerless/app/core/config.py`; an empty value disables all Redis-backed features.
- Optional chat configuration uses the `LLM_*` fields in `spoilerless/app/core/config.py`; runtime graph-stored overrides are resolved by `spoilerless/app/services/settings.py` and `spoilerless/app/services/chat.py`.
- Frontend build-time configuration is templated in `frontend/.env.example`. `VITE_GOOGLE_CLIENT_ID` is consumed by `frontend/src/components/auth/LoginPage.tsx`. `VITE_API_BASE_URL` is now consumed by `frontend/src/api/client.ts`: it prefixes every `apiFetch` request (`const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''`) and the `apiUrl()` helper prefixes backend-relative `/api/static/...` image URLs at call time so tests can `vi.stubEnv` it; an empty value preserves the relative-URL Vite-proxy development behavior.

**Build:**
- Frontend build and test plugins, `@` alias, `/api` development proxy, and jsdom setup are in `frontend/vite.config.ts`.
- TypeScript project references are in `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, and `frontend/tsconfig.node.json`.
- Tailwind/shadcn aliases and CSS-variable conventions are in `frontend/components.json`; use `frontend/src/index.css` as the style entry point.
- Python dependency and pytest configuration is centralized in `pyproject.toml`; preserve `uv.lock` whenever dependency resolution changes.

## Platform Requirements

**Development:**
- Install Python 3.13+, uv, Node.js satisfying Vite 8, npm, Docker, and Docker Compose; authoritative manifests are `pyproject.toml`, `uv.lock`, `frontend/package.json`, and `frontend/package-lock.json`.
- Start only Neo4j with `docker-compose.yml`, then run setup, backend, and frontend separately. Do not infer a full-container stack from the Compose file.
- Keep Neo4j available for backend integration tests: `spoilerless/tests/conftest.py` and repository tests are designed around a real graph rather than an ORM or embedded substitute.
- Preserve the spoiler boundary in backend data access; frontend filtering is not a substitute for repository/retrieval filtering under `spoilerless/app/spoiler/`, `spoilerless/app/repository/`, and `spoilerless/app/retrieval/`. The visualization projection service (`spoilerless/app/services/visualization.py`) consumes only already-safe `GraphResponse` detail and enforces boundary-before-projection (D-05); keep it that way when adding view types.
- Repo-root verification scripts `run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, and `verify_arch.py` are claim checkers for planning/documentation docs; they import only the standard library (`os`, `sys`, `re`, `json`) and add no third-party dependency requirements. They are currently untracked.

**Production:**
- Render deployment is defined by `render.yaml`: a free-tier `spoilerless-api` web service (`uv sync --frozen`, `uv run uvicorn spoilerless.app.main:app`) that auto-deploys on git push. No Kubernetes/Helm manifests or other cloud targets are tracked.
- CI is configured as GitHub Actions in `.github/workflows/ci.yml` plus a separate `release.yml`; no GitLab CI, Jenkins, or Azure Pipelines definitions are tracked.
- `frontend/vercel.json` defines a Vercel-style SPA rewrite for static hosting; no production API base URL or reverse-proxy manifest is tracked. `VITE_API_BASE_URL` is the supported hook for pointing the production bundle at a hosted backend, and `/api/static` character portraits are prefixed with it by `apiUrl()` in `frontend/src/api/client.ts`.
- A production deployment must provide HTTPS, set secure cookie behavior, route `/api` (including `/api/static`) to FastAPI, host the built frontend, and supply external Neo4j, optional Upstash Redis, and provider configuration.
- `LICENSE` is present (MIT, Spoilerless Team); the README demo disclaimer in `README.md` remains project prose.

## Map Delta (2026-08-14 vs 2026-08-12 / 1710d57)

- **New frontend dependency:** `cytoscape-dagre` 4.0.0 (+ `@types/cytoscape-dagre` 2.3.4) in `frontend/package.json`; dagre is bundled, so `frontend/package-lock.json` gained only those two packages. Backend `pyproject.toml`/`uv.lock` unchanged.
- **New backend modules:** `spoilerless/app/services/visualization.py` (VisualizationProjectionService, ~1,170 lines), `spoilerless/app/domain/visualization.py` (DTOs and view constants), `spoilerless/app/api/exceptions.py` (`install_repository_error_handlers`), and static character portraits in `spoilerless/app/static/characters/*.webp`.
- **New frontend modules:** `frontend/src/lib/visualizationAdapter.ts`, `frontend/src/hooks/useSceneState.ts`, `frontend/src/components/graph/AnswerGraph.tsx` (presentation-only temporary surface), `frontend/src/components/evidence/EvidenceChain.tsx`; plus untracked `frontend/src/components/graph/cytoscapeReconciler.ts` and its test (pure `cytoscape` type imports, no new dependencies).
- **OpenAPI surface:** 37 → 39 path templates, 50 → 52 operations.
- **Untracked repo-root artifacts:** `.hermes/` (Hermes desktop-attachment notes, markdown planning documents only) and the four stdlib-only verification scripts listed above.

---

*Stack analysis: 2026-08-14*
