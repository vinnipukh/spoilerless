<!-- refreshed: 2026-08-20 -->
---
last_mapped: 2026-08-20
focus: arch
last_mapped_commit: 5ad68675e20b4c9b69e9b88335286b5e2f6f04fa
---

# Codebase Structure

**Analysis Date:** 2026-08-20

## Directory Layout

```text
hdgrafcehennemi/
├── spoilerless/
│   ├── app/
│   │   ├── api/             # FastAPI route modules, shared boundary, dependencies
│   │   ├── cache/           # Redis singleton + graph/visualization cache (now with focus-set cap)
│   │   ├── core/            # Settings (209 lines), error envelopes, token helpers
│   │   ├── domain/          # Pydantic contracts (change_set max_length=20, settings URL validation)
│   │   ├── graph/           # Neo4j driver, Cypher, ontology, labels, seed/setup, candidates
│   │   ├── llm/             # Provider adapters, prompts, safe fallbacks
│   │   ├── repository/      # Neo4j persistence and transaction boundary
│   │   ├── retrieval/       # GraphRAG tool registry, context sections (CONTEXT_SECTIONS), grounding
│   │   ├── revisions/       # Revision repository implementation (expanded 11-04)
│   │   ├── services/        # Business orchestration (chat semaphore, change_set propose_via_tool)
│   │   ├── spoiler/         # Visibility policy + spoiler-safe graph-read Cypher
│   │   ├── static/          # Self-hosted character portrait assets (webp)
│   │   └── main.py          # FastAPI entry point (363 lines: body/host middleware, docs gating)
│   ├── scripts/             # smoke.sh and zombie_sweep.py
│   └── tests/               # pytest backend suite (52 modules; new test_security_boundary.py)
├── frontend/
│   ├── public/               # Vite-served static assets
│   ├── src/
│   │   ├── api/              # Typed REST and SSE clients (incl. projection/expansion)
│   │   ├── assets/           # Imported images, including template residue
│   │   ├── components/       # Feature and UI React components (reconciler now tracked)
│   │   ├── hooks/            # Async data/state hooks + scene-state reducer
│   │   ├── lib/              # Shared helpers incl. visualizationAdapter
│   │   ├── providers/        # Auth context/provider/hook
│   │   ├── test/             # Vitest setup and shared fixtures
│   │   ├── types/            # Wire/UI contracts incl. VisualizationDTO
│   │   ├── App.tsx           # SPA composition + controlled graph mode
│   │   └── main.tsx          # Browser mount entry
│   ├── package.json          # npm scripts and dependencies (cytoscape-dagre 4.0.0)
│   ├── vite.config.ts        # React/Tailwind/Vitest and /api proxy
│   └── vercel.json           # SPA rewrite + security headers (CSP, HSTS, nosniff, DENY)
├── data/dexter/
│   ├── metadata/             # Series and episode JSON
│   ├── seed/                 # Canonical graph JSON
│   └── test/                 # Extraction fixture JSON
├── ontology/                 # Versioned graph vocabulary YAML
├── docs/                     # Product/reference documentation
├── .planning/                # GSD state, milestones, research, codebase map
├── .agents/skills/hdgrafcehennemi/  # 181-file project runbook + references
├── .github/workflows/         # GitHub Actions CI and release
├── docker-compose.yml        # Neo4j service and volumes (single neo4j service)
├── render.yaml               # Render Blueprint (free-tier API)
├── pyproject.toml            # Python package, setup CLI, pytest config
├── uv.lock                   # Locked Python dependency graph
├── run_verification.py       # Root doc-claim verification (untracked, stdlib-only)
├── run_doc_verification.py   # Root doc-claim verification (untracked)
├── verify_all_claims.py      # Root doc-claim verification (untracked)
├── verify_arch.py            # Root doc-claim verification (untracked)
├── LICENSE                   # MIT license
├── README.md                 # Product and local-development overview
└── ROADMAP.md                # Canonical product scope; not implementation proof (now in .planning when GSD active)
```

## Directory Purposes

**`spoilerless/app/api/` (now with shared boundary):**
- Purpose: Define the public FastAPI boundary and enforce spoiler/host/body gates before handlers.
- Contains: Eleven router modules (auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, share) plus `boundary.py` (66 lines, D-01 `resolve_effective_boundary`), shared auth/database deps (`deps.py`), and repository error-handler installation (`exceptions.py`). The graph router (`graph.py`, now 92 lines trimmed from prior inline resolver) delegates graph GET to `boundary.py` and keeps `_resolve_effective_boundary = resolve_effective_boundary` alias for visualization/expand/path/export routes.
- Key files: `spoilerless/app/api/boundary.py`, `spoilerless/app/api/deps.py`, `spoilerless/app/api/graph.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/change_set.py`, `spoilerless/app/api/share.py`, `spoilerless/app/api/exceptions.py`, `spoilerless/app/api/candidates.py` (boundary-wired since 11), `spoilerless/app/api/user_content.py` / `spoilerless/app/api/revisions.py` / `spoilerless/app/api/series.py` (hardened in 11).
- Placement rule: Add one route module per resource; register its router in `spoilerless/app/main.py`; keep business logic in `spoilerless/app/services/`; never hand-roll `min(...view_as_of...)` — call `resolve_effective_boundary()` instead.

