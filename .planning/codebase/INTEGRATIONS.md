---
last_mapped: 2026-08-20
focus: tech
last_mapped_commit: 6256214f672d21e0c264a4910033fe02dc51da80
---

# External Integrations

**Analysis Date:** 2026-08-20

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
  - Concurrency (new D-07): `ChatService` now gates generation with a process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` (default 4, from `spoilerless/app/core/config.py:llm_max_concurrent_generations`) in addition to the per-user slot — prevents burst starvation across users/workers.
  - Tool-call cap (new D-07): `spoilerless/app/retrieval/pipeline.py:llm_max_tool_calls_per_round` (default 8) caps calls executed per tool round; `ProposeChangesetInput.operations` is capped at 20 in the same module.
  - Compatibility: any service matching the expected streaming chat-completions/tool-call protocol may be used; there is no vendor-specific OpenAI Python SDK dependency in `pyproject.toml`.
  - Special handling: models whose identifier starts with `deepseek` receive thinking mode disabled in `spoilerless/app/llm/provider.py` so tool-call round trips use the supported message shape.
  - Answer-delimiter hardening (new): `spoilerless/app/retrieval/pipeline.py:_neutralize_answer_delimiters()` escapes exact `<CONTEXT_SECTIONS>` / `</CONTEXT_SECTIONS>` shapes (`series_context`, `boundary`, `entities`, `relationships`, `claims`, `evidence`, `sources`, `notes`, `chat_history`) in model answers before assembly — ordinary angle-bracket text is untouched, but a forged `</sources>` cannot break the 9-section context framing.
- Google Gemini REST is implemented directly over HTTPX in `spoilerless/app/llm/provider.py`.
  - Endpoint: `POST /v1beta/models/{model}:streamGenerateContent?alt=sse` against the configured base URL.
  - Default host: `https://generativelanguage.googleapis.com`, defined in `spoilerless/app/domain/settings.py`.
  - Auth: `x-goog-api-key` request header applied by `GeminiProvider`; the full key remains backend-only.
  - Translation: `spoilerless/app/llm/provider.py` converts OpenAI-shaped pipeline messages/tools into Gemini `contents`, `functionCall`, and `functionResponse` structures.
- Both provider paths are optional and fail closed when disabled or incompletely configured; selection is limited to `gemini` and `openai_compatible` by `spoilerless/app/domain/settings.py`.
- BYOK overrides: the browser may send provider/key/base URL/model as per-request `X-LLM-Provider`/`X-LLM-Api-Key`/`X-LLM-Base-URL`/`X-LLM-Model` headers from `frontend/src/lib/byok.ts` (localStorage key `spoilerless:byok-llm-settings`); header values then replace stored/environment settings for that request. CORS and the allowlist are in `spoilerless/app/main.py`.

**Application HTTP API:**
- FastAPI exposes the local application contract from `spoilerless/app/main.py` (363 lines); direct OpenAPI generation still reports 39 path templates and 52 operations (boundary extraction is internal — no new template since 08-14).
  - Machine contract: `/openapi.json`; interactive docs: `/docs` and `/redoc` — but disabled when `ENVIRONMENT=production` (`spoilerless/app/main.py:_docs_kwargs` — `docs_url=None, redoc_url=None, openapi_url=None` when `environment == "production"`; set `ENVIRONMENT` before process start via Render dashboard env).
  - Browser client: relative `fetch` wrappers in `frontend/src/api/client.ts` and feature modules under `frontend/src/api/`. `VITE_API_BASE_URL` prefixes every `apiFetch` request when set; empty keeps relative-URL Vite-proxy behavior.
  - Body-size gate (new D-08): `BodySizeLimitMiddleware` in `spoilerless/app/main.py:BodySizeLimitMiddleware` rejects bodies over `max_body_size_bytes` (default 1 MiB, ge 1024, from `spoilerless/app/core/config.py`) with `413 {"detail":{"code":"payload_too_large","message":"Request body too large."}}` — Content-Length is checked before any byte is read, chunked bodies are counted as they stream via `guarded_receive`, and `BodyTooLarge` is caught to emit the same envelope.
  - Host validation (new): `TrustedHostMiddleware` in `spoilerless/app/main.py:_trusted_hosts()` builds allowlist from `ALLOWED_HOSTS` when set, otherwise from `FRONTEND_ORIGINS` hosts + `localhost`, `127.0.0.1`, `api.spoilerless.net`, `testserver`; `urlparse(origin).hostname` extracts hosts.
  - Credentials: every shared API fetch sends `credentials: 'include'` from `frontend/src/api/client.ts`.
  - Development routing: Vite proxies `/api` to `http://127.0.0.1:8000` in `frontend/vite.config.ts`.
  - Production routing: provide a reverse proxy or same-origin gateway for `/api`; `VITE_API_BASE_URL` is the supported production hook.
  - Spoiler boundary (new central): `spoilerless/app/api/boundary.py:resolve_effective_boundary()` (66 lines) is the single fail-closed resolver for every spoiler-sensitive read — anonymous readers fixed at order 1, authenticated readers without persisted progress fail closed to 1 (SEC-BE-001), authenticated readers with a record get `min(requested, view_as_of, watched_through)` via `spoilerless/app/spoiler/policy.py:effective_view_order`; return is validated to a persisted episode or else 422 `INVALID_VISIBLE_UNTIL_ORDER`. `spoilerless/app/api/graph.py:116-123` now delegates graph GET there and keeps `_resolve_effective_boundary = resolve_effective_boundary` alias for visualization/expand/path/export call sites.
  - Read-only sharing: token-based share links via `spoilerless/app/api/share.py`; raw tokens stored only as hashes by `spoilerless/app/repository/share.py`.
