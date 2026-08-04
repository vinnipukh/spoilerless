<!-- generated-by: gsd-doc-writer -->
# Deployment

HD Graf Cehennemi is live on the zero-cost production stack below, with
custom domains at `spoilerless.net`, automated CI, and production-grade
access control.

## Production Hosting Stack

| Platform | Tier | Scope | Public hostname |
|---|---|---|---|
| **Vercel** | Hobby (free) | Frontend static/SPA hosting | `app.spoilerless.net` |
| **Render** | Free web service | Backend FastAPI (uvicorn) | `api.spoilerless.net` |
| **Neo4j AuraDB** | Free | Production graph database (managed) | `neo4j+s://<dbid>.databases.neo4j.io` |
| **Upstash Redis** | Free | Rate-limit counters + graph query response cache | `rediss://...` |
| **Cloudflare** | Registrar | DNS for `spoilerless.net` (custom domains) | — |
| **Google OAuth** | — | User authentication (no local password store) | — |

The `api.` subdomain's Cloudflare DNS record is **DNS-only (grey cloud)** —
the proxy's idle timeout would kill long-running SSE chat streams. The
`app.` subdomain is proxied (orange cloud). An apex redirect from
`spoilerless.net` → `app.spoilerless.net` is configured via a Cloudflare
Redirect Rule.

### Platform configuration files

| File | Platform | Purpose |
|---|---|---|
| `render.yaml` | Render | Blueprint: `uv sync --frozen` → `uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`, free plan, `autoDeploy: true` |
| `frontend/vercel.json` | Vercel | SPA catch-all rewrite (`/(.*)` → `/index.html`) for client-side routing. No `/api` proxy — the frontend calls the Render backend directly via `VITE_API_BASE_URL`. |
| `.github/workflows/ci.yml` | GitHub Actions | Pull-request gate: backend `pytest` + frontend `build`/`lint` (see Build Pipeline) |

### Database — Neo4j AuraDB Free

The backend connects to AuraDB via `Neo4jDatabase.open()` in
`backend/app/graph/database.py`, with the following Aura-specific config:

- **TLS**: the `neo4j+s://` scheme is normalised to `neo4j://` +
  `encrypted=True` + `TrustCustomCAs(certifi.where())`, because the
  Windows OS trust store lacks the SSL.com root Aura's certificate chain
  presents.
- **Pool**: `max_connection_pool_size=50`,
  `connection_timeout=30.0`, `liveness_check_timeout=60.0` — the short
  liveness check survives Aura's ~5-minute idle-connection cutoff.
- **Credential model**: AuraDB Free does not support custom Cypher
  `CREATE ROLE`/`CREATE USER` — database user administration is a
  paid-tier feature. The app runs with the single instance admin
  credential from the Aura credentials file. Least-privilege DB access
  (D-16) is a documented Free-tier ceiling; upgrading to a paid tier is
  the path to true custom RBAC.

The seed data (Dexter S01E01-03 fixture graph) is migrated via the
existing idempotent `hdgraf-setup` script (`backend.app.graph.setup`)
run against the Aura instance. Docker Compose Neo4j is **no longer part
of any production deployment path** — it exists only for local
development (see Local Deployment below).

### Redis — Upstash free tier

`REDIS_URL` (Upstash `rediss://` TLS connection string, set on Render)
gates two features that share one Redis client
(`backend/app/cache/redis_client.py`):

- **Rate limiting** (`backend/app/services/rate_limit.py`): login,
  chat-send, and content-write endpoints return `429` in the standard
  error envelope once per-user/IP thresholds are exceeded. Empty
  `REDIS_URL` disables all rate limiting — the app boots unthrottled.
- **Graph query response cache** (`backend/app/cache/graph_cache.py`):
  `GET /api/series/{series_id}/graph` reads cache-aside, keyed by
  `(series_id, effective_boundary, user_id)` with a 300s TTL, and
  invalidated on every content-changing write (candidate
  approve/reject/edit, ChangeSet confirm/revert, custom-node/relation
  create/update/delete). A boundary change is always a cache miss with
  no need to invalidate.

With `REDIS_URL` unset, both features are no-ops — every graph fetch
queries Neo4j directly and no rate limiting exists.

## Local Deployment

Local development against Docker Compose Neo4j is still supported. These
instructions are for **local dev only** — the Compose recipe is not used
in any production deployment path.

### Prerequisites

