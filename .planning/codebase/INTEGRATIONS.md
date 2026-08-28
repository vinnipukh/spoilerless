---
last_mapped: 2026-08-26
focus: tech
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---

# External Integrations

**Analysis Date:** 2026-08-26

## APIs & External Services

**Google Identity Services:**
- The browser loads Google Identity Services from `https://accounts.google.com/gsi/client` in `frontend/index.html` and initializes popup sign-in in `frontend/src/components/auth/LoginPage.tsx`.
  - SDK/Client: browser GIS global (`window.google.accounts.id`); no npm Google identity package is used.
  - Frontend configuration: `VITE_GOOGLE_CLIENT_ID`, declared in `frontend/.env.example` and consumed only by `frontend/src/components/auth/LoginPage.tsx`.
  - Backend client: `google-auth[requests]` 2.56.2, declared in `pyproject.toml` and called by `ProductionGoogleVerifier` in `spoilerless/app/services/auth.py`.
  - Backend configuration: `GOOGLE_CLIENT_ID` in `spoilerless/app/core/config.py`; it must identify the same web client as the frontend value.
  - Flow: browser obtains an ID token, `POST /api/auth/google` in `spoilerless/app/api/auth.py` verifies signature, audience, issuer, and expiry, then upserts the local user and creates a server-side session.
  - No Google client secret is consumed by the implementation; do not introduce one into `.env`, frontend variables, or source.

**Optional LLM Providers:**
- OpenAI-compatible chat completions are implemented directly over HTTPX in `spoilerless/app/llm/provider.py`.
  - Endpoint: configurable base URL plus `POST /chat/completions`.
  - Auth: bearer token assembled from the effective API key inside `OpenAICompatibleProvider`; never send this key to `frontend/`.
  - Configuration: effective `provider`, `base_url`, `api_key`, `model`, and `enabled` are resolved by `spoilerless/app/services/chat.py` with per-request BYOK override honoring `X-LLM-*` headers.
  - Concurrency: `ChatService` gates generation with a process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` (default 4, from `spoilerless/app/core/config.py:llm_max_concurrent_generations`) in addition to the per-user slot.
  - Tool-call cap: `spoilerless/app/retrieval/pipeline.py:llm_max_tool_calls_per_round` (default 8) caps calls executed per tool round; `ProposeChangesetInput.operations` is capped at 20 in `spoilerless/app/domain/change_set.py`.
  - SSRF protection (Phase 12): `_validate_base_url` in `spoilerless/app/domain/settings.py` now bounds DNS resolution to a 1.0s timeout with `asyncio.wait_for`, preventing event-loop stalling from slow/unresponsive DNS servers during SSRF validation.
  - Compatibility: any service matching the expected streaming chat-completions/tool-call protocol may be used; there is no vendor-specific OpenAI Python SDK dependency in `pyproject.toml`.
  - Special handling: models whose identifier starts with `deepseek` receive thinking mode disabled in `spoilerless/app/llm/provider.py` so tool-call round trips use the supported message shape.
  - Answer-delimiter hardening: `spoilerless/app/retrieval/pipeline.py:_neutralize_answer_delimiters()` escapes exact `<CONTEXT_SECTIONS>` / `</CONTEXT_SECTIONS>` shapes in model answers before assembly.
- Google Gemini REST is implemented directly over HTTPX in `spoilerless/app/llm/provider.py`.
  - Endpoint: `POST /v1beta/models/{model}:streamGenerateContent?alt=sse` against the configured base URL.
  - Default host: `https://generativelanguage.googleapis.com`, defined in `spoilerless/app/domain/settings.py`.
  - Auth: `x-goog-api-key` request header applied by `GeminiProvider`; the full key remains backend-only.
  - Translation: `spoilerless/app/llm/provider.py` converts OpenAI-shaped pipeline messages/tools into Gemini `contents`, `functionCall`, and `functionResponse` structures.
- Both provider paths are optional and fail closed when disabled or incompletely configured; selection is limited to `gemini` and `openai_compatible` by `spoilerless/app/domain/settings.py`.
- BYOK overrides: the browser may send provider/key/base URL/model as per-request `X-LLM-Provider`/`X-LLM-Api-Key`/`X-LLM-Base-URL`/`X-LLM-Model` headers from `frontend/src/lib/byok.ts` (localStorage key `spoilerless:byok-llm-settings`); header values then replace stored/environment settings for that request.