- Typed visualization projections are part of the application contract:
  - Endpoint: `GET /api/series/{series_id}/graph/visualization` in `spoilerless/app/api/graph.py`, returning `VisualizationDTO`.
  - Parameters: `view` (one of `episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`), `episode_order`, and optional repeated `focus_id` (graphrag_focus only, capped 20).
  - Implementation: `VisualizationProjectionService` in `spoilerless/app/services/visualization.py` projects only over complete spoiler-safe `GraphResponse` detail plus safe editorial event context; it never narrows GraphRAG retrieval detail and rejects hidden rows rather than dropping them.
  - Client: `frontend/src/lib/visualizationAdapter.ts` converts DTO into Cytoscape `ElementDefinition`s; `frontend/src/hooks/useSceneState.ts` manages view/scene state (including temporary Answer Graph surface).
  - Cache bound (new D-12): `spoilerless/app/cache/graph_cache.py:_focus_capacity_allows()` gates visualization caching — per-series `vizfocus:{series_id}` set caps distinct focus signatures at `FOCUS_SET_CAP=64` with `FOCUS_SET_TTL_SECONDS=3600`; enumeration of focus_id combinations can no longer mint unbounded Redis keys (each miss still pays fetch, memory growth bounded). `focus_signature()` is SHA-256 over sorted distinct ids.

**Server-Sent Events:**
- Chat streaming uses `StreamingResponse` with `text/event-stream` in `spoilerless/app/api/chat.py`.
  - Client: streaming `fetch`, `ReadableStream`, and custom SSE parser in `frontend/src/api/chat.ts`; native `EventSource` is not used because request is a credentialed POST with JSON body.
  - Protocol: ordinary `data:` frames carry deltas, `event: done` carries final envelope, `event: error` carries terminal failures.
  - Keep backend terminal events and frontend EOF handling synchronized whenever the stream contract changes.
  - The one state-changing tool `propose_changeset` now delegates via thin `ChangeSetService.propose_via_tool()` (QUAL-02) — pipeline threads only the server-resolved `visible_until_order` boundary; model-supplied boundary is never stamped.

**External Media:**
- Graph nodes may reference external portrait/image URLs supplied by graph data and rendered by Cytoscape styles in `frontend/src/components/graph/graphStylesheet.ts`.
  - Browser policy: `frontend/index.html` sets page-wide `no-referrer` behavior to accommodate external portrait CDNs; `frontend/vercel.json` now hardens `img-src 'self' data: https:` via CSP (see CI/CD section) — self-hosted portraits under `/api/static` satisfy `img-src 'self'`.
  - Storage: external images are hotlinked by URL; no upload service, media proxy, or managed object-storage integration is present.
