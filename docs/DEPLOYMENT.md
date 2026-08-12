<!-- generated-by: gsd-doc-writer -->
# Deployment

Spoilerless includes repository configuration for a Vercel frontend, a
Render FastAPI service, pull-request CI, and local Neo4j through Docker
Compose. The named production domains, tiers, and managed-service resources
below are intended operator configuration, not asserted current state. Their
current deployment state is unknown from the repository.

<!-- VERIFY: Operator step — open the Vercel, Render, Neo4j Aura, Upstash, and Cloudflare dashboards and record whether the production deployments, custom domains, service tiers, and managed-resource identifiers match the intended values below. Until checked, their current state is unknown. -->

## Production Hosting Stack

| Platform | Intended tier | Intended scope | Intended public hostname |
|---|---|---|---|
| **Vercel** | Hobby (free) | Frontend static/SPA hosting | `app.spoilerless.net` |
| **Render** | Free web service | Backend FastAPI (uvicorn) | `api.spoilerless.net` |
| **Neo4j AuraDB** | Free | Production graph database (managed) | `neo4j+s://<dbid>.databases.neo4j.io` |
| **Upstash Redis** | Free | Rate-limit counters + graph query response cache | `rediss://...` |
| **Cloudflare** | Registrar | DNS for `spoilerless.net` (custom domains) | — |
| **Google OAuth** | — | User authentication (no local password store) | — |

The intended DNS layout keeps the `api.` record **DNS-only (grey cloud)** so
the Cloudflare proxy is not placed in front of long-running SSE chat streams;
the `app.` record may be proxied. The intended apex behavior is a redirect
from `spoilerless.net` to `app.spoilerless.net`. Current DNS and redirect-rule
state is unknown because no DNS/IaC declaration is tracked.
<!-- VERIFY: Operator step — in Cloudflare DNS, inspect the `app` and `api` records and their proxy modes; then inspect Redirect Rules for the apex redirect. Record the observed values before relying on this layout. -->

### Platform configuration files

| File | Platform | Purpose |
|---|---|---|
| `render.yaml` | Render | Blueprint service `spoilerless-api`: `uv sync --frozen` → `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`, free plan, `autoDeploy: true` |
| `frontend/vercel.json` | Vercel | SPA catch-all rewrite (`/(.*)` → `/index.html`) for client-side routing. No `/api` proxy — the frontend calls the Render backend directly via `VITE_API_BASE_URL`. |
| `.github/workflows/ci.yml` | GitHub Actions | Pull-request gate: backend `pytest` + DB-pollution gate + frontend `build`/`lint`/`audit` (see Build Pipeline) |
| `.github/workflows/release.yml` | GitHub Actions | Incomplete manual promotion skeleton. Its “CI gate” only prints a message; it does not query check status. The `release` path attempts to push a `release-*` tag, but the workflow declares `contents: read`, so tag push is not currently authorized. |

No `Dockerfile` or `.dockerignore` is tracked. Render uses its native Python
runtime and the commands in `render.yaml`; Docker Compose is only the local
Neo4j dependency.

### Database — Neo4j AuraDB Free

The backend connects to AuraDB via `Neo4jDatabase.open()` in
`spoilerless/app/graph/database.py`, with the following Aura-specific config:

- **TLS**: the `neo4j+s://` scheme is normalised to `neo4j://` +
  `encrypted=True` + `TrustCustomCAs(certifi.where())`, because the
  Windows OS trust store lacks the SSL.com root Aura's certificate chain
  presents.
- **Pool**: `max_connection_pool_size=50`,
  `connection_timeout=30.0`, and `liveness_check_timeout=60.0` are set in
  `Neo4jDatabase.open()`.
- **Credentials**: the application consumes one configured username and
  password; it does not provision database users or roles.
- **Env aliases**: `Settings` (`spoilerless/app/core/config.py`) accepts
  both the `aura_uri` / `aura_username` / `aura_password` /
  `aura_database` names (the local `.env` convention) and the `NEO4J_*`
  names (the deployed/Render convention); when both are present the
  `aura_*` value wins. `NEO4J_DATABASE` defaults to `neo4j` — the
  docker-local database name — so set it to the actual Aura database name
  in production.

