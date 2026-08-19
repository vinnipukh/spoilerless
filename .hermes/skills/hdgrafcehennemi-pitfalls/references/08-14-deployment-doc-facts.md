# 08-14 deployment-doc facts — verified during docs/DEPLOYMENT.md update

Verified 2026-08-14 (gsd-doc-writer, update mode). Trust these over any task
brief. Siblings: `08-12-doc-update-facts.md` (DEVELOPMENT.md era),
`08-14-architecture-doc-facts.md`, `08-14-testing-doc-facts.md`.

## Deploy config (verbatim, re-verified this pass)
- `render.yaml`: service `name: spoilerless-api` (NOT `spoilerless`, NOT
  `hdgrafcehennemi-api`), `buildCommand: uv sync --frozen`,
  `startCommand: uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`,
  free plan, `autoDeploy: true`, **no `envVars:` block**.
- `frontend/vercel.json` (root has NO vercel.json): SPA catch-all
  `{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`.
- `docker-compose.yml`: `neo4j:2026.06.0-community`, container
  `spoilerless-neo4j`, `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` (env
  fallback, NOT hardcoded), ports `127.0.0.1:7474/7687` only.
- `.github/workflows/`: only `ci.yml` (pull_request gate: backend pytest +
  DB-pollution gate + frontend build/lint/audit) and `release.yml`
  (skeleton: echo-only CI gate, `contents: read` — cannot push tags).
- No `Dockerfile`/`.dockerignore`; no `RENDER_API_KEY` anywhere (repo + root
  `.env`); no sentry/otel/datadog/newrelic in pyproject.toml or
  frontend/package.json → DEPLOYMENT.md correctly says "No monitoring
  integration tracked".

## Backend facts (re-verified this pass)
- `SERVICE_NAME = "spoilerless-backend"` (`spoilerless/app/main.py:38`);
  `/health` GET returns 200 `{status:"ok", database:"connected",
  service:"spoilerless-backend"}` or 503 `{status:"degraded",
  database:"unavailable", ...}`; `HEAD /health` variant exists (main.py:222-249).
- config.py: `AliasChoices("aura_uri","neo4j_uri")` etc. — aura_* wins when
  both present; `NEO4J_DATABASE` default `neo4j`; `SESSION_COOKIE_SECURE=True`,
  `SESSION_COOKIE_SAMESITE="lax"`, `SESSION_TTL_SECONDS=604800`,
  `FRONTEND_ORIGINS` default `http://localhost:5173`, `REDIS_URL` default `""`.
- Rate limits (`services/rate_limit.py`): login 10/300s per IP, chat-send
  20/60s per user, content-write 30/60s per user-or-IP.
- Graph cache (`cache/graph_cache.py`): `DEFAULT_GRAPH_TTL_SECONDS = 300`;
  `invalidate_series` call sites in candidates.py, change_set.py,
  user_content.py only — revisions.py still omits it (known bug, live).
- LLM settings: resolution order BYOK `X-LLM-*` headers → Neo4j
  `:AppSetting {key:'llm'}` (admin-managed GET/PUT `/api/settings/llm`) →
  env vars as FALLBACK. `LLM_PROVIDER` supports `openai_compatible` (default)
  and `gemini`. `.env.example` does NOT ship ALLOWED_EMAILS/ADMIN_EMAILS/
  REDIS_URL/SESSION_COOKIE_SAMESITE/LLM_FALLBACK_*.
- pyproject.toml has NO `[build-system]` → `spoilerless-setup` console script
  is NOT installed by `uv sync` (no executable in .venv); seeding via module
  command. `uv run --project spoilerless python -m spoilerless.app.graph.setup`
  works (uv resolves the root project; ci.yml uses it verbatim).

## Drift traps fixed in DEPLOYMENT.md this pass
1. **Sweep `logger` NameError claim REMOVED (bug fixed in code)** — see
   `doc-claim-verification.md` §6. Docs must not re-assert it.
2. **UptimeRobot "live since Phase 8 UAT #11" was stale**: `docs/ops/runbook.md`
   §1 (newer ops record) says "PLANNED, NOT yet configured"; no phase-8 UAT
   file exists (`docs/uat/` has only phase-10-golden-path.md). Rule: when doc
   sections conflict on operator state, `docs/ops/runbook.md` is the
   authoritative ops record — phrase as planned/unknown + VERIFY markers.
3. **Intro said "service `spoilerless`"** but render.yaml says
   `spoilerless-api`; the UAT record never mentions the service name → align
   any service-name citation sitting next to render.yaml build/start commands
   with render.yaml's `name:` field verbatim.
4. **VERIFY marker count**: on-disk DEPLOYMENT.md = 14 (reference said 13;
   v1.3/10-11 update added one). Count on disk, report final count.

## Update-mode workflow that worked (deployment docs)
Read full doc → verify platform configs verbatim (render.yaml, vercel.json,
compose) → config.py defaults → main.py health/SERVICE_NAME → workflows →
absence claims (`ls Dockerfile .dockerignore`, `grep RENDER_API_KEY`) →
re-check EVERY known-bug claim in code (fixes land silently) → cross-check
operator records (runbook.md, ROADMAP.md, docs/uat/) for conflicting claims →
apply targeted `patch` edits (NOT full-file Write; 570-line docs are safer
surgically) → final grep sweep for stale strings + `grep -c 'VERIFY:'` +
`wc -l`. Note: `search_files` mangles Windows paths (os error 3) — use
terminal grep/read_file instead.

## Verifier pass (re-verify mode, 08-14) — 101/101 PASS
Result JSON: `.planning/tmp/verify-DEPLOYMENT.md.json` (101 checked, 101 passed,
0 failed; contract re-validated by re-parse). All facts above re-confirmed;
known-bug revisions.py still has 0 `invalidate_series` hits; on-disk
`grep -c 'VERIFY:'` = 14. New traps from this pass:
- **Route-location trap**: `GET /api/series/{series_id}/graph` lives in
  `api/graph.py` (APIRouter prefix `/api/series`), NOT `api/series.py` (which has
  only `''`, `/{series_id}`, `/{series_id}/episodes`). `GET/PUT /api/settings/llm`
  lives in `api/settings.py` (prefix `/api/settings`, paths `/llm`). auth routes:
  `post /google`, `get /me`, `post /logout`. Grep the api/ dir for the path string
  before concluding a route module is missing.
- **config.py field-name grep trap**: settings fields are snake_case
  (`session_cookie_name`, `neo4j_uri`), NOT the UPPER env names — a regex for
  `SESSION_COOKIE_NAME` returns ABSENT. Search snake_case field names or just
  read `spoilerless/app/core/config.py` directly (170 lines).
- **OPS-02** (uptime monitor) is traceable in `docs/ROADMAP.md`, not
  runbook.md/PROBLEMS.md; runbook §1 says "PLANNED, NOT yet configured".
- **uat/phase-10-golden-path.md contains NO `/health` or `service` mentions**
  (local-stack golden-path checklist) — the intro's "operator evidence" claim
  passes on file existence + operator-verified framing + Monitoring VERIFY
  markers, NOT on file content.
- **CSRF mechanism**: `api/deps.py` `verify_origin` fail-closed 403
  `AUTH_ORIGIN_NOT_ALLOWED` on missing Origin/Referer; exported as
  `CsrfGuardDependency` used by `post /google` + `post /logout`; `FRONTEND_ORIGINS`
  drives BOTH CORS `allow_origins` and the CSRF check.
