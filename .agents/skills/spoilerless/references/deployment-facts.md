# Deployment facts (verified 2026-08-12 during docs/DEPLOYMENT.md update)

All claims below verified against current source + git history. Use for
DEPLOYMENT.md updates, Render deploy debugging, and /health diagnosis.

## /health = build marker (the trap)
- `GET /health` and `HEAD /health` exist (`spoilerless/app/main.py`,
  `HealthResponse` with `extra="forbid"`). Shapes:
  - 200 `{"status":"ok","database":"connected","service":"spoilerless-backend"}`
  - 503 `{"status":"degraded","database":"unavailable","service":"spoilerless-backend"}`
- `service` field = `SERVICE_NAME` constant = **build marker**: pre-rename
  builds reported `hdgrafcehennemi-backend`; current source reports
  `spoilerless-backend` (rename commit `b94ac6f`).
- HTTP 200 does NOT prove the newest commit is deployed: if a Render deploy
  fails (e.g. stale Start Command), the previous successful build keeps
  serving and `/health` keeps returning 200. Check the `service` field, or
  probe a recently added endpoint, to confirm the build.

## Render Start Command override trap
- `render.yaml` (Blueprint) is correct: buildCommand `uv sync --frozen`,
  startCommand `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`,
  free plan, autoDeploy true, service name `spoilerless-api`. No envVars block.
- A dashboard override left from the pre-rename layout
  (`uv run uvicorn backend.app.main:app ...`) → `ModuleNotFoundError:
  No module named 'backend'` on every deploy; the old build keeps serving.
  Fix is **operator-touch**: Render dashboard Settings → Start Command, or
  delete/recreate the service from the Blueprint. No `RENDER_API_KEY`
  exists in repo or root `.env` → no repo-side automation possible.
  See `docs/BACKEND_DEPLOY_FIX.md`.

## Config loading
- `Settings` (`spoilerless/app/core/config.py`) uses `env_file=".env"`
  resolved against the **process CWD** — root `.env` only, no per-env
  split files; Render must start from repo root.
- Env aliases: `aura_uri/aura_username/aura_password/aura_database` (local
  `.env` convention) vs `NEO4J_*` names (deployed). `aura_*` wins when both
  are present. `NEO4J_DATABASE` defaults to `neo4j` — the docker-local name —
  so set the real Aura database name in production.
- `verify_google_client_id_equality` fails startup ONLY when both
  `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` are set and differ.
- `REDIS_URL` empty → rate limiting + graph cache disabled at runtime
  (no crash); `init_rate_limiter()` binds during lifespan.

## Infra facts
- `docker-compose.yml`: `neo4j:2026.06.0-community`, ports 7474/7687 bound
  to **127.0.0.1 only**, `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}`,
  healthcheck wget-spider on localhost:7474 (interval 10s / timeout 5s /
  retries 10), data in `./neo4j_data` bind mount. Local dev only — not a
  production path.
- Rate limits (`services/rate_limit.py`): login 10 / 5 min per IP,
  chat-send 20 / min per user, content-write 30 / min per user-or-IP.
- Graph cache (`cache/graph_cache.py`): 300s TTL, key
  `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`;
  `invalidate_series()` is called in candidates / change_set /
  user_content routes but NOT in revisions revert (stale until TTL).
- `ci.yml`: backend job seeds its service container via
  `uv run --project spoilerless python -m spoilerless.app.graph.setup`,
  setup-uv pinned v8.1.0 (SHA), DB-pollution gate, upload-artifact on
  failure; frontend job Node 24 + npm ci/build (`tsc -b && vite build`)/lint/audit.
- `release.yml`: skeleton only — `verify-ci-gate` echoes text (no checks
  API query), workflow `permissions: contents: read` → tag push not
  authorized.
- Versions: `.python-version` = 3.13, pyproject `requires-python >=3.13`;
  jsdom engines `^22.22.2 || ^24.15.0 || >=26.0.0` (CI uses Node 24);
  frontend VITE_API_BASE_URL consumed via `import.meta.env.VITE_API_BASE_URL ?? ''`
  (`frontend/src/api/{client,chat,export}.ts`); vite `envDir: '..'`,
  dev proxy `/api` → `http://127.0.0.1:8000`.

## Verification techniques used
- Build-marker archaeology: `git log -S "hdgrafcehennemi-backend" --all`
  locates the rename commit; `git show <sha>` shows exact old/new values.
- Inspect `.env` key names without leaking values:
  `grep -oE '^[A-Z_0-9]+' .env`; prove a variable's absence repo-wide with
  `grep -rIn "RENDER_API_KEY" . --include=*.yaml --include=*.yml ...`
  (exclude node_modules/.venv).
- Multiple same-file edits: batch sequential `patch()` calls in ONE
  execute_code script (each returns its own diff) — safer than a single
  V4A multi-hunk patch, single round-trip, order-controlled.