The deployed tier, console permission limits, and effective credential scope
are unknown from source control.
<!-- VERIFY: Operator step — in the Aura console, inspect the deployed tier and available user/role controls; use a non-destructive permission check to determine the application's effective credential scope. Record the result without copying credentials into this document. -->

The seed data (Dexter S01E01-03 fixture graph) is migrated by running the
idempotent setup module against the target database:

```bash
uv run --project spoilerless python -m spoilerless.app.graph.setup
```

`pyproject.toml` declares a `spoilerless-setup` console entry, but this
project has no build-system configuration and `uv sync` does not install that
executable; use the module command above. Docker Compose Neo4j is **not part
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
  invalidated after successful candidate approve/reject/edit, ChangeSet
  confirm/revert, and custom-node/relation create/update/delete routes.
  Revision revert also changes graph-visible resources but currently omits
  `invalidate_series(series_id)`, so an existing graph-cache entry can remain
  stale until its 300s TTL expires. A boundary change is always a cache miss
  with no need to invalidate.

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

   For this local Vite-proxy path, delete `VITE_API_BASE_URL=/api` from the
   copied `.env` or set `VITE_API_BASE_URL=`. Frontend request paths already
   begin with `/api`; setting the base to `/api` would produce `/api/api/...`.
   Use a full backend origin only for a separately hosted frontend.

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
   uv run --project spoilerless python -m spoilerless.app.graph.setup
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

   `SESSION_COOKIE_SECURE=true` is the production-safe default. If the local
   browser does not retain the cookie over plain HTTP, set
   `SESSION_COOKIE_SECURE=false` in the local `.env`; never use that override
   in production.

## Build Pipeline

A GitHub Actions workflow (`.github/workflows/ci.yml`) gates every pull
request with two jobs:

