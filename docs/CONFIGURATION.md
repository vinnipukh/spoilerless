<!-- generated-by: gsd-doc-writer -->
# Configuration

> **HD Graf Cehennemi** — configuration reference for all runtime, build, and infrastructure settings.

---

## Table of Contents

- [Environment Variables](#environment-variables)
- [Backend Configuration (Pydantic Settings)](#backend-configuration-pydantic-settings)
- [Per-Environment Overrides](#per-environment-overrides)
- [Runtime LLM Settings Override (stored in Neo4j)](#runtime-llm-settings-override-stored-in-neo4j)
- [Session Storage](#session-storage)
- [Docker Compose (Neo4j)](#docker-compose-neo4j)
- [Frontend Configuration](#frontend-configuration)
- [Ontology Configuration](#ontology-configuration)
- [Common Workflows](#common-workflows)

---

## Environment Variables

The backend reads configuration from the current working directory's `.env` file, as configured by
`backend/app/core/config.py`. When starting it from the project root, copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

> **Verified against the repo:** `.env.example` (project root) was read directly and matches the table
> below. The live `.env` currently sets only `GOOGLE_CLIENT_ID` — every other variable falls back to its
> default. `LLM_FALLBACK_EN` and `LLM_FALLBACK_TR` exist in the `Settings` class but are **not** listed in
> `.env.example` (they are optional overrides). Secret values are never documented here.

### Variable Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `NEO4J_URI` | _(none — must be set)_ | Yes | Bolt URI for the Neo4j database. Use `neo4j+s://` for TLS connections (e.g. Neo4j Aura). |
| `NEO4J_USERNAME` | _(none — must be set)_ | Yes | Neo4j authentication username. |
| `NEO4J_PASSWORD` | _(none — must be set)_ | Yes | Neo4j authentication password. Must match `NEO4J_AUTH` in `docker-compose.yml` for local development. |
| `NEO4J_DATABASE` | `neo4j` | No | Neo4j database name to connect to. |
| `GOOGLE_CLIENT_ID` | `""` (empty) | No — but sign-in fails without it | Google OAuth 2.0 Web Client ID used to verify Google ID tokens. When unset, `POST /api/auth/google` returns `401 AUTH_DISABLED`. |
| `SESSION_COOKIE_NAME` | `session` | No | Name of the HttpOnly session cookie. |
| `SESSION_TTL_SECONDS` | `604800` (7 days) | No — but sign-in fails if `<= 0` | Session time-to-live in seconds. `POST /api/auth/google` returns `401 AUTH_DISABLED` if this is explicitly set to a non-positive value; when unset, the default applies. |
| `SESSION_COOKIE_SECURE` | `false` | No | Sets the `Secure` flag on the session cookie. Should be `true` in any HTTPS deployment. |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | No | Comma-separated list of allowed CORS origins for the FastAPI backend. Also used by `verify_origin` in `backend/app/api/auth.py` for CSRF `Origin`/`Referer` validation on `POST /api/auth/google`; `POST /api/auth/logout` does not apply that dependency. |
| `LLM_ENABLED` | `false` | No | Master switch for the GraphRAG chat/retrieval endpoints. When `false`, chat calls raise `LLMProviderDisabled`, mapped to HTTP 503 with code `LLM_DISABLED`. |
| `LLM_PROVIDER` | `openai_compatible` | No | Provider implementation selector. Two implementations exist: `openai_compatible` and `gemini` (see [Runtime LLM Settings Override](#runtime-llm-settings-override-stored-in-neo4j) — the stored/runtime default is `gemini`, this env default is `openai_compatible`). |
| `LLM_BASE_URL` | `""` (empty) | Effectively required for `openai_compatible` if `LLM_ENABLED=true` and no runtime override is stored; optional for Gemini | Base URL for the OpenAI-compatible `/chat/completions` endpoint, or the Gemini API base when `LLM_PROVIDER=gemini` (defaults to `https://generativelanguage.googleapis.com` if left empty for Gemini). |
| `LLM_API_KEY` | `""` (empty) | Effectively required if `LLM_ENABLED=true` and no runtime override is stored | LLM provider API key. The full key is accessed by settings masking, chat provider resolution, and provider implementations; API responses expose only the masked key, and the full key is never logged or returned to the frontend. |
| `LLM_MODEL` | `""` (empty) | Effectively required if `LLM_ENABLED=true` and no runtime override is stored | Model identifier passed to the provider (e.g. `gpt-4.1-mini`, `gemini-2.0-flash`). |
| `LLM_TIMEOUT_SECONDS` | `60` | No | Per-request timeout for LLM provider calls, in seconds. |
| `LLM_MAX_OUTPUT_TOKENS` | `800` | No | Maximum tokens the model may generate per completion call. |
| `LLM_TEMPERATURE` | `0.0` | No | Sampling temperature for LLM completions (`0` = deterministic). |
| `LLM_MAX_TOOL_ROUNDS` | `4` | No | Maximum bounded tool-calling rounds per chat turn. |
| `LLM_MAX_CONTEXT_ITEMS` | `40` | No | Maximum number of retrieved context items assembled per turn. |
| `LLM_MAX_CONTEXT_CHARACTERS` | `12000` | No | Maximum total character budget for the assembled context per turn. |
| `LLM_FALLBACK_EN` | `None` (unset) | No | Optional override for the localized "insufficient evidence" fallback response in English (not listed in `.env.example`). Falls back to `INSUFFICIENT_EVIDENCE_FALLBACK_EN` in `backend/app/llm/fallbacks.py` when unset or blank. |
| `LLM_FALLBACK_TR` | `None` (unset) | No | Optional override for the localized "insufficient evidence" fallback response in Turkish (not listed in `.env.example`). Falls back to `INSUFFICIENT_EVIDENCE_FALLBACK_TR` in `backend/app/llm/fallbacks.py` when unset or blank. |

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

The `Settings` class in `backend/app/core/config.py` uses **pydantic-settings** (`BaseSettings`) to load
configuration from `.env` (or the process environment). Every field reads from its uppercase environment
variable name (e.g. `neo4j_uri` ← `NEO4J_URI`).

```python
class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str = "neo4j"

    google_client_id: str = ""
    session_cookie_name: str = "session"
    session_ttl_seconds: int = 604800
    session_cookie_secure: bool = False
    frontend_origins: str = "http://localhost:5173"

    llm_enabled: bool = False
    llm_provider: str = "openai_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 60
    llm_max_output_tokens: int = 800
    llm_temperature: float = 0.0
    llm_max_tool_rounds: int = 4
    llm_max_context_items: int = 40
    llm_max_context_characters: int = 12000
    llm_fallback_en: str | None = None
    llm_fallback_tr: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

### Behaviour

- **File precedence:** `.env` relative to the process's current working directory, then process environment variables (process env takes
  precedence — pydantic-settings default behavior).
- **`extra="ignore"`:** Unknown variables present in `.env` are silently ignored rather than raising an error.
- **`@lru_cache`:** `get_settings()` caches a single `Settings` instance for the process lifetime — call it
  freely from routes and services without re-parsing `.env` on every call.
- **No startup validation beyond Pydantic's type coercion:** `neo4j_uri`, `neo4j_username`, and
  `neo4j_password` have no default, so `Settings()` raises a `pydantic.ValidationError` at import time if
  they are missing. All other fields have defaults and will not block startup.

### Database connection

`Neo4jDatabase` (`backend/app/graph/database.py`):

1. Creates an `AsyncGraphDatabase.driver(...)` using `neo4j_uri` and `(neo4j_username, neo4j_password)`.
2. Exposes `execute_query()` and `execute_write()`, both scoped to the configured `neo4j_database`.
3. Connection is verified once at FastAPI startup via `verify_connection()`; failures are swallowed
   (degraded startup) so `/health` can report live connectivity rather than crash the process.

### CORS

`backend/app/main.py` parses `FRONTEND_ORIGINS` and configures `CORSMiddleware`:

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

The same `FRONTEND_ORIGINS` value also drives `verify_origin()` in `backend/app/api/auth.py`, a FastAPI
dependency applied to `POST /api/auth/google` but not `POST /api/auth/logout`. It compares the request's `Origin` (or, if absent,
`Referer`) header against the configured origin list and rejects mismatches with `403 AUTH_ORIGIN_NOT_ALLOWED`.
Setting `FRONTEND_ORIGINS=*` disables this check entirely (not recommended).

### Health check

```http
GET /health
```

Returns `{"status": "ok", "database": "connected", "service": "hdgrafcehennemi-backend"}` (HTTP 200) when
Neo4j is reachable, or `{"status": "degraded", "database": "unavailable", ...}` with HTTP 503 otherwise.

---

## Per-Environment Overrides

There are no `.env.development` / `.env.production` / `.env.test` files and no `NODE_ENV`-style
conditional loading. The backend has a single `.env` file and no `ENVIRONMENT` setting, so per-environment
configuration is done by maintaining a separate `.env` per deployment:

- **Local development** — `cp .env.example .env`; set `NEO4J_PASSWORD` to the password portion of `NEO4J_AUTH`
  (`hdgraf-local-password`); keep `NEO4J_URI=neo4j://localhost:7687` and
  `FRONTEND_ORIGINS=http://localhost:5173`.
- **Production / Neo4j Aura** — set `NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io:7687`, real
  credentials, `SESSION_COOKIE_SECURE=true`, and the deployed frontend origin(s) in `FRONTEND_ORIGINS`.
  <!-- VERIFY: The exact production Neo4j Aura instance URI and cloud region are deployment-specific and
  not discoverable from the repository. -->
- **Frontend** — Vite convention supports `frontend/.env`, `frontend/.env.local` (local
  overrides, gitignored), plus optional `frontend/.env.production` / `frontend/.env.staging`; `frontend/.env` is absent. Only
  `frontend/.env.example` and `frontend/.env.local` currently exist in the repo. `VITE_*` variables are
  inlined into the bundle at build time, so production values must be present when `npm run build` runs —
  they cannot be injected at runtime.

---

## Runtime LLM Settings Override (stored in Neo4j)

In addition to the `LLM_*` environment variables above, the effective LLM provider configuration can be
set at runtime through the API and is persisted in the graph — it is **not** purely `.env`-driven.

- **Storage:** `SettingsRepository` (`backend/app/repository/settings.py`) persists a single
  `:AppSetting {key: 'llm'}` node in Neo4j via `MERGE`, storing the payload as a JSON string property.
- **Endpoints (auth required):**
  - `GET /api/settings/llm` — returns stored values with environment fallbacks, but not provider-construction defaults (for example, Gemini's default base URL is still returned as `null` when no URL is configured); the API key is masked
    (`mask_api_key()` returns `"••••" + last 4 chars` for keys longer than four characters, one bullet per character for shorter keys, or `None` if unset).
  - `PUT /api/settings/llm` — updates the configuration (`backend/app/api/settings.py`,
    `SettingsService.update_llm`).
- **Precedence:** For `provider`, `api_key`, `base_url`, and `model`, the stored graph value wins if
  present; otherwise the corresponding `LLM_*` setting from `Settings` is used as the fallback
  (`SettingsService.get_llm` in `backend/app/services/settings.py`). `enabled` follows the same rule,
  falling back to `settings.llm_enabled`.
- **Supported providers:** `backend/app/domain/settings.py` declares
  `LLM_PROVIDERS = ("gemini", "openai_compatible")`. The `PUT` request body (`LLMSettingsUpdate`) defaults
  `provider` to `"gemini"` when not supplied — note this differs from the `LLM_PROVIDER` env default of
  `"openai_compatible"` described above.
- **Gemini default base URL:** When `provider` is `gemini` and no `base_url` is stored or set via
  `LLM_BASE_URL`, the service falls back to `DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"`.
- **URL scheme validation:** `LLMSettingsUpdate.base_url` is validated to require an `http`/`https`
  scheme and a hostname (`_validate_base_url` in `backend/app/domain/settings.py`) — an SSRF-via-scheme
  guard. It deliberately does **not** block private/loopback addresses, since local vLLM/Ollama endpoints
  (`http://127.0.0.1:...`) are a supported deployment target.
- **System prompt:** The assistant prompt is user-owned in `backend/app/llm/system_prompt.py`, versioned
  via `SYSTEM_PROMPT_VERSION = "v1"`, with two localized variants: `SYSTEM_PROMPT_ENG` (English) and
  `SYSTEM_PROMPT_TR` (Turkish).
- **Assistant language:** `system_prompt_language` (`"english"` or `"turkish"`, default `"english"`) is
  also stored/updated through this endpoint. It controls both which system prompt variant is sent to the
  LLM (`backend/app/services/chat.py` reads the stored value per turn) and which localized fallback text
  is used for a turn — see `_fallback_for()` in `backend/app/retrieval/pipeline.py`, which selects `"tr"`
  when `system_prompt_language == "turkish"` and otherwise `"en"` (this is a direct selection, not
  automatic detection of the user's message language — `detect_language()` in `backend/app/llm/fallbacks.py`
  exists but is not used by `_fallback_for`).
- **Secret write semantics:** `PUT /api/settings/llm` accepts `api_key: str | None`; sending `None` or an
  empty string preserves the previously stored key rather than clearing it, since `GET` never returns the
  full key for a client to round-trip.

<!-- VERIFY: Whether `PUT /api/settings/llm` has any authorization/role check beyond "any authenticated
session" — the route only depends on `CurrentUserDependency`, so any signed-in user can view (masked) and
change the shared LLM provider configuration. Confirm this is the intended access model before exposing
this endpoint outside a trusted/single-tenant deployment. -->

---

## Session Storage

Two `SessionRepository` implementations exist in `backend/app/repository/session.py`:

| Implementation | Storage | Used when |
|---|---|---|
| `InMemorySessionRepository` | In-process Python dict | `AuthService`'s constructor default when no `session_repo` is explicitly passed (used directly by some tests). |
| `Neo4jSessionRepository` | `(:Session)` nodes in Neo4j, linked via `(:AppUser)-[:HAS_SESSION]->(:Session)` | The actual FastAPI app — `backend/app/main.py`'s `lifespan()` sets `app.state.session_repo = Neo4jSessionRepository(database)` at startup, and `get_auth_service()` (`backend/app/api/deps.py`) always injects it. |

Only the raw session token's SHA-256 hash is ever persisted (`token_hash`); the raw token returned to the
browser as the cookie value is never stored. Session lookups reject expired (`expires_at <= now`) or
revoked (`revoked_at IS NOT NULL`) sessions. There is currently no automated cleanup job for
expired/revoked `Session` nodes — the module docstring documents the intended periodic cleanup Cypher
query, but it is not scheduled anywhere in this codebase.

---

## Docker Compose (Neo4j)

The `docker-compose.yml` at the project root runs a single Neo4j Community container for local development.

```yaml
services:
  neo4j:
    image: neo4j:2026-community
    container_name: hdgrafcehennemi-neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/hdgraf-local-password
    volumes:
      - ./neo4j_data:/data
      - ./neo4j_logs:/logs
      - ./neo4j_import:/import
      - ./neo4j_plugins:/plugins
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
```

### Key details

| Property | Value | Notes |
|---|---|---|
| **Image** | `neo4j:2026-community` | <!-- VERIFY: This tag uses an unconventional (year-based) versioning scheme; confirm it resolves in your Docker registry. --> |
| **Bolt port** | `7687` | Used by the Python driver — set `NEO4J_URI=neo4j://localhost:7687` to match. |
| **HTTP port** | `7474` | Neo4j Browser UI at `http://localhost:7474`. |
| **Credentials** | `neo4j` / `hdgraf-local-password` | Must match `NEO4J_PASSWORD` in `.env`. This is a hardcoded development-only secret. |
| **APOC** | — | The `./neo4j_plugins` volume is mounted but no plugin JAR is auto-installed. To enable APOC, place `apoc-*-core.jar` in `neo4j_plugins/` and add `NEO4J_PLUGINS='["apoc"]'` to the `environment` block. |

### Starting Neo4j

```bash
docker compose up -d
docker compose ps neo4j
# Or open http://localhost:7474 in a browser
```

---

## Frontend Configuration

### Vite dev server (`frontend/vite.config.ts`)

```typescript
export default defineConfig({
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
at `http://127.0.0.1:8000`. During development, the frontend calls `fetch('/api/...')` with relative paths
(see `frontend/src/api/client.ts`) rather than an absolute base URL. In production, a reverse proxy or a
combined deployment must route `/api` traffic to the backend since Vite's dev proxy does not exist outside
`vite dev`.

### Frontend environment variables

`frontend/.env.example` (verified) declares two variables, and `frontend/.env.local` exists for local
overrides (gitignored):

| Variable | Required | Description |
|---|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Yes, for sign-in | Google OAuth client ID, read via `import.meta.env.VITE_GOOGLE_CLIENT_ID` in `frontend/src/components/auth/LoginPage.tsx`. Must match the backend's `GOOGLE_CLIENT_ID`. When unset, the login page renders a "Google Sign-In is not configured" message instead of the sign-in button. |
| `VITE_API_BASE_URL` | No | Declared in `frontend/.env.example` and `frontend/.env.local` with the value `/api`, but **not yet read by any source file** — `import.meta.env` is only consumed for `VITE_GOOGLE_CLIENT_ID`, and each API module (`frontend/src/api/series.ts`, `frontend/src/api/auth.ts`, etc.) still hardcodes the `/api` prefix. Reserved for future base-URL configuration. |

> **Security:** Vite inlines `VITE_*` variables into the built JavaScript bundle at build time — never
> store secrets in `frontend/.env.local`. `VITE_GOOGLE_CLIENT_ID` is a public OAuth client identifier
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
`backend/app/graph/ontology.py::load_ontology()`.

### File structure

```
ontology/
├── node_types.yaml        # Node type declarations grouped by category
├── relation_types.yaml    # Relationship type declarations grouped by category
└── claim_types.yaml       # Claim types, statuses, and confidence levels
```

All three files must declare `ontology_version: "0.1"` (matching `ONTOLOGY_VERSION` in `backend/app/graph/ontology.py`) or
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

`load_ontology()`:

1. Reads all three YAML files from the `ontology/` directory.
2. Validates each file's `ontology_version` matches `"0.1"`.
3. Builds a frozen `Ontology` dataclass with `frozenset` members for O(1) membership checks.
4. Exposes `require_node_type()`, `require_relationship_type()`, `require_claim_type()`,
   `require_claim_status()`, and `require_confidence_level()`, each raising `OntologyValidationError` for
   an undeclared value.

Seed data validation (`backend/app/graph/setup.py`) calls these `require_*()` methods before any data is
written to Neo4j.

---

## Common Workflows

### 1. First-time setup

```bash
# 1. Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local
# Edit .env — set NEO4J_PASSWORD to match docker-compose.yml, and GOOGLE_CLIENT_ID
# Edit frontend/.env.local — set VITE_GOOGLE_CLIENT_ID to the same Google client ID

# 2. Start Neo4j
docker compose up -d

# 3. Install Python deps and seed the database
uv sync
uv run hdgraf-setup

# 4. Start the backend
uv run uvicorn backend.app.main:app --reload

# 5. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### 2. Switching databases

Change `NEO4J_URI` (and credentials) to point at a different Neo4j instance, e.g. Neo4j Aura:

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

### 3. Adding a new ontology type

1. Edit the appropriate YAML file in `ontology/`.
2. Add any required indexes in `backend/app/graph/seed.py` (`create_constraints()`).
3. Add seed data if needed under `data/dexter/seed/` or `data/dexter/metadata/`.
4. If the new label/type is used by seed data, update the relevant `NODE_LABELS` or `RELATIONSHIP_TYPES` tuple in `backend/app/graph/seed.py`; these tuples cover seeded types, not every ontology declaration.
5. Restart the backend so modules that loaded an ontology at import time see the change. `load_ontology()` itself is uncached and independently called by several modules.

### 4. Setting up authentication (required to sign in)

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials.
2. Create an **OAuth 2.0 Client ID** of type **Web application**.
3. Add `http://localhost:5173` to **Authorized JavaScript origins** (or your deployed frontend origin).
4. Copy the **Client ID** and set it in both places:

```bash
# Backend .env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# Frontend .env.local
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

5. Restart the backend and rebuild/restart the frontend dev server.

**Important:** The `GOOGLE_CLIENT_ID` values in `.env` and `frontend/.env.local` must match exactly. The
backend verifies the token audience against its configured `GOOGLE_CLIENT_ID`; a mismatch causes
`google_auth()` to raise `GoogleVerificationError("audience_mismatch")`, returned to the client as
`401 AUTH_INVALID_GOOGLE_CREDENTIAL`.

> `GOOGLE_CLIENT_SECRET` is **not** used anywhere in this codebase. Never add it to any configuration file.

### 5. Enabling the GraphRAG chat feature

1. Set `LLM_ENABLED=true` in `.env`, **or** enable it later via `PUT /api/settings/llm` (`enabled: true`)
   once signed in — the runtime setting takes precedence over the env value.
2. Provide `LLM_API_KEY` and `LLM_MODEL` — either in `.env` or through the same `PUT /api/settings/llm`
   call. `LLM_PROVIDER` has a default; an explicit base URL is required only for `openai_compatible` because Gemini supplies its default URL.
3. For `LLM_PROVIDER=gemini` with an empty `LLM_BASE_URL`, the service automatically uses
   `https://generativelanguage.googleapis.com`.
4. Restart the backend if changes were made via `.env`; runtime-settings changes via the API take effect
   on the next chat call without a restart.
