# Deployment Guide

> **HD Graf Cehennemi** — local development deployment reference.
>
> **Status:** Prototype phase. This project is not deployed to any production environment. This guide covers local development setup only.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Environment Configuration](#environment-configuration)
4. [Docker Compose Services](#docker-compose-services)
5. [Production Considerations](#production-considerations)

---

## Prerequisites

### Docker Desktop (for Neo4j)

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) or Docker Engine + Docker Compose plugin (Linux).
- Required to run the Neo4j Community database container.
- Minimum 4 GB of memory allocated to the Docker VM (default is usually sufficient for development).

### Python 3.13+ with uv

- Python 3.13 or later is required (see `requires-python = ">=3.13"` in `pyproject.toml`).
- [uv](https://docs.astral.sh/uv/) — the Python package manager used for dependency resolution and virtual environment management.
- Install uv via the standalone installer:

  ```bash
  # Windows (PowerShell)
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Node.js 20+ with npm

- Node.js 20 or later (includes `npm`).
- Required to install frontend dependencies and run the Vite dev server.
- Verify with `node --version` and `npm --version`.

---

## Local Deployment

### 1. Clone and configure

```bash
git clone <repository-url>
cd hdgrafcehennemi
cp .env.example .env
```

Edit `.env` to set values that match your local environment. At minimum, ensure **`NEO4J_PASSWORD`** matches the password in `docker-compose.yml` (default: `hdgraf-local-password`).

### 2. Start Neo4j via Docker Compose

```bash
docker compose up -d
```

This starts the Neo4j container in the background. The first pull may take a minute.

Verify the container is healthy:

```bash
docker compose ps neo4j
```

Expected output — `State: Up` and `Status: healthy` (may take ~10–30 seconds for the health check to pass).

Neo4j Browser is available at [http://localhost:7474](http://localhost:7474) (credentials: `neo4j` / `hdgraf-local-password`).

**Ports exposed:**

| Port | Protocol | Purpose |
|------|----------|---------|
| `7474` | HTTP | Neo4j Browser UI / REST API |
| `7687` | Bolt | Python driver connection (`NEO4J_URI`) |

### 3. Install Python dependencies

```bash
uv sync
```

This creates a virtual environment (`.venv`) at the project root and installs all dependencies defined in `pyproject.toml`, including dev dependencies (`pytest`, `httpx`).

### 4. Seed the database

```bash
uv run hdgraf-setup
```

The `hdgraf-setup` command (defined as `backend.app.graph.setup:main` in `pyproject.toml`):

1. **Validates** the ontology YAML files (`ontology/node_types.yaml`, `ontology/relation_types.yaml`, `ontology/claim_types.yaml`).
2. **Creates** Neo4j constraints and indexes (uniqueness constraints on node IDs, range indexes on `visible_from_order`, etc.).
3. **Seeds** the Dexter S01E01–03 data: series, episodes, characters, locations, events, claims, sources, and evidence fragments.
4. **Runs** a visibility integrity audit.

This step is idempotent — running it multiple times is safe (uses `MERGE`).

<!-- VERIFY: Confirm that `uv run hdgraf-setup` correctly executes the setup entrypoint and that all seed data files under `data/dexter/` are present and valid. -->

### 5. Start the backend

```bash
uv run uvicorn backend.app.main:app --reload
```

The FastAPI server starts on [http://localhost:8000](http://localhost:8000).

| Feature | URL |
|---------|-----|
| API root | [http://localhost:8000/](http://localhost:8000/) |
| Swagger UI (OpenAPI docs) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| ReDoc | [http://localhost:8000/redoc](http://localhost:8000/redoc) |
| Health check | [http://localhost:8000/health](http://localhost:8000/health) |

The `--reload` flag enables auto-restart on source changes (useful during development). Omit it for a production-like local run.

If Neo4j is not yet ready when the backend starts, the application still boots (degraded startup) and returns `503` from `/health` with `"database": "unavailable"`.

### 6. Start the frontend

Open a **separate terminal**:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts on [http://localhost:5173](http://localhost:5173).

**Vite proxy:** The dev server automatically proxies `/api/*` requests to the backend at `http://127.0.0.1:8000`, so the frontend can use relative URLs like `fetch('/api/series')` without CORS issues during development.

### 7. Verify everything is running

1. Open [http://localhost:5173](http://localhost:5173) — the frontend loads.
2. The frontend should fetch series data from the backend, and you can select Dexter S01.
3. Open [http://localhost:8000/health](http://localhost:8000/health) — returns `{"status": "ok", "database": "connected", "service": "hdgrafcehennemi-backend"}`.
4. Open [http://localhost:7474](http://localhost:7474) — Neo4j Browser shows the graph.

### Quick start (all at once)

```bash
# Terminal 1
docker compose up -d
uv sync
uv run hdgraf-setup
uv run uvicorn backend.app.main:app --reload

# Terminal 2
cd frontend && npm install && npm run dev
```

---

## Environment Configuration

The backend reads configuration from a `.env` file at the project root (next to `pyproject.toml`). Copy the template and edit:

```bash
cp .env.example .env
```

### Variable reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEO4J_URI` | `neo4j://localhost:7687` | Yes | Bolt URI for the Neo4j database. Use `neo4j+s://` for TLS connections. |
| `NEO4J_USERNAME` | `neo4j` | Yes | Neo4j authentication username. |
| `NEO4J_PASSWORD` | `change-me` | Yes | Neo4j authentication password. Must match the password in `docker-compose.yml` (`hdgraf-local-password`). |
| `NEO4J_DATABASE` | `neo4j` | No | Neo4j database name. |
| `GOOGLE_CLIENT_ID` | _(empty)_ | No | Google OAuth 2.0 Web Client ID for ID token verification. Leave empty to disable Google Sign-In. |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | No | Comma-separated list of allowed CORS origins for the FastAPI backend. |
| `SESSION_COOKIE_NAME` | `session` | No | Name of the HttpOnly session cookie set on the browser. |
| `SESSION_TTL_SECONDS` | `604800` | No | Session time-to-live in seconds (default: 7 days). |
| `SESSION_COOKIE_SECURE` | `false` | No | Set the `Secure` flag on the session cookie. **Must be `true` in production** (HTTPS). |

### Notes

- There is currently no `ENVIRONMENT` or `SECRET_KEY` variable in the codebase (see [CONFIGURATION.md](./CONFIGURATION.md) for details).
- `GOOGLE_CLIENT_SECRET` is **not** used — the backend verifies Google ID tokens via the `google-auth` library, which fetches public keys from Google's JWKS endpoint.
- Process environment variables take precedence over `.env` values.

---

## Docker Compose Services

### Neo4j service

The project's `docker-compose.yml` runs a single Neo4j Community container. There are **no backend or frontend containers** — those run natively during development.

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

#### Volumes

| Volume mount | Container path | Purpose |
|-------------|---------------|---------|
| `./neo4j_data` | `/data` | Persists graph database files across restarts |
| `./neo4j_logs` | `/logs` | Neo4j debug and operation logs |
| `./neo4j_import` | `/import` | Mount for bulk CSV/JSON import files |
| `./neo4j_plugins` | `/plugins` | Mount for Neo4j plugins (e.g., APOC) |

> **Note:** The `./neo4j_plugins` volume is mounted but no plugins are auto-installed. To enable APOC, download `apoc-*-core.jar` into `neo4j_plugins/` and set the environment variable `NEO4J_PLUGINS='["apoc"]'` in the Compose file.

#### Commands

```bash
# Start
docker compose up -d

# Stop (preserves data in volumes)
docker compose stop

# Stop and remove container (data persists in volumes)
docker compose down

# Stop and delete everything (including volumes — data loss!)
docker compose down -v
```

<!-- VERIFY: The `neo4j:2026-community` image tag uses an unconventional versioning scheme. If it does not resolve, try `neo4j:5-community` (latest Neo4j 5 Community). -->

---

## Production Considerations

> **This project is currently in prototype phase.** Production deployment has not been implemented, tested, or scoped. The notes below document areas that would need attention before any production use.

<!-- VERIFY: The entire "Production Considerations" section is speculative. All assertions below must be re-evaluated against the actual deployment target. -->

### Containerization

- The backend (FastAPI + Uvicorn) and frontend (Vite-built static files) currently run as **native processes**, not containers.
- A production deployment would require:
  - A **Dockerfile** for the backend (Python 3.13 slim image, `uv` install, `uvicorn` as the entrypoint).
  - A **multi-stage Dockerfile** or build step for the frontend (`npm run build` → serve via nginx or similar).
  - A **container registry** (Docker Hub, GitHub Container Registry, AWS ECR) to push built images.
- The `docker-compose.yml` would expand to include `backend` and `frontend` services alongside `neo4j`.

<!-- VERIFY: Container registry, CI/CD pipeline, and image build tooling have not been set up. -->

### CI/CD

- No CI/CD pipeline exists.
- A production pipeline would require:
  - Automated test runs (`uv run pytest` in the backend, `npm run test` in the frontend).
  - Lint and type-check gates (`tsc -b` for frontend).
  - Container build and push steps.
  - Deployment to a target environment (staging → production).

<!-- VERIFY: No CI/CD configuration files (GitHub Actions, GitLab CI, Jenkins) are present in the repository. -->

### Reverse proxy / SSL termination

- During development, `SESSION_COOKIE_SECURE=false` and there is no TLS.
- In production:
  - Place a reverse proxy (nginx, Caddy, Traefik, or a cloud load balancer) in front of the backend.
  - Terminate TLS at the proxy.
  - Set `SESSION_COOKIE_SECURE=true`.
  - Set `FRONTEND_ORIGINS` to the production frontend domain.

### Database

- The Neo4j container uses **local bind-mount volumes** (`./neo4j_data`). These are tied to the host filesystem and are not suitable for production.
- A production deployment would use:
  - **Named Docker volumes** or cloud-managed block storage.
  - **Regular backups** of the Neo4j data volume.
  - Optionally, a managed Neo4j service (Neo4j Aura) or a dedicated Neo4j cluster.
- The current password (`hdgraf-local-password` in `docker-compose.yml`) is a hardcoded development secret and **must** be changed in production.

### Session management

- Sessions are stored in-memory (`InMemorySessionRepository`). This is **ephemeral**: all sessions are lost on backend restart.
- A production deployment would replace this with:
  - **Redis** or another external session store.
  - Optionally, JWT-based sessions (which would introduce the need for a `SECRET_KEY`).

### Health monitoring

- A basic `/health` endpoint exists. In production, extend it to include:
  - Database connection pool health.
  - Dependency health (e.g., session store, external APIs).
  - Uptime and version information.
  - Integration with container orchestrator liveness/readiness probes.

### Resource requirements

- **Neo4j Community** is single-instance only (no clustering). For high-availability production, Neo4j Enterprise or Neo4j Aura would be required.
- Estimated minimum resources for a small production deployment:
  - Backend: 1 vCPU, 512 MB RAM (single instance).
  - Frontend: Static file serving — negligible resources.
  - Neo4j: 2 vCPU, 2 GB RAM (for small graph sizes).
- These are estimates only and have **not** been load-tested.

### Security checklist (pre-production)

- [ ] Change all default credentials (`NEO4J_AUTH`, `SECRET_KEY` if added).
- [ ] Enable `SESSION_COOKIE_SECURE=true` with valid TLS certificates.
- [ ] Restrict `FRONTEND_ORIGINS` to the actual production domain(s).
- [ ] Move session storage out of memory (Redis, database).
- [ ] Add rate limiting to authentication endpoints.
- [ ] Audit CORS configuration.
- [ ] Scan dependencies for vulnerabilities (`uv audit`, `npm audit`).
- [ ] Review Neo4j network exposure (Bolt should not be publicly accessible).

---

## Troubleshooting

### Neo4j container fails to start

```bash
# Check container logs
docker compose logs neo4j

# Most common cause: port conflict (7474 or 7687 already in use)
# Check with:
netstat -ano | findstr :7474
netstat -ano | findstr :7687
```

### Backend fails to connect to Neo4j

```
# Error: Couldn't connect to database
```

1. Ensure Docker Desktop is running and the Neo4j container is healthy (`docker compose ps neo4j`).
2. Verify `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` in `.env` match the values in `docker-compose.yml`.
3. Wait a few seconds after starting the container — Neo4j takes ~10-30 seconds to become ready.
4. Try connecting directly: `curl http://localhost:7474`.

### Frontend shows blank page or API errors

1. Open browser DevTools → Network tab.
2. Check that API requests to `/api/...` return 200 (not 502/503).
3. Ensure the backend is running on `localhost:8000`.
4. Verify the Vite proxy configuration in `frontend/vite.config.ts` points to the correct backend target.
5. Clear sessionStorage (the app caches watch progress there — stale data can cause glitches).

---

## LLM / GraphRAG Configuration (Deployment Notes)

The "Environment Configuration" variable reference table above predates the GraphRAG chat/retrieval
feature and does not list the `LLM_*` settings. These are deployment-relevant because they control
whether the chat/retrieval endpoints are active at all, and because part of the effective
configuration is **not** purely `.env`-driven. See [CONFIGURATION.md](./CONFIGURATION.md#environment-variables)
for the full variable reference; the notes below are deployment-specific additions.

### Additional environment variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LLM_ENABLED` | `false` | No | Master switch for the GraphRAG chat/retrieval endpoints. Must be `true` to activate them in any environment. |
| `LLM_PROVIDER` | `openai_compatible` | No | Provider selector. `openai_compatible` and `gemini` are both supported (see runtime override note below). |
| `LLM_BASE_URL` | _(empty)_ | Yes, if `LLM_ENABLED=true` and no runtime override is stored | Base URL of the chat completions endpoint. |
| `LLM_API_KEY` | _(empty)_ | Yes, if `LLM_ENABLED=true` and no runtime override is stored | Provider API key. Treat as a deployment secret — never commit, never log. |
| `LLM_MODEL` | _(empty)_ | Yes, if `LLM_ENABLED=true` and no runtime override is stored | Model identifier passed to the provider. |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_TEMPERATURE`, `LLM_MAX_TOOL_ROUNDS`, `LLM_MAX_CONTEXT_ITEMS`, `LLM_MAX_CONTEXT_CHARACTERS` | See CONFIGURATION.md | No | Tuning parameters for LLM provider calls; defaults are generally suitable for a first deployment. |
| `LLM_FALLBACK_EN`, `LLM_FALLBACK_TR` | _(empty/unset)_ | No | Optional overrides for the localized "insufficient evidence" fallback response text. If unset, built-in defaults in `backend/app/llm/fallbacks.py` are used. |

### Runtime override stored in Neo4j (deployment implication)

The effective LLM provider configuration (`provider`, `api_key`, `base_url`, `model`, `enabled`) can be
set at runtime via `PUT /api/settings/llm` and is persisted as an `:AppSetting {key: 'llm'}` node in
Neo4j (`SettingsRepository`), taking precedence over the corresponding `LLM_*` environment variable
whenever a stored value is present.

This has deployment implications beyond what a `.env`-only configuration model would suggest:

- **Secrets may live in the database, not just `.env`.** Anyone who can restore a Neo4j backup or
  query the graph directly could potentially retrieve the stored API key. Restrict Neo4j network
  access and backup storage accordingly (see the Security checklist above).
- **Rotating the API key requires updating both places** if the key was ever set via the API: the
  stored graph value must be cleared/updated through `PUT /api/settings/llm`, not just by changing
  `LLM_API_KEY` in `.env` — otherwise the stored value continues to take precedence.
- **`/api/settings/llm` should be treated as a privileged endpoint** in any production access control
  scheme, since it can view (masked) and change the active LLM provider and key.

<!-- VERIFY: Whether `PUT /api/settings/llm` currently has any authorization/role check beyond an
authenticated session — confirm before exposing this endpoint in a production deployment. -->

---

## See also

- [README.md](../README.md) — Project overview and quick start.
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture, layers, and data flow.
- [CONFIGURATION.md](./CONFIGURATION.md) — All runtime, build, and infrastructure configuration.
