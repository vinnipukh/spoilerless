# AGENTS.md — Spoilerless (formerly HD Graf Cehennemi)

> Single-file agent orientation for the Spoilerless repository. Merged and
> verified 2026-09-05 from the in-repo docs tree, `.agents/skills/spoilerless`
> runbook, and live repo artifacts (HEAD `31ed391`). Current-state facts below
> were cross-checked against `pyproject.toml`, `render.yaml`,
> `docker-compose.yml`, `.github/workflows/*.yml`, contract tests, and
> `docs/PROBLEMS.md` passes. Historical pass-by-pass narration lives in
> `docs/PROBLEMS.md`; this file keeps only durable, current rules.
>
> Full archive of every doc concatenated: `hdgraf-giant-knowledge.md`
> (964 KB, 2026-09-05).

## 0. What this project is

Spoiler-safe narrative knowledge-graph workspace ("spoilerless" = spoiler-free).
Prototype content: Dexter Season 1, S01E01–S01E03. Users browse a
source-grounded graph, control a **watch-progress boundary**, add personal
content (notes, custom nodes/relationships), inspect revisions, and
optionally chat with an LLM over only the allowed (already-watched)
subgraph.

- Product name: **Spoilerless**. UI title "Spoilerless". Import root
  `spoilerless/` (rebrand from `backend/` shipped 2026-08-05 — do not
  reintroduce `backend/` paths).
- Import root is `spoilerless/`; backend tests live at `spoilerless/tests/`.
- Remote: `https://github.com/vinnipukh/hdgrafcehennemi.git` (product
  branding `spoilerless`; repo filename keeps the legacy name).
- Live production: Vercel `app.spoilerless.net` + Render
  `api.spoilerless.net` + Neo4j AuraDB Free + Upstash Redis (verified live by
  operator 2026-08-13).

## 1. Repository layout

```text
spoilerless/            FastAPI backend package (app/ + tests/)
  app/api/              route modules (auth, graph, chat, settings, user_content,
                        candidate, revisions, share, series, progress, change-sets)
  app/core/             config (Settings), errors, http
  app/domain/           pydantic models (chat, progress, change_set, ...)
  app/graph/            Neo4j database, seed.py (schema-as-code), candidates.py
  app/llm/              provider abstractions + fallbacks
  app/retrieval/        GraphRAG pipeline + tools
  app/repository/       data-access layer
  app/services/         auth, chat, settings, rate_limit
  app/cache/            redis_client, graph_cache
  app/revisions/        RevisionRepository (revisions module)
frontend/               React + TS + Vite + Cytoscape.js SPA (React 19, Tailwind v4)
  src/components/{graph,detail,episode,chat,layout}
  src/api/              client.ts, chat.ts, progress.ts, ...
  src/lib/              byok.ts, searchIndex.ts, useWatchProgress.ts, ...
data/dexter/            seed JSON (seed/, per-episode subtitles)
ontology/               claim_types.yaml, node_types.yaml, relation_types.yaml
docs/                   canonical documentation (see §10)
.planning/              GSD artifacts (STATE.md, ROADMAP.md, phase dirs) — planning
                        metadata, never a doc source of truth
.agents/skills/spoilerless/   the historical agent runbook (177 references)
scripts/                run_backend_tests.py, env-local.sh, run_doc_verification.py
```

Root `pyproject.toml` is the single Python project (name `spoilerless`,
requires-python `>=3.13`, `.python-version` = 3.13). No build system;
console script `spoilerless-setup` = `spoilerless.app.graph.setup:main`.
Pytest configured via `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`,
`testpaths = ["spoilerless/tests"]`, module-scoped asyncio fixtures.

## 2. Stack (verified from manifests)

- **Backend:** FastAPI `>=0.140.7` (lazy router inclusion — see API doc
  trap §8), pydantic-settings, uvicorn, neo4j driver `>=6.2.0`, google-auth
  `>=2.56.0` (Google ID-token sign-in), redis `>=8.1.0` + fastapi-limiter,
  certifi (AuraDB TLS).
- **Frontend:** React 19, TypeScript, Vite, Tailwind v4 (`@tailwindcss/vite`,
  tokens in `frontend/src/index.css` `@theme inline`), Cytoscape.js +
  cytoscape-fcose, shadcn-style Radix components, vitest + jsdom + fetch-mock.
  **No DaisyUI, no router** (App.tsx is state-driven; route matching on
  `window.location.pathname`).
