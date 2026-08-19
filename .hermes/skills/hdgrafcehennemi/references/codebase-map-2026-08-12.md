# Codebase-map facts verified 2026-08-12 (HEAD 1710d57)

Refresh of `.planning/codebase/{STACK,INTEGRATIONS,ARCHITECTURE,STRUCTURE}.md`
against live code. Map commit was `0b4c83c` (08-02); 239 commits of drift.
Every fact below was verified by grep/find/wc/uv.lock/package-lock/openapi probe.

## Renames / entry points
- CLI entry point: `spoilerless-setup` (was `hdgraf-setup`). `[project.scripts]`
  lives in the ROOT `pyproject.toml` → run `uv run spoilerless-setup`, never
  `--project`. `hdgraf-setup` appears nowhere outside `.planning/` + `docs/`.
- Package name in pyproject: `spoilerless`; testpaths `spoilerless/tests`.
- No `backend/` references remain in `spoilerless/` source.

## New subpackages / modules since 08-02 map
- `app/cache/` — `redis_client.py` (ONE shared `redis.asyncio` singleton,
  lru_cache, Upstash `rediss://` from `REDIS_URL`; empty URL disables all
  Redis features) + `graph_cache.py` (cache-aside for GET graph, keys
  `graph:{series}:{boundary}:{user}`; any Redis error degrades to Neo4j).
- `app/core/tokens.py` — `hash_token()` / `generate_token()`.
- `app/graph/labels.py` — `NODE_LABELS` / `STORY_LABELS` inventory (PROB-09/#81).
- `app/spoiler/policy.py` — `effective_view_order` etc. (owner of boundary
  formula); `app/spoiler/visibility.py` — `derive_visible_from_order` (ONE rule).
- `app/retrieval/context.py` — `CONTEXT_SECTIONS` / `CONTEXT_DELIMITERS` registry.
- `app/services/rate_limit.py` — fastapi-limiter 0.2.0 / pyrate-limiter
  RedisBucket; `login_rate_limiter`, `chat_send_rate_limiter`,
  `content_write_rate_limiter`; bound at startup via `init_rate_limiter()`.
- `app/api/share.py` + `app/repository/share.py` + `app/domain/share.py` —
  token-based read-only share links (create/get/list/revoke, hash-stored,
  `sweep_expired()`); `ShareToken` DOES get explicit uniqueness constraints +
  expiry index in `seed.py`.
- `app/graph/change_set.py:46` — `WITH u, s` between MERGEs (local 5.x 503 fix).
- `app/repository/change_set.py:734` — table-driven `_APPLY_SPECS` dispatch.

## Refactor verification anchors (grep these before claiming the refactor)
- `TOOL_SPECS: list[ToolSpec]` at `retrieval/pipeline.py:427` — TWELVE tools
  (incl. `propose_changeset`); `_walk_visible_claims` shared BFS in tools.py:330.
- `visible_claim_where()` / `claim_projection()` in `spoiler/filter.py:4/22`.
- `neo4j_row_to_python` + `run_single` — both in `graph/database.py:16/38`.
- `NoopGoogleVerifier` fixture at `tests/conftest.py:27`; AuthService
  `__init__(user_repo, session_repo, verifier)` — REQUIRED, no fallback
  (built in `api/deps.py` via `get_auth_service`).
- `ClientError` deliberately EXCLUDED from 503 mapping (`core/errors.py:121`).
- Candidates: no catch-all 422 (`api/candidates.py` PROB-09/#71 comment).

## Numbers (all re-derived, not copied)
- Python: 122 files / 32,332 lines — 75 app (14,699) + 46 tests (17,460)
  + 1 script `spoilerless/scripts/zombie_sweep.py` (173).
- Frontend: TSX 79 / 13,257; TS 65 / 6,239; CSS 2 / 174. Root still `frontend/src`.
- OpenAPI: 37 path templates / 50 operations (probe via `uv run python -c
  "from spoilerless.app.main import app; ..."` FROM REPO ROOT — package not
  importable from inside `spoilerless/`).
- Big tests: test_graph_api.py 1268, test_retrieval_tools.py 1280,
  test_error_handlers.py 318, test_google_verifier.py 264, conftest.py 255.
- Hotspots: pipeline.py 969, system_prompt.py 827, repository/change_set.py 850,
  DetailPanel.tsx 1001, GraphCanvas.tsx 909.
- Exact versions: lockfiles are truth (uv.lock / package-lock.json):
  react 19.2.8, vite 8.1.5, typescript 6.0.3, eslint 10.8.0, vitest 4.1.10,
  cytoscape 3.34.0 + cytoscape-fcose 2.2.0 (primary layout; cose-bilkent 4.1.0
  fallback), fastapi 0.140.7, pydantic 2.13.4, neo4j 6.2.0, google-auth 2.56.2,
  redis 8.1.0, fastapi-limiter 0.2.0, pytest 9.1.1, uvicorn 0.51.0.
- Node engine for locked Vite: `^22.13.0 || >=24.0.0`.
- Neo4j Compose image: `neo4j:2026.06.0-community`; container `spoilerless-neo4j`.

## Deployment/CI now tracked (were "not detected" in the 08-02 map)
- `render.yaml` — free-tier `spoilerless-api` web service, `uv sync --frozen`,
  `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`.
- `.github/workflows/ci.yml` + `release.yml`.
- `frontend/vercel.json` — SPA rewrite only.
- MIT `LICENSE` (Spoilerless Team).

## Frontend state
- `hooks/useFetchState.ts` — shared idle|loading|error|success machine; 6 hooks
  migrated (useGraph, useSeries, useEpisodes, useNotes, useRevisions,
  useChatSessions). useWatchProgress (sessionStorage cache) and
  useChatMessages (SSE) NOT migrated.
- BYOK: `lib/byok.ts` sends per-request `X-LLM-*` headers (localStorage
  `spoilerless:byok-llm-settings`); overrides stored settings.
- Residue: root `index.html` (58KB stale dup of `frontend/index.html`);
  `frontend/README.md` and root `main.py` GONE.