**`spoilerless/app/core/` (209 lines, hardened):**
- Purpose: Hold process-wide configuration and transport-level error policy.
- Contains: Pydantic `Settings` (`config.py`, 209 lines, new fields `environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`; Neo4j fields now with safe local defaults), exception-handler/error-envelope helpers (`errors.py`, now maps `payload_too_large` 413), and token generation (`spoilerless/app/core/tokens.py`).
- Key files: `spoilerless/app/core/config.py`, `spoilerless/app/core/errors.py`.
- Placement rule: Put cross-feature config or HTTP error infrastructure here, not feature persistence. Gate docs with `ENVIRONMENT` correctly — constructor args are fixed at import time, so `ENVIRONMENT=production` must be set before process start.

**`spoilerless/app/domain/` (hardened caps):**
- Purpose: Define strict contracts shared across backend layers.
- Contains: Pydantic models/enums for auth, graph, series, user content, extraction (8-line hardening), revisions, progress, chat, ChangeSets (`change_set.py`, now `operations: max_length=20`, D-07), settings (`settings.py`, +83 lines: base-URL http/https + host validation, masked suffix, loopback allowed), and the library-neutral visualization DTOs (`visualization.py`: `VisualizationDTO`, `VIEW_TYPES`, `EXPANSION_KEYS`, `PROJECTION_VERSION`).
- Key files: `spoilerless/app/domain/graph.py`, `spoilerless/app/domain/change_set.py`, `spoilerless/app/domain/chat.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/domain/settings.py`, `spoilerless/app/domain/extraction.py`.
- Placement rule: Add request/response/domain types here before wiring API/service/repository code; forbid extra fields when the existing contract does. Enforce caps (20 ops, 8 tool calls/round, focus 20, etc.) at the domain/schema layer, not just in handlers.

**`spoilerless/app/services/` (concurrency + delegation):**
- Purpose: Coordinate business workflows and enforce rules spanning repositories.
- Contains: Feature classes for series, graph, auth, progress, chat (`chat.py`, +28 lines: `asyncio.Semaphore(llm_max_concurrent_generations)` + `warn_if_open_signup` wiring), ChangeSets (`change_set.py`, +41 lines: `propose_via_tool` extraction for thin pipeline delegation), settings, Redis-backed rate limiting (`rate_limit.py`, +68 lines: fail-closed 503 when `environment==production` and `rate_limit_fail_open is False`), and `VisualizationService` (`visualization.py`, 1,173 lines) producing boundary-checked projections. `AuthService` still requires injected repos + verifier, no silent fallback.
- Key files: `spoilerless/app/services/graph.py`, `spoilerless/app/services/chat.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/services/rate_limit.py`, `spoilerless/app/services/visualization.py`.
- Placement rule: Put orchestration here; do not call `tx.run()` from services when the transaction belongs in a repository callback. When adding LLM cost gates, make them server-owned settings, not request fields.

**`spoilerless/app/repository/` (mostly unchanged):**
- Purpose: Own user scoping, Neo4j commands, managed transactions, and row normalization.
- Contains: Users, sessions, user content, progress, chat, settings, ChangeSet, share-token repositories. Candidate graph writes live beside this layer in `spoilerless/app/graph/candidates.py` (99-line hardening) — the direct-use exception.
- Key files: `spoilerless/app/repository/user_content.py`, `spoilerless/app/repository/change_set.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`.
- Placement rule: Add persistence code here and keep query constants in owning `spoilerless/app/graph/` module unless a tightly scoped local query follows the established pattern.

**`spoilerless/app/cache/` (cardinality-bounded):**
- Purpose: Own the single Redis connection and the cache-aside graph/visualization response caches with bounded cardinality.
- Contains: `redis_client.py` (shared `redis.asyncio` singleton), `graph_cache.py` (286 lines, now 63 lines of new bound logic: `FOCUS_SET_CAP=64`, `FOCUS_SET_TTL_SECONDS=3600`, `_focus_capacity_allows()` + call before `set_cached_visualization`; `focus_signature()` SHA-256 over sorted distinct ids; `vizfocus:{series_id}` per-series set). `get_cached_visualization`/`set_cached_visualization` remain the only visualization cache entry points.
- Key files: `spoilerless/app/cache/redis_client.py`, `spoilerless/app/cache/graph_cache.py`.
- Placement rule: Never construct a second `redis.asyncio` client; guard every Redis call on non-empty `REDIS_URL`. Do not add caching to the expansion path (T10-CACHE-06). When adding a new cache key family with attacker-controlled cardinality (e.g. focus_id combos), bound it via a per-entity set with cap + TTL like the focus-set pattern.