- **Database:** Neo4j 2026.06.0-community — local docker container
  `spoilerless-neo4j` (`docker-compose.yml`, ports 127.0.0.1:7474/7687,
  `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` — env fallback, never a
  hardcoded password) and production AuraDB Free (credentials in root `.env`
  as `aurausername`/`aurapassword`, instance-id `NEO4J_DATABASE`).
- **CI:** `.github/workflows/ci.yml` — backend job spins its own Neo4j
  container, seeds, runs full pytest, then a **DB-pollution gate** (zero
  `series_scratch*`/`origin='candidate'` residue). Frontend job: node 24,
  `npm ci`, `npm run build`, `npm run lint`, `npm audit --audit-level=high`.
  Triggers on **pull_request only** — pushes to main run no tests.

## 3. Local quickstart (verified commands)

```bash
# 1. Neo4j (docker)
docker compose up -d          # container spoilerless-neo4j

# 2. Root .env — copy .env.example; set NEO4J_PASSWORD=hdgraf-local-password
#    (must match scripts/env-local.sh), GOOGLE_CLIENT_ID + VITE_GOOGLE_CLIENT_ID
#    (same value), ADMIN_EMAILS, AUTH_DEV_CODE (dev login, empty = disabled).
#    VITE_API_BASE_URL must be EMPTY/absent locally (frontend paths already
#    include /api; '/api' in .env produces /api/api/... requests).

# 3. Backend deps + seed
uv sync
uv run python -m spoilerless.app.graph.setup     # idempotent; or uv run spoilerless-setup

# 4. Backend
uv run uvicorn spoilerless.app.main:app --reload --port 8000

# 5. Frontend (separate terminal, frontend/)
cd frontend && npm install && npm run dev        # vite on :5173, proxies /api
```

Docker-local env override for the full suite (AuraDB-safe recipes vary, see
§5): `NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j`.

## 4. Test commands (the #1 time sink — memorize)

- **Backend tests (AuraDB-safe chunk runner):** `uv run python scripts/run_backend_tests.py`
  (10-chunk runner; strips host PYTHONPATH itself; `--list`, `--chunk <name>`).
  NEVER run two pytest processes in parallel against shared live AuraDB —
  residue trips the seed audit.
- **Single/fast backend test:** `uv run pytest spoilerless/tests/test_X.py -v` from repo root.
- **Hermes-shell trap:** the session injects a host `PYTHONPATH` that shadows
  the venv (`ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`).
  Fix: `unset PYTHONPATH` first. Verified clean invocation:
  `unset PYTHONPATH; export PATH="$PWD/.venv/Scripts:$PATH"; pytest <focused> -q`.
  Diagnose interpreter/path choice with `uv run python -c "import sys; print(sys.executable); print(sys.path)"`.
- **pytest invocation traps (verified 08-13):** no `pytest-timeout` in venv —
  drop `--timeout=` flags (usage error EXIT=2). `-k` must be its own argv
  entry — a single quoted `"file.py -k 'a or b'"` is parsed as ONE file path
  (collection error EXIT=4); bare `-k` applies to ALL files in the run.
- **Frontend tests:** `cd frontend && NODE_ENV=test CI=1 npm run test`.
  ALWAYS prefix `NODE_ENV=test` (or `CI=1`) — if `NODE_ENV=production` is set
  in the shell, React loads production builds, `React.act` is undefined, tests
  fail with empty renders.
- **Frontend typecheck = `npm run build`** (`tsc -b && vite build`) — plain
  `tsc --noEmit` SKIPS referenced projects, so test-file type errors pass
  locally and red the Vercel deploy (observed: TS18048, TS18047/TS2339,
  TS2353 — only `npm run build` catches them). After ANY frontend-touching
  executor return, run `npm run build` yourself before closing the plan.
- **Docs link & anchor check:** `python .agents/skills/spoilerless/scripts/check-doc-links.py`.
- **Seed idempotency check:** run setup twice — both runs identical counts
  (49 nodes, 32 relationships).

## 5. Live-DB test discipline (non-negotiable)

- **No DB mocking layer.** Backend tests are integration tests against a live
  seeded Neo4j. Test-created nodes pollute other files' integrity audits.