**Application HTTP API:**
- FastAPI exposes the application contract from `spoilerless/app/main.py` (363 lines); direct OpenAPI generation reports 39 path templates and 52 operations.
  - Machine contract: `/openapi.json`; interactive docs: `/docs` and `/redoc` — disabled when `ENVIRONMENT=production` (`spoilerless/app/main.py:_docs_kwargs`).
  - Browser client: relative `fetch` wrappers in `frontend/src/api/client.ts` and feature modules under `frontend/src/api/`. `VITE_API_BASE_URL` prefixes every `apiFetch` request when set; empty keeps relative-URL Vite-proxy behavior.
  - Body-size gate: `BodySizeLimitMiddleware` in `spoilerless/app/main.py` rejects bodies over `max_body_size_bytes` (default 1 MiB) with `413 {"detail":{"code":"PAYLOAD_TOO_LARGE","message":"Request body too large."}}`.
  - Host validation: `TrustedHostMiddleware` in `spoilerless/app/main.py:_trusted_hosts()` builds allowlist from `ALLOWED_HOSTS` when set, otherwise from `FRONTEND_ORIGINS` hosts + `localhost`, `127.0.0.1`, `api.spoilerless.net`, `testserver`, and `*.onrender.com` wildcard matching for Render deployments.
  - Credentials: every shared API fetch sends `credentials: 'include'` from `frontend/src/api/client.ts`.
  - Development routing: Vite proxies `/api` to `http://127.0.0.1:8000` in `frontend/vite.config.ts`.
  - Production routing: reverse proxy or same-origin gateway for `/api`; `VITE_API_BASE_URL` is the supported production hook.
  - Spoiler boundary: `spoilerless/app/api/boundary.py:resolve_effective_boundary()` and `require_boundary` dependency are the single fail-closed enforcement seam.
  - Read-only sharing: token-based share links via `spoilerless/app/api/share.py`; raw tokens stored only as hashes by `spoilerless/app/repository/share.py`.
- Typed visualization projections:
  - Endpoint: `GET /api/series/{series_id}/graph/visualization` in `spoilerless/app/api/graph.py`, returning `VisualizationDTO`.
  - Parameters: `view` (`episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`), `episode_order`, and optional repeated `focus_id` (capped at 20).
  - Implementation: `VisualizationProjectionService` in decomposed package `spoilerless/app/services/visualization/` (`service.py`, `views.py`, `expansion.py`, `focus.py`, `boundary.py`, `node_builders.py`, `constants.py`).
  - Client: `frontend/src/lib/graph/sceneElements.ts` and `frontend/src/lib/visualizationAdapter.ts` convert DTO into Cytoscape element definitions; `useWorkspaceScene` and `useSceneState` manage scene state.
  - Cache bound: `spoilerless/app/cache/graph_cache.py:_focus_capacity_allows()` gates visualization caching with `FOCUS_SET_CAP=64` and `FOCUS_SET_TTL_SECONDS=3600`.

**Server-Sent Events:**
- Chat streaming uses `StreamingResponse` with `text/event-stream` in `spoilerless/app/api/chat.py`.
  - Client: streaming `fetch`, `ReadableStream`, and custom SSE parser in `frontend/src/api/chat.ts`.
  - Protocol: ordinary `data:` frames carry deltas, `event: done` carries final envelope, `event: error` carries terminal failures.
  - ChangeSet proposing: `propose_changeset` tool delegates via `ChangeSetService.propose_via_tool()` with server-resolved boundary.

**External Media:**
- Graph nodes may reference external portrait/image URLs supplied by graph data and rendered by Cytoscape styles.
  - Browser policy: `frontend/index.html` sets page-wide `no-referrer` behavior; `frontend/vercel.json` configures `img-src 'self' data: https:`.
  - Storage: external images are hotlinked by URL; local static media is served by `app.mount("/api/static", StaticFiles(...))` in `spoilerless/app/main.py`.
  - Production prefixing: `apiUrl()` in `frontend/src/api/client.ts` prefixes backend-relative `/api/static/...` URLs with `VITE_API_BASE_URL` at call time.

## Data Storage

**Databases:**
- Neo4j Community is the sole application database.
  - Local service: one `neo4j` Compose service using `neo4j:2026.06.0-community`, defined by `docker-compose.yml`.
  - Connection configuration: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, optional `NEO4J_DATABASE`, modeled in `spoilerless/app/core/config.py`.
  - Client: Neo4j Python Driver 6.2.0 using `AsyncGraphDatabase` in `spoilerless/app/graph/database.py`.
  - Lifecycle: `spoilerless/app/main.py` opens one application-owned async driver during lifespan and closes at shutdown; `warn_if_open_signup()` in `spoilerless/app/services/auth.py` is called inside lifespan.
  - Access pattern: use repositories under `spoilerless/app/repository/` and `spoilerless/app/revisions/repository.py` with managed transactions.
