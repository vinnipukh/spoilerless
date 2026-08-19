# 08-14 architecture doc-writer facts — verified against live source

Verified 2026-08-14 during the docs/ARCHITECTURE.md update (gsd-doc-writer,
update mode). Every claim below was grepped/read from live code, not inferred
from task briefs. Trust these over older reference files and over any
doc-generated "normative follow-up" list.

## Retrieval-hop gating is COMPLETE (was the last spoiler gap)
- All **8 claim-selecting query templates** in `spoilerless/app/retrieval/tools.py`
  compose `visible_claim_where()` / `claim_projection()` from `spoiler/filter.py`
  (usages at lines 52, 88, 112, 174, 196, 221, 250, 293: CLAIMS_FOR_FRONTIER,
  EVIDENCE_FOR_CLAIMS, SOURCES_FOR_CLAIMS, GET_CLAIMS, GET_EVIDENCE,
  GET_SOURCES, GRAPH_SUMMARY_COUNTS, ALL_VISIBLE_CLAIMS).
- `GET_EVIDENCE_QUERY` / `GET_SOURCES_QUERY` now gate the matched `Claim`, the
  traversed relationship, AND the evidence/source hop — the "two ungated
  queries" claim (in older docs, PROBLEMS.md passes, and this skill's earlier
  references) is STALE.
- `GRAPH_SUMMARY_COUNTS_QUERY` additionally requires visible subject+object
  endpoints via `EXISTS` subqueries.
- `visible_claim_where()` total call sites: **11** (3 in filter.py, 8 in
  tools.py) — docs saying "seven call sites" are stale.
- 12 ToolSpec registrations in `retrieval/pipeline.py` (11 read tools in
  tools.py + `propose_changeset`) — unchanged.

## CSRF coverage is uniform (SEC-02, docs/PROBLEMS.md #10)
- `api/deps.py` defines `CsrfGuardDependency = Annotated[None, Depends(verify_origin)]`;
  every state-changing cookie-authenticated route declares it as `_csrf`:
  auth 2 (login/logout), candidates 4 (ingest/PATCH/approve/reject),
  change_set 4 (propose/confirm/reject/revert), chat 4, progress 1,
  revisions 1 (revert), settings 1 (PUT), share 2 (create/revoke),
  user_content 9 → 27 handlers total.
- Fail-closed: request with NEITHER `Origin` NOR `Referer` is rejected
  403 `AUTH_ORIGIN_NOT_ALLOWED` (header absence = non-browser client).
- `auth.py` re-exports `verify_origin` (`# noqa: F401`) for backward compat —
  old code importing it from auth.py still works.

## Share creation clamps to creator progress (CR-01)
- `POST /api/share`: requested boundary → `min(requested, progress.view_as_of_order)`
  → `effective_view_order(view, watched_through_order)`; **no progress record
  fails closed to 1**; then `GraphService.resolve_boundary()` (BOUNDARY_QUERY)
  validates the clamped value is a persisted episode order (else 422
  INVALID_VISIBLE_UNTIL_ORDER). Docs saying "share creation accepts any
  persisted episode order without comparing to progress" are STALE.

## BOUNDARY_QUERY callers (08-14)
- `services/graph.py` (`resolve_boundary`) — used by graph route, export,
  candidate reads (`api/candidates.py` calls `graph_service.resolve_boundary`),
  and share create.