- **Shared-live-AuraDB rules:** sequential per-module buckets only; never
  parallel pytest; full suite ≈ 75+ min on AuraDB (docker-local much faster).
  For a frontend-only change prove `git diff --name-only <base>..HEAD -- spoilerless/` = 0
  first — pytest can't be affected, don't run it.
- **Never touch real dev user rows** (dev user id
  `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`).
- **`:AppSetting`/`:Session` test writes MUST backup→restore, never
  delete-and-let-user-redo** (a 2026-08-01 incident wiped the stored LLM key:
  chat regressed to `LLM_DISABLED`). Fixture backs up the pre-existing node's
  `value` via a fresh driver, restores in teardown; delete only when no node
  existed before.
- **Scratch series for candidate tests** (conftest constants
  `CANDIDATE_SCRATCH_SERIES = "series_scratch_candidates"`,
  `REVIEW_SCRATCH_SERIES = "series_scratch_review"`): must bootstrap
  Series + Episode nodes (persisted-episode boundary check 422s bare ids);
  teardown triad = series-scoped delete + `MATCH (n) WHERE n.origin='candidate'
  DETACH DELETE n` + delete `UserSeriesProgress` rows. try/finally, module
  scope, fresh driver/loop via `asyncio.run` (never the app's portal-loop
  driver inside sync TestClient tests).
- **Seed-integrity audit** fails on any node under the seeded series with null
  `visible_from_order`. `:ChangeSet` is the same class (orphaned ChangeSets
  trip `test_seed_idempotency` constraint asserts) — `AND NOT node:ChangeSet`
  or sweep orphans. `UserSeriesProgress`/`ChatSession`/`ChatMessage` are the
  documented exclusions.
- **Full-suite HANG after aborted pytest runs:** reseed (`setup_database()` —
  idempotent, preserves `origin='user'` layer AND `:AppSetting`) before rerun;
  never debug a hang in a file that passes in isolation first.
- **Sync-vs-async loop rule:** TestClient's app driver is bound to the portal
  loop. NEVER touch that driver from another loop (`'NoneType' send` crash).
  Teardown cleanup = FRESH `Neo4jDatabase()` inside `asyncio.run(_cleanup())`.
- **Async tests + async `database` fixture** (e.g. test_retrieval_tools.py)
  share one event loop → same-driver cleanup safe there.
- **Stored llm settings flip env-based tests:** once `:AppSetting {key:'llm'}`
  exists with `enabled:true`, `get_llm_provider` resolves stored>env —
  `test_disabled_provider_returns_503_never_401` then fails `200 == 503`
  against live DB. Expected contamination once settings are configured.
- **Ad-hoc scripts using in-app `Neo4jDatabase` need** BOTH
  `PYTHONPATH=<repo root>` AND `db.open()` + `await db.verify_connection()`
  before `execute_query` (else `RuntimeError: Neo4j driver has not been
  initialized`).
- **Stub databases match query CONTENT markers, not constant names**
  (constant names never appear in Cypher text): use `$entity_id`, `$frontier`,
  `$node_ids`, `SUPPORTED_BY`, `REFERS_TO`, `"note.user_id = $user_id"`, etc.
  Watch fragment collisions (USER_NOTES_QUERY and SOURCES_FOR_CLAIMS_QUERY
  both contain `REFERS_TO`). Canned rows must mirror real RETURN shapes.

## 6. Neo4j schema & query facts

- Story node labels: `Character|Event|Location|Organization|Object` +
  `Series`, `Episode {episode_order, code, visible_from_order}`,
  `Claim {subject_id, predicate, object_id, valid_from/until_order, source_id,
  claim_type}`, `EvidenceFragment {text, locator, source_id}`,
  `Source {source_type, locator}`, `UserNote {target_type, target_id, content,
  origin:'user'}` (via `-[:REFERS_TO]->`), **`AppUser` — NOT `User`**,
  `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `AppSetting {key}`,
  `Session` (via `(:AppUser)-[:HAS_SESSION]->(:Session)`).
- Story nodes carry `series_id`, `visible_from_order`, `origin`
  (canonical|candidate|user). Seeded `Source`/`EvidenceFragment` nodes also
  carry `series_id`.
- **Graph edges are PROJECTED from Claim nodes** (`{claim.id}:edge`) — no
  direct character-character relationships in the DB. Pathfinding walks Claim
  nodes (subject/object pairs), BFS via `CLAIMS_FOR_FRONTIER_QUERY`.
- Core visibility predicate: `visible_from_order IS NOT NULL AND
  visible_from_order <= $visible_until_order` — compose via
  `spoilerless/app/spoiler/filter.py`, don't add a new rule. NOT universal:
  verify each read query before blanket spoiler-safety claims.
- Cypher pitfalls:
  1. `execute_query(query, **parameters)` — never name a bound param `query`
     (`TypeError: got multiple values for argument 'query'`).
  2. `(:User)` silently matches zero rows — schema uses `(:AppUser)`.
  3. Neo4j driver 6.x on Windows + AuraDB: `neo4j+s://` needs the
     `TrustCustomCAs(certifi.where())` normalization in `database.py`;
     standalone scripts must pass the same config to `AsyncGraphDatabase.driver`.
  4. `zombie_sweep.py` driver config: pass `encrypted`/`trust` ONLY for
     `neo4j+s://` URIs (plain bolt + `trust=None` → ConfigurationError).