**`spoilerless/app/graph/` (candidates hardened):**
- Purpose: Provide graph infrastructure and feature-specific Cypher.
- Contains: Async driver lifecycle, ontology loading, seed/setup, candidate queries (`candidates.py`, +99 lines: series scoping + progress-scoped filters), label inventories, progress/chat/ChangeSet queries.
- Key files: `spoilerless/app/graph/database.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`, `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/candidates.py`.
- Placement rule: Add parameterized query modules by feature; interpolate only server-controlled labels/types selected from ontology allowlists. Never trust a client-supplied order without passing it through `resolve_effective_boundary`.

**`spoilerless/app/spoiler/` (boundary authority):**
- Purpose: Isolate spoiler visibility rules and the core spoiler-safe graph response queries; owns the effective-boundary formula reused by the shared resolver.
- Contains: Claim-visibility fragment builders and graph-response Cypher (`filter.py`), effective-boundary rule (`policy.py`: `is_visible`/`resolve_effective_boundary`/`effective_view_order`/`validate_visibility_order`), and single derived-visibility rule (`visibility.py`).
- Key files: `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/spoiler/visibility.py`.
- Placement rule: Put graph-response visibility changes here; enforce boundary on every traversed story-sensitive entity; keep the pure `effective_view_order` formula in `policy.py` and the DB-touching `resolve_effective_boundary` (progress fetch + episode validation + 422) in `spoilerless/app/api/boundary.py`.

