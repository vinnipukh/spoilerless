<!-- generated-by: gsd-doc-writer -->
# Deployment

Spoilerless is live on the zero-cost production stack below, with
custom domains at `spoilerless.net`, automated CI, and production-grade
access control.

## Production Hosting Stack

| Platform | Tier | Scope | Public hostname |
|---|---|---|---|
| **Vercel** | Hobby (free) | Frontend static/SPA hosting | `app.spoilerless.net` |
| **Render** | Free web service | Backend FastAPI (uvicorn) | `api.spoilerless.net` |
| **Neo4j AuraDB** | Free | Production graph database (managed) | `neo4j+s://<dbid>.databases.neo4j.io` <!-- VERIFY: dbid is 03a8623b --> |
| **Upstash Redis** | Free | Rate-limit counters + graph query response cache | `rediss://...` <!-- VERIFY: instance name darling-rat-221809 --> |
| **Cloudflare** | Registrar | DNS for `spoilerless.net` (custom domains) | — |
| **Google OAuth** | — | User authentication (no local password store) | — |

The `api.` subdomain's Cloudflare DNS record is **DNS-only (grey cloud)** —
the proxy's idle timeout would kill long-running SSE chat streams. The
`app.` subdomain is proxied (orange cloud). An apex redirect from
`spoilerless.net` → `app.spoilerless.net` is configured via a Cloudflare
Redirect Rule. <!-- VERIFY: Cloudflare apex redirect rule active -->

### Platform configuration files

| File | Platform | Purpose |
|---|---|---|
| `render.yaml` | Render | Blueprint: `uv sync --frozen` → `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`, free plan, `autoDeploy: true` |
| `frontend/vercel.json` | Vercel | SPA catch-all rewrite (`/(.*)` → `/index.html`) for client-side routing. No `/api` proxy — the frontend calls the Render backend directly via `VITE_API_BASE_URL`. |
| `.github/workflows/ci.yml` | GitHub Actions | Pull-request gate: backend `pytest` + DB-pollution gate + frontend `build`/`lint`/`audit` (see Build Pipeline) |
| `.github/workflows/release.yml` | GitHub Actions | Staged-promotion skeleton (carry-over 09-07): manual `workflow_dispatch` with `release-candidate` / `release` stages. The `release` stage creates a `release-*` tag. Gated on the `ci` workflow passing on `main`. |

### Database — Neo4j AuraDB Free

The backend connects to AuraDB via `Neo4jDatabase.open()` in
`spoilerless/app/graph/database.py`, with the following Aura-specific config:

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
existing idempotent `spoilerless-setup` script (`spoilerless.app.graph.setup`)
run against the Aura instance. Docker Compose Neo4j is **no longer part
of any production deployment path** — it exists only for local
development (see Local Deployment below).

### Redis — Upstash free tier

`REDIS_URL` (Upstash `rediss://` TLS connection string, set on Render)
gates two features that share one Redis client
(`spoilerless/app/cache/redis_client.py`):

- **Rate limiting** (`spoilerless/app/services/rate_limit.py`): login,
  chat-send, and content-write endpoints return `429` in the standard
  error envelope once per-user/IP thresholds are exceeded. Empty
  `REDIS_URL` disables all rate limiting — the app boots unthrottled.