- Docker Engine or Docker Desktop with Docker Compose (local Neo4j only).
- Python `>=3.13`, as required by `pyproject.toml` and pinned in `.python-version`.
- [`uv`](https://docs.astral.sh/uv/) for the Python environment.
- Node.js and npm for the frontend (`jsdom` constrains to `^22.22.2 || ^24.15.0 || >=26.0.0`).

### Start the application

1. Create the backend environment file and configure it as described in
   [CONFIGURATION.md](./CONFIGURATION.md):

   ```bash
   cp .env.example .env
   ```

2. Start Neo4j:

   ```bash
   docker compose up -d
   docker compose ps neo4j
   ```

   `docker-compose.yml` runs `neo4j:2026.06.0-community` (pinned patch
   tag) with Bolt (`7687`) and HTTP (`7474`) bound to `127.0.0.1` only
   — not reachable from outside the host. The `NEO4J_AUTH` credential
   is substituted from the same `NEO4J_PASSWORD` value the backend
   reads, keeping both in sync.

3. Install the Python dependencies and seed the graph:

   ```bash
   uv sync
   uv run hdgraf-setup
   ```

4. Start the FastAPI backend:

   ```bash
   uv run uvicorn backend.app.main:app --reload
   ```

5. In another terminal, install frontend dependencies and start Vite:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   Vite proxies `/api` requests to `http://127.0.0.1:8000` during
   development.

6. Verify:

   ```bash
   docker compose ps neo4j
   curl http://localhost:8000/health
   ```

   A healthy backend returns HTTP 200 with `status: "ok"` and
   `database: "connected"`. If Neo4j is unavailable, the backend
   returns HTTP 503 with `status: "degraded"`.

   With `SESSION_COOKIE_SECURE=true` (the default), session cookies
   won't be set over plain HTTP — set `SESSION_COOKIE_SECURE=false` in
   your local `.env` for development.

## Build Pipeline

A GitHub Actions workflow (`.github/workflows/ci.yml`) gates every pull
request with two jobs:

| Job | Runner | Steps |
|---|---|---|
| `backend` | `ubuntu-latest` | `actions/checkout@v5` → `astral-sh/setup-uv` → `uv sync --frozen` → seed a throwaway `neo4j:2026.06.0-community` service container → `uv run pytest` |
| `frontend` | `ubuntu-latest` | `actions/checkout@v5` → `actions/setup-node@v4` (Node 24, satisfies `jsdom`'s engines constraint) → `npm ci` → `npm run build` (`tsc -b && vite build`) → `npm run lint` |

The CI backend job uses its own ephemeral Neo4j service container
(pinned patch tag, port 7687, health check polling `localhost:7474`) —
it never touches production AuraDB. No deploy step is included; Render
and Vercel auto-deploy on push to the connected branch via their native
git integration.

To run the validation sequence locally:

```bash
# From the repository root, against a test-only Neo4j database
uv run pytest

# From frontend/
npm run lint
NODE_ENV=test CI=1 npm run test
```

## Environment Setup

Use [CONFIGURATION.md](./CONFIGURATION.md) as the authoritative
reference for all backend, frontend, Docker Compose, and runtime LLM
settings. **Never commit `.env` files or real credentials.**

### Render (backend web service)

These environment variables must be set in the Render service's
environment variable settings:

**Database**
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE` (defaults to `neo4j`; on AuraDB it is the instance ID)

**Authentication**
- `GOOGLE_CLIENT_ID`
- `SESSION_COOKIE_SECURE` (default `true` — production-safe;
  Render/Vercel are HTTPS-only so no override is needed)
- `SESSION_COOKIE_SAMESITE` (default `lax` — correct for the same-site
  subdomain layout `app.spoilerless.net` / `api.spoilerless.net`)
- `FRONTEND_ORIGINS` (must be `https://app.spoilerless.net` in
  production — this value drives both CORS and the backend's CSRF
  `Origin`/`Referer` check)
- `ALLOWED_EMAILS` (comma-separated; empty = unrestricted — any verified
  Google account can sign in)
- `ADMIN_EMAILS` (comma-separated; the operator's email to grant the
  `admin` role at login)

**Redis / rate limiting**
- `REDIS_URL` (Upstash `rediss://` TLS connection string; empty disables
  rate limiting and the graph cache)

### Vercel (frontend static hosting)

These are **build-time** environment variables, set in the Vercel
project's Production and Preview environment variable settings:

- `VITE_API_BASE_URL` (the deployed backend origin, e.g.
  `https://api.spoilerless.net` — controls where the frontend's
  `apiFetch` and chat SSE stream point. When unset, requests stay
  relative and rely on the Vite dev proxy, which does not exist in a
  Vercel-hosted build.)
- `VITE_GOOGLE_CLIENT_ID` (must match the Render `GOOGLE_CLIENT_ID`)

### Upstash Redis

The `REDIS_URL` value itself is set on Render (above). No separate
Upstash-side configuration is needed beyond provisioning the free-tier
instance and copying its `rediss://` connection string.

### Provisioning Redis (required for production)

1. Provision a free Upstash Redis instance and copy its `rediss://`
   connection string.
2. Set `REDIS_URL` in Render's environment variable settings.
3. Redeploy the backend — `init_rate_limiter()` binds the shared Redis
   client during FastAPI's `lifespan()` startup.

With `REDIS_URL` unset, **no rate limiting exists** and every graph
fetch queries Neo4j directly.

## Production Safety

### Closed by this phase (08)

- **Session cookie** defaults to `Secure` (production-safe out of the
  box), with settings-driven `SameSite`.
- **Admin role** gates candidate review (approve/reject/edit), ChangeSet
  confirmation, and the admin-only server-side LLM settings endpoint
  (`GET`/`PUT /api/settings/llm`). Admin status is derived from
  `ADMIN_EMAILS` at every login.
- **CSRF** `verify_origin` dependency covers `POST /api/auth/google` and
  `POST /api/auth/logout`, and is fail-closed in production (missing
  `Origin`/`Referer` → 403).
- **BYOK chat** (`X-LLM-Api-Key` / `X-LLM-Base-URL` / `X-LLM-Model`
  headers) removes the shared server-side LLM key model — keys are
  browser-held, never persisted or logged server-side.
- **Rate limiting** (Redis-backed, shared across Render workers):
  login 10 req / 5 min per IP, chat-send 20 req / min per user,
  content-write 30 req / min per user-or-IP. Disabled without Redis.
- **Graph response cache** (Redis cache-aside, 300s TTL, invalidated on
  write) reduces Neo4j load on repeated graph fetches.
- **CI gate** — GitHub Actions runs backend `pytest` and frontend
  `build`/`lint` on every PR, with its own throwaway Neo4j service
  container.

### Known gaps (explicitly deferred to Phase 9)

Ownership binding, session-ID collision fix, user-content auth on all
mutation routes, full request/response casing consistency, test-suite
isolation from the live DB, frontend lint debt, stale-doc corrections,
Neo4j AuraDB backup/restore, and ten new features — see
`docs/PROBLEMS.md` (41 items) and `.planning/REQUIREMENTS.md` Phase 9
(PROB-01..21, FEAT-01..10).

### Gaps not yet implemented (Phase 8 items pending 08-07 completion)

- **Structured exception logging**: the backend's `install_error_handlers`
  returns sanitised responses but does not yet log the original
  exception before sanitising (OPS-03, planned 08-07 Task 2).
- **Request-logging middleware**: no redacting request-logging
  middleware exists yet (planned 08-07 Task 2).
- **External uptime monitor**: no UptimeRobot (or equivalent) monitor
  polls `GET /health` yet (OPS-02, planned 08-07 Task 3 — requires
  human account sign-up).

## Rollback

### Render (backend)

Render supports **redeploying a prior successful deploy** from its
dashboard: open the Render service → Deploys tab → select the last known
good deploy → **Deploy** to re-run the same commit's build and start
command. This is a full redeploy, not a hot-swap — the service restarts.
Alternatively, a `git revert` + push to the connected branch triggers a
fresh auto-deploy.

### Vercel (frontend)

Vercel supports **promoting a prior deployment** from its dashboard:
open the Vercel project → Deployments tab → select the last known good
deployment → **Promote to Production**. This is **atomic and instant**
— the chosen deployment's already-built assets become the production
domain's content with no rebuild.

### Neo4j AuraDB

**No automated backup or restore is configured on the AuraDB Free
instance.** This is the most significant rollback gap — if graph data is
corrupted or accidentally deleted, there is no repository-defined or
platform-provided restore path on the Free tier. AuraDB's paid tiers
include snapshot-based backup; until then, any database-level rollback
is a manual task outside the repository.

For the Docker Compose local-dev path: stop the processes, check out the
prior revision, re-run `uv sync --frozen` and `npm ci`, rebuild the
frontend, and restart. If graph data changed, restore a separately
created Neo4j backup. **Do not use `docker compose down -v` as a
rollback command** — the Compose service uses bind mounts, so `-v`
destroys the data without restoring an earlier graph.

## Monitoring

### `/health` endpoint

`GET https://api.spoilerless.net/health` returns:

- HTTP 200 `{"status": "ok", "database": "connected"}` — backend and
  Neo4j are healthy.
- HTTP 503 `{"status": "degraded", "database": "unavailable"}` —
  backend is running but Neo4j is unreachable.

The endpoint is unauthenticated and read-only. The backend verifies
Neo4j connectivity with a lightweight `verify_connection()` call.

### External uptime monitor

An UptimeRobot (or equivalent free-tier service) monitor on
`https://api.spoilerless.net/health` with a 5-minute check interval and
email alert on non-200 response or timeout is planned (08-07 Task 3,
human-provisioned — not yet configured at time of writing).

### Platform-level monitoring

Render and Vercel each provide build/runtime logs and basic metrics in
their respective dashboards. No custom log drain, alert rule, custom
dashboard, Sentry, Datadog, or OpenTelemetry integration is configured.
The backend currently drops exceptions silently after sanitising
responses — structured exception logging is planned (08-07 Task 2) but
not yet shipped.

### Local development

- `docker compose ps neo4j` shows the Compose container's status.
- Neo4j logs persist at `./neo4j_logs`; container output via
  `docker compose logs neo4j`.
- The Compose health check probes `http://localhost:7474` every 10
  seconds with a 5-second timeout and 10 retries.