**`spoilerless/app/retrieval/` (delimiter + cap hardening):**
- Purpose: Expose a bounded, typed GraphRAG read surface to the LLM with server-owned framing.
- Contains: Twelve retrieval tools registered in one `TOOL_SPECS` list, input models, 9-section shared context registry (`context.py`, now `CONTEXT_SECTIONS` + 26-line delimiter awareness), `_neutralize_answer_delimiters()` + `llm_max_tool_calls_per_round` handling and thin `propose_changeset` delegation (`pipeline.py`, +67/- delegation narrowing), and citation validation. `context.py` now owns the delimiter-tag list consumed by the neutralizer.
- Key files: `spoilerless/app/retrieval/tools.py`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/context.py`.
- Placement rule: Add a retrieval capability as a typed allowlisted tool, inject authority parameters server-side (`series_id`, `user_id`, `visible_until_order` via boundary), and include its returned IDs in grounding validation. Escape exact delimiter shapes in model-visible answers via `_neutralize_answer_delimiters()` — never generic angle-bracket replacement.

**`spoilerless/app/llm/` (unchanged contracts):**
- Purpose: Isolate external model-provider behavior and prompt policy.
- Contains: `LLMProvider` protocol, Gemini/OpenAI-compatible adapters, localized fallbacks, large system-prompt prose.
- Key files: `spoilerless/app/llm/provider.py`, `spoilerless/app/llm/fallbacks.py`, `spoilerless/app/llm/system_prompt.py`.
- Placement rule: Add provider implementations against `LLMProvider`; do not mix graph querying or writes into adapters. Treat `system_prompt.py` as user-owned prose.

**`spoilerless/app/revisions/` (11-04 wiring):**
- Purpose: Create append-only audit records inside caller-owned Neo4j transactions.
- Contains: `RevisionRepository`, snapshot/JSON helpers, and revision-create Cypher directly in `spoilerless/app/revisions/__init__.py` (+36 lines in Phase 11: expanded call sites for graph mutation logging).
- Key files: `spoilerless/app/revisions/__init__.py`.
- Placement rule: Reuse `RevisionRepository.log_revision()` for mutations; put additional revision modules in named files rather than expanding the initializer further.

**`spoilerless/app/static/` (unchanged):**
- Purpose: Serve self-hosted product images through the `/api/static` mount registered in `spoilerless/app/main.py`.
- Contains: Character portrait `.webp` files under `spoilerless/app/static/characters/`; seed `image_url` values are relative (`/api/static/characters/<id>.webp`) and pass the CSP `img-src 'self'` rule. `frontend/vercel.json` now mirrors this CSP at the edge.
- Placement rule: Keep media referenced by seed content here (never external CDNs); add a file per asset and reference via relative URL.

**`spoilerless/tests/` (52 modules, new boundary suite):**
- Purpose: Verify backend contracts, graph boundaries, persistence, retrieval, prompt safety, ChangeSets, and visualization projections with the new fail-closed/rate-limit/cache-cap/boundary coverage.
- Contains: 52 pytest modules and shared fixtures — including `NoopGoogleVerifier`, scratch-series isolation helpers (`conftest.py`), and `fixtures/visualization/` (`s01e01_safe.json`, `s01e02_cumulative_safe.json`). Deltas since 08-14: **new** `test_security_boundary.py` (316 lines, anonymous fixed 1 / no-progress fail-closed / clamped min() / series mismatch / missing boundary 422); `test_candidate_ingest.py` (+86), `test_candidate_review.py` (+31), `test_visualization_cache.py` (+18, focus-set cap + boundary-aware key), `test_graph_api.py` (+7), `test_auth.py` (+1), `test_revisions.py` (+2), `test_user_content_api.py` (+3).
- Key files: `spoilerless/tests/test_graph_api.py` (1,268+ lines), `spoilerless/tests/test_retrieval_tools.py` (1,280), `spoilerless/tests/test_security_boundary.py` (316), `spoilerless/tests/test_visualization_projection.py` (1,711), `spoilerless/tests/test_visualization_cache.py` (393 + deltas), `spoilerless/tests/test_visualization_baseline.py` (752), `spoilerless/tests/test_visualization_graphrag.py` (267).
- Placement rule: Add `test_<feature>.py` here; use dependency overrides/fake providers rather than external LLM calls. Always clean up scratch `series_scratch_*` nodes and sweep `vizfocus:*` Redis keys in teardown; never run two suites in parallel against the shared live AuraDB.

**`frontend/src/api/` (unchanged surface):**
- Purpose: Convert typed frontend operations to backend HTTP calls.
- Contains: One client module per backend feature, plus shared `client.ts` wrapper (2-line delta retained: `apiBase` prefix + `apiUrl()` image prefixing; handles new 413 `payload_too_large` envelope via normal `client.ts:normalize` — no code change needed, but callers must not assume only 401/422/429). `graph.ts` still carries `fetchVisualization()` + `fetchExpansion()` beside `getGraph()`/`findPath()`.
- Key files: `frontend/src/api/client.ts`, `frontend/src/api/chat.ts`, `frontend/src/api/changeSet.ts`, `frontend/src/api/graph.ts`.
- Placement rule: Add feature calls here; use `apiFetch()` for JSON and preserve `credentials: 'include'` in streaming transports. When handling 413/503 fail-closed responses, surface the `detail.code` (not just status) so the UI can explain the gate.

**`frontend/src/hooks/` (minor):**
- Purpose: Encapsulate async state and browser behavior; hold the serializable scene reducer.
- Contains: Shared `useFetchState`, series/episodes, graph, progress, notes, revisions, chat sessions/messages, and the scene reducer `useSceneState.ts` (view, filters, selection, focus, camera, positions, expansions, timeline, Inspector). `useWatchProgress.ts` has a 3-line tightening since 08-14 (storage handling, fail-closed alignment).
- Key files: `frontend/src/hooks/useFetchState.ts`, `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/hooks/useChatMessages.ts`, `frontend/src/hooks/useSceneState.ts`.
- Placement rule: Put reusable fetch/state machines here; keep visual rendering in `frontend/src/components/`; keep graph-workspace mode state in the reducer and expose `mode`/`onModeChange` seam to the parent.

**`frontend/src/components/` (reconciler promoted):**
- Purpose: Render the product UI by feature.
- Contains: `auth/`, `chat/`, `detail/`, `episode/`, `graph/`, `layout/`, `palette/`, `series/`, `settings/`, `share/`, `timeline/`, reusable `ui/` primitives. `graph/` now holds fully tracked `cytoscapeReconciler.ts` (126 lines) + `cytoscapeReconciler.test.ts` (91 lines, headless identity/position/selection/compound→flat tests) alongside co-located tests; `GraphCanvas.tsx` (50-line delta) adds controlled/uncontrolled mode seam, guards, and `initialElementsRef`/`initialLayoutRef` freeze; `relationshipStyles.ts` palette tweak (34 lines) and `graphStylesheet.ts` (4 lines).
- Key files: `frontend/src/components/detail/DetailPanel.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/components/graph/AnswerGraph.tsx`, `frontend/src/components/chat/ChatPanel.tsx`.
- Placement rule: Place domain components in their feature folder; add generic shadcn/Radix wrappers only to `frontend/src/components/ui/`; keep pure diff logic in `cytoscapeReconciler.ts` with headless tests, not inside `GraphCanvas.tsx`.

**`frontend/src/lib/` (unchanged contract):**
- Purpose: Hold non-visual helpers, including the DTO→Cytoscape bridge.
- Contains: `visualizationAdapter.ts` (`toCytoscapeElements()` with `visualizationAdapter.test.ts`), export-Markdown helpers, node-type maps, highlight logic, BYOK storage helpers, graph filters.
- Placement rule: Put library-neutral conversion utility here; keep components visual and hooks stateful.

**`frontend/src/providers/` and `frontend/src/types/` (unchanged):**
- Purpose: Provide cross-tree auth state and shared TypeScript contracts.
- Contains: Split auth context/provider/hook files and backend-mirroring interfaces, including `VisualizationDTO`, `VisualizationViewType`, `ExpansionKey` in `frontend/src/types/graph.ts`.
- Key files: `frontend/src/providers/AuthProvider.tsx`, `frontend/src/providers/AuthContext.ts`, `frontend/src/types/graph.ts`.
- Placement rule: Mirror wire-contract changes in `frontend/src/types/`; reserve providers for genuinely cross-tree state.

**`data/dexter/` and `ontology/` (unchanged):**
- Purpose: Supply deterministic prototype content and the accepted graph vocabulary.
- Contains: JSON metadata/seed/fixtures and YAML node/relation/claim definitions.
- Key files: `data/dexter/metadata/episodes.json`, `data/dexter/seed/claims.json`, `ontology/relation_types.yaml`.
- Placement rule: Add content under a series-specific data directory; update ontology only for legitimate new graph types.

**Root verification scripts (untracked, unchanged):**
- Purpose: Verify claims in `docs/ARCHITECTURE.md` against live repo.
- Contains: `run_verification.py` (420), `run_doc_verification.py` (429), `verify_all_claims.py` (418), `verify_arch.py` (68) — hard-code repo root and parse doc line-by-line.
- Placement rule: Extend these when adding claim-bearing statements to `docs/ARCHITECTURE.md`; they are workspace tooling, not package code.

## Key File Locations

**Entry Points:**
- `spoilerless/app/main.py` (363 lines): Production ASGI application — builds FastAPI, installs `BodySizeLimitMiddleware` + `TrustedHostMiddleware` + CORS, registers routers/middleware/handlers, owns Neo4j/Redis lifecycle, mounts `/api/static`, disables docs when `environment == "production"`, and runs `warn_if_open_signup()` in lifespan.
- `spoilerless/app/api/boundary.py` (66 lines): Shared spoiler-boundary resolver consumed by every spoiler-sensitive route.
- `spoilerless/app/graph/setup.py`: `spoilerless-setup` database bootstrap CLI.
- `frontend/src/main.tsx`: React browser mount.
- `frontend/src/App.tsx`: Composition root; state-driven graph/settings navigation; Overview vs Full workspace (`graphMode`); now controlled graph mode (`mode`/`onModeChange` seam).

**Configuration:**
- `pyproject.toml`: Python version/dependencies, CLI registration, pytest path (unchanged since 08-14).
- `spoilerless/app/core/config.py` (209 lines): Settings with new fields `environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`; local-default Neo4j values for dev.
- `frontend/package.json`: npm scripts/dependencies (still `cytoscape-dagre` 4.0.0).
- `frontend/vite.config.ts`: React/Tailwind plugins, `@` alias, `/api` proxy, Vitest setup.
- `frontend/tsconfig.app.json`: Frontend TypeScript compiler settings.
- `frontend/vercel.json`: SPA rewrite + security headers (CSP, HSTS, nosniff, DENY, referrer-policy).
- `docker-compose.yml`: Neo4j container/volume config (unchanged; single `neo4j` service).
- `render.yaml`: Render Blueprint for free-tier API (minor polish since 08-14; `ENVIRONMENT` must be set on Render dashboard, not in YAML).
- `.github/workflows/ci.yml` / `release.yml`: GitHub Actions pipelines.
- `LICENSE`: MIT (Spoilerless Team).
- `.env.example`, `frontend/.env.example`: Templates — add `ENVIRONMENT`, `ALLOWED_HOSTS`, `MAX_BODY_SIZE_BYTES`, `RATE_LIMIT_FAIL_OPEN`, `LLM_MAX_*` to `.env.example` when their defaults change (check head against `spoilerless/app/core/config.py`).

**Core Logic:**
- `spoilerless/app/spoiler/filter.py`: Canonical spoiler-safe graph-read queries.
- `spoilerless/app/api/boundary.py`: Single fail-closed boundary resolver (D-01) — every spoiler-sensitive handler must call it.
- `spoilerless/app/services/graph.py`: Concurrent graph assembly and claim-edge projection.
- `spoilerless/app/services/visualization.py`: Boundary-checked visualization projections and expansion deltas (Phase 10, still 1,173 lines; Phase 11 adds focus-set cap upstream in cache layer only).
- `spoilerless/app/domain/visualization.py`: Library-neutral `VisualizationDTO` contract, view vocabulary, expansion allowlist.
- `spoilerless/app/cache/graph_cache.py` (286 lines): Cache-aside graph + visualization with boundary/version/focus-aware keys plus `_focus_capacity_allows()` focus-set cap (D-12).
- `spoilerless/app/retrieval/pipeline.py` (hardened): GraphRAG orchestration now with `_neutralize_answer_delimiters()` (context-section escaping), `operations max_length=20`, `llm_max_tool_calls_per_round` cap, and thin `propose_via_tool` delegation.
- `spoilerless/app/retrieval/tools.py`: Allowlisted Neo4j retrieval operations.
- `spoilerless/app/repository/change_set.py`: Transactional ChangeSet apply/reject/revert via `_APPLY_SPECS`.
- `spoilerless/app/api/share.py`: Token-based read-only share links.
- `frontend/src/hooks/useSceneState.ts`: Serializable graph-workspace scene reducer (D-24).
- `frontend/src/lib/visualizationAdapter.ts`: `VisualizationDTO` → Cytoscape element conversion.
- `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines): Topology-aware imperative scene reconciliation — fully tracked with 91-line headless tests.
- `frontend/src/components/detail/DetailPanel.tsx`: Main inspector/editing surface.
- `frontend/src/components/graph/GraphCanvas.tsx` (hardened): Cytoscape rendering, interaction, controlled/uncontrolled mode, `initialElementsRef`/`initialLayoutRef` freeze, `useImperativeReconcileRef` guard.

