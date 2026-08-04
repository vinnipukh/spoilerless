<!-- generated-by: gsd-doc-writer -->
# Deployment

HD Graf Cehennemi's repository now includes a **production hosting skeleton** — `render.yaml` (backend) and
`frontend/vercel.json` (frontend), plus an Aura-ready Neo4j driver configuration — but there is no evidence
in the repository of a live, verified production deployment: no CI/CD pipeline, no `.github/workflows`
directory, and several unauthenticated write endpoints remain (see
[Pre-production safety gaps](#pre-production-safety-gaps)). Treat the skeleton as a documented starting
point, not a production-ready configuration.

## Detected Deployment Targets

| Target | Scope | Repository configuration |
|---|---|---|
| Render (Blueprint, free tier) | Backend FastAPI web service | `render.yaml` |
| Vercel | Frontend static/SPA hosting | `frontend/vercel.json` |
| Neo4j Aura (managed, external) | Production graph database | Aura-aware TLS handling in `backend/app/graph/database.py`; no Aura instance is provisioned or referenced by name in the repository |
| Docker Compose | Local Neo4j Community database only | `docker-compose.yml` |
| Native Python process | Local FastAPI backend | `pyproject.toml`, `backend/requirements.txt`, `backend/app/main.py` |
| Vite development server or static build | Local frontend development, or the build artifact Vercel deploys | `frontend/package.json`, `frontend/vite.config.ts` |

There are no backend or frontend `Dockerfile` files, and no Fly.io, Railway, Serverless Framework,
Kubernetes, Helm, or other production deployment configuration beyond the Render/Vercel files above.

<!-- VERIFY: Confirm that the `neo4j:2026.06.0-community` image tag used by `docker-compose.yml` (local
development only) is available in the container registry used by any deployment environment before relying
on it. -->

### Production hosting skeleton (Render + Vercel + Neo4j Aura)

- **Backend — Render Blueprint (`render.yaml`):** a single free-tier `web` service, `runtime: python`,
  `autoDeploy: true`. `buildCommand: uv sync --frozen`; `startCommand: uv run uvicorn backend.app.main:app
  --host 0.0.0.0 --port $PORT`. Render supplies `$PORT` at runtime; no other Render-specific configuration
  (health check path, scaling, disks) is declared in the file.
- **Frontend — Vercel (`frontend/vercel.json`):** a single SPA rewrite rule
  (`{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`) so client-side routing resolves on
  refresh/deep-link. No build command, framework preset, or environment variable is declared in the file
  itself — those are configured in the Vercel project's own dashboard settings.
  <!-- VERIFY: Confirm the Vercel project's build command (`npm run build`), output directory
  (`frontend/dist`), and root directory (`frontend/`) settings, since `vercel.json` does not declare them. -->
- **Database — Neo4j Aura:** `Neo4jDatabase.open()` (`backend/app/graph/database.py`) detects
  `neo4j+s://`/`bolt+s://` URIs (Aura's TLS scheme), normalizes them to the plain scheme with explicit
  `encrypted=True`, and trusts `certifi`'s CA bundle rather than the host OS trust store — this is an
  explicit Aura compatibility fix, not a generic feature. The driver also sets
  `max_connection_pool_size=50`, `connection_timeout=30.0`, and `liveness_check_timeout=60.0` to tolerate
  Aura's idle-connection cutoffs. No Aura instance URI, region, or tier is referenced anywhere in the
  repository.
  <!-- VERIFY: Provision a Neo4j Aura instance (or equivalent managed Neo4j) and set the production
  `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD` accordingly; this is not automated by any file in the repo. -->
- None of Render, Vercel, or Aura configuration has been exercised by an automated deploy in this
  repository — there is no `.github/workflows` directory, so a push relies entirely on each platform's own
  `autoDeploy`/git-integration behavior with no test, lint, or type-check gate beforehand.

## Local Deployment

### Prerequisites

- Docker Engine or Docker Desktop with Docker Compose (local Neo4j only — production uses Neo4j Aura instead).
- Python `>=3.13`, as required by `pyproject.toml` and pinned in `.python-version`.
- [`uv`](https://docs.astral.sh/uv/) for the Python environment.
- Node.js and npm for the frontend. `frontend/package.json` has no `engines` field, but the committed `jsdom` lockfile entry currently requires `^22.22.2 || ^24.15.0 || >=26.0.0`.

### Start the application

1. Create the backend environment file and configure it as described in [CONFIGURATION.md](./CONFIGURATION.md):

   ```bash
   cp .env.example .env
   ```

2. Start Neo4j:

   ```bash
   docker compose up -d
   docker compose ps neo4j
   ```

   `docker-compose.yml` runs `neo4j:2026.06.0-community` (a pinned, calendar-versioned tag) with Bolt
   (`7687`) and HTTP (`7474`) bound to `127.0.0.1` only — not reachable from outside the host. The
   `NEO4J_AUTH` credential is substituted from the same `NEO4J_PASSWORD` value the backend reads
   (`NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}`), so setting `NEO4J_PASSWORD` in `.env` keeps both in
   sync — see [CONFIGURATION.md § Docker Compose](./CONFIGURATION.md#docker-compose-neo4j).

3. Install the Python dependencies and initialize the graph:

   ```bash
   uv sync
   uv run hdgraf-setup
   ```

   The `hdgraf-setup` script resolves to `backend.app.graph.setup:main` through `pyproject.toml`.

4. Start the FastAPI backend:

   ```bash
   uv run uvicorn backend.app.main:app --reload
   ```

5. In another terminal, install the frontend dependencies and start Vite:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   Vite proxies `/api` requests to `http://127.0.0.1:8000` during development.

6. Verify Neo4j and the backend:

   ```bash
   docker compose ps neo4j
   curl http://localhost:8000/health
   ```

   A healthy backend returns HTTP 200 with `status: "ok"` and `database: "connected"`. If Neo4j is unavailable, the backend remains running and `/health` returns HTTP 503 with `status: "degraded"`.

## Build Pipeline

No `.github/workflows` directory or other repository-defined CI/CD configuration is present. **No
repository-level CI/CD pipeline detected.** Builds, tests, artifact publication, and deployment are not
automated by this repository beyond each platform's own git-push deploy hook:

- **Render** (`render.yaml`) runs `buildCommand: uv sync --frozen` then `startCommand: uv run uvicorn
  backend.app.main:app --host 0.0.0.0 --port $PORT` on every push, via `autoDeploy: true`. This is
  Render's own continuous-deployment behavior, not a test/lint gate — nothing in `render.yaml` runs `pytest`
  or blocks a deploy on a failing build.
- **Vercel** deploys the frontend on push per its own git-integration settings (not declared in the repo;
  `frontend/vercel.json` only adds the SPA rewrite rule).

Neither platform's pipeline is configured in this repository to run tests, linting, or type-checking before
deploying — the manual validation sequence below is the only test/lint gate that exists, and it is not
automated:

The repository-defined manual build sequence is:

1. Resolve the locked Python environment:

   ```bash
   uv sync --frozen
   ```

   The backend has no compilation or packaging step; it runs from the repository source through Uvicorn. `backend/requirements.txt` is a uv-generated export, while `pyproject.toml` and `uv.lock` define the project environment.

2. Install the locked frontend dependencies:

   ```bash
   cd frontend
   npm ci
   ```

3. Type-check and build the frontend:

   ```bash
   npm run build
   ```

   `frontend/package.json` defines this as `tsc -b && vite build`. Vite writes the static artifact to its default `frontend/dist/` directory because no custom output directory is configured.

4. Run validation manually before deployment:

   ```bash
   # From the repository root, with Neo4j pointed at a disposable/test-only database
   uv run pytest

   # From frontend/
   npm run lint
   NODE_ENV=test CI=1 npm run test
   ```

No container image build, image registry push, release trigger, or artifact upload exists in the repository.

## Environment Setup

Use [CONFIGURATION.md](./CONFIGURATION.md) as the authoritative reference for all backend, frontend, Docker Compose, and runtime LLM settings. Never commit `.env` files or real credentials.

For any backend deployment, these settings have no code defaults and must be supplied:

- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

For a Neo4j Aura database, `NEO4J_URI` uses the `neo4j+s://` scheme (e.g.
`neo4j+s://<instance>.databases.neo4j.io:7687`); the driver's Aura-specific TLS handling is described in
[Production hosting skeleton](#production-hosting-skeleton-render--vercel--neo4j-aura) above.

`NEO4J_DATABASE` defaults to `neo4j`. `SESSION_COOKIE_SECURE` now **defaults to `true`** (production-safe
for Render/Vercel's HTTPS-only hosting); local HTTP development must explicitly set
`SESSION_COOKIE_SECURE=false`. Authentication additionally needs matching `GOOGLE_CLIENT_ID` and build-time
`VITE_GOOGLE_CLIENT_ID` values, and `FRONTEND_ORIGINS` restricted to the deployed frontend origin(s) — this
value also drives the backend's CSRF `Origin`/`Referer` check (`verify_origin`, applied to
`POST /api/auth/google` and `POST /api/auth/logout`). LLM-backed chat remains disabled unless an effective
LLM configuration enables it; `GET`/`PUT /api/settings/llm` require an authenticated session with the
`admin` role (`ADMIN_EMAILS`) — see CONFIGURATION.md for full environment and Neo4j-stored runtime override
precedence.

The frontend's `VITE_*` values are embedded at build time. `VITE_GOOGLE_CLIENT_ID` is consumed by the login
UI. `VITE_API_BASE_URL` (commented out by default in `frontend/.env.example`, with the example value
`https://api.spoilerless.net`) is read by the shared API client (`frontend/src/api/client.ts`) and the chat
SSE stream (`frontend/src/api/chat.ts`); when it is unset, requests stay relative and rely on the Vite dev
proxy, which does not exist in a Vercel-hosted build — a hosted frontend must set this Vercel project
environment variable to the deployed backend's origin.

<!-- VERIFY: The exact production API origin for `VITE_API_BASE_URL` and the exact Neo4j Aura instance URI
are deployment-specific and not discoverable from the repository; confirm both in the Vercel project's
build-time environment variables and the Render service's environment variables respectively. -->

No deployment-platform secret manager is configured in this repository beyond each platform's own
environment-variable UI. <!-- VERIFY: Store `NEO4J_PASSWORD`, `LLM_API_KEY`, `GOOGLE_CLIENT_ID`, and any
other deployment secrets in Render's and Vercel's own environment-variable settings for the actual hosting
project; neither is configured or referenced by name in this repository. -->

### Provisioning Redis (optional, recommended for production)

`REDIS_URL` (not declared in `.env.example`) is empty by default and is not required for the backend to
start. It gates two independent, optional features that share the single Redis client in
`backend/app/cache/redis_client.py`:

- **Rate limiting** (`backend/app/services/rate_limit.py`) on `POST /api/auth/google` (10 requests / 5 min
  per IP), chat send (20 requests / 60s per user), and content-write routes (30 requests / 60s per user,
  falling back to IP for the anonymous routes — see [Pre-production safety gaps](#pre-production-safety-gaps)).
- **Response cache** (`backend/app/cache/graph_cache.py`) for `GET /api/series/{series_id}/graph`, keyed by
  series/boundary/user with a 300-second TTL.

With `REDIS_URL` unset, both features are no-ops: **no rate limiting exists in a deployment that has not
provisioned Redis**, and every graph fetch queries Neo4j directly. `redis_client.py`'s own docstring states
the expected connection string is an Upstash `rediss://` TLS URL — Upstash is the tested target, not a
requirement enforced by the code. To enable both features in production:

1. Provision a Redis instance (Upstash is the documented/tested target) and copy its `rediss://` connection string.
2. Set `REDIS_URL` in the backend's deployment environment (e.g. Render's environment variable settings).
3. Restart/redeploy the backend — `init_rate_limiter()` binds the shared client during FastAPI's `lifespan()` startup.

<!-- VERIFY: No Upstash (or other Redis) instance is provisioned or referenced by name/URL in this
repository; provisioning is a manual step outside the codebase. -->

## Pre-production safety gaps

The repository now includes a hosting skeleton (Render/Vercel/Aura-ready driver), admin-gated LLM settings,
a fail-closed CSRF check, and optional Redis-backed rate limiting/caching. Public deployment is still **not
recommended** until the gaps below are addressed — verify each one directly against current source before
exposing this application to the public internet:

- **Anonymous write endpoints remain.** `POST /api/series/{id}/candidates/ingest`
  (`backend/app/api/candidates.py`), and the notes/custom-node/custom-relationship create/update/delete
  routes and `POST /api/series/{id}/revisions/{revision_id}/revert`
  (`backend/app/api/user_content.py`, `backend/app/api/revisions.py`) have no `CurrentUserDependency` or
  `RequireAdminDependency` — any visitor can create, edit, or delete this content. (Candidate
  approve/reject/edit are now admin-gated via `RequireAdminDependency`, and both are behind the
  content-write rate limiter described above — but ingest and the routes above are not.)
- **User content has no owner.** `NoteResponse` and the custom-node/relationship models carry no `user_id`;
  any visitor (or, once auth is added, any signed-in user) can edit or delete another user's notes and
  custom content.
- **Sessions are never swept.** `repository/session.py` documents the intended cleanup query but does not
  schedule it; expired/revoked `Session` nodes accumulate indefinitely, and `AuthService.get_current_user`
  performs a Neo4j write on every authenticated request to slide the session TTL.
- **Rate limiting and the graph cache are no-ops until `REDIS_URL` is provisioned** — see
  [Provisioning Redis](#provisioning-redis-optional-recommended-for-production) above. No Redis/Upstash
  instance is referenced anywhere in the repository.
- **No CI/CD pipeline gates a deploy.** There is no `.github/workflows` directory; Render's `autoDeploy` and
  Vercel's git integration will ship a push that fails `pytest`, `npm run lint`, or `npm run test` with no
  automated warning.
- **No LICENSE file** exists in the repository root, which is a legal/compliance gap independent of the
  technical items above.
- **No security response headers.** `backend/app/main.py` configures CORS only — no
  Content-Security-Policy, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy`.
- **No production observability.** No structured request logging, metrics endpoint, tracing, or
  Sentry/Datadog/New-Relic/OpenTelemetry dependency exists; failed logins, failed LLM streams, and database
  errors are not surfaced anywhere beyond ad hoc `logger.warning` calls in `backend/app/api/auth.py`.
- **Durable Neo4j storage and backups are unaddressed for the local Compose path**; a production deployment
  should use Neo4j Aura (which handles this) rather than the Compose recipe, but no backup/restore
  procedure for Aura is documented in this repository.
- **Runtime LLM settings are stored in plaintext** in the `:AppSetting {key: 'llm'}` node; a Neo4j backup
  can contain the full provider API key even though API responses always return a masked value.

These are requirements to close before a public launch, not capabilities already supplied by the current
repository. Confirm the current state of each item against source before treating any of them as resolved,
since this list can drift as the codebase changes.

## Rollback

There is no repository-defined production rollback command, release workflow, immutable image tag policy, or database migration rollback procedure.

Render and Vercel each provide platform-level rollback (redeploying a previous build/commit from their
respective dashboards), but neither is configured, scripted, or referenced by name in this repository.
<!-- VERIFY: Confirm the exact rollback mechanism (dashboard redeploy vs. CLI) for the actual Render service
and Vercel project used in production. -->

For the current manual/local deployment model:

1. Stop the affected backend and frontend processes.
2. Check out the previously verified source revision in a clean working tree.
3. Re-run `uv sync --frozen` and `npm ci`, then rebuild the frontend with `npm run build`.
4. Restart the application processes and verify `GET /health` plus the main frontend flow.
5. If graph data changed, restore a separately created Neo4j backup that matches the prior application revision. The repository does not configure or automate Neo4j backups (Compose or Aura).

<!-- VERIFY: Adapt the rollback commands, process manager restart, artifact selection, and backup restoration steps to the actual production platform before first deployment. -->

Do not use `docker compose down -v` as a rollback command. The Compose service uses bind mounts, so `-v` does not restore an earlier graph (and does not make a backup); a real rollback requires a separately created, revision-compatible Neo4j backup.

## Monitoring

Repository-provided monitoring is limited to:

- `GET /health` in `backend/app/main.py`, which verifies Neo4j connectivity and returns HTTP 200 or 503.
- The Neo4j Compose health check, which probes `http://localhost:7474` every 10 seconds with a 5-second timeout and 10 retries (local development only).
- Neo4j logs persisted at `./neo4j_logs` by `docker-compose.yml`; container output can be viewed with `docker compose logs neo4j` (local development only).

Render and Vercel each provide their own platform-level build/runtime logs and basic metrics dashboards, but
neither is configured beyond the default platform behavior — no custom log drain, alert rule, or dashboard
is defined in this repository.
<!-- VERIFY: Confirm what, if anything, is configured in the actual Render service and Vercel project
dashboards for logs, metrics, and alerts. -->

No Sentry, Datadog, New Relic, or OpenTelemetry application dependency or configuration is present. The
repository also defines no metrics endpoint, log aggregation, alert rules, uptime checks, monitoring
dashboard, or alert webhook.

<!-- VERIFY: Select an external uptime, logging, metrics, and alerting service for production, and configure it to monitor `/health` and the hosting platform's process/container health. -->
