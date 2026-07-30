# Configuration

> **HD Graf Cehennemi** — configuration reference for all runtime, build, and infrastructure settings.

---

## Table of Contents

- [Environment Variables](#environment-variables)
- [Docker Compose (Neo4j)](#docker-compose-neo4j)
- [Backend Configuration (Pydantic Settings)](#backend-configuration-pydantic-settings)
- [Frontend Configuration](#frontend-configuration)
- [Ontology Configuration](#ontology-configuration)
- [Common Workflows](#common-workflows)

---

## Environment Variables

The backend reads configuration from a `.env` file at the **project root** (next to `pyproject.toml`).  
Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

### Variable Reference

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | `neo4j://localhost:7687` | Bolt URI for the Neo4j database. Use `neo4j+s://` for TLS. |
| `NEO4J_USERNAME` | `neo4j` | Neo4j authentication username. |
| `NEO4J_PASSWORD` | `change-me` | Neo4j authentication password. |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name to connect to. |
| `GOOGLE_CLIENT_ID` | _(required)_ | Google OAuth 2.0 client ID for ID token verification. Must be set to enable sign-in. |
| `SESSION_COOKIE_NAME` | `session` | Name of the HttpOnly session cookie set on the browser. |
| `SESSION_TTL_SECONDS` | `604800` | Session time-to-live in seconds (default: 7 days). |
| `SESSION_COOKIE_SECURE` | `false` | Set the `Secure` flag on the session cookie. Enable in production (HTTPS). |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed CORS origins for the FastAPI backend. |

> **Note:** There is currently no `ENVIRONMENT` (development/production) variable in the codebase. If you need environment-specific branching, add an `ENVIRONMENT` variable to `.env` and read it in `config.py`.

> **Note:** `GOOGLE_CLIENT_SECRET` is **not** used by this project. The backend only needs `GOOGLE_CLIENT_ID` to verify Google ID tokens via the `google-auth` library's `verify_oauth2_token` function, which fetches public keys from Google's JWKS endpoint. No client secret is stored on the server.

> **Note:** `SECRET_KEY` is **not** currently used. Session tokens are opaque UUIDs stored server-side; they are not signed with a symmetric key. If JWT-based sessions are adopted in the future, a `SECRET_KEY` will be required.

<!-- VERIFY: The exact default value for SESSION_TTL_SECONDS (604800) comes from backend/app/core/config.py line 23. -->

---

## Docker Compose (Neo4j)

The `docker-compose.yml` at the project root runs a single Neo4j Community container for local development.

```yaml
services:
  neo4j:
    image: neo4j:2026-community       # <!-- VERIFY: Image tag -->
    container_name: hdgrafcehennemi-neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"                    # HTTP browser / REST API
      - "7687:7687"                    # Bolt protocol
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
| **Image** | `neo4j:2026-community` | <!-- VERIFY: This tag uses an unconventional versioning scheme. If it does not resolve, try `neo4j:5-community` (latest Neo4j 5 Community). --> |
| **Bolt port** | `7687` | Used by the Python driver (`NEO4J_URI=neo4j://localhost:7687`) |
| **HTTP port** | `7474` | Browser UI at `http://localhost:7474` |
| **Credentials** | `neo4j` / `hdgraf-local-password` | Must match `NEO4J_PASSWORD` in `.env` |
| **APOC** | — | The `./neo4j_plugins` volume is mounted but no APOC JAR is auto-installed. To enable APOC, download `apoc-*-core.jar` into `neo4j_plugins/` and add the environment variable `NEO4J_PLUGINS='["apoc"]'`. |

### Starting Neo4j

```bash
docker compose up -d
```

Verify with the health check or:

```bash
docker compose ps neo4j
# Or open http://localhost:7474 in a browser
```

---

## Backend Configuration (Pydantic Settings)

The `Settings` class in `backend/app/core/config.py` uses **pydantic-settings** to load environment variables from `.env` (or the process environment). Every Pydantic field reads from its uppercase equivalent.

### Settings class

```python
class Settings(BaseSettings):
    neo4j_uri: str                                    # NEO4J_URI
    neo4j_username: str                                # NEO4J_USERNAME
    neo4j_password: str                                # NEO4J_PASSWORD
    neo4j_database: str = "neo4j"                      # NEO4J_DATABASE
    google_client_id: str = ""                         # GOOGLE_CLIENT_ID
    session_cookie_name: str = "session"               # SESSION_COOKIE_NAME
    session_ttl_seconds: int = 604800                  # SESSION_TTL_SECONDS
    session_cookie_secure: bool = False                # SESSION_COOKIE_SECURE
    frontend_origins: str = "http://localhost:5173"    # FRONTEND_ORIGINS
```

### Behaviour

- **File precedence:** `.env` in the project root → process environment variables. Process env takes precedence (Pydantic default behaviour).
- **`extra="ignore"`:** Unknown variables in `.env` are silently ignored.
- **`@lru_cache`:** The `get_settings()` function caches the singleton — call it freely in routes and services.

### Database connection

The `Neo4jDatabase` class in `backend/app/graph/database.py`:

1. Creates an `AsyncGraphDatabase.driver(...)` with the URI and credentials from `Settings`.
2. Provides `execute_query()` and `execute_write()` methods scoped to the configured `neo4j_database`.
3. Connection is verified on startup via `verify_connection()` (degraded startup allowed if Neo4j is not yet ready).

### CORS

The FastAPI app (`backend/app/main.py`) parses `FRONTEND_ORIGINS` from settings and configures the CORS middleware:

```python
_allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origins.split(",")
    if origin.strip()
]
```

Supports multiple origins separated by commas.

### Health check

```http
GET /health
```

Returns `{"status": "ok", "database": "connected", "service": "hdgrafcehennemi-backend"}` when Neo4j is reachable, or HTTP 503 with `"database": "unavailable"` otherwise.

---

## Frontend Configuration

### Vite dev server (`frontend/vite.config.ts`)

The Vite dev server runs on `http://localhost:5173` (Vite default) and proxies `/api` requests to the FastAPI backend:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',    // FastAPI backend
      changeOrigin: true,
    },
  },
},
```

This means during development the frontend can call `fetch('/api/...')` without hardcoding the backend URL. In production, a reverse proxy (e.g., nginx) or a combined deployment should serve both static files and route `/api` traffic.

### Frontend environment variables

The frontend reads environment variables from `frontend/.env.local` (NOT loaded from the root `.env`). Create it from the template:

```bash
cp frontend/.env.example frontend/.env.local
```

| Variable | Required | Description |
|---|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID — must match the backend `GOOGLE_CLIENT_ID` |
| `VITE_API_BASE_URL` | No (default: `/api`) | API base path for fetch requests |

> **Security:** Vite inlines `VITE_*` variables at build time. Never store secrets in `.env.local`. The `GOOGLE_CLIENT_ID` is a public identifier (exposed to the browser by design) and is safe to include.

### TypeScript config

| File | Purpose |
|---|---|
| `tsconfig.json` | Root config — references `tsconfig.app.json` and `tsconfig.node.json`, defines `@/*` path alias. |
| `tsconfig.app.json` | App source config — `target: es2023`, `jsx: react-jsx`, strict linting. |
| `tsconfig.node.json` | Node-side config for `vite.config.ts` — `module: nodenext`. |

### Path alias

Both `tsconfig.json` and `vite.config.ts` register the `@` alias pointing to `./src`:

```typescript
// vite.config.ts
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
},
```

```json
// tsconfig.json
"compilerOptions": {
  "paths": {
    "@/*": ["./src/*"]
  }
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

---

## Ontology Configuration

The ontology is defined in three YAML files under `ontology/`, loaded at runtime by `backend/app/graph/ontology.py`.

### File structure

```
ontology/
├── node_types.yaml        # Node type declarations grouped by category
├── relation_types.yaml    # Relationship type declarations grouped by category
└── claim_types.yaml       # Claim types, statuses, and confidence levels
```

All three files must declare `ontology_version: "0.1"` or loading will fail with an `OntologyValidationError`.

### `node_types.yaml`

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

Groups are used for documentation and access control; the flat `node_types` set (all groups combined) is what the validator checks.

### `relation_types.yaml`

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

The `participation` and `character` groups are exposed as **user-safe** — frontend users may create relationships of these types via the API. All other groups require backend or admin access.

### `claim_types.yaml`

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

The `load_ontology()` function:

1. Reads all three YAML files from the `ontology/` directory.
2. Validates the `ontology_version` field matches the expected version (`"0.1"`).
3. Builds a frozen `Ontology` dataclass with `frozenset` constraints for efficient lookup.
4. Exposes `require_*()` methods that raise `OntologyValidationError` if a type is undeclared.

Seed data validation (in `backend/app/graph/setup.py`) calls `ontology.require_node_type()`, `ontology.require_relationship_type()`, `ontology.require_claim_type()`, `ontology.require_claim_status()`, and `ontology.require_confidence_level()` before any data is written to Neo4j.

---

## Common Workflows

### 1. First-time setup

```bash
# 1. Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local
# Edit .env — at minimum set NEO4J_PASSWORD to match docker-compose.yml
# Edit both .env and frontend/.env.local — set GOOGLE_CLIENT_ID matching values

# 2. Start Neo4j
docker compose up -d

# 3. Install Python deps and seed the database
uv sync
uv run hdgraf-setup

# 4. Start the backend
uv run uvicorn backend.app.main:app --reload

# 5. Start the frontend (separate terminal)
cd frontend && npm run dev
```

### 2. Switching databases

Change `NEO4J_URI` to point to a different Neo4j instance (e.g., a remote server or Neo4j Aura):

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

### 3. Adding a new ontology type

1. Edit the appropriate YAML file in `ontology/`.
2. Add any required indexes in `backend/app/graph/seed.py` (`create_constraints()`).
3. Add seed data if needed in `data/dexter/seed/` or `data/dexter/metadata/`.
4. Update the `NODE_LABELS` or `RELATIONSHIP_TYPES` tuples in `seed.py` if adding new labels/types.
5. Restart the backend (live ontology reload is not yet supported).

### 4. Setting up authentication (required)

This application requires Google OAuth to log in.

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials.
2. Create an **OAuth 2.0 Client ID** of type **Web application**.
3. Add `http://localhost:5173` to **Authorized JavaScript origins**.
4. Copy the **Client ID** and set it in both:

```bash
# Backend .env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# Frontend .env.local
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

5. Restart the backend. The frontend login page becomes active.

**Important:** The `GOOGLE_CLIENT_ID` values in `.env` and `frontend/.env.local` must match exactly. The backend verifies the token audience against its configured `GOOGLE_CLIENT_ID`; the frontend passes the same ID to the Google Identity Services library. A mismatch between the two will cause the backend to reject the token with a 401 error.

> `GOOGLE_CLIENT_SECRET` is **not** used. Never add it to any configuration file.
> Wait up to 5 minutes for Google Cloud configuration changes to propagate.