- Neo4j also stores application infrastructure state:
  - Users, opaque-token session hashes, and share-token hashes.
  - Watch progress, user content (with note target mapping for all custom node types), revisions, candidates, chat sessions/messages, and change sets.

**File Storage:**
- No external file-storage provider or upload pipeline is detected.
- Curated seed content is repository-local JSON/YAML under `data/dexter/` and ontology YAML under `ontology/`; `spoilerless/app/graph/setup.py` imports it into Neo4j. Character portrait images are repository-local `.webp` under `spoilerless/app/static/characters/`.

**Caching:**
- Redis is integrated via Upstash (`REDIS_URL`, `rediss://`): one shared `redis.asyncio` singleton in `spoilerless/app/cache/redis_client.py`.
- Graph responses and visualization projections are cached cache-aside with boundary-aware keys in `spoilerless/app/cache/graph_cache.py`.
- Rate limiting uses fastapi-limiter 0.2.0 / pyrate-limiter Redis buckets in `spoilerless/app/services/rate_limit.py`. Supports resilient lazy re-initialization on startup connection blips (THERMO-P2-04); in production with `RATE_LIMIT_FAIL_OPEN=false`, Redis outage surfaces as `503 {"detail":{"code":"RATE_LIMIT_UNAVAILABLE"}}`.

## Authentication & Identity

**Auth Provider:**
- Google Identity Services provides external identity assertion; local authorization uses custom Neo4j-backed session.
  - Browser: `frontend/src/components/auth/LoginPage.tsx` receives Google credential and submits to `POST /api/auth/google`.
  - Token verification: `ProductionGoogleVerifier` in `spoilerless/app/services/auth.py` calls `google.oauth2.id_token.verify_oauth2_token`.
  - User persistence: `AuthService` in `spoilerless/app/services/auth.py` keys local identity from verified Google `sub` and delegates to `spoilerless/app/repository/user.py`.
  - Session persistence: `Neo4jSessionRepository` in `spoilerless/app/repository/session.py`.
  - Session tokens: opaque random values stored only as SHA-256 hashes.
  - Cookie policy: HttpOnly, SameSite Lax, path `/`, configurable Secure behavior.
  - CORS: credentialed origins from `FRONTEND_ORIGINS`.
  - Candidate review and ChangeSet confirmation use role gate `RequireAdminDependency` in `spoilerless/app/api/deps.py`.

## CI/CD & Deployment

**Hosting:**
- Render is configured by `render.yaml`: free-tier `spoilerless-api` web service (`uv sync --frozen`, `uv run uvicorn spoilerless.app.main:app`) with `--proxy-headers --forwarded-allow-ips` for trusted proxy forwarding.
- Vercel is configured by `frontend/vercel.json`: SPA rewrite plus hardened security headers:
  - `Content-Security-Policy`: `default-src 'self'; script-src 'self' https://accounts.google.com; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self' https://accounts.google.com https://api.spoilerless.net https://*.onrender.com; frame-src https://accounts.google.com; object-src 'none'; base-uri 'self'; form-action 'self'`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

**CI Pipeline:**
- GitHub Actions in `.github/workflows/ci.yml` and `.github/workflows/release.yml`.

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **CSP & TrustedHost Production Hardening (12-04):** `frontend/vercel.json` and `frontend/index.html` CSP updated to include `https://api.spoilerless.net` and `https://*.onrender.com` in `connect-src`; `spoilerless/app/main.py:_trusted_hosts()` updated with regex fallback for Render `*.onrender.com` wildcard domains.
- **SSRF DNS Timeout (12-05):** `spoilerless/app/domain/settings.py` bounds DNS resolution to a 1.0s timeout with `asyncio.wait_for` during base URL SSRF validation.
- **RateLimiter Startup Resilience & Uppercase Error Codes (12-05):** `spoilerless/app/services/rate_limit.py` implements lazy re-initialization to recover from transient startup Redis outages, with uppercase registered error codes (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`).
- **Domain & Service Layering Cleanup (12-06):** `ProposeChangesetInput` moved to `spoilerless/app/domain/change_set.py`; `warn_if_open_signup` moved to `spoilerless/app/services/auth.py`; `spoilerless/app/revisions/` split into `repository.py` and `service.py`.
- **Cypher Ingestion Optimization (12-03):** Candidate ingest claim visibility checks consolidated into a single Cypher roundtrip in `spoilerless/app/graph/candidates.py`.
- **Privacy-Scrubbed Model Alignment (12-01):** `NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse` in `spoilerless/app/domain/user_content.py` allow `user_id: Optional[str] = None` for non-owner and anonymous reads.

---

*Integration audit: 2026-08-26*
