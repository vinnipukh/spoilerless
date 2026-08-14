---
last_mapped: 2026-08-14
focus: concerns
last_mapped_commit: 5bd1641d7a9c44d693669d356ea602a23aa3664f
---
# Codebase Concerns

**Analysis Date:** 2026-08-14

Severity follows repository impact: High means a security breach, data loss, crash, or deployment blocker; Medium means a plausible load, correctness, or maintenance failure; Low means contained debt or a non-blocking edge case. Documented future scope is identified separately from defects.

## Technical Debt

### 1.1 Starter and roadmap residue obscures the executable product

**Files:** `spoilerless/app/main.py` (lines 1–16), `frontend/README.md` (deleted), `.planning/ROADMAP.md` (lines 104–116, 301–475), `spoilerless/app/repository/settings.py` (lines 1–7), `spoilerless/app/graph/seed.py` (lines 114–231)

**Evidence:**
```text
main.py is the untouched PyCharm "print_hi" sample.
frontend/README.md still describes the generic React + TypeScript + Vite template.
ROADMAP.md marks implemented health, seed, API, UI, revisions, candidate, and LLM-chat work as unchecked or out of scope.
SettingsRepository says an AppSetting.key uniqueness constraint exists, but create_constraints() creates no AppSetting constraint.
```

**Problem:** Tracked entry-looking files and authoritative-looking prose disagree with the live application. The root roadmap remains the canonical aspirational scope and must not be narrowed, but its completion markers and "later phase" language do not describe the executable state.

**Risk:** New contributors can run the wrong entry point, infer the wrong feature state, or design schema work around a constraint that does not exist.

**Severity:** Low.

**Status:** RESOLVED (08-11/08-12) — the PyCharm sample is gone (`spoilerless/app/main.py` is the real FastAPI app), `frontend/README.md` was deleted, the settings docstring now states there is no `key` constraint (matching DDL), and the root `ROADMAP.md` moved to `.planning/ROADMAP.md` where its unchecked items are GSD plan markers, not product-state claims.

**Scope:** Documentation and root-level scaffolding; production execution uses `spoilerless/app/main.py` and `frontend/src/main.tsx`.

**Fix direction:** Remove or clearly label the PyCharm sample, replace the Vite template README with a pointer to the root documentation, reconcile status language without deleting canonical future scope, and correct the repository docstring to match executable DDL.

**Effort:** Hours.

### 1.2 Integration tests share the application’s live Neo4j state

**Files:** `spoilerless/tests/conftest.py` (lines 15–21, 122–140, 149–255), `spoilerless/tests/test_settings_api.py` (lines 24–117), `spoilerless/tests/test_candidate_review.py` (lines 18–45), `spoilerless/tests/test_session_repository.py`, `scripts/run_phase10_backend_tests.py`

**Evidence:**
```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```
`test_settings_api.py` must back up and restore the global `:AppSetting {key:'llm'}` value, while synchronous `TestClient` requests and `asyncio.run()` cleanup require separate drivers and event loops. The guarded Phase 10 runner (`scripts/run_phase10_backend_tests.py`, NINETEENTH PASS 08-13) now provisions a uniquely named ephemeral `neo4j:2026.06.0-community` container (random password, random loopback ports, no volume mounts) and fail-closed refuses ambient `NEO4J_*`/`aura_*` overrides, remote/Aura URIs, the developer containers `spoilerless-neo4j`/`hdgraf-neo4j`, and pre-existing containers/volumes with its generated name; it proves the effective `Settings` equals the ephemeral credentials and the target holds 0 nodes before running, and always tears down container + volumes.

**Problem:** Integration isolation depends on every fixture using collision-resistant IDs, narrowly scoped cleanup, and correct sync/async driver ownership. The suite originally targeted the same default database as local application use rather than provisioning an ephemeral test database.

**Risk:** An interrupted or incorrectly scoped test can pollute seed state, erase user configuration, become order-dependent, or fail through cross-event-loop Neo4j driver reuse.

**Severity:** Medium.

**Status:** RESOLVED for full-suite runs (NINETEENTH PASS, 08-13) — the Phase 10 regression gate runs exclusively through `scripts/run_phase10_backend_tests.py` against a disposable ephemeral container; the seven-red baseline was retired, not whitelisted. Residual: plain `pytest` or `scripts/run_backend_tests.py` still connects to whatever the environment resolves (root `.env` AuraDB is the legacy default), so ad-hoc local runs can still hit the shared/live database; the guarded runner is the sanctioned path.

**Scope:** Cross-cutting integration tests, especially settings, sessions/auth, candidates, retrieval, chat, and ChangeSets.

**Fix direction:** Keep the guarded ephemeral-container runner as the only documented full-suite path; provision a disposable Neo4j database/container per test run for ad-hoc runs too, separate unit and integration markers, centralize scratch-data factories and teardown, and keep `TestClient`-owned drivers on one portal loop.

**Effort:** Days.

### 1.3 Schema evolution is bootstrap-driven rather than migration-driven

**Files:** `spoilerless/app/graph/seed.py` (lines 114–231, 380–395), `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/progress.py`, `spoilerless/app/graph/chat.py`, `spoilerless/app/graph/change_set.py`, `spoilerless/app/graph/labels.py`, `spoilerless/app/repository/settings.py` (lines 17–42), `spoilerless/tests/test_setup_schema_check.py`