- **Schema-as-code:** `spoilerless/app/graph/seed.py` runs CREATE
  CONSTRAINT/INDEX; `test_seed_idempotency` asserts an EXACT constraint set —
  additive-only changes, and never a uniqueness constraint on `:AppSetting.key`
  (breaks the exact-set + id-coverage invariants; AppSetting persists via
  plain MERGE on `key`).
- Setup startup check: `_check_visibility_schema` (non-null
  `visible_from_order` for seeded nodes under `series_dexter`). There is
  **no** `_check_episode_schema` — docs must not claim it exists.
- Seed drift fact (don't re-derive): enriched S01E01 seed moved
  `harry_morgan` to `visible_from_order: 1`. Genuinely-hidden-at-1 characters
  today: `paul_bennett` (vfo=2), `rudy_cooper` (vfo=3). Write drift-agnostic
  assertions (idempotent re-run equality, fixture-derived supersets,
  constraint-label supersets), never exact-hidden-probe assumptions on Harry.

## 7. Backend architecture & API facts

- **Import root `spoilerless`**, app factory `spoilerless.app.main:app`.
  `/health` reports `{status, database, service}`; the `service` field is the
  deploy build marker (`hdgrafcehennemi-backend` = OLD pre-rebrand build,
  `spoilerless-backend` = current). Health 200 does NOT prove the latest
  deploy landed — check the service field.
- **API surface (verified against contract tests, 2026-09-05):** 52
  operations / **39 path templates** — locked green by
  `test_frontend_contract_doc.py` + `test_openapi_contract.py` (asserts
  `len(EXPECTED_TEMPLATES) == 39`, `len(schema["paths"]) == 39`). Any route
  addition must update BOTH tests + `docs/reference/frontend-api-contract.md`
  + `docs/API.md`. OpenAPI ground truth: `app.openapi()` — never walk
  `app.routes` (FastAPI 0.140+ lazy `include_router` yields placeholder
  objects; schema-visible = 50 ops + hidden `HEAD /health`
  `include_in_schema=False` = 51 raw… do not "fix" one count into the other).
- **Auth:** Google ID-token sign-in (`POST /api/auth/google`), HttpOnly
  session cookie, `CurrentUserDependency` gating all user-content/candidate/
  revision WRITE paths. Dev login `POST /api/auth/dev` with `AUTH_DEV_CODE`
  (empty env = disabled → 403). Visitor (misafir) read-only mode is a
  FRONTEND-ONLY state (`AuthState.status:'visitor'`, sessionStorage flag
  `spoilerless.visitor`); all GET routes stay anonymous.
- **Owner-scoping house pattern (09-03+):** cross-owner mutation → 403
  `forbidden`; `origin != 'user'` → 409 `resource_conflict`; missing → 404.
  Cypher owner scope: `AND ($is_admin = true OR resource.user_id = $user_id)`.
  Legacy records with no stored `user_id` → admin-only (fail-closed).
- **Error codes:** uppercase snake convention, catalog in
  `spoilerless/app/core/errors.py` (`_ERROR_SPECS` statuses:
  401/403/404/409/422/429/503). A route whose `responses=` uses an unlisted
  status crashes at import (`ValueError: Unsupported shared error response
  status`) — add to catalog first. Registry membership ≠ emission: verify a
  code has a live raise/handler site before documenting it.
- **LLM / chat:** `services/chat.py` answer_stream (SSE), provider resolution
  stored>env per field (`GeminiProvider` base
  `https://generativelanguage.googleapis.com`; `OpenAICompatibleProvider`
  covers openai_compatible/vllm/ollama). Stored LLM config = single
  `:AppSetting {key:'llm'}` node, JSON value payload incl. `enabled` bool +
  `system_prompt_language: english|turkish`. Settings API:
  `GET/PUT /api/settings/llm` — key write-only, responses expose
  `api_key_masked` ("••••last4") + `api_key_configured`; PUT null/"" keeps the
  stored key. BYOK (frontend `lib/byok.ts`, localStorage
  `hdgraf:byok-llm-settings`) spreads X-LLM-Api-Key/X-LLM-Provider/
  X-LLM-Base-URL/X-LLM-Model headers per request.
- **Retrieval pipeline** (`spoilerless/app/retrieval/`): 9-section context
  assembly, dedupe by stable id, `distance` hop prioritization, char-bound by
  Python `len()`. Eleven keyword-only read tools (server-injected
  `series_id`/`visible_until_order`) + model-visible `propose_changeset`
  (validates typed ops, persists only `awaiting_confirmation` draft via
  `ChangeSetService.propose`). Ceilings: `MAX_PATH_HOPS=4`,
  `MAX_TRAVERSAL_DEPTH=3`, `MAX_SEARCH_RESULTS=25`, `MAX_RESULT_LIMIT=50`.
  No tool accepts raw Cypher. Citation validation: against THIS turn's
  retrieved set only — never a fresh DB existence check.
- **Boundary semantics (12-02):** positive unpersisted `visible_until_order`
  CLAMPS via resolver (200/404); only malformed values stay 422.
- **Redis (optional, prod):** `spoilerless/app/cache/` — cache-aside graph
  cache (`graph:{series_id}:{effective_boundary}:{user_id|'anon'}`, boundary in
  key ⇒ auto-miss) + fastapi-limiter rate limiter, active only when
  `REDIS_URL` set. Graph cache fail-open; rate limiter fail-closed since
  Phase 11 (503 `rate_limit_unavailable`). Invalidate AFTER the write commit
  (`result = await ...; await invalidate_series(...); return result`) — never
  in `finally`.
- **Phase 11 hardening (closed 2026-08-20):** anonymous boundary clamps,
  trusted-proxy per-IP limiter with allowlist, LLM cost bounds (semaphore +
  tool cap), BYOK/stored SSRF blocklists, output guard, body-size 413,
  docs-off-in-prod, CSP, sanitized validation logs, TrustedHostMiddleware,
  ingest rate-limit + cache invalidation, revert label allowlist + ownership
  fail-closed, ChangeSet revert admin-gated.
- **Known open items (see docs/PROBLEMS.md "Still open" + Phase 12 plans):**
  THERMO-P0-01 `NoteResponse`/`CustomNodeResponse` mandatory `user_id` 500 on
  anonymous reads (plan 12-01); read-boundary unification; shared LLM
  settings scoping (per-user, at-rest encryption); god-file decomposition
  (#79); no migration framework (#19); operator: push ~40 local commits to
  origin/main (#29), least-privilege DB user (#36).

## 8. Frontend facts & design system

- **Design tokens ONLY in `frontend/src/index.css`** (`@theme inline`):
  background `#0F172A`, card `#192134`, accent `#7C3AED`, primary `#4338CA`,
  destructive `#DC2626`, warning `#F59E0B`, elevated `#1E2740`. Fonts
  self-hosted Space Grotesk (--font-heading) + Inter (--font-sans). No new
  fonts/colors ever. 44px min touch targets, 4px spacing scale.
- **NO DaisyUI, NO plain `btn`/`select` classes** — Tailwind tokens +
  `[color-scheme:dark]` on selects; buttons use inline Tailwind. Components
  under `src/components/{graph,detail,episode,chat,layout}`. Shared nav
  contract: `HeaderNavAction` (icon/label/ariaLabel/active/onClick, icons
  forced 16px `[&_svg]:size-4`, label `hidden md:inline`).
- **GraphCanvas** is the god-file (~900 lines; D-06 says extract — don't pile
  on). Overview/Full modes: Overview hides Story/Characters/Evidence/Advanced
  nav; Full exposes them. fcose layout via `layoutOptionsFor(mode)` in
  `layoutConfig.ts`. Overview/Full regression matrix lives in the repo
  runbook; keep topology-aware Cytoscape reconciliation in Full mode.
  Cluster box `node[isCluster]`: NON-INTERACTIVE dashed outline, `events:'no'`
  (NOT `pointer-events` — TS2353). Pictureless nodes with <3 edges get
  `simple:true` → 13px dot + 9px gray label.
- **Radix `Tooltip` must be used within `TooltipProvider`** — a component
  adding a Tooltip must SELF-WRAP its subtree (GraphCanvas pattern at :531);
  the error in tests = production crash bug, not a harness quirk.
  `ToggleGroup` items expose `role="radio"` not `button`.
- **Radix `Select` trigger min-h-11; `role="switch"` for the LLM enable
  toggle.** Settings page: `view: 'graph' | 'settings'` state in App.tsx (no
  router); topBar gear `aria-label` must flip (Settings ↔ Back to graph).
- **API client:** every request prefixed with `VITE_API_BASE_URL` (client.ts
  + chat.ts streaming). Paths already start `/api` → local `.env` value must
  be empty/absent (else `/api/api/...`); deployed = full origin
  (`https://api.spoilerless.net`). Google GIS loads
  `https://accounts.google.com/gsi/client` — keep in any CSP.
- **Vitest traps:** `localStorage.clear()` in beforeEach (jsdom persists
  across tests in a file); hoist fetch-mock helpers to module scope
  (describe-scoped invisible to siblings); compute expected URLs with the
  same `VITE_API_BASE_URL ?? ''` expression as source; `NODE_ENV=test CI=1`
  prefix mandatory. FE suite: 44 test files. Typecheck: `npm run build`
  (see §4). Lint: `npm run lint`.
- **App.tsx fetch-stub convention:** unknown URLs → `notFoundResponse()`;
  `graphFetchCalls()` filters `.includes('/graph')`; use named-role queries
  only. `useWatchProgress`: hydration race guard via `userInteractedRef`
  (`if (cancelled || userInteractedRef.current) return`).

## 9. Deploy / ops (verified against render.yaml + docs/DEPLOYMENT.md)

- **Render backend** (`render.yaml`, service name `spoilerless-api`,
  dashboard service may read "spoilerless"): free web service, auto-deploy on
  push to connected branch. Build `uv sync --frozen`; start command MUST be
  the uvicorn form targeting `spoilerless.app.main:app`
  (`uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT
  --proxy-headers --forwarded-allow-ips "<render proxy CIDRs>"`). A stale
  `backend.app.main:app` override breaks every deploy while the live service
  keeps serving the last good build — probe `/health` and check the
  `service` field (`hdgrafcehennemi-backend` = old build,
  `spoilerless-backend` = current). No RENDER_API_KEY exists in repo/.env —
  dashboard changes are operator-touch via the Render dashboard/API.
- **Render env vars (all four `NEO4J_*` REQUIRED):** missing `NEO4J_URI`
  crashes uvicorn at import. `ALLOWED_EMAILS=()` literal parens = non-empty
  allowlist `{'()'}` → EVERY login rejected — set the operator email or leave
  empty/absent. `ALLOWED_HOSTS` must include `*.onrender.com` +
  `api.spoilerless.net` (TrustedHostMiddleware, Phase 11).
- **Neo4j AuraDB Free:** single credential from the downloaded credentials
  file (`NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io`, `NEO4J_USERNAME=<dbid>`,
  `NEO4J_DATABASE=<dbid>` — NOT `neo4j`). No CREATE USER/ROLE on Free tier
  (console roles are human access; `SHOW CURRENT USER` = UUID
  `console_admin_free_*` for tool-auth). Driver 6.x Windows TLS fix in
  `database.py` (`neo4j+s://`→`neo4j://` + encrypted + TrustCustomCAs
  certifi).
- **Vercel frontend** (`frontend/vercel.json` SPA rewrites): Root Directory
  `frontend/`; `VITE_*` build-time (Production + Preview). Google OAuth
  client needs `https://app.spoilerless.net` in JS origins + redirect URIs
  (else `redirect_uri_mismatch`).
- **Cloudflare:** `api.` subdomain MUST be DNS-only (grey cloud) — proxy idle
  timeout kills long SSE chat streams; `app.` proxied is fine. Apex redirect
  via proxied `@` record (placeholder `192.0.2.1`) + dynamic 301 rule to
  `app.spoilerless.net`.
- **GitHub Pages:** legacy Jekyll root build (`vinnipukh.github.io/
  hdgrafcehennemi`) — unrelated to Vercel. `ci.yml` fires on PR only, so a red
  X on a pushed commit = Pages deploy failure, not CI. Transient
  `upload-pages-artifact` 404 after successful upload = infra flake: rerun.
- **Login rejection reads:** "This account is not authorized" = allowlist
  rejection (`EmailNotAllowedError` 403) NOT OAuth config; `redirect_uri_mismatch`
  = OAuth client origins missing.
- **Diagnosis ladder for "chat is dead":** three live-DB counts —
  `MATCH (s:ChatSession) RETURN count(s)`, `MATCH (p:UserSeriesProgress)
  RETURN count(p)`, `MATCH (s:AppSetting {key:'llm'}) RETURN s.value` —
  identify the wall (session-create 422 / progress-404 / LLM-disabled).
- **Windows/MSYS quirks that cost time:** terminal `PYTHONPATH` shadows venv
  (unset it); git-bash `/tmp` invisible to Windows python (use
  `$LOCALAPPDATA/Temp` or repo-local files); killing backgrounded bash suites
  ORPHANS python children (check tasklist, never Stop-Process by bare PID —
  confirm CommandLine matches pytest first; the Hermes desktop itself runs as
  python.exe); orphaned vite/uvicorn children survive `process kill` (find via
  `netstat -ano | grep LISTEN`, kill with PowerShell Stop-Process — git-bash
  taskkill `//F //PID` fails); background long suites: redirect to a log file,
  NEVER `| tail` (silent zombie wrappers).

## 10. Docs conventions & repo process

- **docs/ structure** (2026-08-12 restructure, commit `5cb6451`): canonical
  uppercase docs stay at docs root (API, ARCHITECTURE, CONFIGURATION,
  DEPLOYMENT, DEVELOPMENT, GETTING-STARTED, PROBLEMS, README, ROADMAP,
  TESTING) + lifecycle groups: `architecture/` (project-spec,
  spoiler-threat-model, spoiler-terminology, spoiler-deferred-design,
  decision-logs/), `reference/` (frontend-api-contract, backend-modules,
  frontend-components, security-attack-surface, security-test-plan),
  `ops/` (runbook), `ideas/`, `uat/`. **Thematic kebab names only, NEVER
  versioned filenames** (user rule).
- **`docs/PROBLEMS.md` is the canonical problem ledger** — append numbered
  passes with dated headers; never rewrite history. Its "Still open" section
  = live open-work list. Per-change noise goes to PROBLEMS.md, not decision
  records.
- **Stability classes:** test-locked (frontend-api-contract.md, API.md —
  never hand-edit counts; regenerate from `app.openapi()`), decision records
  (architecture/* — changed only when the decision changes), snapshots
  (backend-modules.md, frontend-components.md — dated, verify before
  trusting), living process (runbook, DEPLOYMENT, PROBLEMS, ROADMAP).
- **Doc updates = supplement-and-refresh** (user preference): preserve
  accurate sections, surgically refresh stale commands/paths/symbols/counts.
  Verify claims with file:line evidence; assertions must quote observed
  content exactly. Counts drift — recount from live code, never propagate an
  older total (API.md was 247/247 claims-verified 2026-08-14).
- **Roadmap:** `docs/ROADMAP.md` canonical (root ROADMAP.md = 7-line stub;
  `.planning/ROADMAP.md` is the separate GSD artifact). Milestones: v1.1
  (graph foundation + polished Cytoscape), v1.3 (four-view visualization
  hierarchy + deployment), v1.5 (Phase 12 remediation of thermo-nuclear
  audit findings 12-01..12-06).
- **GSD workflow** (if resumed): single checkout, feature branches per phase;
  never commit `.planning/config.json`; stage explicit paths; commit RED
  (`test(06-02): ...`) → GREEN (`feat...`) → docs; user expects finished small
  changes COMMITTED + PUSHED immediately, confirm `git log --oneline -1
  origin/main`. Executors die at provider 429/503 caps — verify git state
  after each return, never trust child summaries; for plans > ~50 tool calls
  split into two half-dispatches.
- **Pre-existing-reds proof:** `git stash push -- <paths>` → run failing
  files → pop; committed-state RED proof:
  `git show HEAD~1:frontend/src/App.tsx > frontend/src/App.tsx` → run the new
  test (expect RED) → `git checkout -- <path>`.