**Testing:**
- `spoilerless/tests/conftest.py`: Backend fixtures, `NoopGoogleVerifier`, scratch-series isolation helpers.
- `spoilerless/tests/test_security_boundary.py` (316 lines, new): Security boundary suite covering D-01 anonymous fixed-1, authenticated no-progress fail-closed, clamped `min(...)` with episode validation, missing-persisted-boundary 422, series mismatch.
- `spoilerless/tests/test_candidate_ingest.py` (+86), `spoilerless/tests/test_candidate_review.py` (+31): Phase-11 boundary/progress/scratch-series hardening.
- `spoilerless/tests/test_openapi_contract.py`: API operation/contract verification (still expects 52/39; production docs-off does not change the in-`development` probe count).
- `spoilerless/tests/test_visualization_projection.py`: 1,711-line projection contract suite (still green).
- `spoilerless/tests/test_visualization_cache.py` (393 +18): Cache contract now including focus-set cap case.
- `frontend/src/test/setup.ts`: jsdom/Vitest global setup.
- `frontend/src/test/fixtures/`: Shared typed frontend fixtures.
- `frontend/src/components/graph/cytoscapeReconciler.test.ts` (91 lines): Headless reconciler tests (identity, position, selection, compound→flat).
- `frontend/src/**/*.test.ts(x)`: Co-located frontend tests.