**Evidence:**
```python
await create_constraints(database)
await seed_graph(database, data)
await audit_visibility_integrity(database, data["series"]["id"])
```
No tracked migration directory or migration runner exists. DDL is an idempotent setup routine; `create_constraints()` now iterates the single `NODE_LABELS` inventory (`spoilerless/app/graph/labels.py`), and `spoilerless/tests/test_setup_schema_check.py` verifies the live schema matches the seed contract but does not version it. Seed-content drift keeps being fixed in seed code: SEVENTEENTH PASS (08-12) fixed the 01N52 class by having `load_seed_data()` materialize null reveal-points as the episode's own `visible_from_order` (the Neo4j driver drops `None` properties).

**Problem:** Setup/seed can prepare the present schema but cannot express ordered data transformations, rollback steps, or a database’s applied-version history.

**Risk:** A future property rename, relationship rewrite, or uniqueness change can leave existing databases in mixed states or require undocumented manual intervention; seed fixes must be manually re-applied to already-seeded databases (local docker and AuraDB independently).

**Severity:** Medium.

**Status:** OPEN (unchanged since 08-12; `#19` deferred per PROBLEMS.md FOURTEENTH PASS). Seed remains schema-as-code with a startup schema check (`PROB-20/#44`).

**Scope:** All persisted Neo4j data and every repository that introduces a new label or relationship shape.

**Fix direction:** Add versioned, forward-only Neo4j migrations with an applied-migration ledger, preflight/rollback guidance, and explicit identity/index decisions for runtime-owned labels; retain setup only for fresh databases and deterministic seed content.

**Effort:** Days.

### 1.4 Revision revert does not invalidate the series graph cache

**Files:** `spoilerless/app/revisions/__init__.py` (`revert_revision_work`), `spoilerless/app/graph/candidates.py` (approve/reject/edit paths that call `invalidate_series`), `spoilerless/app/api/revisions.py`

**Evidence:** Documented in `docs/PROBLEMS.md` #60 FIXED record (THIRTEENTH PASS) and `docs/DEPLOYMENT.md`: "The revert path still omits `invalidate_series` (known bug)". A 2026-08-14 grep confirms no `invalidate_series` call exists anywhere in the revisions revert path, while the candidate mutation paths (approve/reject/edit) invalidate after every write.

**Problem:** Reverting a revision restores snapshot values onto live nodes but leaves any cached series graph state stale, so the graph can serve pre-revert content until the cache is otherwise invalidated.

**Risk:** Users see graph state that contradicts the revision history after a revert; the divergence is silent.

**Severity:** Medium (correctness/staleness; live in the deployed backend).

**Scope:** Revision revert (`POST /api/series/{series_id}/revisions/{revision_id}/revert`) and the series graph cache.

**Fix direction:** Call `invalidate_series` inside `revert_revision_work` (same transaction boundary as the revert, matching the candidate-mutation pattern) and add a revert-then-read cache test.

**Effort:** Hours.

### 1.5 Uncommitted work in flight and machine-local files sit outside git

**Files (modified, 2026-08-14):** `frontend/src/App.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/graphStylesheet.ts`, `frontend/src/components/graph/relationshipStyles.ts`, `frontend/src/App.test.tsx`, `.planning/codebase/{ARCHITECTURE,CONVENTIONS,INTEGRATIONS,STACK,STRUCTURE,TESTING}.md`, `.planning/config.json`, `.planning/tmp/docs-work-manifest.json`

**Files (untracked, 2026-08-14):** `frontend/src/components/graph/cytoscapeReconciler.ts` (+ `cytoscapeReconciler.test.ts`), `run_doc_verification.py`, `run_verification.py`, `verify_all_claims.py`, `verify_arch.py`, `.hermes/`

**Evidence:** `git status --short` shows 13 modified + 7 untracked. The graph reconciler extraction is half-committed: `frontend/src/components/graph/GraphCanvas.tsx:44` imports `reconcileCytoscapeElements` from the **untracked** module `./cytoscapeReconciler`. The four root-level `verify_*.py` scripts are claim-checking tooling cited by the documented docs workflow (`docs/PROBLEMS.md` TWELFTH PASS cites `run_doc_verification.py` 276/276) yet are untracked. `.hermes/` contains only `desktop-attachments/` (machine-local Hermes scratch drafts such as `spoiler-free-graph-db-plan.md`) and has no `.gitignore` entry.

**Problem:** The reconciler module is the target of the in-flight refactor but is not tracked — a hard reset or careless stash discards it while `GraphCanvas.tsx` already depends on it; verify scripts exist at the repo root without a home; `.hermes/` is one `git add .` away from committing local tool state.

**Risk:** Lost work, accidental commit of machine-local attachments, and root-level clutter that obscures the executable product.

**Severity:** Low (transient).

**Scope:** Frontend graph reconciler work and GSD/doc-verification tooling only.

**Fix direction:** Commit the reconciler extraction (module + test + `GraphCanvas`/`App`/stylesheet wiring) as one logical unit; move the verify scripts under `scripts/` or add them to `.gitignore`; add `.hermes/` to `.gitignore`.

**Effort:** Minutes–Hours.

## Security

### 2.1 Candidate administration is unauthenticated and bypasses spoiler authority