- `repository/user_content.py` — imports it aliased as
  `BOUNDARY_VALIDATION_QUERY` (PROB-09/#81, merged with `>= 1` guard).
- NOT imported by `graph/candidates.py` / `api/candidates.py` directly.
- Route-level `Boundary` aliases in user_content/revisions APIs are still
  `Query(gt=0)` positive-integer only.

## Frontend workspace: Overview vs Full (App.tsx, 260814-viz wiring)
- `graphMode`: `'overview' | 'full'`. Overview = original curated graph from
  the legacy `GraphResponse`, no tab navigation. Full = Phase 10 narrative
  workspace with Story / Characters / Evidence / Advanced tabs.
- `activeView` mapping: story → null, advanced → null (LEGACY scene — projection
  DTOs never carry user content; custom nodes/edges live only in GraphResponse);
  characters → `character_network`; evidence → `investigation` (or
  `graphrag_focus` when answer_graph mode open).
- Frontend wires only character_network / investigation / graphrag_focus;
  `episode_overview`, `plot_threads`, `full` remain API-supported view types.
- Raw relation names appear only in Advanced → Debug. Evidence Chain is a
  frontend layered component, not a projection. Answer Graph lifecycle owned by
  `useSceneState` (OPEN_TEMPORARY/CLOSE_TEMPORARY).
- Shared workspace (GraphCanvas + search + Inspector + chat) stays mounted below
  the tab strip; nested modes remember last value per tab; switching top tabs
  never resets filters (D-47).

## cytoscapeReconciler.ts (persistent scene reconciliation)
- `reconcileCytoscapeElements(cy, nextDefinitions)` in
  `frontend/src/components/graph/cytoscapeReconciler.ts` is the batched-diff
  engine: preserves shared element identity, runtime classes/selection,
  positions, zoom, pan; safely detaches/reparents shared nodes and rewires
  edges before removing stale topology (react-cytoscapejs compound removal
  would cascade-delete shared children otherwise). GraphCanvas routes every
  post-mount scene update through it.

## Visualization constants (spoilerless/app/domain/visualization.py)
- EXPANSION_KEYS (7): family|work|conflict|episode_events|clues|locations|evidence
- EXPANSION_DEFAULT_LIMIT 12, EXPANSION_MAX_LIMIT 25
- EPISODE_OVERVIEW_MAX_NODES 40, EPISODE_OVERVIEW_MAX_EDGES 60
- GRAPHRAG_FOCUS_MAX_IDS 20, GRAPHRAG_FOCUS_MAX_NODES 20 (5–20 element DTO)
- View types: episode_overview, character_network, plot_threads, investigation,
  full, graphrag_focus. Routes: GET /graph/visualization?view&episode_order&focus_id,
  GET /graph/expand?node_id&expansion_key&episode_order&limit.
- Cache: `graph:{series_id}:{boundary}:{user or 'anon'}` TTL 300
  (DEFAULT_GRAPH_TTL_SECONDS); `viz:{series_id}:*` keys carry view type +
  projection version + per-series epoch (`graph_revision`, D-30) + focus digest;
  invalidate_series sweeps both prefixes (SCAN+DELETE), epoch bumped atomically
  BEFORE deletion.

## Other re-verified numbers (08-14)
- ERROR_CODES = **32** (9 shared + 12 route-level + 8 auth + 3 LLM) — "32 error
  codes" doc claim is correct.
- Graph routes: GET /graph, GET /graph/visualization, GET /graph/expand,
  POST /graph/path, GET /export (5 handlers in api/graph.py).
- API surface: **52 ops / 39 path templates** (contract test; supersedes the
  50/37 in 08-12-doc-update-facts.md).
- docker-compose: `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` env fallback
  (re-confirmed); `.env.example` change-me vs `scripts/env-local.sh`
  hdgraf-local-password.
- Config defaults re-checked: session_ttl_seconds 604800, samesite lax,
  session_cookie_secure True, frontend_origins http://localhost:5173,
  llm_provider openai_compatible, neo4j_database 'neo4j'
  (AliasChoices aura_database|neo4j_database).
- RequireAdminDependency still gates exactly 6 routes (candidates PATCH/approve/
  reject, change_set confirm, settings GET/PUT).
- Rate limiter: login 10/300s IP, chat 20/60s user, content_write 30/60s user→IP.

## Doc-update workflow note (where stale claims hide)
When a task brief says "recent architectural changes MUST be reflected", the
stale claims are usually in: (1) "normative follow-ups / future work" lists —
completed items still written as open; (2) cross-cutting invariant sections
(e.g. 7.10-style spoiler-safety lists); (3) per-route boundary descriptions.
Verify each candidate claim by grepping the NAMED SYMBOL (CsrfGuardDependency,
visible_claim_where, BOUNDARY_QUERY) for usage counts, and read the contract
test's live asserts rather than trusting any reference file's counts.

## Verifier-pass additions (same doc, same day — gsd-doc-verifier)
Symbol-location traps — grep by class/function name, never by assumed directory:
- `CandidateRepository` (`approve_claim`/`reject_claim`/`edit_claim`) lives in
  `graph/candidates.py`; there is NO `repository/candidates.py`. Docs saying
  "repository layer" are loose, but class + methods exist and api/candidates.py
  uses them.
- `install_llm_error_handlers` is defined in `llm/provider.py`;
  `install_database_error_handlers` in `core/errors.py`; both installed from main.py.
- `assemble_context` is in `retrieval/pipeline.py` (NOT context.py — that holds
  only CONTEXT_SECTIONS / CONTEXT_DELIMITERS).
- `STORY_NODE_LABELS` (retrieval entity allowlist) is defined in
  `retrieval/tools.py` (7 uses), not labels.py.
- `Origin` StrEnum (CANONICAL/CANDIDATE/USER) is in `domain/user_content.py`.
- system_prompt.py: `SYSTEM_PROMPT_ENG`/`SYSTEM_PROMPT_TR`,
  `SYSTEM_PROMPT_LANGUAGES = ("english","turkish")`, `SYSTEM_PROMPTS` dict with
  `.get(language, SYSTEM_PROMPT_ENG)` fallback, `compose_system_prompt()`;
  `SYSTEM_PROMPT_VERSION` confirmed ABSENT (0 hits) — do not let docs add it.
- `_session_sweep_loop` + `SESSION_SWEEP_INTERVAL_SECONDS = 3600`
  (`asyncio.create_task` in lifespan) sweeps BOTH session_repo and share_repo.
- `VITE_GOOGLE_CLIENT_ID` == `GOOGLE_CLIENT_ID` mismatch validation is in
  `core/config.py` (~lines 156-166), not main.py.
- `@app.head("/health", include_in_schema=False)`: openapi-visible ops = 52
  (51 api handlers + GET /health); registered handlers = 53. Contract test
  counts openapi only — "52 including HEAD /health" phrasing is a nuance, not an error.
- `_SECURITY_HEADERS` dict in main.py (CSP incl. accounts.google.com script-src,
  HSTS, nosniff, XFO DENY, Referrer-Policy) + `app.add_middleware(CORSMiddleware, ...)`
  with explicit allow_methods/allow_headers lists. Health 503 returns
  `HealthResponse(status="degraded", database=..., service=...)`.
- GraphEdge in domain/graph.py: `claim_id: str | None = None` (D-03 structural
  + user-authored edges carry claim_id null); GraphClaim carries the full
  doc'd Claim field set (subject_id/predicate/object_id/claim_type/status/
  confidence_level/relationship_effect/valid_from|until/source_id/evidence_ids/origin).

Label/relationship inventory traps (check BOTH sources before failing a doc table):
- `RELATIONSHIP_TYPES` in seed.py is only a 5-entry structural tuple
  (PART_OF, PRECEDES, OCCURRED_IN, SUPPORTED_BY, REFERS_TO) — the doc's
  36-type relationship table is backed by `ontology/relation_types.yaml`,
  NOT this tuple. Verify against the ontology YAML too.
- `Season`/`Scene` are absent from NODE_LABELS/seed.py/setup.py but defined in
  `ontology/node_types.yaml` and appear in seed JSON — absence from NODE_LABELS
  alone does NOT falsify a label-table row (ontology types are seedable).
- package.json stack claims: `radix-ui ^1.6.7` + `shadcn ^4.16.0` are the
  UNIFIED packages (no @radix-ui/* scoped deps); `pyrate-limiter` is transitive
  via `fastapi-limiter>=0.2.0`; `fuse.js` absent (searchIndex.ts:
  "fuse.js is FORBIDDEN").
