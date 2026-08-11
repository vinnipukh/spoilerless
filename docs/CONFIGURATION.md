<!-- generated-by: gsd-doc-writer -->
# Configuration

> **Spoilerless** — configuration reference for all runtime, build, and infrastructure settings.

---

## Table of Contents

- [Environment Variables](#environment-variables)
- [Backend Configuration (Pydantic Settings)](#backend-configuration-pydantic-settings)
- [Per-Environment Overrides](#per-environment-overrides)
- [Runtime LLM Settings & BYOK Overrides](#runtime-llm-settings--byok-overrides)
- [Session Storage](#session-storage)
- [Docker Compose (Neo4j)](#docker-compose-neo4j)
- [Deployment Configuration](#deployment-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Ontology Configuration](#ontology-configuration)
- [Common Workflows](#common-workflows)

---

## Environment Variables

The backend reads configuration from the current working directory's `.env` file, as configured by
`spoilerless/app/core/config.py`. When starting it from the project root, copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

> **Verified against the repo:** `.env.example` (project root) was read directly. `VITE_GOOGLE_CLIENT_ID` and `VITE_API_BASE_URL` are included in the root template for Vite frontend configuration (via `envDir: '..'`). `SESSION_COOKIE_SAMESITE`, `ALLOWED_EMAILS`, `ADMIN_EMAILS`, `REDIS_URL`, `LLM_FALLBACK_EN`, and `LLM_FALLBACK_TR` exist as fields on the `Settings` class but are **not** listed in `.env.example` (they are optional overrides/additions with in-code defaults). `frontend/.env.example` remains a reference template, but Vite's configured environment directory is the repository root. Secret-bearing `.env` files were not read and no secret values are documented here.

### Variable Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `NEO4J_URI` | _(none — must be set)_ | Yes | Bolt URI for the Neo4j database. Use `neo4j+s://` for TLS connections (e.g. Neo4j Aura). Can also be configured via `AURA_URI`. |
| `NEO4J_USERNAME` | _(none — must be set)_ | Yes | Neo4j authentication username. Can also be configured via `AURA_USERNAME`. |
| `NEO4J_PASSWORD` | _(none — must be set)_ | Yes | Neo4j authentication password. Must match `NEO4J_AUTH` in `docker-compose.yml` for local development. Can also be configured via `AURA_PASSWORD`. |
| `NEO4J_DATABASE` | `neo4j` | No | Neo4j database name to connect to. Can also be configured via `AURA_DATABASE`. |
| `GOOGLE_CLIENT_ID` | `""` (empty) | No — but sign-in fails without it | Google OAuth 2.0 Web Client ID used to verify Google ID tokens. When unset, `POST /api/auth/google` returns `401 AUTH_DISABLED`. Must match `VITE_GOOGLE_CLIENT_ID`. |
| `VITE_GOOGLE_CLIENT_ID` | unset at runtime; placeholder in both templates | Yes — for frontend sign-in | Google OAuth 2.0 Web Client ID loaded by Vite from the root environment directory (`envDir: '..'`). It must equal `GOOGLE_CLIENT_ID`. The backend equality check reads this value from the **process environment**, not from Pydantic's `.env` parsing; see [startup validation](#behaviour). |
| `VITE_API_BASE_URL` | `""` when unset; root template currently declares `/api` | No | Origin prepended to frontend API paths, which already begin with `/api`. Leave unset/empty for local Vite proxying; use an origin such as `https://api.example.com` for a separately hosted backend. The root template's current `/api` value would produce `/api/api/...` requests and should be removed or overridden with an empty value for local development. |
| `SESSION_COOKIE_NAME` | `session` | No | Name of the HttpOnly session cookie. |
| `SESSION_TTL_SECONDS` | `604800` (7 days) | No — but sign-in fails if `<= 0` | Session time-to-live in seconds. `POST /api/auth/google` returns `401 AUTH_DISABLED` if this is explicitly set to a non-positive value; when unset, the default applies. |
| `SESSION_COOKIE_SAMESITE` | `lax` | No — not in `.env.example` | `SameSite` policy applied to the session cookie by `_make_cookie`/`_delete_cookie` in `spoilerless/app/api/auth.py`. Use `strict` or `none` deliberately per environment; `none` requires a secure cookie in modern browsers. |
| `SESSION_COOKIE_SECURE` | `true` | No | Sets the `Secure` flag on the session cookie. Local plain-HTTP development can explicitly set `SESSION_COOKIE_SECURE=false`. |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | No | Comma-separated list of allowed CORS origins for the FastAPI backend. Also used by `verify_origin` in `spoilerless/app/api/auth.py` for CSRF `Origin`/`Referer` validation on both `POST /api/auth/google` and `POST /api/auth/logout`. |
| `ALLOWED_EMAILS` | `""` (empty) | No — not in `.env.example` | Comma-separated, case-insensitive allowlist of emails permitted to sign in. Empty disables the allowlist (any verified Google account may sign in) — never leave empty in production. A verified-but-unlisted email raises `EmailNotAllowedError`, returned as `403 AUTH_EMAIL_NOT_ALLOWED`. |
| `ADMIN_EMAILS` | `""` (empty) | No — not in `.env.example` | Comma-separated, case-insensitive allowlist of emails granted the `admin` application role at login (`spoilerless/app/services/auth.py`). Empty means no admin exists yet. Role is re-derived from this variable on every login, so removing an email demotes that user on their next sign-in. |
| `REDIS_URL` | `""` (empty) | No | Upstash-style `rediss://` Redis connection string used for rate-limit counters (`spoilerless/app/services/rate_limit.py`) and the graph query response cache (`spoilerless/app/cache/graph_cache.py`). Empty disables both features — rate limiting becomes a no-op and caching always falls through to Neo4j. See [Rate Limiting & Redis Cache](#rate-limiting--redis-cache). |
| `LLM_ENABLED` | `false` | No | Fallback enable switch for server-managed (stored/env) LLM configuration. When no stored `enabled` value exists and no BYOK key is supplied, `false` raises `LLMProviderDisabled`, mapped to HTTP 503 with code `LLM_DISABLED`. A request with a non-blank `X-LLM-Api-Key` uses the BYOK branch before this switch is checked. |
| `LLM_PROVIDER` | `openai_compatible` | No | Environment fallback for the active provider selector. Two implementations exist: `openai_compatible` and `gemini`. The PUT request model defaults an omitted `provider` field to `gemini`, which is then stored; that request default is distinct from this env/runtime fallback. |
| `LLM_BASE_URL` | `""` (empty) | Effectively required for `openai_compatible` if `LLM_ENABLED=true` and no runtime override is stored; optional for Gemini | Base URL for the OpenAI-compatible `/chat/completions` endpoint, or the Gemini API base when `LLM_PROVIDER=gemini` (defaults to `https://generativelanguage.googleapis.com` if left empty for Gemini). |
| `LLM_API_KEY` | `""` (empty) | Effectively required if `LLM_ENABLED=true` and no runtime override is stored | LLM provider API key. The full key is accessed by settings masking, chat provider resolution, and provider implementations; API responses expose only the masked key, and the full key is never logged or returned to the frontend. |
| `LLM_MODEL` | `""` (empty) | Effectively required if `LLM_ENABLED=true` and no runtime override is stored | Model identifier passed to the provider (e.g. `gpt-4.1-mini`, `gemini-2.0-flash`). |
| `LLM_TIMEOUT_SECONDS` | `60` | No | Per-request timeout for LLM provider calls, in seconds. |
| `LLM_MAX_OUTPUT_TOKENS` | `800` | No | Maximum tokens the model may generate per completion call. |
| `LLM_TEMPERATURE` | `0.0` | No | Sampling temperature for LLM completions (`0` = deterministic). |
| `LLM_MAX_TOOL_ROUNDS` | `4` | No | Maximum bounded tool-calling rounds per chat turn. |
| `LLM_MAX_CONTEXT_ITEMS` | `40` | No | Maximum number of retrieved context items assembled per turn. |
| `LLM_MAX_CONTEXT_CHARACTERS` | `12000` | No | Maximum total character budget for the assembled context per turn. |
| `LLM_FALLBACK_EN` | `None` (unset) | No | Optional override for the localized "insufficient evidence" fallback response in English (not listed in `.env.example`). Falls back to `INSUFFICIENT_EVIDENCE_FALLBACK_EN` in `spoilerless/app/llm/fallbacks.py` when unset or blank. |
| `LLM_FALLBACK_TR` | `None` (unset) | No | Optional override for the localized "insufficient evidence" fallback response in Turkish (not listed in `.env.example`). Falls back to `INSUFFICIENT_EVIDENCE_FALLBACK_TR` in `spoilerless/app/llm/fallbacks.py` when unset or blank. |

> **Note:** There is currently no `ENVIRONMENT` (development/production) or `SECRET_KEY` variable in the
> codebase. Session tokens are opaque, cryptographically random strings (`secrets.token_urlsafe(48)`)
> hashed with SHA-256 before storage — they are not signed with a symmetric key, so no `SECRET_KEY` is
> needed for the current session design.

> **Note:** `GOOGLE_CLIENT_SECRET` is **not** used by this project. The backend only needs
> `GOOGLE_CLIENT_ID` to verify Google ID tokens via the `google-auth` library's
> `id_token.verify_oauth2_token()` function, which fetches Google's public signing keys over the network.
> No client secret is stored or required on the server.

---

## Backend Configuration (Pydantic Settings)

The `Settings` class in `spoilerless/app/core/config.py` uses **pydantic-settings** (`BaseSettings`) to load
configuration from `.env` (or the process environment). Every field reads from its uppercase environment
variable name (e.g. `neo4j_uri` ← `NEO4J_URI`).

```python
class Settings(BaseSettings):
    # Accept either the aura_* names used in local .env files or the NEO4J_*
    # names used in deployed environments (Render/Aura credential file). The
    # aura_* alias wins when both are present.
    neo4j_uri: str = Field(validation_alias=AliasChoices("aura_uri", "neo4j_uri"))
    neo4j_username: str = Field(validation_alias=AliasChoices("aura_username", "neo4j_username"))
    neo4j_password: str = Field(validation_alias=AliasChoices("aura_password", "neo4j_password"))
    neo4j_database: str = Field(default="neo4j", validation_alias=AliasChoices("aura_database", "neo4j_database"))

    google_client_id: str = Field(default="")
    session_cookie_name: str = Field(default="session")
    session_ttl_seconds: int = Field(default=604800)
    session_cookie_samesite: str = Field(default="lax")
    session_cookie_secure: bool = Field(default=True)
    frontend_origins: str = Field(default="http://localhost:5173")
    allowed_emails: str = Field(default="")
    admin_emails: str = Field(default="")

    redis_url: str = Field(default="")

    llm_enabled: bool = Field(default=False)
    llm_provider: str = Field(default="openai_compatible")
    llm_base_url: str = Field(default="")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="")
    llm_timeout_seconds: int = Field(default=60)
    llm_max_output_tokens: int = Field(default=800)
    llm_temperature: float = Field(default=0.0)
    llm_max_tool_rounds: int = Field(default=4)
    llm_max_context_items: int = Field(default=40)
    llm_max_context_characters: int = Field(default=12000)
    llm_fallback_en: str | None = Field(default=None)
    llm_fallback_tr: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

### Behaviour

- **Source precedence:** process environment variables override values from `.env`; `.env` is resolved relative to the process's current working directory. Within one settings source, each `AURA_*` alias is checked before its corresponding `NEO4J_*` name. Source precedence still wins across sources: for example, process `NEO4J_URI` overrides `.env` `AURA_URI`.
- **`extra="ignore"`:** Unknown variables present in `.env` are silently ignored rather than raising an error.
- **`@lru_cache`:** `get_settings()` caches a single `Settings` instance for the process lifetime.
- **Required-field and Google-ID startup validation:** `neo4j_uri`, `neo4j_username`, and
  `neo4j_password` have no default, so `Settings()` raises a `pydantic.ValidationError` at import time if
  they are missing. All other fields have defaults. During lifespan startup, `verify_google_client_id_equality()` compares the resolved backend `GOOGLE_CLIENT_ID` with `os.environ["VITE_GOOGLE_CLIENT_ID"]` only when both are non-empty. Because Pydantic reading root `.env` does not populate `os.environ`, two values that exist only in `.env` are **not** compared by this function; deployment environments should set both as process/build environment variables and keep them equal.

### Database connection

`Neo4jDatabase` (`spoilerless/app/graph/database.py`):

1. Creates an `AsyncGraphDatabase.driver(...)` using `neo4j_uri` and `(neo4j_username, neo4j_password)`.
2. Exposes `execute_query()` and `execute_write()`, both scoped to the configured `neo4j_database`.
3. Connection is verified once at FastAPI startup via `verify_connection()`; failures are swallowed
   (degraded startup) so `/health` can report live connectivity rather than crash the process.

### CORS

`spoilerless/app/main.py` parses `FRONTEND_ORIGINS` and configures `CORSMiddleware`:

```python
_allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origins.split(",")
    if origin.strip()
]
```

Supports multiple comma-separated origins. `allow_credentials=True` is set, so the session cookie is
honored on cross-origin requests from any listed origin.

### CSRF protection

The same `FRONTEND_ORIGINS` value also drives `verify_origin()` in `spoilerless/app/api/auth.py`, a FastAPI
dependency applied to both `POST /api/auth/google` and `POST /api/auth/logout`. It compares the request's `Origin` (or, if absent,
`Referer`) header against the configured origin list and rejects mismatches with `403 AUTH_ORIGIN_NOT_ALLOWED`.
A request with neither header is also rejected (fail-closed). Setting `FRONTEND_ORIGINS=*` disables this
check entirely (not recommended). `SESSION_COOKIE_SAMESITE` (see below) is the complementary cookie-level
defense — `verify_origin()` covers cases `SameSite` alone does not (subdomain-based attacks, top-level
navigations).

### Session cookie SameSite policy

`_make_cookie()` / `_delete_cookie()` in `spoilerless/app/api/auth.py` set the session cookie's `SameSite`
attribute from `SESSION_COOKIE_SAMESITE` (default `lax`) rather than a hardcoded value, so it can be tuned
per deployment (`strict` or `none` — the latter requires `SESSION_COOKIE_SECURE=true`).

### Authentication allowlist and admin role

Two optional comma-separated, case-insensitive email lists gate and classify sign-in
(`spoilerless/app/services/auth.py`, `spoilerless/app/api/auth.py`):

- **`ALLOWED_EMAILS`** — when non-empty, restricts sign-in to the listed emails. A verified-but-unlisted
  Google account is rejected with `403 AUTH_EMAIL_NOT_ALLOWED` (`EmailNotAllowedError`). Empty means any
  verified Google account may sign in.
- **`ADMIN_EMAILS`** — when the signed-in email (lowercased) is a member, the user's `role` is set to
  `"admin"`; otherwise `"user"`. Role is re-derived from this variable **on every login** — removing an
  email demotes that user's `role` the next time they sign in, it is never read from client input or
  persisted independent of login. `RequireAdminDependency` (`spoilerless/app/api/deps.py`) enforces
  `role == "admin"` on admin-only routes (for example `GET`/`PUT /api/settings/llm`), rejecting with
  `403 FORBIDDEN` otherwise.

Both checks run **after** Google token verification succeeds, so they are driven by a Google-attested email
plus a server-controlled env var — never by unverified client input.

### Rate limiting & Redis cache

Two independent features share the single `REDIS_URL` setting and the one shared `redis.asyncio` client in
`spoilerless/app/cache/redis_client.py` (`get_redis()`, `lru_cache`-decorated). Both are guarded on a non-empty
`REDIS_URL`; when it is unset, local development runs unthrottled and always queries Neo4j directly. Graph-cache
operations catch Redis errors and fall through to Neo4j. Rate-limiter initialization is awaited during startup
when `REDIS_URL` is non-empty, so an invalid or unreachable configured Redis service can fail startup rather than
silently disabling throttling:

- **Rate limiting** (`spoilerless/app/services/rate_limit.py`) — `RateLimiter` dependencies backed by
  `pyrate-limiter`'s Redis `RedisBucket` (one bucket key per window). Bound
  once at FastAPI startup by `init_rate_limiter()` (`spoilerless/app/main.py`'s `lifespan()`) when `REDIS_URL` is
  set. Configured windows:

  | Route group | Limit | Window | Key |
  |---|---|---|---|
  | Login (`POST /api/auth/google`) | 10 requests | 300s (5 min) | per IP |
  | Chat send | 20 requests | 60s | per user |
  | Content write | 30 requests | 60s | per user, falling back to IP |

  A request over the limit is rejected with `429 TOO_MANY_REQUESTS`.
- **Graph query response cache** (`spoilerless/app/cache/graph_cache.py`) — cache-aside layer for
  `GET /api/series/{series_id}/graph`. Cache key is `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`
  with a `300`-second TTL (`DEFAULT_GRAPH_TTL_SECONDS`); any Redis error or unset `REDIS_URL` falls through
  to querying Neo4j directly rather than surfacing a request failure.

`REDIS_URL` is expected to be an Upstash-style `rediss://` TLS connection string and is not declared in
`.env.example`. It is consumed by the startup guard in `main.py`, the shared Redis client, the rate limiter,
and the graph cache.

### Health check

```http
GET /health
```

Returns `{"status": "ok", "database": "connected", "service": "spoilerless-backend"}` (HTTP 200) when
Neo4j is reachable, or `{"status": "degraded", "database": "unavailable", ...}` with HTTP 503 otherwise.

---

## Per-Environment Overrides

No `.env.development`, `.env.production`, or `.env.test` files are committed. The backend's
`SettingsConfigDict` names only `.env` and has no `ENVIRONMENT` setting, so backend per-environment values come
from the current working directory's `.env` and/or the process environment. Vite uses the repository root as
its environment directory and may receive build-mode or hosting-process `VITE_*` values even though no
mode-specific files are committed:

- **Local development** — `cp .env.example .env`; set `NEO4J_PASSWORD` (the same value is substituted into
  `docker-compose.yml`'s `NEO4J_AUTH`, defaulting to `change-me` if unset — see
  [Docker Compose](#docker-compose-neo4j)); keep `NEO4J_URI=neo4j://localhost:7687` and
  `FRONTEND_ORIGINS=http://localhost:5173`. Remove or blank the root template's `VITE_API_BASE_URL=/api` so
  frontend calls use their existing `/api/...` paths through the Vite proxy. `.env.example` ships
  `SESSION_COOKIE_SECURE=true`; set it to `false` if the local backend is served over plain HTTP on a
  non-`localhost` host.
- **Production / Neo4j Aura** — set `NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io:7687`, real
  credentials, `SESSION_COOKIE_SECURE=true`, and the deployed frontend origin(s) in `FRONTEND_ORIGINS`.
  <!-- VERIFY: The exact production Neo4j Aura instance URI and cloud region are deployment-specific and
  not discoverable from the repository. -->
- **Frontend** — the frontend reads `VITE_*` variables from the repository root via `envDir: '..'` in `frontend/vite.config.ts`. `frontend/.env.example` is only a reference template; creating `frontend/.env` or `frontend/.env.local` will not override the configured root environment directory. `VITE_*` variables are inlined into the bundle at build time, so production values must be present when `npm run build` runs — they cannot be injected at runtime.
- **Local test helper** — `source scripts/env-local.sh` exports the four `NEO4J_*` variables for the local Docker database before a test command. Because process variables outrank `.env`, this intentionally overrides database values from the root file for that shell. The script contains a fixed local-only password; keep it aligned with the local container rather than reusing it for any deployed database.

---

## Runtime LLM Settings & BYOK Overrides

In addition to the `LLM_*` environment variables above, the effective LLM provider configuration can be
set at runtime through the API (persisted in Neo4j) or passed on a per-request basis via HTTP headers.

### Persisted Settings (Stored in Neo4j)

- **Storage:** `SettingsRepository` (`spoilerless/app/repository/settings.py`) persists a single
  `:AppSetting {key: 'llm'}` node in Neo4j via `MERGE`, storing the payload as a JSON string property.
- **Endpoints (admin role required):**
  - `GET /api/settings/llm` — returns stored values with environment fallbacks, but not provider-construction defaults (for example, Gemini's default base URL is still returned as `null` when no URL is configured); the API key is masked
    (`mask_api_key()` returns `"••••" + last 4 chars` for keys longer than four characters, one bullet per character for shorter keys, or `None` if unset).
  - `PUT /api/settings/llm` — updates the configuration (`spoilerless/app/api/settings.py`,
    `SettingsService.update_llm`).
  - Both routes depend on `RequireAdminDependency` (`spoilerless/app/api/deps.py`), so only a session whose
    `role == "admin"` (see [Authentication allowlist and admin role](#authentication-allowlist-and-admin-role))
    may view or change the shared LLM provider configuration; any other authenticated user gets
    `403 FORBIDDEN`.
- **Precedence:** For `provider`, `api_key`, `base_url`, and `model`, a non-empty stored graph value wins;
  otherwise the corresponding `LLM_*` setting from `Settings` is used as the fallback (`get_llm()` and
  `get_llm_provider()` use `stored.get(field) or env_value`). `enabled` is different because `false` is
  meaningful: presence in storage wins via `stored.get("enabled", env_value)`; only an absent stored key
  falls back to `settings.llm_enabled` (`spoilerless/app/services/settings.py`).
- **Supported providers:** `spoilerless/app/domain/settings.py` declares
  `LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm", "ollama")`. `vllm` and `ollama` are scaffolding
  only — accepted, validated, and stored, but with no dedicated provider class yet; both route through
  `OpenAICompatibleProvider` since they speak the same OpenAI-compatible `/chat/completions` wire shape.
  The `PUT` request body (`LLMSettingsUpdate`) defaults `provider` to `"gemini"` when not supplied — note
  this differs from the `LLM_PROVIDER` env default of `"openai_compatible"` described above.
- **Gemini default base URL:** When `provider` is `gemini` and no `base_url` is stored or set via
  `LLM_BASE_URL`, the service falls back to `DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"`.
- **Provider protocol and activation:** Two implementations back the four supported providers, but only the
  effective configured provider is active for a chat call. `OpenAICompatibleProvider` posts to
  `/chat/completions` and serves `"openai_compatible"`, `"vllm"`, and `"ollama"`. `GeminiProvider` uses
  Gemini's `generateContent`/`streamGenerateContent` action family and serves `"gemini"`; the current
  streaming implementation posts to `/v1beta/models/{model}:streamGenerateContent?alt=sse`. It is not an
  OpenAI-compatible chat-completions endpoint.
- **URL scheme validation:** `LLMSettingsUpdate.base_url` is validated to require an `http`/`https`
  scheme and a hostname (`_validate_base_url` in `spoilerless/app/domain/settings.py`) — an SSRF-via-scheme
  guard. It deliberately does **not** block private/loopback addresses, since local vLLM/Ollama endpoints
  (`http://127.0.0.1:...`) are a supported deployment target.
- **System prompt:** The assistant prompt lives in `spoilerless/app/llm/system_prompt.py` with two localized
  variants: `SYSTEM_PROMPT_ENG` (English) and `SYSTEM_PROMPT_TR` (Turkish), selected through the
  `SYSTEM_PROMPTS` mapping (English is the fallback for any unknown language).
- **Assistant language:** `system_prompt_language` (`"english"` or `"turkish"`, default `"english"`) is
  also stored/updated through this endpoint. It controls both which system prompt variant is sent to the
  LLM (`spoilerless/app/services/chat.py` reads the stored value per turn) and which localized fallback text
  is used for a turn — see `_fallback_for()` in `spoilerless/app/retrieval/pipeline.py`, which selects `"tr"`
  when `system_prompt_language == "turkish"` and otherwise `"en"`. This is a direct selection — there is
  no automatic detection of the user's message language anywhere in the codebase (`detect_language()` no
  longer exists in `spoilerless/app/llm/fallbacks.py`).
- **Secret write semantics:** `PUT /api/settings/llm` accepts `api_key: str | None`. `None` preserves the
  previously stored key. Blank/whitespace also preserves an existing stored key, but is rejected with
  `422 INVALID_REQUEST` when no key is stored. There is currently no API operation that clears a stored key;
  `GET` never returns the full key for a client to round-trip.

### Request-Scoped BYOK (Bring-Your-Own-Key) Header Overrides

In addition to stored graph settings and environment variables, the backend supports per-request LLM configuration via HTTP headers sent on chat endpoints (`spoilerless/app/services/chat.py`):

| Header | Description |
|---|---|
| `X-LLM-Api-Key` | Per-request LLM API key. When present and non-blank, triggers BYOK resolution. |
| `X-LLM-Provider` | LLM provider selector. Missing/blank defaults to `openai_compatible`; `gemini` selects `GeminiProvider`. The current header path does not validate the other strings against `LLM_PROVIDERS`: every non-`gemini` value follows the OpenAI-compatible branch. Clients should send only `openai_compatible`, `vllm`, or `ollama` there. |
| `X-LLM-Base-URL` | Custom base URL for the LLM endpoint (validated for HTTP/HTTPS scheme and hostname). |
| `X-LLM-Model` | LLM model identifier. |

**Resolution Order / Precedence:**
1. **BYOK Headers:** If `X-LLM-Api-Key` is present and non-blank in the request headers, the provider is constructed **exclusively** from the `X-LLM-*` header values. Stored graph settings and `.env` fallbacks are not consulted. Header credentials reach only the provider constructor and are never logged, stored in Neo4j, or returned in API response models.
2. **Neo4j Graph Storage:** If no BYOK key is provided, non-empty settings stored in the `:AppSetting {key: 'llm'}` graph node take next precedence.
3. **Environment Fallbacks:** If a setting is absent in graph storage, the corresponding `LLM_*` environment variable default is used.

---

## Session Storage

Two `SessionRepository` implementations exist in `spoilerless/app/repository/session.py`:

| Implementation | Storage | Used when |
|---|---|---|
| `InMemorySessionRepository` | In-process Python dict | Development/testing only — used directly by tests and dev scripts. It is **not** an `AuthService` constructor default: `AuthService` requires explicit repository arguments (PROB-09/#77 removed the old silent `InMemorySessionRepository()` fallback). |
| `Neo4jSessionRepository` | `(:Session)` nodes in Neo4j, linked via `(:AppUser)-[:HAS_SESSION]->(:Session)` | The actual FastAPI app — `spoilerless/app/main.py`'s `lifespan()` sets `app.state.session_repo = Neo4jSessionRepository(database)` at startup, and `get_auth_service()` (`spoilerless/app/api/deps.py`) always injects it. |

Only the raw session token's SHA-256 hash is ever persisted (`token_hash`); the raw token returned to the
browser as the cookie value is never stored. Session lookups reject expired (`expires_at <= now`) or
revoked (`revoked_at IS NOT NULL`) sessions.

### Periodic Session Cleanup

Automated background cleanup is active whenever Neo4j is reachable during application startup:
- During application `lifespan()` startup in `spoilerless/app/main.py`, an asyncio background task (`_session_sweep_loop`) is launched if Neo4j is reachable on startup.
- The sweep runs periodically every **3,600 seconds (1 hour)** (`SESSION_SWEEP_INTERVAL_SECONDS`).
- Each iteration calls `app.state.session_repo.sweep_expired()` and `app.state.share_repo.sweep_expired()`, deleting expired or revoked `(:Session)` and `(:ShareToken)` nodes from Neo4j.
- Failed sweep iterations log an exception and retry on the next interval without crashing the process.

---

## Docker Compose (Neo4j)

The `docker-compose.yml` at the project root runs a single Neo4j Community container for local development.

```yaml
services:
  neo4j:
    image: neo4j:2026.06.0-community
    container_name: spoilerless-neo4j
    restart: unless-stopped

    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"

    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}

    volumes:
      - ./neo4j_data:/data
      - ./neo4j_logs:/logs
      - ./neo4j_import:/import
      - ./neo4j_plugins:/plugins

    healthcheck:
      test:
        [
          "CMD-SHELL",
          "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"
        ]
      interval: 10s
      timeout: 5s
      retries: 10
```

### Key details

| Property | Value | Notes |
|---|---|---|
| **Image** | `neo4j:2026.06.0-community` | Exact image tag committed in `docker-compose.yml`. |
| **Bolt port** | `7687`, bound to `127.0.0.1` only | Used by the Python driver — set `NEO4J_URI=neo4j://localhost:7687` to match. Not reachable from outside the host. |
| **HTTP port** | `7474`, bound to `127.0.0.1` only | Neo4j Browser UI at `http://localhost:7474`. |
| **Credentials** | `neo4j` / value of the host's `NEO4J_PASSWORD` env var, defaulting to `change-me` if unset | `NEO4J_AUTH` is substituted from the shell/`.env` `NEO4J_PASSWORD` via Compose's `${VAR:-default}` syntax — it must match the backend's own `NEO4J_PASSWORD` for the driver to authenticate. Docker Compose reads `.env` at the project root automatically for this substitution. |
| **APOC** | Not configured | The `./neo4j_plugins` volume is mounted, but the Compose file neither installs APOC nor declares a Neo4j plugin environment setting. |

### Starting Neo4j

```bash
docker compose up -d
docker compose ps neo4j
# Or open http://localhost:7474 in a browser
```

---

## Deployment Configuration

### Render backend (`render.yaml`)

The committed Render Blueprint declares one free Python web service:

| Setting | Repository value |
|---|---|
| Service name | `spoilerless-api` |
| Runtime / plan | `python` / `free` |
| Auto-deploy | `true` |
| Build command | `uv sync --frozen` |
| Start command | `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` |

`render.yaml` does not declare an `envVars` block. Configure the required `NEO4J_URI`, `NEO4J_USERNAME`, and
`NEO4J_PASSWORD` values in the deployment environment, plus any optional settings from the table above. Keep
secrets server-side: do not expose Neo4j, Redis, or LLM credentials through `VITE_*` variables. `PORT` is read by
the committed start command from the hosting process environment.

<!-- VERIFY: The connected Render branch and the currently configured Render environment-variable values live
outside the repository; confirm them in the Render service settings before deployment. -->

### Vercel frontend (`frontend/vercel.json`)

The Vercel configuration contains a single SPA fallback rewrite from `/(.*)` to `/index.html`, allowing
client-side paths to load the frontend entry point. The frontend build is controlled by `frontend/package.json`:
`npm run build` runs `tsc -b && vite build`, and Vite emits build-time `VITE_*` values into the bundle.

<!-- VERIFY: The Vercel project's Root Directory, production domain, and build-time `VITE_GOOGLE_CLIENT_ID` /
`VITE_API_BASE_URL` values are external project settings. If Root Directory is `frontend`, the committed
`frontend/vercel.json` is the applicable deployment config. -->

---

## Frontend Configuration

### Vite dev server (`frontend/vite.config.ts`)

```typescript
export default defineConfig({
  envDir: '..',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

The dev server runs on the Vite default port (`5173`) and proxies `/api/*` requests to the FastAPI backend
at `http://127.0.0.1:8000`. Frontend API call sites already pass paths beginning with `/api`; with
`VITE_API_BASE_URL` unset or empty, those paths use this proxy. For a separately hosted backend,
`VITE_API_BASE_URL` should be the backend **origin** (without a trailing `/api` path), so the frontend issues
absolute cross-origin requests. Vite's dev proxy does not exist outside `vite dev`.

### Frontend environment variables

`frontend/vite.config.ts` sets `envDir: '..'`, so Vite reads its `VITE_*` variables from the repository-root environment files. `frontend/.env.example` is a reference template only and declares the same two public variables:

| Variable | Required | Description |
|---|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Yes, for sign-in | Google OAuth client ID, read via `import.meta.env.VITE_GOOGLE_CLIENT_ID` in `frontend/src/components/auth/LoginPage.tsx`. It must match the backend's `GOOGLE_CLIENT_ID`. When unset, the login page renders a configuration error instead of the Google sign-in button. |
| `VITE_API_BASE_URL` | No — runtime fallback is empty | Read via `import.meta.env.VITE_API_BASE_URL ?? ''` in `frontend/src/api/client.ts`, `frontend/src/api/chat.ts`, and `frontend/src/api/export.ts`. Leave empty for local proxying. For a hosted backend use an origin such as `https://api.example.com`, without `/api`, because every call site already supplies `/api/...`. The root `.env.example` currently declares `/api`; that template value is inconsistent with the consumers and creates `/api/api/...` URLs. <!-- VERIFY: The exact production API origin is deployment-specific; confirm the current value in the Vercel project's build-time environment variables. --> |

> **Security:** Vite inlines `VITE_*` variables into the built JavaScript bundle at build time — never
> store secrets in the root `.env`. `VITE_GOOGLE_CLIENT_ID` is a public OAuth client identifier
> (safe to expose to the browser by design), not a secret.

### TypeScript config

| File | Purpose |
|---|---|
| `frontend/tsconfig.json` | Root config — references `frontend/tsconfig.app.json` and `frontend/tsconfig.node.json`; declares the `@/*` path alias. |
| `frontend/tsconfig.app.json` | App source config — `target: es2023`, `module: esnext`, `moduleResolution: bundler`, `jsx: react-jsx`, strict unused-locals/params linting. |
| `frontend/tsconfig.node.json` | Config for `frontend/vite.config.ts` itself — `target: es2023`, `module: nodenext`. |

### Path alias

Both `frontend/tsconfig.json`/`frontend/tsconfig.app.json` and `frontend/vite.config.ts` register `@` as an alias
for `./src`:

```typescript
// vite.config.ts
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
},
```

```json
// tsconfig.json / tsconfig.app.json
"paths": {
  "@/*": ["./src/*"]
}
```

### Shadcn UI (`frontend/components.json`)

| Setting | Value |
|---|---|
| Style | `radix-nova` |
| Base color | `zinc` |
| CSS variables | Enabled |
| Icon library | `lucide` |
| Components path | `@/components` |
| Utils path | `@/lib/utils` |
| Hooks path | `@/hooks` |

---

## Ontology Configuration

The ontology is defined in three YAML files under `ontology/`, loaded at runtime by
`spoilerless/app/graph/ontology.py::load_ontology()`.

### File structure

```
ontology/
├── node_types.yaml        # Node type declarations grouped by category
├── relation_types.yaml    # Relationship type declarations grouped by category
└── claim_types.yaml       # Claim types, statuses, and confidence levels
```

All three files must declare `ontology_version: "0.1"` (matching `ONTOLOGY_VERSION` in `spoilerless/app/graph/ontology.py`) or
`load_ontology()` raises `OntologyValidationError`.

### `ontology/node_types.yaml`

```yaml
ontology_version: "0.1"

node_types:
  structural:
    - Series
    - Season
    - Episode
    - Scene

  narrative:
    - Character
    - Location
    - Organization
    - Object
    - Event

  knowledge:
    - Claim
    - Source
    - EvidenceFragment

  user:
    - UserNote

  system:
    - Revision
```

Groups are used for documentation and access control; the flattened `node_types` set (all groups combined)
is what `require_node_type()` checks against.

### `ontology/relation_types.yaml`

```yaml
ontology_version: "0.1"

relation_types:
  structural:
    - PART_OF
    - PRECEDES
    - OCCURRED_IN
    - LOCATED_IN

  participation:
    - PARTICIPATED_IN
    - WITNESSED
    - CAUSED
    - AFFECTED
    - TARGETED
    - MENTIONED

  character:
    - KNOWS
    - FAMILY_OF
    - WORKS_WITH
    - TRUSTS
    - DISTRUSTS
    - HELPS
    - OPPOSES
    - THREATENS
    - ATTACKS
    - KILLS

  provenance:
    - SUPPORTED_BY
    - CONTRADICTED_BY
    - DERIVED_FROM
    - REFERS_TO

  revision:
    - CORRECTS
    - SUPERSEDES
    - REVERTS_TO
```

`Ontology.user_safe_relationship_types` exposes the union of the `participation` and `character` groups —
these are the relationship types the API allows a signed-in user to create directly. All other groups are
backend/system-only.

### `ontology/claim_types.yaml`

```yaml
ontology_version: "0.1"

claim_types:
  - explicit_fact
  - observed_event
  - inferred_state
  - external_interpretation
  - user_authored

claim_statuses:
  - candidate
  - corroborated
  - canonical
  - disputed
  - rejected

confidence_levels:
  - low
  - medium
  - high
  - verified
```

### Validation at load time

`load_ontology()` (cached by `@lru_cache(maxsize=None)` per directory argument):

1. Reads all three YAML files from the `ontology/` directory.
2. Validates each file's `ontology_version` matches `"0.1"`.
3. Builds a frozen `Ontology` dataclass with `frozenset` members for O(1) membership checks.
4. Exposes `require_node_type()`, `require_relationship_type()`, `require_claim_type()`,
   `require_claim_status()`, and `require_confidence_level()`, each raising `OntologyValidationError` for
   an undeclared value.

Seed data validation calls these `require_*()` methods before any data is written to Neo4j: the
`setup_database()` routine in `spoilerless/app/graph/seed.py` (invoked by `spoilerless/app/graph/setup.py`)
validates every seeded node type, relationship type, claim type/status, and confidence level against the
loaded ontology.

---

## Common Workflows

### 1. First-time setup

```bash
# 1. Copy the environment template (Vite reads VITE_* from this root file)
cp .env.example .env
# Edit .env — set NEO4J_PASSWORD (docker-compose.yml substitutes this same
# value into NEO4J_AUTH, defaulting to "change-me" if left unset),
# GOOGLE_CLIENT_ID and VITE_GOOGLE_CLIENT_ID (same value), optionally
# ADMIN_EMAILS to grant yourself the admin role (required for the LLM
# settings endpoints). Remove or blank VITE_API_BASE_URL=/api for local
# proxying; the frontend call paths already include /api.

# 2. Start Neo4j
docker compose up -d

# 3. Install Python deps and seed the database
uv sync
uv run python -m spoilerless.app.graph.setup
#   (equivalent: uv run spoilerless-setup — the console script declared in the root pyproject.toml)

# 4. Start the backend
uv run uvicorn spoilerless.app.main:app --reload

# 5. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### 2. Switching databases

Change `NEO4J_URI` (and credentials) to point at a different Neo4j instance, e.g. Neo4j Aura:

```env
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io:7687
NEO4J_USERNAME=<database-username>
NEO4J_PASSWORD=<database-password>
NEO4J_DATABASE=<database-name>
```

### 3. Adding a new ontology type

1. Edit the appropriate YAML file in `ontology/`.
2. Add any required indexes in `spoilerless/app/graph/seed.py` (`create_constraints()`).
3. Add seed data if needed under `data/dexter/seed/` or `data/dexter/metadata/`.
4. If the new label/type is used by seed data, update the relevant tuple: `NODE_LABELS` in
   `spoilerless/app/graph/labels.py` (re-exported by `seed.py`) or `RELATIONSHIP_TYPES` in
   `spoilerless/app/graph/seed.py`; these tuples cover seeded types, not every ontology declaration.
5. Restart the backend so modules that loaded an ontology at import time see the change. `load_ontology()` is `lru_cache`-cached by directory argument for the process lifetime.

### 4. Setting up authentication (required to sign in)

<!-- VERIFY: Google Cloud Console labels and OAuth setup screens are external infrastructure and can change;
confirm the current Web application client workflow in the Google Cloud Console. -->

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials.
2. Create an **OAuth 2.0 Client ID** of type **Web application**.
3. Add `http://localhost:5173` to **Authorized JavaScript origins** (or your deployed frontend origin).
4. Copy the **Client ID** and set it in both places:

```bash
# Backend + frontend, both in the root .env (`envDir: '..'`)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

5. Restart the backend and rebuild/restart the frontend dev server.

**Important:** `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` must match exactly. The backend verifies the token
audience against `GOOGLE_CLIENT_ID`; a mismatch is returned as `401 AUTH_INVALID_GOOGLE_CREDENTIAL`. Startup
runs `verify_google_client_id_equality()`, but that function reads `VITE_GOOGLE_CLIENT_ID` directly from the
process environment. It catches differing process-level values when both are set; it does not read that frontend
value from Pydantic's `.env` source. Keep the root `.env` values aligned for local development and configure both
deployment/build environment values explicitly in hosted environments.

> `GOOGLE_CLIENT_SECRET` is **not** used anywhere in this codebase. Never add it to any configuration file.

### 5. Restricting sign-in and granting the admin role

1. Set `ALLOWED_EMAILS` to a comma-separated list of emails to restrict who may sign in at all; leave
   empty (the default) to allow any verified Google account.
2. Set `ADMIN_EMAILS` to a comma-separated list of emails that should receive the `admin` role, most
   importantly your own — the LLM settings endpoints (`GET`/`PUT /api/settings/llm`) require it.
3. Restart the backend. Role and allowlist membership are re-evaluated on **every** login, so removing an
   email from `ADMIN_EMAILS`/`ALLOWED_EMAILS` and restarting takes effect the next time that user signs in
   — no database migration needed.

### 6. Enabling the GraphRAG chat feature

1. Set `LLM_ENABLED=true` in `.env`, **or** enable it later via `PUT /api/settings/llm` (`enabled: true`)
   once signed in as an admin (see [above](#5-restricting-sign-in-and-granting-the-admin-role)) — the
   runtime setting takes precedence over the env value. Alternatively, send BYOK request headers (`X-LLM-Api-Key`, `X-LLM-Provider`, etc.) on chat requests to override both env and stored graph settings for that request.
2. Provide `LLM_API_KEY` and `LLM_MODEL` — either in `.env` or through the same `PUT /api/settings/llm`
   call. `LLM_PROVIDER` has a default; an explicit base URL is required for the OpenAI-compatible branch
   (`openai_compatible`, `vllm`, and `ollama`), while Gemini supplies its default URL.
3. For `LLM_PROVIDER=gemini` with an empty `LLM_BASE_URL`, the service automatically uses
   `https://generativelanguage.googleapis.com`.
4. Restart the backend if changes were made via `.env`; runtime-settings changes via the API or request headers take effect on the next chat call without a restart.

### 7. Enabling Redis-backed rate limiting and the graph query cache (optional)

1. Provision a Redis instance (Upstash's `rediss://` TLS URLs are the tested target) and set `REDIS_URL`
   in `.env` to its connection string.
2. Restart the backend. `init_rate_limiter()` binds the shared Redis client during `lifespan()` startup,
   enabling the login/chat-send/content-write rate limits and the `GET /api/series/{series_id}/graph`
   response cache described in [Rate Limiting & Redis Cache](#rate-limiting--redis-cache).
3. Leaving `REDIS_URL` empty (the default) is a valid and supported local-dev configuration — both
   features degrade to a no-op rather than failing startup or requests.