- Local static media is served by the backend itself: `spoilerless/app/main.py` mounts `app.mount("/api/static", StaticFiles(directory=spoilerless/app/static), name="static")`. `spoilerless/app/static/characters/` ships six character portrait `.webp` files; seed `image_url` values reference them as `/api/static/characters/...`.
  - Production prefixing: `apiUrl()` in `frontend/src/api/client.ts` prefixes backend-relative `/api/static/...` URLs with `VITE_API_BASE_URL` at call time (only `'/'`-leading paths; absolute `http(s)` URLs pass through).
  - Constraint: `/api/static` is a FastAPI route, so production must route it to the backend alongside the rest of `/api`.

## Data Storage

**Databases:**
- Neo4j Community is the sole application database.
  - Local service: one `neo4j` Compose service using `neo4j:2026.06.0-community`, defined by `docker-compose.yml`.
  - Connection configuration: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, optional `NEO4J_DATABASE`, modeled in `spoilerless/app/core/config.py` (now with safe local defaults `bolt://127.0.0.1:7687` / `neo4j` / `hdgraf-local-password` but still honoring `Aura*` aliases).
  - Client: Neo4j Python Driver 6.2.0 using `AsyncGraphDatabase` in `spoilerless/app/graph/database.py`. Windows `neo4j+s://` → `neo4j://` + `TrustCustomCAs(certifi.where())` fix remains.
  - Lifecycle: `spoilerless/app/main.py` opens one application-owned async driver during lifespan and closes at shutdown; `warn_if_open_signup()` is now called inside lifespan before driver open (11-05 wiring, guarded — failure must not crash startup).
  - Access pattern: use repositories under `spoilerless/app/repository/` and managed write transactions; no ORM or relational migration framework.
- Neo4j also stores application infrastructure state:
  - Users, opaque-token session hashes, and share-token hashes via `spoilerless/app/repository/user.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`.
  - Watch progress, user content, revisions, candidates, chat sessions/messages, and change sets through repositories under `spoilerless/app/repository/`.

**File Storage:**
- No external file-storage provider or upload pipeline is detected.
- Curated seed content is repository-local JSON/YAML under `data/dexter/` and ontology YAML under `ontology/`; `spoilerless/app/graph/setup.py` imports it into Neo4j. Character portrait images are repository-local `.webp` under `spoilerless/app/static/characters/` served through the `/api/static` mount.
- Runtime user notes and graph edits are database records, not files; keep new persistent user content behind `spoilerless/app/repository/`.

