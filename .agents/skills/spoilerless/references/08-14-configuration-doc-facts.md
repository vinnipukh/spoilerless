# CONFIGURATION.md verified facts (2026-08-14)

Re-verified against live code 08-14 by the gsd-doc-verifier: **90/90 claims PASS**
(baseline artifact `.planning/tmp/verify-CONFIGURATION.md.json`). VERIFY marker
count on disk: **5** (doc lines 259, 437, 446, 494, 738). Doc uses NO
`uv run --project spoilerless` anywhere — never "fix" it in.

## Env vars
- Root `.env.example` contains: NEO4J_URI/USERNAME/PASSWORD/DATABASE,
  GOOGLE_CLIENT_ID, VITE_GOOGLE_CLIENT_ID, `VITE_API_BASE_URL=/api`,
  SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, `SESSION_COOKIE_SECURE=true`,
  FRONTEND_ORIGINS, LLM_ENABLED/PROVIDER/BASE_URL/API_KEY/MODEL/TIMEOUT_SECONDS/
  MAX_OUTPUT_TOKENS/TEMPERATURE/MAX_TOOL_ROUNDS/MAX_CONTEXT_ITEMS/
  MAX_CONTEXT_CHARACTERS.
- NOT in `.env.example` (must not be claimed present): SESSION_COOKIE_SAMESITE,
  ALLOWED_EMAILS, ADMIN_EMAILS, REDIS_URL, LLM_FALLBACK_EN, LLM_FALLBACK_TR.
- `spoilerless/app/core/config.py`: AliasChoices aura-* wins over NEO4J_* within
  a source; neo4j_uri/username/password have NO default (ValidationError at
  import); `env_file=".env"`, `extra="ignore"`; `get_settings()` @lru_cache.
- `verify_google_client_id_equality()` reads `os.environ["VITE_GOOGLE_CLIENT_ID"]`
  only when BOTH ids non-empty → two values that exist only in `.env` are NOT
  compared. No ENVIRONMENT / SECRET_KEY anywhere in `spoilerless/`.
- Tokens: `core/tokens.py` `generate_token(nbytes=48)` → `secrets.token_urlsafe(48)`;
  `hash_token` = sha256 hexdigest. GOOGLE_CLIENT_SECRET absent repo-wide (only
  "not used" mentions in docs/README).

## LLM
- `llm/system_prompt.py`: SYSTEM_PROMPT_ENG, SYSTEM_PROMPT_TR, `SYSTEM_PROMPTS`
  dict (English fallback via `.get(language, SYSTEM_PROMPT_ENG)`), plus
  SYSTEM_PROMPT_LANGUAGES. **SYSTEM_PROMPT_VERSION does not exist.**
- `repository/settings.py`: single `:AppSetting {key:'llm'}` node, MERGE upsert,
  payload = JSON string property. GET/PUT `/api/settings/llm` both
  `RequireAdminDependency`; PUT also `_csrf` (api/settings.py).
- `mask_api_key` (domain/settings.py:103): `"••••" + last 4` for len>4, one
  bullet per char for <=4, None when unset.
- `LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm", "ollama")`; vllm/ollama
  are scaffolding → route through OpenAICompatibleProvider. `LLMSettingsUpdate.provider`
  defaults to `"gemini"` (≠ env default `openai_compatible`). `_validate_base_url`:
  http/https + hostname only; loopback deliberately allowed. `DEFAULT_GEMINI_BASE_URL
  = "https://generativelanguage.googleapis.com"`.
- GeminiProvider posts `/v1beta/models/{model}:streamGenerateContent?alt=sse`
  with header `x-goog-api-key` (llm/provider.py:374/376). OpenAICompatibleProvider
  posts `/chat/completions`.
- BYOK (services/chat.py): non-blank `X-LLM-Api-Key` → provider built EXCLUSIVELY
  from headers; `X-LLM-Provider` missing/blank → openai_compatible; every
  non-`gemini` value → OpenAI branch. Headers never logged (main.py
  `_DENIED_HEADER_PREFIXES=("x-llm-",)`), never stored, never in responses.
- Precedence: `stored.get(field) or env_value`; `enabled = stored.get("enabled", env)`.
  `LLMProviderDisabled` → HTTP 503 code `LLM_DISABLED`.