| Job | Runner | Steps |
|---|---|---|
| `backend` | `ubuntu-latest` | `actions/checkout@v5` → `astral-sh/setup-uv` (pinned v8.1.0) → `uv sync --frozen` → seed the throwaway `neo4j:2026.06.0-community` service container via `spoilerless.app.graph.setup` → `uv run pytest` → DB-pollution gate (assert zero scratch/candidate residue) → `actions/upload-artifact@v4` (pytest cache on failure) |
| `frontend` | `ubuntu-latest` | `actions/checkout@v5` → `actions/setup-node@v4` (Node 24, satisfies `jsdom`'s engines constraint) → `npm ci` → `npm run build` (`tsc -b && vite build`) → `npm run lint` → `npm audit --audit-level=high` |

The CI backend job uses its own ephemeral Neo4j service container
(pinned patch tag, port 7687, health check polling `localhost:7474`) —
it never touches production AuraDB. The DB-pollution gate fails the build if any scratch-series or
candidate-origin nodes are left behind by the test suite. No deploy step is included. `render.yaml` requests Render auto-deploy;
Vercel deployment and each platform's connected branch depend on
operator-managed native git integration. The connected branches and current
native-git deployment settings are unknown from the repository.
<!-- VERIFY: Operator step — inspect the connected repository, production branch, and automatic-deployment toggle in both the Render and Vercel dashboards; record the observed state before release. -->

A separate release workflow (`.github/workflows/release.yml`) exposes a
manual `workflow_dispatch` input (`release-candidate` or `release`), but it is
only a skeleton: `verify-ci-gate` echoes text instead of querying GitHub's
checks API, the checkout is not explicitly pinned to `main`, and the tag job
attempts `git push` while workflow permissions are `contents: read`. Do not
use it as evidence that a commit passed CI or that a tag was published.

To run the validation sequence locally:

```bash
# From the repository root, against a test-only Neo4j database
uv run pytest

# From frontend/
npm run build
npm run lint
npm run test -- --run
npm audit --audit-level=high
```

## Environment Setup

Use [CONFIGURATION.md](./CONFIGURATION.md) as the authoritative
reference for all backend, frontend, Docker Compose, and runtime LLM
settings. **Never commit `.env` files or real credentials.**

The backend reads configuration from a single root `.env` file
(`env_file=".env"` in `Settings`, resolved against the **process working
directory**). Only the root `.env` is consulted — there are no
`.env.production` / `.env.development` split files and no per-environment
overlay. On Render the service must therefore start from the repository
root (Render's default working directory) so the root `.env` is found;
dashboard environment variables, when set, take precedence over file
values (pydantic-settings behaviour).

### Render (backend web service)

`render.yaml` contains **no `envVars` block**. The following are
dashboard-only operator settings and are not supplied by the repository.
Never copy values from a local `.env` into documentation or frontend
`VITE_*` variables.

In the Render dashboard, keep the Start Command exactly:

```bash
uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT
```

**Dashboard override trap — the Start Command is the single most likely
deployment failure.** `render.yaml` (the Blueprint) carries the correct
command above, but a service created from the Blueprint can hold a
*dashboard override* that differs from it. A stale override left over from
the pre-rename package layout —

```bash
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

— fails every deploy with `ModuleNotFoundError: No module named 'backend'`
(the package is `spoilerless/`; there is no `backend/` directory). The
service keeps serving the **previous successful build**, so `/health`
continues to return HTTP 200 while the new code is never deployed. See
`docs/ops/runbook.md` for the root-cause write-up and the manual
dashboard fix. No `RENDER_API_KEY` (or equivalent deployment-automation
credential) exists anywhere in the repository or the root `.env`, so this
fix is **operator-touch**: it can only be applied from the Render dashboard
(Settings → Start Command) — or by deleting and re-creating the service
from the Blueprint — never from the repository.
<!-- VERIFY: Operator step — open Render Settings → Start Command for the `spoilerless-api` service and record the exact current value; if it is not `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`, fix it and redeploy. Then record the `service` field of the live `/health` response (see Monitoring) as the build-marker check. -->

The required/production environment settings are:

**Database**
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE` (defaults to `neo4j`; set the actual Aura database name supplied by the provider)

**Authentication**
- `GOOGLE_CLIENT_ID`
- `SESSION_COOKIE_NAME` (optional; default `session`)
- `SESSION_TTL_SECONDS` (optional; default `604800`, or 7 days)
- `SESSION_COOKIE_SECURE` (default `true`; keep it enabled for an HTTPS
  production deployment)
- `SESSION_COOKIE_SAMESITE` (default `lax` — correct for the same-site
  subdomain layout `app.spoilerless.net` / `api.spoilerless.net`)
- `FRONTEND_ORIGINS` (set to the deployed frontend origin, for example
  `https://app.spoilerless.net`; this value drives both CORS and the
  backend's CSRF `Origin`/`Referer` check)
- `ALLOWED_EMAILS` (comma-separated; empty = unrestricted — any verified
  Google account can sign in)
- `ADMIN_EMAILS` (comma-separated; the operator's email to grant the
  `admin` role at login)

**Redis / rate limiting**
- `REDIS_URL` (Upstash-style `rediss://` TLS connection string; empty
  disables rate limiting and the graph cache)

**Optional server-managed LLM fallback**
- `LLM_ENABLED` (default `false`)
- `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_TEMPERATURE`,
  `LLM_MAX_TOOL_ROUNDS`, `LLM_MAX_CONTEXT_ITEMS`, and
  `LLM_MAX_CONTEXT_CHARACTERS`
- `LLM_FALLBACK_EN` and `LLM_FALLBACK_TR` (optional localized fallback text)

These settings are optional when users supply request-scoped BYOK headers.
See [CONFIGURATION.md](./CONFIGURATION.md) for provider resolution order,
defaults, and runtime settings stored in Neo4j.

`ALLOWED_EMAILS`, `ADMIN_EMAILS`, `REDIS_URL`,
`SESSION_COOKIE_SAMESITE`, `LLM_FALLBACK_EN`, and `LLM_FALLBACK_TR` are
declared by `Settings` but are not present in the committed `.env.example`;
add them only in the Render dashboard when needed. Do not set
`VITE_GOOGLE_CLIENT_ID` in Render merely to configure the frontend: Vite
consumes it at frontend build time in Vercel. The backend's startup equality
guard compares the two IDs only if both are present in the backend process
environment.

The connected branch, custom domain, dashboard command override, and actual
environment-variable values are unknown from source control.
<!-- VERIFY: Operator step — in Render, inspect the connected branch and custom domain; confirm the Start Command is exactly `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`; confirm every required variable is present without copying secret values into this document. -->

### Vercel (frontend static hosting)

These are **build-time** environment variables, set in the Vercel
project's Production and Preview environment variable settings:

- `VITE_API_BASE_URL` (the deployed backend origin, e.g.
  `https://api.spoilerless.net` — controls where the frontend's
  `apiFetch` and chat SSE stream point. When unset, requests stay
  relative and rely on the Vite dev proxy, which does not exist in a
  Vercel-hosted build.)
- `VITE_GOOGLE_CLIENT_ID` (must match the Render `GOOGLE_CLIENT_ID`)

The intended dashboard settings are Framework Preset **Vite**, Root
Directory **`frontend/`**, Build Command **`npm run build`**, and Output
Directory **`dist`**. Only the SPA rewrite is repository-defined in
`frontend/vercel.json`; these project settings, scopes, values, and domains are
external and their current state is unknown from source control.
<!-- VERIFY: Operator step — in Vercel, inspect Root Directory, Framework Preset, Build Command, Output Directory, Production/Preview variable scopes, custom domain, and the presence and shape (not secret contents) of current `VITE_*` values. Record any divergence. -->

### Upstash Redis

The `REDIS_URL` value itself is set on Render (above). Provisioning the Redis
resource and obtaining its TLS connection string are external operator tasks.

### Provisioning Redis (required for production)

1. Provision a free Upstash Redis instance and copy its `rediss://`
   connection string.
2. Set `REDIS_URL` in Render's environment variable settings.
3. Redeploy the backend — `init_rate_limiter()` binds the shared Redis
   client during FastAPI's `lifespan()` startup.

The existence and current state of the managed Redis resource, its network
policy, and the Render secret binding are unknown from source control.
<!-- VERIFY: Operator step — inspect the Upstash resource and network policy, then confirm Render has a matching `REDIS_URL` secret binding; test connectivity without exposing or copying the credential. -->

With `REDIS_URL` unset, **no rate limiting exists** and every graph
fetch queries Neo4j directly.

## Production Safety

### Security and Reliability Features

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
  headers) overrides stored/server `LLM_*` settings for that request. BYOK
  keys are browser-held and are not persisted or logged server-side; when
  BYOK is absent, stored or environment-backed provider settings can still
  be used.
- **Rate limiting** (Redis-backed, shared across Render workers):
  login 10 req / 5 min per IP, chat-send 20 req / min per user,
  content-write 30 req / min per user-or-IP. Disabled without Redis.
- **Graph response cache** (Redis cache-aside, 300s TTL, invalidated on
  write) reduces Neo4j load on repeated graph fetches.
- **CI gate** — GitHub Actions runs backend `pytest` and frontend
  `build`/`lint`/`audit` on every PR, with its own throwaway Neo4j service
  container and a DB-pollution gate.
- **Structured exception logging**: the chat stream handler logs
  `LLMProviderUnavailable` and bare exceptions with `logger.exception`
  before yielding the SSE error event. The session/share sweep intends to log
  failed iterations, but its exception branch calls undefined `logger` while
  the module defines `log`; a failed sweep therefore raises `NameError`
  instead of producing that log. Database and LLM error handlers are installed
  during startup (`install_database_error_handlers`,
  `install_llm_error_handlers`).
- **Request-logging middleware**: completed requests are logged with method,
  path, status, and duration (ms); `X-LLM-*`, `Cookie`, `Set-Cookie`, and
  `Authorization` header values are redacted. An unhandled exception from
  `call_next` bypasses this log because the middleware has no exception or
  `finally` branch.
- **Security headers**: `Content-Security-Policy`,
  `Strict-Transport-Security`, `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy` on every response.
- **DB-pollution CI gate**: the CI backend job asserts zero
  scratch-series or candidate-origin residue after the test suite.
- **Zombie sweep**: `spoilerless/scripts/zombie_sweep.py`
  removes tie-less `AppUser` rows and expired/revoked/orphaned `Session`
  nodes. `--dry-run` first, then `--execute`. Protected dev user is
  never deleted.
- **Session sweep**: a background task in the FastAPI lifespan
  deletes expired/revoked sessions every hour.
- **Write-path auth hardening**: all mutation routes require
  authentication; ownership binding on user content; admin-only
  candidate review.

### Repository-visible deployment gaps

- `render.yaml` does not declare environment variables or managed backing
  services; production secrets and resource bindings are dashboard-only.
- `release.yml` does not enforce its stated CI gate and cannot push tags with
  its current `contents: read` permission.
- No deployment smoke-test workflow, infrastructure-as-code for DNS, external
  uptime monitor configuration, or automated database backup/restore job is
  committed.
- No `RENDER_API_KEY` (or equivalent deployment-automation credential)
  exists in the repository or the root `.env`, so dashboard-level fixes —
  most importantly a stale Start Command override — are operator-touch
  only: they cannot be applied or verified from the repository.

### Outstanding (not yet configured)

- **External uptime monitor**: no UptimeRobot (or equivalent)
  monitor polls `GET /health` yet — requires human account sign-up. See
  `docs/ops/runbook.md` §1 for the planned detection flow.

## Rollback

### Render (backend)

Do not assume a project-specific rollback control or connected auto-deploy
branch exists. If the dashboard exposes redeployment of a prior successful
deploy, open the service's Deploys tab, select the last known-good deploy, and
follow the displayed redeploy action; expect a service restart. A `git revert`
and push triggers a fresh deployment only if the observed connected branch and
auto-deploy setting support it. Current controls and integration state are
unknown from source control.
<!-- VERIFY: Operator step — before an incident, inspect the Render Deploys tab for prior-deploy controls and verify the connected branch and auto-deploy toggle; record the tested rollback sequence. -->

### Vercel (frontend)

Do not assume this project exposes a particular rollback control or that it is
atomic. In the Vercel project, inspect the Deployments tab, select a known-good
deployment, and follow the rollback or promotion action actually displayed.
Current project-specific controls and behavior are unknown from source control.
<!-- VERIFY: Operator step — before an incident, inspect and test the Vercel project's rollback/promotion controls with a non-production or otherwise safe deployment; record whether assets are reused, whether a rebuild occurs, and how the production domain changes. -->

### Neo4j AuraDB

**No automated backup or restore job is defined in this repository.** If
graph data is corrupted or accidentally deleted, repository automation does
not provide a restore path; recovery depends on whatever backup capability
the operator has configured with the database provider.
The deployed tier, retention policy, backup/snapshot availability, and usable
restore procedure are unknown from source control.
<!-- VERIFY: Operator step — in the Aura console, inspect tier-specific retention and backup/snapshot capabilities, then perform and document a safe restore test before treating provider recovery as available. -->

For the Docker Compose local-dev path: stop the processes, check out the
prior revision, re-run `uv sync --frozen` and `npm ci`, rebuild the
frontend, and restart. If graph data changed, restore a separately
created Neo4j backup. **Do not treat `docker compose down -v` as a rollback
command**: it does not restore an earlier graph, and this Compose file stores
Neo4j data in the `./neo4j_data` bind-mounted host directory.

## Monitoring

### `/health` endpoint

`GET https://api.spoilerless.net/health` returns:

- HTTP 200 `{"status": "ok", "database": "connected", "service": "spoilerless-backend"}` — backend and
  Neo4j are healthy.
- HTTP 503 `{"status": "degraded", "database": "unavailable", "service": "spoilerless-backend"}` —
  backend is running but Neo4j is unreachable.

The `service` field is a **build marker**: current source sets
`SERVICE_NAME = "spoilerless-backend"` (`spoilerless/app/main.py`), while
the pre-rename build reported `hdgrafcehennemi-backend`. A live response of
`hdgrafcehennemi-backend` means an old build is still serving — for example
after a deploy failed on the stale dashboard Start Command described above —
so HTTP 200 alone does **not** prove the newest commit is deployed. Check
the `service` field, or probe a recently added endpoint, to confirm the
build.
<!-- VERIFY: Operator step — curl the live health URL and record the actual `service` field value; `spoilerless-backend` confirms a new build, `hdgrafcehennemi-backend` indicates the old build is still serving. -->

The endpoint is unauthenticated and read-only. The backend verifies
Neo4j connectivity with a lightweight `verify_connection()` call. A
`HEAD /health` variant is also available for uptime monitors.

### External uptime monitor

An UptimeRobot (or equivalent free-tier service) monitor on
`https://api.spoilerless.net/health` with a 5-minute check interval and
email alert on non-200 response or timeout is planned (human-provisioned
— see `docs/ops/runbook.md` §1 for the detection flow). No monitor configuration
is tracked; whether one exists in an external account is unknown.
<!-- VERIFY: Operator step — inspect the monitoring provider for this health URL, interval, timeout/non-200 policy, and alert target; if absent, provision it and record the result without exposing recipient details. -->

### Platform-level monitoring

No custom log drain, alert rule, custom dashboard, Sentry, Datadog, or
OpenTelemetry integration is tracked in this repository. Repository source
does not establish provider log/metric availability,
retention, or alert settings; their current state is unknown.
<!-- VERIFY: Operator step — inspect Render and Vercel for available logs and metrics, their retention periods, and active alerts; record the observed capabilities and settings. -->

The backend includes partial structured logging infrastructure:
- **Request-logging middleware** logs method, path, status, and duration
  for requests whose `call_next` completes, with sensitive headers
  (`X-LLM-*`, `Cookie`, `Set-Cookie`, `Authorization`) redacted. Unhandled
  request exceptions bypass this middleware's log.
- **Exception logging** works in the chat stream handler. The session/share
  sweep's exception branch currently raises `NameError` because it calls
  undefined `logger` instead of the module's `log` logger.
- **Database and LLM error handlers** installed at startup
  (`install_database_error_handlers`, `install_llm_error_handlers`).

### Incident response

See `docs/ops/runbook.md` for the full incident detection, diagnosis ladder,
rollback procedure, and zombie-sweep runbook. Key diagnostic commands
are executable by a future operator without platform dashboard access.

### Local development

- `docker compose ps neo4j` shows the Compose container's status.
- Neo4j logs persist at `./neo4j_logs`; container output via
  `docker compose logs neo4j`.
- The Compose health check probes `http://localhost:7474` every 10
  seconds with a 5-second timeout and 10 retries.

## Branch-protection checklist (operator applies in GitHub UI)

Branch-protection and tag-protection settings are not declared in the
repository. The operator configures them in GitHub repository settings:

1. **Require a pull request before merging** — required approvals: 1,
   dismiss stale reviews: on.
2. **Require status checks to pass before merging** — select the actual
   backend and frontend checks emitted by `.github/workflows/ci.yml` (the
   workflow runs only on pull requests). Require branches up-to-date: on.
3. **Require conversation resolution** before merging.
4. **Do not allow bypassing** the above settings (administrator-included).
5. **Tag protection** (Settings → Tags): protect `release-*` tags —
   restrict creation to maintainers.
6. **Repository → Actions → General:** keep default permissions
   (read-only contents); enable only the workflows present in this repo.

The current `release.yml` does **not** enforce CI status despite its comments;
its gate must be implemented before it can be treated as staged promotion.
Current rulesets, protection settings, review count, bypass policy, tag rules,
and repository-level Actions permissions are unknown from the tracked files.
<!-- VERIFY: Operator step — use GitHub Settings or the repository API to inspect the active ruleset/branch-protection checks, required review count, bypass policy, `release-*` tag rules, and Actions permissions; compare the observed state with this checklist. -->