**Documentation and Planning:**
- `README.md`: Product/setup overview.
- `docs/ARCHITECTURE.md`: High-level architecture context; verify against source (root `verify_*.py` scripts audit its claims).
- `docs/reference/frontend-api-contract.md`: Frontend-facing API contract (still correct 52/39).
- `.planning/STATE.md`: GSD milestone state and accumulated decisions (now reflects Phase 11 hardening).
- `.agents/skills/hdgrafcehennemi/SKILL.md` + `references/` (181 files): Project runbook and vetted failure modes — the authoritative source for planner/executor guardrails.

## Naming Conventions

**Files:**
- Python modules use lowercase snake case: `spoilerless/app/services/change_set.py`. New convention: shared cross-route resolvers live under `spoilerless/app/api/` with verb-noun names (`boundary.py` — `resolve_effective_boundary`), and ASGI middleware classes live directly in `spoilerless/app/main.py` (not in `spoilerless/app/middleware/`) to keep lifespan wiring co-located.
- React component files use PascalCase: `frontend/src/components/chat/ChangeSetCard.tsx`.
- Hooks use `use<Name>.ts`/`.tsx`: `frontend/src/hooks/useChatMessages.ts`.
- Frontend API/type modules use lower camel case where compound: `frontend/src/api/changeSet.ts`.
- Pure non-component modules use camelCase: `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/lib/visualizationAdapter.ts`.
- Tests use `test_<feature>.py` in Python and `<subject>.test.ts(x)` beside frontend code; the new boundary suite follows `test_security_boundary.py` (D-01 prefix `test_*_boundary` is not required — use plain feature grouping).

**Directories:**
- Backend directories represent architectural layers: `spoilerless/app/services/`, `spoilerless/app/repository/`.
- Frontend component directories represent product features: `frontend/src/components/graph/`, `frontend/src/components/chat/`.
- Seed content is series-scoped: `data/dexter/`.
- Cache boundary-aware keys live under `spoilerless/app/cache/`; the focus-set cardinality guard co-locates with the visualization cache key constructor.

## Where to Add New Code

**New backend HTTP feature:**
- Domain contracts: `spoilerless/app/domain/<feature>.py`.
- Route handler: `spoilerless/app/api/<feature>.py`, register router in `spoilerless/app/main.py` (and add any new ASGI middleware *inside* `spoilerless/app/main.py` beside the BodySize/TrustedHost pair if it must run before routing).
- Business orchestration: `spoilerless/app/services/<feature>.py`.
- Persistence: `spoilerless/app/repository/<feature>.py` and parameterized Cypher in `spoilerless/app/graph/<feature>.py`.
- Spoiler-sensitive read: add a route-level call to `spoilerless/app/api/boundary.py:resolve_effective_boundary()` and pass its result downstream — never compute `min(requested, view_as_of, watched_through)` inside the handler.
- Tests: `spoilerless/tests/test_<feature>.py`; for boundary-sensitive routes add a `spoilerless/tests/test_security_boundary.py`-style case or a dedicated module mirroring that file's pattern (anonymous=1, no-progress→1, clamped, missing-422).
- Body-size aware: any route that accepts JSON or multipart bodies already inherits the 413 gate — add a focused test that sends a body > `max_body_size_bytes` (via `monkeypatch.setattr(get_settings(), "max_body_size_bytes", ...)` or a real oversized payload) and asserts `{"detail":{"code":"payload_too_large"}}`.