- `system_prompt_language` read per turn in services/chat.py (`stored.get(...,"english")`);
  `_fallback_for` in retrieval/pipeline.py selects `"tr"` iff `== "turkish"`;
  `detect_language()` deleted (PROB-28/#52).

## Auth / sessions
- AuthService __init__ requires user_repo, session_repo, verifier — **no silent
  defaults** (PROB-09/#77); deps.py `get_auth_service()` passes
  `ProductionGoogleVerifier()` explicitly. main.py lifespan:
  `app.state.session_repo = Neo4jSessionRepository(database)`.
- `CsrfGuardDependency = Annotated[None, Depends(verify_origin)]` in api/deps.py;
  `_csrf` declared on: POST /api/auth/google, POST /api/auth/logout,
  PUT /api/settings/llm, candidates.py (4 routes), change_set.py (4), chat.py (4).
  verify_origin: Origin preferred, Referer scheme+host fallback, fail-closed on
  neither, `"*"` disables; 403 `AUTH_ORIGIN_NOT_ALLOWED`.
- ALLOWED_EMAILS → `EmailNotAllowedError` → 403 `AUTH_EMAIL_NOT_ALLOWED`.
  ADMIN_EMAILS role re-derived every login (services/auth.py:169);
  RequireAdminDependency → 403 `FORBIDDEN`. POST /api/auth/google → 401
  `AUTH_DISABLED` when google_client_id empty or session_ttl_seconds <= 0;
  verify failure → 401 `AUTH_INVALID_GOOGLE_CREDENTIAL`.
- Session storage: InMemorySessionRepository dev/test-only, constructed
  explicitly — NOT an AuthService default. Neo4jSessionRepository: `(:Session)`
  + `(:AppUser)-[:HAS_SESSION]->(:Session)`, only `token_hash` persisted, lookups
  reject `expires_at <= now` / `revoked_at IS NOT NULL`. Sweep loop every
  **3600 s** (SESSION_SWEEP_INTERVAL_SECONDS in lifespan) calls
  `session_repo.sweep_expired()` + `share_repo.sweep_expired()`, log-and-retry.

## Redis / rate limit / cache
- `get_redis()` @lru_cache (cache/redis_client.py), single shared client.
- Windows: login 10/300 s per IP; chat send 20/60 s per user; content write
  30/60 s per user falling back to IP; over limit → 429 `TOO_MANY_REQUESTS`.
  `init_rate_limiter()` unbound = no-op; request-time `try_acquire_async()`
  failure → warn + let through (PROB-23, never 500).
- Graph cache: key `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`,
  `DEFAULT_GRAPH_TTL_SECONDS = 300`. Route `GET /api/series/{series_id}/graph`
  lives in **api/graph.py** (router prefix `/api/series`), NOT series.py.

## Docker / deploy / frontend
- docker-compose.yml: `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` —
  env-substituted, NOT hardcoded; image `neo4j:2026.06.0-community`;
  `container_name: spoilerless-neo4j`; ports 127.0.0.1:7474/7687; volumes
  neo4j_data/logs/import/plugins; healthcheck wget spider localhost:7474
  (10s/5s/10). APOC not configured.
- scripts/env-local.sh exports 4 NEO4J_* vars, `NEO4J_PASSWORD=hdgraf-local-password`
  (fixed local-only; never reuse for deployed DBs).
- render.yaml: name `spoilerless-api`, runtime python, plan free, autoDeploy true,
  buildCommand `uv sync --frozen`, startCommand
  `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`, NO
  `envVars` block. vercel.json: single rewrite `/(.*)` → `/index.html`.
  frontend build = `tsc -b && vite build`.
- vite.config.ts: `envDir: '..'` → VITE_* from ROOT .env; frontend/.env and
  frontend/.env.local are ignored; frontend/.env.example is reference-only
  (VITE_GOOGLE_CLIENT_ID + commented `VITE_API_BASE_URL=https://api.spoilerless.net`).
  Root template `VITE_API_BASE_URL=/api` → `/api/api` pitfall; doc must say to
  blank it locally. Consumers: client.ts/chat.ts/export.ts use
  `import.meta.env.VITE_API_BASE_URL ?? ''`; LoginPage.tsx reads
  VITE_GOOGLE_CLIENT_ID and renders a config error when unset. Proxy `/api` →
  http://127.0.0.1:8000.
- Canonical setup commands: `uv run python -m spoilerless.app.graph.setup` or
  `uv run spoilerless-setup` (root pyproject `[project.scripts]` →
  `spoilerless.app.graph.setup:main`).

## Ontology / health
- Three YAMLs under `ontology/` (node_types / relation_types / claim_types), all
  `ontology_version: "0.1"` (matches `ONTOLOGY_VERSION` in graph/ontology.py).
  `load_ontology()` @lru_cache(maxsize=None) per directory; frozen dataclass with
  frozensets; `user_safe_relationship_types` = participation ∪ character
  (ontology.py:57); require_* raise OntologyValidationError.
- seed.py `setup_database()` (invoked by setup.py `async_main`) calls require_*
  per record; `create_constraints()` in seed.py; `NODE_LABELS` in graph/labels.py
  (re-exported by seed.py), `RELATIONSHIP_TYPES` in seed.py. Seed data:
  `data/dexter/{seed,metadata}/`.
- `GET /health`: `{"status":"ok","database":"connected","service":"spoilerless-backend"}`
  200; degraded/unavailable → 503 (main.py HealthResponse).