**Caching:**
- Redis is integrated via Upstash (`REDIS_URL`, `rediss://`): one shared `redis.asyncio` singleton in `spoilerless/app/cache/redis_client.py` (lru_cache, mirroring `get_settings`).
- Graph responses are cached cache-aside with boundary-aware keys in `spoilerless/app/cache/graph_cache.py` (286 lines); empty `REDIS_URL` or any Redis error degrades to querying Neo4j.
- Typed visualization projections use the same cache-aside path: `get_cached_visualization`/`set_cached_visualization` in `spoilerless/app/cache/graph_cache.py`, now fronted by `_focus_capacity_allows` (FOCUS_SET_CAP=64, TTL 3600) — enumeration of focus_id combos cannot mint unbounded keys; when the cap is hit `set_cached_visualization` returns without storing (compute-fresh, never store).
- Rate limiting uses fastapi-limiter 0.2.0 / pyrate-limiter Redis buckets in `spoilerless/app/services/rate_limit.py`, initialized at startup only when `REDIS_URL` is set; empty URL means unthrottled local dev. In production with `RATE_LIMIT_FAIL_OPEN=false`, Redis outage now surfaces as `503 {"detail":{"code":"rate_limit_unavailable"}}` on gated routes (login, chat-send, content-write) instead of silent pass-through.
- `get_settings()` uses process-local `functools.lru_cache` in `spoilerless/app/core/config.py`; this is configuration memoization, not shared caching.
- Chat concurrency guard is now two-layer: per-user in-memory slot (existing) plus process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` in `spoilerless/app/services/chat.py` — prevents burst starvation across users under one worker, but still not cross-worker coordinated.

## Authentication & Identity

**Auth Provider:**
- Google Identity Services provides the external identity assertion; local authorization uses a custom Neo4j-backed session.
  - Browser: `frontend/src/components/auth/LoginPage.tsx` receives Google credential and submits it through auth code under `frontend/src/api/` and `frontend/src/providers/`.
  - Token verification: `ProductionGoogleVerifier` in `spoilerless/app/services/auth.py` calls `google.oauth2.id_token.verify_oauth2_token` with configured audience.
  - User persistence: `AuthService` in `spoilerless/app/services/auth.py` keys local identity from verified Google `sub` and delegates persistence to `spoilerless/app/repository/user.py`.
  - Session persistence: `spoilerless/app/main.py` installs `Neo4jSessionRepository` and `Neo4jShareRepository`; `spoilerless/app/api/deps.py` resolves current user from cookie. `AuthService` requires user/session repositories plus verifier with no silent fallback.
  - Session tokens: opaque random values stored only as SHA-256 hashes by `spoilerless/app/repository/session.py`.
  - Cookie policy: HttpOnly, SameSite Lax, path `/`, configurable Secure behavior in `spoilerless/app/api/auth.py`.
  - CORS: credentialed origins from `FRONTEND_ORIGINS` installed by `spoilerless/app/main.py`.
  - Origin check: Google sign-in validates `Origin` or `Referer` against configured origin list in `spoilerless/app/api/auth.py` when either header is supplied.
- No separate authorization provider, RBAC service, JWT issuer, or Google client-secret exchange is present; candidate review and ChangeSet confirmation use role gate `RequireAdminDependency` in `spoilerless/app/api/deps.py`.
- Redis-backed rate limits throttle login, chat send, and content-write routes when `REDIS_URL` is configured.

## Runtime Configuration Integration

**Backend environment settings:**
- `Settings` in `spoilerless/app/core/config.py` (209 lines) loads root `.env` plus process environment. Process environment wins; required Neo4j settings have no defaults in production deploys (local dev now has safe non-secret defaults for one-command startup). `ENVIRONMENT` defaults to `development`; set to `production` on Render to enable fail-closed rate limiting, docs-off, and open-signup warning.
- A sensitive root `.env` exists; its contents were not read. Document only variable names from `.env.example`.
- LLM bootstrap variables: `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, tuning limits, plus new `LLM_MAX_CONCURRENT_GENERATIONS` (default 4, semaphore bound) and `LLM_MAX_TOOL_CALLS_PER_ROUND` (default 8, per-round cap) in `spoilerless/app/core/config.py`.
- Rate-limit/cache config: `REDIS_URL`, plus new `RATE_LIMIT_FAIL_OPEN`, `ALLOWED_HOSTS`, `MAX_BODY_SIZE_BYTES` (1 MiB default) in `spoilerless/app/core/config.py`.
- Host allowlist: `ALLOWED_HOSTS` explicit list wins; when empty `_trusted_hosts()` derives from `FRONTEND_ORIGINS` hosts + `localhost`/`127.0.0.1`/`api.spoilerless.net`/`testserver`.

**Neo4j-stored LLM overrides:**
- `GET /api/settings/llm` and `PUT /api/settings/llm` are authenticated routes in `spoilerless/app/api/settings.py`.
- `SettingsRepository` serializes shared settings payload to JSON in `spoilerless/app/repository/settings.py` because Neo4j properties cannot store dictionaries.
- Effective-field precedence is stored `AppSetting` value first, then `LLM_*` environment value. Validated in `spoilerless/app/services/settings.py` and `spoilerless/app/services/chat.py`.
- Gemini receives `DEFAULT_GEMINI_BASE_URL` from `spoilerless/app/domain/settings.py` when neither stored nor environment supplies a base URL.
- `system_prompt_language` is graph-stored with English default; controls English/Turkish prompt selection through `spoilerless/app/services/chat.py` and `spoilerless/app/llm/system_prompt.py`.
- A null or blank key update preserves stored key; response models expose only configured status and masked suffix through `spoilerless/app/domain/settings.py`.
- Base URLs accepted by settings model must use HTTP or HTTPS and include host; validation is in `spoilerless/app/domain/settings.py`. Loopback/private hosts remain allowed for local compatible servers.
- Treat runtime LLM settings as shared application configuration.

**Frontend build-time settings:**
- `frontend/.env.example` is the safe template. Vite variables are embedded into browser bundle and must never contain provider keys or database credentials.
- `VITE_GOOGLE_CLIENT_ID` is a public OAuth client identifier consumed by `frontend/src/components/auth/LoginPage.tsx`.
- `VITE_API_BASE_URL` consumed by `frontend/src/api/client.ts`: prefixes all `apiFetch` requests when set, and `apiUrl()` applies same prefix to `/api/static/...` image URLs. Empty preserves local-dev relative-URL behavior through Vite proxy; prefix read at call time so tests can `vi.stubEnv` it.

