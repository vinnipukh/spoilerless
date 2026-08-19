# README.md doc facts (verified 2026-08-14)

Baseline artifact: `.planning/tmp/verify-README.md.json` — **169/169 claims
passed, 0 failures** (strict JSON contract, re-parsed OK). A re-verify
compares against this count. README is 383 lines; doc-verifier role
extraction ran clean — the doc was accurate on every checkable claim.

## Drift-prone facts to re-check each pass
- **No root `package.json`.** All npm claims (`npm install`, `npm run dev`,
  `npm run build`) are valid ONLY against `frontend/package.json` (scripts:
  dev/build/lint/preview/test). Never flag a missing npm script at root.
- **render.yaml verbatim** (README L29): service `spoilerless-api`; build
  `uv sync --frozen`; start `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`.
- **Setup command canonical form**: `uv run python -m spoilerless.app.graph.setup`
  — NEVER `--project spoilerless` in docs. `pyproject.toml` HAS
  `[project.scripts] spoilerless-setup` but NO `[build-system]` — README's
  "does not install that executable through uv sync" is accurate.
- **API surface**: `test_frontend_contract_doc.py` asserts 52 ops /
  39 `EXPECTED_TEMPLATES`; `test_openapi_contract.py` asserts
  `len(schema["paths"]) == 39`. Router prefixes: `/api/auth`,
  `/api/series/{series_id}/candidates`, `/change-sets`, `/chat`,
  `/api/series` (graph/series/revisions/user_content), `/api/series/{series_id}`
  (progress), `/api/settings`, `/api/share`; `GET /health` at main.py:222.
- **Visualization**: exactly 6 view types (api/graph.py:57-62 + comment
  199-200): episode_overview, character_network, plot_threads, investigation,
  full, graphrag_focus. `PROJECTION_VERSION = "1.0.0"` (domain/visualization.py:41).
- **Cache key dimensions** (graph_cache.py:155-167 `_visualization_cache_key`):
  series_id, effective_boundary, view, projection_version, user_id/anon,
  epoch (graph_revision), focus_sig — matches README "per series / order /
  view / projection version / graph revision / user"; expansion uncached
  (T10-CACHE-06).
- **Expansion**: 7 keys (family, work, conflict, episode_events, clues,
  locations, evidence); `EXPANSION_DEFAULT_LIMIT = 12`,
  `EXPANSION_MAX_LIMIT = 25` (domain/visualization.py:93-94). README's
  "adds 8–12 elements by default (hard max 25)" is within range → PASS.
- **Ontology YAMLs are ground truth**: node_types.yaml (14 types incl.
  system `Revision`), relation_types.yaml (27 types / 5 groups),
  claim_types.yaml (5 types / 5 statuses / 4 confidence levels).
- **Golden-path record** `docs/uat/phase-10-golden-path.md`: 12 scenario rows
  (numbered 1–12) + 7 backstop rows (UI-RESP-01..UI-RESTORE-01). Pitfall:
  `grep -c "Scenario"` returns 1 (word appears once in the header) — count
  table rows instead of grepping.
- **PROBLEMS.md**: NINETEENTH PASS is newest (2026-08-13, heading line 1196);
  SEVENTEENTH (L1151), EIGHTEENTH (L1176) precede it. README's one-line
  description matches the heading.
- **jsdom engines** in frontend/package-lock.json (node_modules/jsdom block):
  `node "^22.22.2 || ^24.15.0 || >=26.0.0"` — matches README Node prerequisite.
- **Rate limiting**: login (api/auth.py:107), chat-send (api/chat.py:154,185),
  content-write (api/user_content.py) limiters all from
  `services/rate_limit.py`, which imports pyrate_limiter (Duration, Limiter,
  Rate, RedisBucket, SingleBucketFactory); pyrate-limiter in uv.lock
  (transitive via fastapi-limiter).
- **LLM**: `llm_enabled` default False (config.py); `LLM_PROVIDERS =
  ("gemini", "openai_compatible", "vllm", "ollama")` and
  `DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"`
  (domain/settings.py:21,38); stored AppSetting wins over `LLM_ENABLED` env
  fallback (settings.py:92); X-LLM-Api-Key/Provider/Base-URL/Model at
  main.py:209-212.
- **Env template facts**: `.env.example` does NOT list ALLOWED_EMAILS /
  ADMIN_EMAILS / REDIS_URL but config.py declares them (defaults ""/""/"")
  — README phrasing accurate. `.env.example` sets `VITE_API_BASE_URL=/api`;
  README tells users to set it empty locally (vite proxy /api →
  127.0.0.1:8000, vite.config.ts). `frontend/.env.local` does NOT exist.
- `GOOGLE_CLIENT_SECRET`: zero references in spoilerless/ + frontend/ source
  — README "not used" accurate. Config defaults: SESSION_TTL_SECONDS=604800,
  SESSION_COOKIE_SECURE=True, FRONTEND_ORIGINS default http://localhost:5173.
- Structure claims all verified: core/tokens.py, graph/labels.py,
  retrieval/{context,pipeline,tools}.py, services/change_set.py,
  hooks/useFetchState.ts, lib/graph/highlight.ts (applyHighlight at :73);
  AuthService (services/auth.py:113) takes explicit session_repo + verifier.
- Series id `series_dexter` (data/dexter/metadata/series.json:2); episodes
  S01E01–S01E03 (episode_order 1–3).

## VERIFY markers & external-state framing (PASS pattern)
- 4 VERIFY markers on-disk (L28 Render env, L45 Vercel params, L55 Cloudflare
  DNS/redirect, L173 Google Cloud Console OAuth) — always `grep -c 'VERIFY:'`
  live; never hard-code.
- L16 "Live production (operator-verified…)" framed as operator-verified
  external state → PASS; Vercel build settings (L53) under VERIFY marker →
  PASS. Do not FAIL infra claims properly framed this way.
