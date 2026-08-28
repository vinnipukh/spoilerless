# ARCHITECTURE.md re-verification — 2026-08-10 (after surgical fixes)

Re-verification of `docs/ARCHITECTURE.md` after the 8-claim fix batch. Baseline
artifact said 187 checked / 8 failed; this pass re-checked EVERY claim fresh and
produced 264 checked / 264 passed / 0 failed (`docs/ARCHITECTURE.md` was 872
lines at verify time). The GSD marker `<!-- generated-by: gsd-doc-writer -->`
and the section structure (TOC, numbered sections, D-01..D-12) must be
preserved in the doc — assert the marker string in the validator.

## Method (reuse for any re-verification task)

1. Read the PREVIOUS artifact first — its `failures[]` entries carry the exact
   doc line anchors to re-check (160, 269, 391, 644, 733, 803, 814, 815 for
   ARCHITECTURE.md). Then `git diff docs/<doc>` to see precisely which claims
   the fix batch rewrote.
2. Re-verify the fixed claims AND a full re-enumeration of every other claim
   with fresh evidence; never reuse baseline counts (claim counts are a
   function of the doc revision — see the getting-started reference).
3. Route/operation counts: in-process OpenAPI is the authoritative schema
   inventory (`from spoilerless.app.main import app; app.openapi()`); AST-
   parse the api modules for the raw count. See the `_IncludedRouter` pitfall
   in the umbrella SKILL.md — walking `app.routes` gives ~2 ops, not 51.
4. Build the artifact programmatically: a temp generator script that emits
   the JSON from a structured claim list, then an assertion script checking
   the invariants (checked > 0; passed + failed == checked; len(failures) ==
   failed; every failure has line/claim/expected/actual; doc_path matches),
   then DELETE the generator. Keep the generator out of the repo or delete it
   immediately — the changed-path verification hook flags temp scripts in the
   working tree.
5. For the "why no pytest/uvicorn boot" question: `hermes verify --detect-only
   --json` prints the detected recipe (this repo: test = pytest, start =
   `uvicorn main:app --port 8000`) without launching anything — use it as the
   concrete blocker evidence when the task's process-safety rule forbids a
   real boot. Full `hermes verify` would run the live-Neo4j suite + start
   uvicorn, both prohibited for read-only docs tasks.

## Verified snapshot (do NOT re-derive unless code changes)

- **Route inventory:** 11 route modules (auth, candidates, change_set, chat,
  graph, progress, revisions, series, settings, share, user_content — deps.py
  is not a router) + main.py. 51 raw operations = 50 schema-visible + hidden
  `HEAD /health`; 37 unique path templates either way.
- **Admin-gated routes = 6:** candidates PATCH/{id}, POST/{id}/approve,
  POST/{id}/reject (api/candidates.py `RequireAdminDependency`), change_set
  POST/{id}/confirm, settings GET+PUT /api/settings/llm. Candidate ingest =
  CurrentUserDependency (auth, not admin); candidate list/get = anonymous with
  `_require_resolved_boundary` (persisted-episode order, else 422).
- **Rate limiter (services/rate_limit.py):** login 10/300s per IP; chat_send
  20/60s per user on BOTH message routes; content_write 30/60s per user on
  ALL NINE user_content write routes; identifier = request.state.user else
  client.host. `init_rate_limiter()` guarded on `redis_url` in lifespan after
  `database.open()`. Fail-open distinction (D-11): graph_cache get/set/
  invalidate swallow exceptions and fall through to Neo4j; `try_acquire_async`
  in `__call__` and `RedisBucket.init` in `init_rate_limiter` are NOT wrapped
  — Redis errors there propagate once Redis is configured.
- **Candidate transitions:** approve handler `SET claim.status='canonical'`,
  reject `SET claim.status='rejected'` — direct, no corroborated step.
  `corroborated` exists only in ontology/claim_types.yaml statuses; a staged
  progression is future work.
- **ShareToken:** `secrets.token_urlsafe(32)`, SHA-256 hash persisted,
  `series_id` + `visible_until_order` stored on every record and returned from
  reads/lists and used for the snapshot fetch — token-addressed but
  series-bound. 30-day default TTL (2592000). POST /api/share validates a
  persisted episode order but does NOT compare with creator progress.
- **Retrieval gaps (7.10):** GET_EVIDENCE_QUERY / GET_SOURCES_QUERY gate the
  SUPPORTED_BY/REFERS_TO relationship and evidence/source node but NOT the
  matched Claim; GRAPH_SUMMARY_COUNTS_QUERY gates each counted claim and
  requires visible subject/object endpoints via two `EXISTS` subqueries.
- **Entity-type allowlist intersection:** `SearchEntitiesInput.allowed_entity_types`
  is model-supplied (default = the five narrative labels); tools.py search_entities
  does `allowed = STORY_NODE_LABELS & frozenset(allowed_entity_types)` before
  binding `allowed_labels`. 12 tools = 11 read tools in tools.py + 12th
  `propose_changeset` registered in pipeline.py (`_TOOL_INPUT_MODELS`).
- **Misc anchors:** ERROR_CODES = 32; ErrorDetail.code pattern
  `^[A-Z][A-Z0-9_]*$`; fetch_graph signature `(series_id, visible_until_order,
  node_labels, user_relationship_types, effective_view_order=None)` with 7
  concurrent queries; /graph/path passes `MAX_PATH_HOPS` (4) as requested_order
  (PathRequest has no boundary field); verify_origin on google AND logout
  (fail-closed on missing Origin/Referer); session refresh bumps last_seen_at
  only; sweep interval 3600s; LLM_PROVIDERS = 4 values with vllm/ollama routed
  through OpenAICompatibleProvider; config defaults (SESSION_TTL_SECONDS 604800,
  samesite lax, secure True, FRONTEND_ORIGINS http://localhost:5173, REDIS_URL
  "", LLM_ENABLED False, LLM_PROVIDER openai_compatible).

## Frontend anchor checks used

BYOK_STORAGE_KEY `spoilerless:byok-llm-settings` (+ LEGACY `hdgraf:byok-llm-settings`);
VISITOR_STORAGE_KEY `spoilerless.visitor`; X-LLM-Api-Key / X-LLM-Provider /
X-LLM-Base-URL / X-LLM-Model in byok.ts; useWatchProgress watchedThroughOrder/
viewAsOfOrder/confirmedOrder alias + `persist` option; searchIndex.ts zero-dep
(fuse.js forbidden); CommandPalette `onRequestChange`; layoutConfig fcose +
cose-bilkent + built-in cose fallback + OVERVIEW_SPACING_SCALE 1.6;
AUTO_ZOOM_HOLD_MS 20_000; GraphControls "Refresh graph" aria-label; App.tsx
`useState<'graph' | 'timeline' | 'settings'>('graph')`; three-way edge routing
(claim_id == null && origin !== 'user' → StructuralEdgeCard); vite.config.ts
envDir '..' + proxy 127.0.0.1:8000; vercel.json SPA rewrite only; /share/{token}
pathname match in App.tsx → ShareView.