## Monitoring & Observability

**Error Tracking:**
- No Sentry, Rollbar, Datadog, OpenTelemetry collector/exporter, or other managed error-tracking integration is detected in `pyproject.toml`, `frontend/package.json`, or tracked configuration.
- FastAPI centralizes database and LLM exception mapping in `spoilerless/app/core/errors.py` (now includes `payload_too_large` 413 mapping for body-size middleware), `spoilerless/app/llm/provider.py`, and registration in `spoilerless/app/main.py`.
- Repository/service error handlers remain consolidated in `spoilerless/app/api/exceptions.py` and installed by `install_repository_error_handlers(app)`. Add new domain exceptions there.
- Startup warning: `spoilerless/app/services/chat.py:warn_if_open_signup()` logs loud warning when `ENVIRONMENT=production` and signup is open (D-07 wiring called from `spoilerless/app/main.py:lifespan`).

**Logs:**
- Backend uses Python standard-library logging (e.g. `spoilerless/app/api/auth.py`, `spoilerless/app/services/auth.py`); Uvicorn supplies server/access logging.
- Provider-facing errors are sanitized before reaching API/SSE clients in `spoilerless/app/api/chat.py`; never log API keys, ID tokens, raw session tokens, or full stored settings payloads.
- Neo4j container log persistence is a local Compose concern in `docker-compose.yml`; no centralized log shipping is configured.

**Health:**
- `GET /health` and `HEAD /health` in `spoilerless/app/main.py` probe Neo4j connectivity and return connected/degraded service state.
- No external uptime monitor, metrics endpoint, tracing backend, or alerting integration is configured.

## CI/CD & Deployment