**New spoiler-sensitive read:**
- Primary graph response query: `spoilerless/app/spoiler/filter.py`.
- GraphRAG-only read: typed function/query in `spoilerless/app/retrieval/tools.py`, then schema/executor registration in `spoilerless/app/retrieval/pipeline.py` with `_neutralize_answer_delimiters` awareness (ensure new tool's output cannot inject a `<CONTEXT_SECTIONS>` literal that defeats the neutralizer — only exact section names are escaped, so a new section name must be added to `CONTEXT_SECTIONS`).
- Tests: `spoilerless/tests/test_graph_api.py` or `spoilerless/tests/test_retrieval_tools.py`.
- Requirement: Apply `visible_from_order <= $visible_until_order` to every traversed node/relationship/provenance element before returning rows, with the boundary resolved through the shared resolver.

**New visualization projection view:**
- View constant: add to `VIEW_TYPES` in `spoilerless/app/domain/visualization.py` (keep `PROJECTION_VERSION` in sync with fixtures).
- Projection logic: add function in `spoilerless/app/services/visualization.py` consuming only complete safe `GraphResponse` rows (D-05).
- Route wiring: extend `VisualizationView` enum in `spoilerless/app/api/graph.py` and ensure it calls `resolve_effective_boundary`; extend cache key construction in `spoilerless/app/cache/graph_cache.py` if the view should cache, and add a focus-set-cap exemption if the view takes no `focus_ids`.
- Frontend: view mapping in `frontend/src/App.tsx` (`activeView`), conversion in `frontend/src/lib/visualizationAdapter.ts`, scene handling in `frontend/src/hooks/useSceneState.ts`.
- Tests: `spoilerless/tests/test_visualization_projection.py` (contract), `spoilerless/tests/test_visualization_cache.py` (add a focus-cap variant if applicable), `spoilerless/tests/test_visualization_baseline.py`.

**New semantic expansion key:**
- Add key to `EXPANSION_KEYS` allowlist in `spoilerless/app/domain/visualization.py` (D-21) and mirror in `frontend/src/App.tsx` (`EXPANSION_KEYS`). Expansion path stays uncached (T10-CACHE-06); keep `EXPANSION_MAX_LIMIT` cap.

**New graph mutation:**
- User-driven CRUD: owning repository under `spoilerless/app/repository/`, with same-transaction revision logging through `spoilerless/app/revisions/__init__.py`.
- Agent-proposed mutation: operation model in `spoilerless/app/domain/change_set.py` (`max_length=20`), validation in `spoilerless/app/services/change_set.py:propose_via_tool`, transaction in `spoilerless/app/repository/change_set.py`, Cypher in `spoilerless/app/graph/change_set.py`.
- Frontend confirmation: `frontend/src/components/chat/ChangeSetCard.tsx` and `frontend/src/api/changeSet.ts`.

**New frontend feature:**
- Wire types: `frontend/src/types/<feature>.ts`.
- Transport: `frontend/src/api/<feature>.ts`.
- State: `frontend/src/hooks/use<Feature>.ts` when reusable; graph-workspace state belongs in `frontend/src/hooks/useSceneState.ts` reducer; canvas-mode state should use the controlled `mode`/`onModeChange` seam when the workspace needs lockstep.
- UI: `frontend/src/components/<feature>/`.
- Composition: connect at narrowest owner; top-level view/state belongs in `frontend/src/App.tsx` only when it spans features.
- Tests: co-locate `<subject>.test.ts(x)` with implementation or use shared fixtures in `frontend/src/test/fixtures/`.

**New Cytoscape scene behavior:**
- Pure diffing/reconciliation: `frontend/src/components/graph/cytoscapeReconciler.ts` with headless tests in `frontend/src/components/graph/cytoscapeReconciler.test.ts`; keep `GraphCanvas.tsx` for component glue.
- Layout policy: `frontend/src/components/graph/layoutConfig.ts` (fcose default, dagre for investigation).
- Styling: `frontend/src/components/graph/graphStylesheet.ts` and `frontend/src/components/graph/relationshipStyles.ts` (semantic `relationClass` colors in `RELATION_CLASS_TO_FAMILY`).

**New shared frontend primitive:**
- Generic UI wrapper: `frontend/src/components/ui/`.
- Non-visual helper: `frontend/src/lib/`.
- Cross-feature wire/UI type: `frontend/src/types/`.

**New series content:**
- Content: `data/<series>/metadata/` and `data/<series>/seed/`.
- Vocabulary: `ontology/` only when type system changes.
- Bootstrap integration: extend series-specific assumptions currently in `spoilerless/app/graph/seed.py`.
- Portraits: add `.webp` under `spoilerless/app/static/characters/` and reference via relative `/api/static/...` URLs.

**Database schema change:**
- Add idempotent constraints/indexes to `spoilerless/app/graph/seed.py` and cover setup/idempotency in `spoilerless/tests/test_seed_idempotency.py`.
- No migration directory/framework exists; treat setup DDL as executable schema and document any backfill.

**New cache cardinality-bounded key family:**
- When a key family has attacker-controlled cardinality (new focus_id-like enumeration surface), replicate the `FOCUS_SET_CAP` pattern: per-entity Redis set (`<prefix>:{entity_id}`) with `SCARD` cap check + `SADD` + `EXPIRE` inside `_focus_capacity_allows()` before `SETEX`, gated in the `set_*` path (not the `get_*` path).

**Doc-claim verification (root):**
- Extend `verify_arch.py` / `verify_all_claims.py` / `run_doc_verification.py` / `run_verification.py` when adding factual claims to `docs/ARCHITECTURE.md`; they hard-code repo root and are untracked workspace tooling. Update the `spoilerless/app/api/boundary.py` import path claim if the resolver moves.

## Source Inventory and Hotspots

- Python: ~132 files, ~40,200+ lines across `spoilerless/` (80 app / 52 tests / 1 script), excluding untracked root scripts.
- Root doc-verification scripts (untracked): `run_verification.py` (420), `run_doc_verification.py` (429), `verify_all_claims.py` (418), `verify_arch.py` (68).
- TSX: 82 files, ~15,300 lines.
- TypeScript: 72 files, ~8,200 lines (all `.ts` except `.d.ts`, including `.test.ts`).
- Phase-11 deltas are diffused (no single hotspot > 130 lines): largest new file is `spoilerless/app/api/boundary.py` (66 lines); largest diffs are `spoilerless/app/main.py` (+128), `spoilerless/app/graph/candidates.py` (+99), `spoilerless/app/services/rate_limit.py` (+68), `spoilerless/app/retrieval/pipeline.py` (+67/-), `spoilerless/app/retrieval/context.py` (+26), `frontend/src/components/graph/cytoscapeReconciler.ts` (126 as promoted file).
- Prior-phase hotspots remain: `spoilerless/app/services/visualization.py` (1,173), `spoilerless/app/retrieval/pipeline.py` (post-harvest ~1,100 lines), `spoilerless/app/llm/system_prompt.py` (827, user-owned prose), `spoilerless/app/repository/change_set.py` (850, table-driven `_APPLY_SPECS`), `frontend/src/components/detail/DetailPanel.tsx` (1,049), `frontend/src/components/graph/GraphCanvas.tsx` (~1,170 with new seam), contracted test `spoilerless/tests/test_visualization_projection.py` (1,711).
- Add focused named modules around hotspots rather than extending them when a concern has clean boundary; the Phase-11 boundary extraction (`api/boundary.py`) is the model.

## Special Directories and Residue

**`.planning/` (total 2056 lines before this refresh):**
- Purpose: GSD project state, milestone artifacts, research, codebase maps (7 docs: 133/199/323/378/173/306/544 lines before Phase-11 refresh).
- Generated: Partly.
- Committed: Yes.
- Rule: Codebase mapping outputs belong only in `.planning/codebase/` (this STRUCTURE.md, ARCHITECTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md). Do not commit running-test residue or verification logs.

**`.agents/skills/hdgrafcehennemi/` (181 files):**
- Purpose: Project runbook + references — the authoritative source for planner/executor guardrails and verified fact claims.
- Generated: No (vended).
- Committed: Yes since `4037aa8` (previously ignored via `.agents/` gitignore — now force-tracked).
- Rule: Do not edit the skill contract prose to hide a planner gap; fix the code/docs instead.

**`.hermes/` (removed since 08-14 mapping horizon):**
- Previously held Hermes desktop-attachment markdown notes (spoiler-free graph DB design doc). At HEAD the diff shows `.../spoiler-free-graph-db-plan.md` as an added file under `.agents/desktop-attachments/` with equivalent content, but there is no live `.hermes/` directory — treat as historical artifact, not product code.

**Root `verify_*.py` scripts (untracked, stdlib-only):**
- Purpose: Claim-level verification of `docs/ARCHITECTURE.md` against the repository.
- Generated: No.
- Committed: No (untracked).
- Rule: Workspace tooling; do not import from Python package; hard-coded absolute repo root inside the scripts means they fail outside this checkout — port them to `pathlib` relative logic before running on CI.

**`frontend/dist/` (untracked):**
- Purpose: Vite production build output (serves the `vercel.json`-hardened CSP/HSTS edge).
- Generated: Yes.
- Committed: Workspace-dependent; never edit by hand.

**`neo4j_data/`, `neo4j_logs/`, `neo4j_import/`, `neo4j_plugins/` (untracked volumes):**
- Purpose: Docker-mounted Neo4j runtime volumes.
- Generated: Yes.
- Committed: Treat as runtime state, not source.

**Root `index.html` (58 KB stale):**
- Purpose: Duplicate of frontend entry; active entry is `frontend/index.html`.
- Generated: Template residue.
- Committed: Present at repository root.
- Rule: Vite serves from `frontend/`; do not edit the root copy.

**Root `scripts/` (tracked, outside package):**
- Purpose: Local helpers (`run_backend_tests.py`, `env-local.sh`, `sweep_error_codes_09_05.sh`) outside the Python package.
- Generated: No.
- Committed: Yes.
- Rule: Run ASGI app as `spoilerless.app.main:app`; keep package code under `spoilerless/`.

**`frontend/src/assets/react.svg` and `frontend/src/assets/vite.svg` (tracked residue):**
- Purpose: Scaffold assets with no architectural role.
- Generated: Template residue.
- Committed: Present under frontend assets.

---

*Structure analysis: 2026-08-20*