- **Graph query response cache** (`spoilerless/app/cache/graph_cache.py`):
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
   uv run spoilerless-setup
   ```

4. Start the FastAPI backend:

   ```bash
   uv run uvicorn spoilerless.app.main:app --reload
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
| `backend` | `ubuntu-latest` | `actions/checkout@v5` → `astral-sh/setup-uv` → `uv sync --frozen` → seed a throwaway `neo4j:2026.06.0-community` service container → `uv run pytest` → DB-pollution gate (assert zero scratch/candidate residue) → `actions/upload-artifact@v4` (pytest cache on failure) |
| `frontend` | `ubuntu-latest` | `actions/checkout@v5` → `actions/setup-node@v4` (Node 24, satisfies `jsdom`'s engines constraint) → `npm ci` → `npm run build` (`tsc -b && vite build`) → `npm run lint` → `npm audit --audit-level=high` |

The CI backend job uses its own ephemeral Neo4j service container
(pinned patch tag, port 7687, health check polling `localhost:7474`) —
it never touches production AuraDB. The DB-pollution gate (PROB-22,
carry-over 09-08) fails the build if any scratch-series or
candidate-origin nodes are left behind by the test suite. No deploy step
is included; Render and Vercel auto-deploy on push to the connected
branch via their native git integration.

A separate release workflow (`.github/workflows/release.yml`) provides a
manual `workflow_dispatch` for staged promotion (`release-candidate` /
`release`) gated on the `ci` workflow passing on `main`. The `release`
stage creates a `release-*` tag under the tag-protection rules in the
branch-protection checklist below.

To run the validation sequence locally:

```bash
# From the repository root, against a test-only Neo4j database
uv run pytest

# From frontend/
npm run lint
npm run test
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
- `NEO4J_DATABASE` (defaults to `neo4j`; on AuraDB it is the instance ID) <!-- VERIFY: AuraDB instance ID is 03a8623b -->

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
  rate limiting and the graph cache) <!-- VERIFY: Upstash instance darling-rat-221809 -->

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
  `build`/`lint`/`audit` on every PR, with its own throwaway Neo4j service
  container and a DB-pollution gate (carry-over 09-08).

### Closed by Phase 9

- **Structured exception logging** (09-06): the chat stream handler logs
  `LLMProviderUnavailable` and bare exceptions with `logger.exception`
  before yielding the SSE error event. The session-sweep background task
  also logs failed iterations. Database and LLM error handlers are
  installed during startup (`install_database_error_handlers`,
  `install_llm_error_handlers`).
- **Request-logging middleware** (09-08): every request is logged with
  method, path, status, and duration (ms); `X-LLM-*`, `Cookie`,
  `Set-Cookie`, and `Authorization` header values are redacted.
- **Security headers** (PROB-17, 09-05): `Content-Security-Policy`,
  `Strict-Transport-Security`, `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy` on every response.
- **DB-pollution CI gate** (09-08): the CI backend job asserts zero
  scratch-series or candidate-origin residue after the test suite.
- **Zombie sweep** (09-08): `spoilerless/scripts/zombie_sweep.py`
  removes tie-less `AppUser` rows and expired/revoked/orphaned `Session`
  nodes. `--dry-run` first, then `--execute`. Protected dev user is
  never deleted.
- **Session sweep** (09-08): a background task in the FastAPI lifespan
  deletes expired/revoked sessions every hour.
- **Write-path auth hardening** (09-03): all mutation routes require
  authentication; ownership binding on user content; admin-only
  candidate review.

### Known gaps (explicitly deferred to later phases)

Ownership binding, session-ID collision fix, user-content auth on all
mutation routes, full request/response casing consistency, test-suite
isolation from the live DB, frontend lint debt, stale-doc corrections,
Neo4j AuraDB backup/restore, and ten new features — see
`docs/PROBLEMS.md` (57 items) and `.planning/REQUIREMENTS.md` Phase 9
(PROB-01..32, FEAT-01..10).

### Outstanding (not yet configured)

- **External uptime monitor** (OPS-02): no UptimeRobot (or equivalent)
  monitor polls `GET /health` yet — requires human account sign-up. See
  `docs/RUNBOOK.md` §1 for the planned detection flow.

## Rollback

### Render (backend)

Render supports **redeploying a prior successful deploy** from its
dashboard: open the Render service → Deploys tab → select the last known
good deploy → **Deploy** to re-run the same commit's build and start
command. This is a full redeploy, not a hot-swap — the service restarts.
Alternatively, a `git revert` + push to the connected branch triggers a
fresh auto-deploy.

### Vercel (frontend)

Vercel supports **Instant Rollback** from its dashboard:
open the Vercel project → Deployments tab → select the last known good
deployment → **Instant Rollback**. This is **atomic and instant**
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

- HTTP 200 `{"status": "ok", "database": "connected", "service": "spoilerless-backend"}` — backend and
  Neo4j are healthy.
- HTTP 503 `{"status": "degraded", "database": "unavailable", "service": "spoilerless-backend"}` —
  backend is running but Neo4j is unreachable.

The endpoint is unauthenticated and read-only. The backend verifies
Neo4j connectivity with a lightweight `verify_connection()` call. A
`HEAD /health` variant is also available for uptime monitors.

### External uptime monitor

An UptimeRobot (or equivalent free-tier service) monitor on
`https://api.spoilerless.net/health` with a 5-minute check interval and
email alert on non-200 response or timeout is planned (human-provisioned
— see `docs/RUNBOOK.md` §1 for the detection flow; not yet configured at
time of writing). <!-- VERIFY: UptimeRobot monitor configured -->

### Platform-level monitoring

Render and Vercel each provide build/runtime logs and basic metrics in
their respective dashboards. No custom log drain, alert rule, custom
dashboard, Sentry, Datadog, or OpenTelemetry integration is configured.

The backend now includes structured logging infrastructure (Phase 9):
- **Request-logging middleware** logs method, path, status, and duration
  for every request, with sensitive headers (`X-LLM-*`, `Cookie`,
  `Set-Cookie`, `Authorization`) redacted.
- **Exception logging** in the chat stream handler and session-sweep
  background task via `logger.exception`.
- **Database and LLM error handlers** installed at startup
  (`install_database_error_handlers`, `install_llm_error_handlers`).

### Incident response

See `docs/RUNBOOK.md` for the full incident detection, diagnosis ladder,
rollback procedure, and zombie-sweep runbook. Key diagnostic commands
are executable by a future operator without platform dashboard access.

### Local development

- `docker compose ps neo4j` shows the Compose container's status.
- Neo4j logs persist at `./neo4j_logs`; container output via
  `docker compose logs neo4j`.
- The Compose health check probes `http://localhost:7474` every 10
  seconds with a 5-second timeout and 10 retries.

## Branch-protection checklist (carry-over 09-08 — operator applies in GitHub UI)

No repo-local CLI path exists for GitHub branch protection; the operator
configures these in **Settings → Branches → Add rule (main)** during the
final wave:

1. **Require a pull request before merging** — required approvals: 1,
   dismiss stale reviews: on.
2. **Require status checks to pass before merging** — enable the `ci`
   workflow (backend pytest + frontend build/lint/audit + DB-pollution
   gate). Require branches up-to-date: on.
3. **Require conversation resolution** before merging.
4. **Do not allow bypassing** the above settings (administrator-included).
5. **Tag protection** (Settings → Tags): protect `release-*` tags —
   restrict creation to maintainers.
6. **Repository → Actions → General:** keep default permissions
   (read-only contents); enable only the workflows present in this repo.

The `release.yml` staged-promotion workflow is gated on the `ci` workflow
passing; with rules 1–4 enforced, only reviewed, green commits reach main
and therefore release candidates.