**Hosting:**
- Render is configured by `render.yaml`: free-tier `spoilerless-api` web service (Python runtime, `uv sync --frozen`, `uv run uvicorn spoilerless.app.main:app`) that auto-deploys on push. Frontend `frontend/vercel.json` provides Vercel SPA rewrite plus security headers.
- `frontend/vercel.json` now defines `headers` alongside `rewrites`: `Content-Security-Policy: default-src 'self'; script-src 'self' https://accounts.google.com; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self' https://accounts.google.com; frame-src https://accounts.google.com; object-src 'none'; base-uri 'self'; form-action 'self'`, plus `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. Backend CSP `img-src 'self'` stays — local portraits are self-hosted.
- Neo4j Aura is compatible with the configurable driver URI in `spoilerless/app/core/config.py`, but no concrete Aura instance is configured in tracked files.

**CI Pipeline:**
- GitHub Actions is configured in `.github/workflows/ci.yml` and `.github/workflows/release.yml`; no GitLab CI, Jenkinsfile, or Azure Pipelines configuration is present.
- Keep backend pytest and frontend test/build/lint commands runnable from `pyproject.toml` and `frontend/package.json`; CI invokes them through workflow files.

**Production Edge:**
- No reverse-proxy, TLS termination, static hosting, domain, or production API base URL is defined in repo manifest beyond `frontend/vercel.json` rewrite/headers and `ENVIRONMENT` gating in `spoilerless/app/main.py`.
- Production must route `/api` (including `/api/static`) to FastAPI because the Vite proxy in `frontend/vite.config.ts` exists only during development; `TrustedHostMiddleware` means the proxy must forward a valid `Host`.
- MIT `LICENSE` (Spoilerless Team, 2026) is present.

## Environment Configuration

**Required env vars:**
- Database: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`; optional `NEO4J_DATABASE` in `spoilerless/app/core/config.py`.
- Sign-in: backend `GOOGLE_CLIENT_ID` and frontend `VITE_GOOGLE_CLIENT_ID`; session/origin controls in `.env.example` and `spoilerless/app/core/config.py`.
- Optional LLM: `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, plus `LLM_MAX_CONCURRENT_GENERATIONS`, `LLM_MAX_TOOL_CALLS_PER_ROUND`, plus tuning fields in `spoilerless/app/core/config.py`.
- Rate limiting/cache: optional `REDIS_URL` plus `RATE_LIMIT_FAIL_OPEN`, `ALLOWED_HOSTS`, `MAX_BODY_SIZE_BYTES`, `ENVIRONMENT` in `spoilerless/app/core/config.py`.
- Frontend production backend origin: optional `VITE_API_BASE_URL` in `frontend/.env.example`, consumed by `frontend/src/api/client.ts`.

**Secrets location:**
- Local backend secrets belong in gitignored root `.env`; a sensitive file is present, but its contents must never be inspected or documented.
- Frontend local environment files are build inputs, not secret stores; only public `VITE_*` values belong there.
- Runtime LLM API keys may be stored server-side in Neo4j `AppSetting` payload through `spoilerless/app/repository/settings.py`; responses mask them.
- Raw session tokens live only in HttpOnly browser cookies; Neo4j stores their hashes.

## Webhooks & Callbacks

**Incoming:**
- No third-party webhook receiver among the 39 OpenAPI path templates from `spoilerless/app/main.py`.
- Google sign-in is a browser credential POST to `spoilerless/app/api/auth.py`, not an OAuth redirect/callback or server-to-server webhook.

**Outgoing:**
- No webhook delivery, message queue, email, SMS, payment, or notification integration is detected.
- Outbound network calls are limited to Google token-verification support in `spoilerless/app/services/auth.py`, optional LLM HTTP requests in `spoilerless/app/llm/provider.py`, optional Upstash Redis connection, and browser-loaded Google identity/media resources.

## Map Delta (2026-08-20 vs 2026-08-14 / 5bd1641)

- **Body-size & host hardening (SEC-DOS-004 / SEC-BE):** `BodySizeLimitMiddleware` (D-08) and `TrustedHostMiddleware` are new in `spoilerless/app/main.py`; `MAX_BODY_SIZE_BYTES` (1 MiB) and `ALLOWED_HOSTS` are new `Settings` fields in `spoilerless/app/core/config.py`; `payload_too_large` 413 envelope added to `spoilerless/app/core/errors.py`.
- **Docs-off in production (11-06):** `spoilerless/app/main.py:_docs_kwargs` disables `/docs`, `/redoc`, `/openapi.json` when `ENVIRONMENT=production`; `ENVIRONMENT` is a new settings field. Production OpenAPI enumeration via direct `app.openapi()` is only available in `development` now.
- **Fail-closed rate limiting (SEC-DOS-001):** `spoilerless/app/services/rate_limit.py` now checks `rate_limit_fail_open` + `environment` to return 503 on Redis outage in production; new `RATE_LIMIT_FAIL_OPEN` field in `spoilerless/app/core/config.py`.
- **Spoiler boundary centralization (D-01 / SEC-BE-001):** New `spoilerless/app/api/boundary.py:resolve_effective_boundary()` replaces ad-hoc per-route clamps; `spoilerless/app/api/graph.py` deletes 69-line inline `_resolve_effective_boundary` and aliases the shared one.
- **Visualization cache cardinality bound (D-12):** `spoilerless/app/cache/graph_cache.py` adds `FOCUS_SET_CAP`/`FOCUS_SET_TTL_SECONDS`/`_focus_capacity_allows()` (64 distinct signatures per series, 3600s TTL) fronting `set_cached_visualization`.
- **LLM cost caps (D-07 / SEC-DOS-002/003):** `LLM_MAX_CONCURRENT_GENERATIONS` (semaphore in `spoilerless/app/services/chat.py`) and `LLM_MAX_TOOL_CALLS_PER_ROUND` (cap in `spoilerless/app/retrieval/pipeline.py:llm_max_tool_calls_per_round`) are new settings; `ProposeChangesetInput.operations` capped at 20.
- **Answer delimiter neutralization:** `spoilerless/app/retrieval/pipeline.py:_neutralize_answer_delimiters()` escapes exact `<CONTEXT_SECTIONS>` tags in model answers to preserve 9-section framing.
- **GraphRAG delegation narrowing (QUAL-02):** `propose_changeset` executor now thin-delegates to `ChangeSetService.propose_via_tool()` — service owns validation + persistence.
- **Production security headers (vercel.json):** `frontend/vercel.json` now ships `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` headers; `render.yaml` minor infra polish.
- **Startup warning (11-05):** `warn_if_open_signup()` wiring in `spoilerless/app/main.py:lifespan` (guarded try/except so import failure cannot crash startup).
- **No new external integration targets:** still one Neo4j, optional Upstash Redis, optional LLM providers, and browser GIS/day-media. No new SaaS, queue, mail, or telemetry vendor.

---

*Integration audit: 2026-08-20*