**Files:** `spoilerless/app/api/candidates.py` (lines 114–225, 231–390), `spoilerless/app/graph/candidates.py` (lines 35–98, 182–263), `spoilerless/tests/test_candidate_review.py` (lines 28–107)

**Evidence:** All mutation routes now require authentication: ingest takes `CurrentUserDependency` (line 144); approve/reject/edit take `RequireAdminDependency` (lines 245, 301, 350). Reads (`GET /candidates`, `GET /candidates/{claim_id}`) require a boundary that must resolve against a persisted episode (`_require_resolved_boundary`, PROB-05/#13); an omitted boundary returns 422 and an above-boundary claim reads as missing (D-15).

**Problem:** (historical) Any network client that could reach the backend could ingest graph content, inspect candidate evidence from any episode, edit candidates, and promote or reject them; candidate `visible_from_order` arrived through the extraction payload rather than a persisted user boundary.

**Risk:** (historical) Unauthorized graph poisoning and review-state mutation; future-episode claim/evidence text could bypass the spoiler boundary.

**Severity:** High.

**Status:** RESOLVED (09-03 auth-gate `0f3c388` + PROB-05 boundary work) — mutations are authenticated (admin for approve/reject/edit), reads are boundary-resolved server-side. Residual (see 4.3): response models are still `dict`, not shared Pydantic contracts.

**Scope:** The complete `/api/series/{series_id}/candidates` read/write surface and candidate-derived graph content.

**Fix direction:** Require authenticated admin/reviewer authorization on every route; derive or validate episode visibility server-side; resolve the requester’s persisted progress for reads; apply claim, endpoint, evidence, source, and relationship visibility predicates on every hop; add unauthenticated, foreign-user, and hidden-equals-missing tests.

**Effort:** Days.

### 2.2 Revision reads and reverts are unauthenticated and trust a caller-supplied boundary

**Files:** `spoilerless/app/api/revisions.py` (lines 59–131, 133–310), `spoilerless/app/revisions/__init__.py` (lines 10–27, 64–90), `spoilerless/tests/test_revisions.py` (lines 32–54, 320–350)

**Evidence:** `revert_revision` now requires `CurrentUserDependency` (line 131), records `actor_id`, and performs admin/ownership checks inside the revert transaction. `list_revisions` and `get_revision` remain unauthenticated and still accept the client-supplied `visible_until_order: Boundary` query; revision snapshots include before/after user content.

**Problem:** (historical) A caller could submit a higher valid order than they have watched, enumerate revision snapshots, and invoke revert without proving identity or resource ownership. The mutation path is now closed; the read paths still trust a caller-supplied boundary.

**Risk:** (historical) User notes/custom content could be disclosed or mutated by unauthenticated clients; a supplied future boundary could reveal spoilery snapshot values. Reads remain enumerable by any caller at a boundary they claim.

**Severity:** High.

**Status:** PARTIALLY RESOLVED (09-03 `0f3c388` + 08-11) — revert is authenticated with in-transaction ownership/admin enforcement; list/get still accept a client-supplied boundary with no auth. Cross-reference 2.5: this is the same read-boundary family the ledger keeps open.

**Scope:** All revision list/get/revert operations and user-content history stored as `:Revision` nodes.

**Fix direction:** Require the authenticated user, resolve progress server-side, scope revisions to the owning `AppUser` or an explicit shared-content policy, enforce ownership inside the same revert transaction, and add direct security contract tests rather than relying on an authenticated fixture whose cookie the route ignores.

**Effort:** Days.

### 2.3 Every authenticated user can replace a shared provider target and credential

**Files:** `spoilerless/app/api/settings.py` (lines 29–50), `spoilerless/app/domain/settings.py` (lines 19–30, 39–77), `spoilerless/app/services/settings.py` (lines 29–81), `spoilerless/app/services/chat.py` (lines 74–113), `spoilerless/app/llm/provider.py` (lines 112–123, 311–323)

**Evidence:** Both settings routes (`GET`, `PUT`) now require `RequireAdminDependency` (`spoilerless/app/api/settings.py` lines 36, 50), so the global `:AppSetting {key:'llm'}` node can no longer be read or replaced by any signed-in user.

**Problem:** (historical) Authentication was treated as administration; any signed-in user could redirect the shared provider to an attacker-controlled HTTP(S) endpoint or an internal/loopback service and replace the shared API key/model.

**Risk:** (historical) A malicious or compromised user could exfiltrate the existing provider credential on a subsequent chat call, probe services reachable from the backend, disable chat for everyone, or redirect all generated content.

**Severity:** High for multi-user or internet-reachable deployment; Medium in the documented single-user local prototype.

**Status:** RESOLVED (09-03 auth-gate `0f3c388`) — settings are admin-only; credential exfiltration via settings writes is closed. Tail remains open (see 2.4).

**Scope:** Global LLM configuration and every chat request that constructs a provider from it.

**Fix direction:** Gate settings behind an explicit administrator role or deployment-only configuration; separate per-user credentials if multi-user configuration is intended; require HTTPS/host allowlists for hosted deployments; block private/link-local/metadata destinations unless an explicit local-provider mode is enabled; rotate any credential after suspected redirection.

**Effort:** Days.

### 2.4 LLM API keys are plaintext application data at rest

**Files:** `spoilerless/app/domain/settings.py` (lines 108–127), `spoilerless/app/repository/settings.py` (lines 17–42), `spoilerless/app/services/settings.py` (lines 50–81)

**Evidence:**
```python
payload["api_key"] = api_key
value=json.dumps(payload)
MERGE (s:AppSetting {key: $key}) SET s.value = $value
```
The HTTP response masks the key correctly, but the full key remains in the Neo4j node’s JSON value.

**Problem:** Response masking is not encryption at rest. Database readers, backups, graph-browser users, and overly broad debug exports can recover the credential.

**Risk:** A Neo4j or backup disclosure also becomes an LLM-provider credential disclosure.

**Severity:** Medium.

**Status:** OPEN — `#5` tail, verified still open 08-12 (PROBLEMS.md THIRTEENTH PASS): the `:AppSetting {key:'llm'}` record is a single global node, admin-gated but not per-user; there is no host allowlist beyond the `http(s)` scheme check; the key remains plaintext at rest.

**Scope:** Stored LLM configuration and all database backup/administration paths.

**Fix direction:** Store only an encrypted envelope or external secret-manager reference, keep the encryption key outside Neo4j, define rotation/clear semantics, and ensure backups inherit equivalent protection.

**Effort:** Days.

### 2.5 Read-boundary resolution is not unified across read surfaces

**Files:** `spoilerless/app/api/candidates.py` (`_require_resolved_boundary`), `spoilerless/app/api/user_content.py`, `spoilerless/app/api/revisions.py` (`visible_until_order: Boundary`), `spoilerless/app/api/graph.py`, `spoilerless/app/api/export.py`, `spoilerless/app/services/progress.py`

**Evidence:** PROBLEMS.md THIRTEENTH PASS "Still open" list (verified 2026-08-12): candidate reads require a boundary that must resolve against a persisted episode; user-content and revision reads accept any positive integer; graph and export reads clamp to persisted progress. Each surface implements its own resolution rule.

**Problem:** The spoiler boundary has different semantics per read family: a client-supplied integer can expose notes/revisions ahead of the user's real progress on the same surfaces that are server-clamped elsewhere.

**Risk:** Inconsistent spoiler safety across surfaces and duplicated, drifting boundary logic.

**Severity:** Medium.

**Scope:** All read endpoints that take a `visible_until_order`-family parameter.

**Fix direction:** Introduce one server-authoritative boundary resolver and use it on every read surface (candidate, user-content, revision, graph, export); keep anonymous reads clamped to the earliest boundary.

**Effort:** Days.

## Performance

### 3.1 Graph reads and Cytoscape rendering return the whole visible graph

**Files:** `spoilerless/app/services/graph.py` (lines 50–110), `spoilerless/app/spoiler/filter.py` (lines 43–187), `frontend/src/components/graph/GraphCanvas.tsx` (1120 lines), `frontend/src/components/graph/graphElements.ts`, `frontend/src/components/graph/cytoscapeReconciler.ts`

**Evidence:**
```python
await asyncio.gather(SERIES_QUERY, NODES_QUERY, STRUCTURAL_EDGES_QUERY,
                     VISIBLE_CLAIMS_QUERY, VISIBLE_USER_RELATIONSHIPS_QUERY,
                     SOURCES_QUERY, EVIDENCE_QUERY)
```
None of the graph queries has a result limit or cursor. The frontend maps the complete response to Cytoscape and runs a layout when graph data changes. Phase 10 (08-13/08-14) added typed visualization DTOs, dagre layout for investigation views, a visualization cache, and a pure element reconciler (`frontend/src/components/graph/cytoscapeReconciler.ts`) on top of the same full-graph fetch.

**Problem:** Seven concurrent queries reduce latency for the tiny Dexter seed but still materialize every visible node, edge, claim, source, and evidence fragment in Neo4j, Python, JSON, and the browser.

**Risk:** Additional series/episodes can cause large responses, high database work, memory pressure, and expensive layout thrashing. The present three-episode prototype keeps the practical impact low.

**Severity:** Medium at expanded-data scale; Low for the shipped prototype dataset.

**Scope:** `GET /api/series/{series_id}/graph` and graph-canvas updates.

**Fix direction:** Measure response/query/layout size, introduce summary and paginated/subgraph endpoints, load details on demand, cap neighborhood expansion, and preserve stable layout positions during incremental updates.

**Effort:** Days–Weeks.

### 3.2 Request-scoped LLM clients have no explicit close lifecycle

**Files:** `spoilerless/app/services/chat.py` (lines 74–113), `spoilerless/app/llm/provider.py` (lines 112–123, 164–230, 311–323, 354–480)

**Evidence:**
```python
return OpenAICompatibleProvider(...)
self._client = client or httpx.AsyncClient(...)
```
`get_llm_provider()` constructs a provider for a request, both provider implementations construct `httpx.AsyncClient`, and neither provider exposes or invokes `aclose()`.

**Problem:** Closing an individual streamed response does not close the owning `AsyncClient` connection pool.

**Risk:** Repeated chat turns can accumulate transport resources, forfeit connection reuse, and eventually produce socket/file-descriptor pressure in a long-lived backend.

**Severity:** Medium.

**Scope:** OpenAI-compatible and Gemini chat traffic.

**Fix direction:** Give providers application-lifespan clients keyed by effective configuration, or make the dependency a yielding async dependency that closes request-owned clients in `finally`; add a lifecycle test with an instrumented client.

**Effort:** Hours–Days.

### 3.3 The chat concurrency ceiling is process-local

**Files:** `spoilerless/app/services/chat.py` (lines 42–72, 147–159, 211–297)

**Evidence:**
```python
_MAX_CONCURRENT_GENERATIONS_PER_USER = 1
_concurrent_generations: dict[str, int] = {}
```

**Problem:** The guard correctly limits one in-flight generation per user inside one Python process, but workers/replicas do not share the dictionary and released users remain as zero-valued keys.

**Risk:** Multi-worker deployment bypasses the intended per-user ceiling and can grow small amounts of stale process memory. This is not general HTTP rate limiting.

**Severity:** Low for single-worker local use; Medium once horizontally scaled.

**Scope:** Chat generation only; it does not protect authentication, graph reads, candidate ingestion, settings, or other HTTP operations.

**Fix direction:** Move generation leases to a shared store with TTL/atomic acquisition for multi-worker deployment and remove zero-valued local entries; keep a separate general request-rate policy.

**Effort:** Hours–Days.

## Maintainability

### 4.1 Core production modules concentrate too many responsibilities

**Files:** `spoilerless/app/retrieval/pipeline.py` (1,102 lines), `spoilerless/app/llm/system_prompt.py` (827 lines), `spoilerless/app/repository/change_set.py` (850 lines), `spoilerless/app/retrieval/tools.py` (881 lines), `spoilerless/app/repository/user_content.py` (856 lines), `frontend/src/components/detail/DetailPanel.tsx` (1,049 lines), `frontend/src/components/graph/GraphCanvas.tsx` (1,120 lines)

**Evidence:** The largest production modules combine orchestration, normalization, validation, persistence/query definitions, UI state, dialogs, effects, and rendering. `spoilerless/app/llm/system_prompt.py` is user-owned prompt prose and must not be casually refactored or rewritten. Since the 08-12 map, `spoilerless/app/retrieval/pipeline.py` grew 969→1,102, `spoilerless/app/retrieval/tools.py` 861→881, `frontend/src/components/detail/DetailPanel.tsx` 1,001→1,049, and `frontend/src/components/graph/GraphCanvas.tsx` 909→1,120 (+211) as Phase 10 visualization work landed; the in-flight reconciler extraction (`frontend/src/components/graph/cytoscapeReconciler.ts`, uncommitted) is the first decomposition step.

**Problem:** Feature changes cross large modules with mixed abstraction levels, increasing review surface and the chance of accidental coupling.

**Risk:** Spoiler predicates, transaction behavior, prompt framing, and UI focus/layout behavior can regress during otherwise localized changes.

**Severity:** Medium.

**Status:** OPEN — `#79` god-file decomposition explicitly deferred (PROBLEMS.md THIRTEENTH/FOURTEENTH PASS, 08-12); sizes grew again since the last map.

**Scope:** Retrieval/LLM, ChangeSets/user content, and the graph/detail frontend.

**Fix direction:** Extract named query modules and narrow repository helpers; split `DetailPanel` dialogs/tabs into feature components; finish the GraphCanvas reconciler extraction and continue extracting lifecycle/focus/reveal hooks; protect the user-owned prompt prose while separating executable composition/guards into small tested modules.

**Effort:** Days–Weeks.

### 4.2 The configured frontend lint gate fails

**Files:** `frontend/eslint.config.js` (lines 8–30), `frontend/src/components/detail/DetailPanel.tsx` (notably lines 259, 288, 454–455, 486–510, 544, 707), `frontend/src/components/graph/GraphCanvas.tsx` (lines 168, 182), `frontend/src/hooks/useChatSessions.ts` (line 34), `frontend/src/hooks/useNotes.ts` (line 35), `frontend/src/hooks/useRevisions.ts` (line 32), related revision tests

**Evidence:** The live 2026-08-12 `npm run lint` run reports **0 errors and 39 warnings**, all `react-hooks/refs` (render-time ref reads); the previous 28-error class (set-state-in-effect, preserve-manual-memoization, no-explicit-any) is gone. EIGHTEENTH PASS (08-13) re-verified ESLint clean on the touched GraphCanvas work.

**Problem:** (historical) A declared quality command was red at the repository baseline (28 errors), so it could not act as a simple regression gate.

**Risk:** (historical) New violations blended into existing output and React lifecycle problems were hard to distinguish from deliberate workarounds.

**Severity:** Medium.

**Status:** RESOLVED (08-11 PROB-09/#72/#73/#74 refactor wave; verified 08-12 and 08-13) — the gate now passes; the remaining `react-hooks/refs` warnings are the only allowed baseline and should not grow.

**Scope:** Frontend source and tests, concentrated in graph/detail state management and revision tests.

**Fix direction:** Triage behavior-affecting hook/ref findings before type-only test findings, refactor without changing graph refresh/focus semantics, establish a clean baseline, and then gate lint in CI.

**Effort:** Days.

### 4.3 Candidate review bypasses service/domain boundaries

**Files:** `spoilerless/app/api/candidates.py` (lines 114–390), `spoilerless/app/graph/candidates.py` (lines 157–263), `spoilerless/app/domain/extraction.py`

**Evidence:** Candidate routes no longer access `repo._db` — they depend on `CandidateRepository` and `GraphService` (`spoilerless/app/api/candidates.py` lines 23–32) and call public repository methods; the catch-all `except Exception → 422 + str(exc)` was removed (08-11, `3a3ae40`) and edit keeps only `except ValueError`. The `#60` closure wave (08-12, `3e80021`/`50484f2`) moved the three duplicated candidate route closures (approve/reject/edit) into `spoilerless/app/graph/candidates.py` as real keyword-param repository methods and the 175-line revert closure into `spoilerless/app/revisions/__init__.py` as `revert_revision_work`; router-level query constants were deleted. Response models are still route-local `dict` rather than shared ontology-backed Pydantic contracts, and a `CandidateService` layer is still absent.

**Problem:** (historical) The API layer owned persistence transactions and validation that other features place in services/repositories, and relabeled DB outages as payload errors while leaking `str(exc)`.

**Risk:** (historical) Authentication, spoiler checks, ontology validation, error shaping, and revision semantics could diverge across ingest/list/get/edit/approve/reject paths.

**Severity:** Medium.

**Status:** RESOLVED (08-11 `3a3ae40` + auth-gate refactor + 08-12 `#60` closure wave) — repository-backed routes, no `_db` access, no catch-all 422, duplicated closures collapsed. Residual: `dict` response models; no `CandidateService` layer. Related open bug: the moved revert path omits `invalidate_series` (see 1.4).

**Scope:** Candidate extraction intake and review workflow.

**Fix direction:** Introduce a `CandidateService`, move managed transactions behind public repository methods, use strict shared request/response models, validate ontology values and episode boundaries centrally, and remove direct access to `repo._db`.

**Effort:** Days.

### 4.4 Backend test files reproduce the god-file pattern

**Files:** `spoilerless/tests/test_visualization_projection.py` (1,711 lines), `spoilerless/tests/test_graph_api.py` (1,684 lines), `spoilerless/tests/test_retrieval_tools.py` (1,350 lines), `spoilerless/tests/test_chat_api.py` (1,302 lines), `spoilerless/tests/test_auth.py` (1,166 lines), `spoilerless/tests/test_retrieval_pipeline.py` (770 lines), `spoilerless/tests/test_visualization_baseline.py` (752 lines), `spoilerless/tests/test_progress_api.py` (712 lines), `spoilerless/tests/test_change_set_api.py` (680 lines)

**Evidence:** Since the 08-12 map, Phase 10 added `spoilerless/tests/test_visualization_projection.py` (1,711 lines) plus `test_visualization_baseline.py` (752), `test_visualization_cache.py` (393), `test_visualization_graphrag.py` (267), `test_phase10_test_runner.py` (345), and `test_phase10_coverage_audit.py` (216); `test_graph_api.py` grew by ~486 lines. Five backend test files now exceed 1,000 lines.

**Problem:** Oversized test modules are hard to navigate, slow to load, and concentrate many feature areas in one file so parallel or chunked runs and blame/ownership suffer; new visualization tests were added to already-large files instead of splitting them.

**Risk:** Test maintenance cost grows; targeted debug runs (`-k` filters) get slower; merge conflicts concentrate.

**Severity:** Low–Medium (maintainability only; the guarded runner executes them greenly).

**Scope:** Backend integration test suite.

**Fix direction:** Split the largest files by fixture group/feature area (e.g. projection variants out of the 1,711-line file), cap new test files at ~400–500 lines, and keep the chunk inventory in `scripts/run_backend_tests.py` in sync.

**Effort:** Days.

## Compatibility

### 5.1 Runtime requirements are documented but incompletely enforced

**Files:** `pyproject.toml` (lines 1–23), `frontend/package.json` (lines 1–52), `README.md` (lines 52–63, 67–74), `frontend/package-lock.json`

**Evidence:** Python is restricted to `>=3.13`, while `frontend/package.json` has no `engines` field even though Vite 8 requires a modern Node runtime. Dependency manifests use lower-bound/caret ranges; reproducibility relies on developers honoring `uv.lock` and `package-lock.json`.

**Problem:** Unsupported Node versions fail only during install/build, and Python 3.12 or older cannot install the backend even if much of the code is syntax-compatible.

**Risk:** Developer and deployment environments can diverge from the documented toolchain, producing avoidable install failures or dependency drift.

**Severity:** Low.

**Scope:** Local setup, CI images, and production build environments.

**Fix direction:** Add Node `engines`/package-manager metadata, pin runtime versions in CI/deployment files, use lockfile-respecting install commands (`uv sync --frozen`, `npm ci`), and retain the Python 3.13 floor only if it is intentional and tested.

**Effort:** Hours.

### 5.2 The Neo4j Compose definition is development-specific

**Files:** `docker-compose.yml` (lines 1–30), `.env.example` (lines 1–11), `spoilerless/app/core/config.py` (lines 7–33)

**Evidence:** Compose now pins `neo4j:2026.06.0-community` (matching CI) and binds both ports to `127.0.0.1` only; it still uses host bind mounts (`./neo4j_data` etc.) and takes `NEO4J_PASSWORD` from the environment with a `change-me` default coupled to `.env.example`.

**Problem:** The file is suitable for local setup but is not portable production orchestration.

**Risk:** Production reuse can still produce platform-specific bind-mount behavior or hardcoded-credential surprises; the database image no longer moves underneath a rebuild.

**Severity:** Low because the repository documents this as local orchestration.

**Status:** PARTIALLY RESOLVED (08-01 `9cf1a4b`) — image pinned to a specific community tag and ports loopback-bound; bind mounts and dev-only orchestration remain.

**Scope:** Neo4j container startup only; backend and frontend are not containerized here.

**Fix direction:** Keep this file explicitly development-only, pin a tested Neo4j patch/digest, move all credentials to runtime secret injection, and create separate production deployment manifests rather than overloading local Compose.

**Effort:** Hours–Days.

## Missing Features

### 6.1 No coverage threshold or browser E2E suite

**Files:** `pyproject.toml` (lines 18–27), `frontend/package.json` (lines 6–11, 31–50), `frontend/vite.config.ts` (lines 23–27), `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `spoilerless/tests/`, `frontend/src/**/*.test.tsx`

**Evidence:** `.github/workflows/ci.yml` runs pytest on every PR against a service-container Neo4j pinned to `neo4j:2026.06.0-community` (seed → suite → DB-pollution gate asserting zero scratch/candidate residue), plus a frontend job (`npm ci`, build, lint, `npm audit`); `release.yml` is a staged-promotion skeleton gated on CI. The OpenAPI contract is re-locked at **52 operations / 39 path templates** (TWENTIETH PASS, 08-14, replacing the older 50/37). Pytest still has no coverage plugin/fail-under setting, Vitest has no coverage configuration, and no Playwright/Cypress configuration is tracked.

**Problem:** (historical) Pytest, Vitest, lint, and build were developer-invoked only, with no automated gate at all.

**Risk:** Broken contracts, authentication cookies, SSE behavior, responsive sheets, or deployment-specific failures can still merge on paths CI does not exercise (no coverage threshold, no browser E2E).

**Severity:** Medium.

**Status:** RESOLVED (09-08 `f9df513`) for the quality-gate half — CI runs backend suite + frontend build/lint/audit on every PR; the 08-14 docs sweep re-verified all gates. Residual: no coverage threshold and no browser E2E suite.

**Scope:** Whole repository and pull-request/release workflow.

**Fix direction:** Add CI with frozen installs, non-destructive unit suites, isolated Neo4j integration jobs, frontend build/lint, coverage reporting with an initially evidence-based threshold, and a small Playwright smoke suite for login/session, graph boundary, chat SSE, and mutation/revert paths.

**Effort:** Days.

### 6.2 Production deployment exists but operations tooling is thin

**Files:** `docs/DEPLOYMENT.md`, `spoilerless/app/core/config.py` (aura_* alias family), `spoilerless/app/main.py` (lines 40–205), `docker-compose.yml`

**Evidence:** The backend is live on Render: `https://spoilerless.onrender.com/health` returned **HTTP 200 `{"status":"ok","database":"connected","service":"spoilerless-backend"}`** verified 2026-08-14 (~0.5 s). The production database is Neo4j AuraDB, addressed through the `aura_*` env alias family that wins over `NEO4J_*` in `spoilerless/app/core/config.py`. `docs/DEPLOYMENT.md` documents the Render dashboard override trap (`backend.app.main:app` → stale builds can keep serving `/health` 200 while deploys fail) and marks 15 operator-only infrastructure claims VERIFY. What remains absent: no structured metrics/tracing/alerting stack, no documented automated backup/restore drill for AuraDB, no release rollback automation, and no automated sync between the local docker Neo4j and AuraDB (see 6.6). Operator actions stay open per PROBLEMS.md: `#29` (~40+ commits ahead of `origin/main`, push + CI-green is operator-touch) and `#36` least-privilege DB user needs provider-issued credentials.

**Problem:** The product runs in production, but incident response and data-safety procedures are undocumented and unrehearsed; a Neo4j or release failure has no automated recovery path.

**Risk:** Live-data loss (AuraDB has no tested restore drill), silent stale-build deploys, and no visibility into request/LLM/DB failures until the product owner notices.

**Severity:** Medium as an operational-hardening gap (revised from High; the deployment is no longer hypothetical — the health check and database connectivity are verified live).

**Scope:** Backend, frontend, Neo4j AuraDB, secrets, monitoring, backups, and release management.

**Fix direction:** Add structured logs, metrics/traces and alerts; document and rehearse AuraDB backup/restore; automate migration-before-rollout and rollback; push `origin/main` and confirm CI green; create a least-privilege AuraDB user.

**Effort:** Weeks.

### 6.3 No general HTTP abuse controls

**Files:** `spoilerless/app/main.py` (lines 58–121), `spoilerless/app/services/rate_limit.py`, `spoilerless/app/api/auth.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/user_content.py`

**Evidence:** Redis-backed rate limiters are wired on the highest-cost surfaces: `login_rate_limiter` (auth login), `chat_send_rate_limiter` (chat send), and `content_write_rate_limiter` (user-content writes) — defined in `spoilerless/app/services/rate_limit.py` and attached as `Annotated[None, Depends(...)]` dependencies (fastapi-limiter 0.2.0 / pyrate-limiter, guarded on `REDIS_URL` so local dev runs unthrottled). Per PROB-23 (SEVENTEENTH PASS, 08-12), the limiter is now **fail-open**: any Upstash Redis error becomes a no-op instead of a plain 500, and `init_rate_limiter` no longer crashes the lifespan on unreachable Redis — so during a Redis outage (the observed free-tier ~daily reset class) rate limiting silently disables. The process-local `_MAX_CONCURRENT_GENERATIONS_PER_USER = 1` chat ceiling remains. There is still no general per-IP/user budget on graph reads, candidate ingestion, or other GET surfaces.

**Problem:** (historical) Authentication attempts, graph reads, candidate ingestion, settings writes, and other API operations had no per-IP/user request budget or payload-cost policy.

**Risk:** Remaining un-throttled surfaces (graph reads, candidate ingestion) can still be flooded on an internet-reachable deployment; chat concurrency remains bounded per process; limiter protection vanishes during Redis outages by design.

**Severity:** Medium for internet exposure; Low for localhost-only use.

**Status:** RESOLVED (08-05 `1f8a3e9`) for the primary abuse surfaces — login, chat-send, and content-write are Redis-rate-limited across workers (D-14); PROB-23 (08-12) converted outage 500s into fail-open no-ops. Residual: no general rate budget on read-only/candidate routes, no payload-size caps, and the fail-open trade-off is untested against sustained outage.

**Scope:** HTTP API except the narrow in-process chat generation guard.

**Fix direction:** Add proxy- and application-level limits keyed by IP/user/route, cap extraction batch size and request bodies, return consistent 429 responses, use a shared limiter for multi-worker deployment, and consider a fail-closed fallback (or explicit alert) for limiter outages on internet-facing deployments.

**Effort:** Days.

### 6.4 Expired and revoked sessions have no automated retention cleanup

**Files:** `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`, `spoilerless/app/services/auth.py`, `spoilerless/app/graph/seed.py` (lines 184–199), `spoilerless/app/main.py` (lines 121–150)

**Evidence:** A background sweep now runs inside the app lifespan (`spoilerless/app/main.py`, `_session_sweep_loop`, hourly): `sweep_expired()` deletes expired/revoked `:Session` nodes and the share repository's expired `ShareToken` nodes; a failed iteration is logged and never fatal. The sweep is started only when the app can reach its database. (PROB-22 tail, 08-12: the standalone `zombie_sweep.py` was fixed for the Neo4j 6.2 driver key change and removed 65 zombies + 8 stale sessions.)

**Problem:** (historical) Security validation was correct at read time, but stale records accumulated indefinitely.

**Risk:** (historical) Session storage and indexes could grow with login churn.

**Severity:** Low.

**Status:** RESOLVED (09-04 `1c7d497`) — periodic cleanup is scheduled at startup; retention is now bounded.

**Scope:** Neo4j `:Session` retention only.

**Fix direction:** Add an idempotent scheduled cleanup query with retention metrics and tests; keep cleanup separate from request authentication.

**Effort:** Hours.

### 6.5 Documented future extraction work is not a present defect

**Files:** `.planning/ROADMAP.md` (lines 104–116, 447–475), `spoilerless/app/api/candidates.py` (lines 76–225), `spoilerless/app/domain/extraction.py`, `docs/ARCHITECTURE.md` (lines 616–635)

**Evidence:** The structured candidate ingestion and human review surface exists, while subtitle/script/podcast extraction connectors and an automated extractor do not.

**Problem:** No significant current-state defect is identified: the repository explicitly treats automated extraction as future scope, and the implemented intake contract is the preparation layer. The security and boundary defects in the existing candidate API are separate concerns documented above.

**Risk:** Misclassifying aspirational extractor work as a bug would distort priorities away from securing the already-executable intake/review endpoints.

**Severity:** Not applicable as a defect.

**Scope:** Future ingestion/connectors only.

**Fix direction:** Preserve the candidate contract, secure it first, and schedule extractor/connectors as product work with source provenance, batch limits, and review gates.

**Effort:** Product-dependent.

### 6.6 Local docker Neo4j and AuraDB can silently diverge

**Files:** `docker-compose.yml`, `scripts/env-local.sh`, `spoilerless/app/core/config.py` (lines 7–33), `scripts/run_phase10_backend_tests.py`, `spoilerless/app/graph/seed.py`

**Evidence:** Two live database targets coexist: the local docker containers `spoilerless-neo4j`/`hdgraf-neo4j` (pinned `neo4j:2026.06.0-community`, used by `scripts/env-local.sh`) and the production AuraDB on Render (the `aura_*` alias family wins in `Settings`; root `.env` AuraDB is the legacy default). There is no export/sync path between them, and the guarded test runner must explicitly refuse both live targets to protect them from test writes. Engine differences are already documented (THIRTEENTH PASS): AuraDB reports `NODE_PROPERTY_UNIQUENESS` constraint names where local 5.x reports `UNIQUENESS`, which forced engine-tolerant assertions. Seed-content fixes (e.g. the 01N52 null reveal-point fix, SEVENTEENTH PASS) must be applied to AuraDB by a separate reseed that nothing automates.

**Problem:** Schema and data verified locally are not the schema/data that run in production, and nothing detects drift.

**Risk:** A green local suite and healthy local graph can coexist with an out-of-date or differently-shaped production database; constraint-name or seed mismatches surface only in production.

**Severity:** Medium (operational).

**Scope:** Local development databases, CI containers, and the production AuraDB instance.

**Fix direction:** Automate or document a reseed-to-AuraDB procedure, add a pre-deploy schema/seed drift check (constraint inventory + seed-content hash), and keep engine-tolerant assertions where the two engines legitimately differ.

**Effort:** Hours–Days.

---

*Concerns audit: 2026-08-14*
