---
last_mapped: 2026-08-12
focus: concerns
last_mapped_commit: 1710d57db7c048a83299cadc072e0779f80f246d
---
# Codebase Concerns

**Analysis Date:** 2026-08-12

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

**Problem:** Tracked entry-looking files and authoritative-looking prose disagree with the live application. The root roadmap remains the canonical aspirational scope and must not be narrowed, but its completion markers and “later phase” language do not describe the executable state.

**Risk:** New contributors can run the wrong entry point, infer the wrong feature state, or design schema work around a constraint that does not exist.

**Severity:** Low.

**Status:** RESOLVED (08-11/08-12) — the PyCharm sample is gone (`spoilerless/app/main.py` is the real FastAPI app), `frontend/README.md` was deleted, the settings docstring now states there is no `key` constraint (matching DDL), and the root `ROADMAP.md` moved to `.planning/ROADMAP.md` where its unchecked items are GSD plan markers, not product-state claims.

**Scope:** Documentation and root-level scaffolding; production execution uses `spoilerless/app/main.py` and `frontend/src/main.tsx`.

**Fix direction:** Remove or clearly label the PyCharm sample, replace the Vite template README with a pointer to the root documentation, reconcile status language without deleting canonical future scope, and correct the repository docstring to match executable DDL.

**Effort:** Hours.

### 1.2 Integration tests share the application’s live Neo4j state

**Files:** `spoilerless/tests/conftest.py` (lines 15–21, 122–140, 149–255), `spoilerless/tests/test_settings_api.py` (lines 24–117), `spoilerless/tests/test_candidate_review.py` (lines 18–45), `spoilerless/tests/test_session_repository.py`

**Evidence:**
```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```
`test_settings_api.py` must back up and restore the global `:AppSetting {key:'llm'}` value, while synchronous `TestClient` requests and `asyncio.run()` cleanup require separate drivers and event loops.

**Problem:** Integration isolation depends on every fixture using collision-resistant IDs, narrowly scoped cleanup, and correct sync/async driver ownership. The suite targets the same default database as local application use rather than provisioning an ephemeral test database.

**Risk:** An interrupted or incorrectly scoped test can pollute seed state, erase user configuration, become order-dependent, or fail through cross-event-loop Neo4j driver reuse.

**Severity:** Medium.

**Status:** OPEN — mitigations in place (2026-08-10/08-11): `scripts/env-local.sh` points full runs at the local docker Neo4j, CI runs the suite against a fresh pinned-Neo4j container with a post-suite residue gate, and conftest centralizes scratch-series bootstrap/teardown + module-scoped cleanup. The shared-live-DB hazard remains for ad-hoc local runs.

**Scope:** Cross-cutting integration tests, especially settings, sessions/auth, candidates, retrieval, chat, and ChangeSets.

**Fix direction:** Provision a disposable Neo4j database/container per test run, separate unit and integration markers, centralize scratch-data factories and teardown, and keep `TestClient`-owned drivers on one portal loop.

**Effort:** Days.

### 1.3 Schema evolution is bootstrap-driven rather than migration-driven

**Files:** `spoilerless/app/graph/seed.py` (lines 114–231, 380–395), `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/progress.py`, `spoilerless/app/graph/chat.py`, `spoilerless/app/graph/change_set.py`, `spoilerless/app/graph/labels.py`, `spoilerless/app/repository/settings.py` (lines 17–42), `spoilerless/tests/test_setup_schema_check.py`

**Evidence:**
```python
await create_constraints(database)
await seed_graph(database, data)
await audit_visibility_integrity(database, data["series"]["id"])
```
No tracked migration directory or migration runner exists. DDL is an idempotent setup routine; `create_constraints()` now iterates the single `NODE_LABELS` inventory (`spoilerless/app/graph/labels.py`), and `spoilerless/tests/test_setup_schema_check.py` verifies the live schema matches the seed contract but does not version it.

**Problem:** Setup/seed can prepare the present schema but cannot express ordered data transformations, rollback steps, or a database’s applied-version history.

**Risk:** A future property rename, relationship rewrite, or uniqueness change can leave existing databases in mixed states or require undocumented manual intervention.

**Severity:** Medium.

**Scope:** All persisted Neo4j data and every repository that introduces a new label or relationship shape.

**Fix direction:** Add versioned, forward-only Neo4j migrations with an applied-migration ledger, preflight/rollback guidance, and explicit identity/index decisions for runtime-owned labels; retain setup only for fresh databases and deterministic seed content.

**Effort:** Days.

## Security

### 2.1 Candidate administration is unauthenticated and bypasses spoiler authority

**Files:** `spoilerless/app/api/candidates.py` (lines 114–225, 231–390), `spoilerless/app/graph/candidates.py` (lines 35–98, 182–263), `spoilerless/tests/test_candidate_review.py` (lines 28–107)

**Evidence:** All mutation routes now require authentication: ingest takes `CurrentUserDependency` (line 144); approve/reject/edit take `RequireAdminDependency` (lines 245, 301, 350). Reads (`GET /candidates`, `GET /candidates/{claim_id}`) require a boundary that must resolve against a persisted episode (`_require_resolved_boundary`, PROB-05/#13); an omitted boundary returns 422 and an above-boundary claim reads as missing (D-15).

**Problem:** (historical) Any network client that can reach the backend could ingest graph content, inspect candidate evidence from any episode, edit candidates, and promote or reject them; candidate `visible_from_order` arrived through the extraction payload rather than a persisted user boundary.

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

**Status:** PARTIALLY RESOLVED (09-03 `0f3c388` + 08-11) — revert is authenticated with in-transaction ownership/admin enforcement; list/get still accept a client-supplied boundary with no auth.

**Scope:** All revision list/get/revert operations and user-content history stored as `:Revision` nodes.

**Fix direction:** Require the authenticated user, resolve progress server-side, scope revisions to the owning `AppUser` or an explicit shared-content policy, enforce ownership inside the same revert transaction, and add direct security contract tests rather than relying on an authenticated fixture whose cookie the route ignores.

**Effort:** Days.

### 2.3 Every authenticated user can replace a shared provider target and credential

**Files:** `spoilerless/app/api/settings.py` (lines 29–50), `spoilerless/app/domain/settings.py` (lines 19–30, 39–77), `spoilerless/app/services/settings.py` (lines 29–81), `spoilerless/app/services/chat.py` (lines 74–113), `spoilerless/app/llm/provider.py` (lines 112–123, 311–323)

**Evidence:** Both settings routes (`GET`, `PUT`) now require `RequireAdminDependency` (`spoilerless/app/api/settings.py` lines 36, 50), so the global `:AppSetting {key:'llm'}` node can no longer be read or replaced by any signed-in user.

**Problem:** (historical) Authentication was treated as administration; any signed-in user could redirect the shared provider to an attacker-controlled HTTP(S) endpoint or an internal/loopback service and replace the shared API key/model.

**Risk:** (historical) A malicious or compromised user could exfiltrate the existing provider credential on a subsequent chat call, probe services reachable from the backend, disable chat for everyone, or redirect all generated content.

**Severity:** High for multi-user or internet-reachable deployment; Medium in the documented single-user local prototype.

**Status:** RESOLVED (09-03 auth-gate `0f3c388`) — settings are admin-only; credential exfiltration via settings writes is closed.

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

**Scope:** Stored LLM configuration and all database backup/administration paths.

**Fix direction:** Store only an encrypted envelope or external secret-manager reference, keep the encryption key outside Neo4j, define rotation/clear semantics, and ensure backups inherit equivalent protection.

**Effort:** Days.

## Performance

### 3.1 Graph reads and Cytoscape rendering return the whole visible graph

**Files:** `spoilerless/app/services/graph.py` (lines 50–110), `spoilerless/app/spoiler/filter.py` (lines 43–187), `frontend/src/components/graph/GraphCanvas.tsx` (909 lines), `frontend/src/components/graph/graphElements.ts`

**Evidence:**
```python
await asyncio.gather(SERIES_QUERY, NODES_QUERY, STRUCTURAL_EDGES_QUERY,
                     VISIBLE_CLAIMS_QUERY, VISIBLE_USER_RELATIONSHIPS_QUERY,
                     SOURCES_QUERY, EVIDENCE_QUERY)
```
None of the graph queries has a result limit or cursor. The frontend maps the complete response to Cytoscape and runs a layout when graph data changes.

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

**Files:** `spoilerless/app/retrieval/pipeline.py` (969 lines), `spoilerless/app/llm/system_prompt.py` (827 lines), `spoilerless/app/repository/change_set.py` (850 lines), `spoilerless/app/retrieval/tools.py` (861 lines), `spoilerless/app/repository/user_content.py` (856 lines), `frontend/src/components/detail/DetailPanel.tsx` (1,001 lines), `frontend/src/components/graph/GraphCanvas.tsx` (909 lines)

**Evidence:** The largest production modules combine orchestration, normalization, validation, persistence/query definitions, UI state, dialogs, effects, and rendering. `spoilerless/app/llm/system_prompt.py` is user-owned prompt prose and must not be casually refactored or rewritten. The PROB-09 dedup wave (08-11) collapsed duplicated registries, fragments, and helpers across these files but did not decompose them.

**Problem:** Feature changes cross large modules with mixed abstraction levels, increasing review surface and the chance of accidental coupling.

**Risk:** Spoiler predicates, transaction behavior, prompt framing, and UI focus/layout behavior can regress during otherwise localized changes.

**Severity:** Medium.

**Scope:** Retrieval/LLM, ChangeSets/user content, and the graph/detail frontend.

**Fix direction:** Extract named query modules and narrow repository helpers; split `DetailPanel` dialogs/tabs into feature components; extract GraphCanvas lifecycle/focus/reveal hooks; protect the user-owned prompt prose while separating executable composition/guards into small tested modules.

**Effort:** Days–Weeks.

### 4.2 The configured frontend lint gate fails

**Files:** `frontend/eslint.config.js` (lines 8–30), `frontend/src/components/detail/DetailPanel.tsx` (notably lines 259, 288, 454–455, 486–510, 544, 707), `frontend/src/components/graph/GraphCanvas.tsx` (lines 168, 182), `frontend/src/hooks/useChatSessions.ts` (line 34), `frontend/src/hooks/useNotes.ts` (line 35), `frontend/src/hooks/useRevisions.ts` (line 32), related revision tests

**Evidence:** The live 2026-08-12 `npm run lint` run reports **0 errors and 39 warnings**, all `react-hooks/refs` (render-time ref reads); the previous 28-error class (set-state-in-effect, preserve-manual-memoization, no-explicit-any) is gone.

**Problem:** (historical) A declared quality command was red at the repository baseline (28 errors), so it could not act as a simple regression gate.

**Risk:** (historical) New violations blended into existing output and React lifecycle problems were hard to distinguish from deliberate workarounds.

**Severity:** Medium.

**Status:** RESOLVED (08-11 PROB-09/#72/#73/#74 refactor wave; verified 08-12) — the gate now passes; the remaining `react-hooks/refs` warnings are the only allowed baseline and should not grow.

**Scope:** Frontend source and tests, concentrated in graph/detail state management and revision tests.

**Fix direction:** Triage behavior-affecting hook/ref findings before type-only test findings, refactor without changing graph refresh/focus semantics, establish a clean baseline, and then gate lint in CI.

**Effort:** Days.

### 4.3 Candidate review bypasses service/domain boundaries

**Files:** `spoilerless/app/api/candidates.py` (lines 114–390), `spoilerless/app/graph/candidates.py` (lines 157–263), `spoilerless/app/domain/extraction.py`

**Evidence:** Candidate routes no longer access `repo._db` — they depend on `CandidateRepository` and `GraphService` (`spoilerless/app/api/candidates.py` lines 23–32) and call public repository methods; the catch-all `except Exception → 422 + str(exc)` was removed (08-11, `3a3ae40`) and edit keeps only `except ValueError`. Response models are still route-local `dict` rather than shared ontology-backed Pydantic contracts, and #60 (revert candidate/revision routes to real repository methods) remains deferred.

**Problem:** (historical) The API layer owned persistence transactions and validation that other features place in services/repositories, and relabeled DB outages as payload errors while leaking `str(exc)`.

**Risk:** (historical) Authentication, spoiler checks, ontology validation, error shaping, and revision semantics could diverge across ingest/list/get/edit/approve/reject paths.

**Severity:** Medium.

**Status:** RESOLVED (08-11 `3a3ae40` + auth-gate refactor) — repository-backed routes, no `_db` access, no catch-all 422. Residual: `dict` response models; `CandidateService`/`#60` layering still deferred.

**Scope:** Candidate extraction intake and review workflow.

**Fix direction:** Introduce a `CandidateService`, move managed transactions behind public repository methods, use strict shared request/response models, validate ontology values and episode boundaries centrally, and remove direct access to `repo._db`.

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

### 6.1 No automated quality gate, coverage threshold, or browser E2E suite

**Files:** `pyproject.toml` (lines 18–27), `frontend/package.json` (lines 6–11, 31–50), `frontend/vite.config.ts` (lines 23–27), `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `spoilerless/tests/`, `frontend/src/**/*.test.tsx`

**Evidence:** `.github/workflows/ci.yml` now runs pytest on every PR against a service-container Neo4j pinned to `neo4j:2026.06.0-community` (seed → suite → DB-pollution gate asserting zero scratch/candidate residue), plus a frontend job (`npm ci`, build, lint, `npm audit`); `release.yml` is a staged-promotion skeleton gated on CI. Pytest still has no coverage plugin/fail-under setting, Vitest has no coverage configuration, and no Playwright/Cypress configuration is tracked.

**Problem:** (historical) Pytest, Vitest, lint, and build were developer-invoked only, with no automated gate at all.

**Risk:** Broken contracts, authentication cookies, SSE behavior, responsive sheets, or deployment-specific failures can still merge on paths CI does not exercise (no coverage threshold, no browser E2E).

**Severity:** Medium.

**Status:** RESOLVED (09-08 `f9df513`) for the quality-gate half — CI runs backend suite + frontend build/lint/audit on every PR. Residual: no coverage threshold and no browser E2E suite.

**Scope:** Whole repository and pull-request/release workflow.

**Fix direction:** Add CI with frozen installs, non-destructive unit suites, isolated Neo4j integration jobs, frontend build/lint, coverage reporting with an initially evidence-based threshold, and a small Playwright smoke suite for login/session, graph boundary, chat SSE, and mutation/revert paths.

**Effort:** Days.

### 6.2 Production deployment and operations are not implemented

**Files:** `docker-compose.yml`, `spoilerless/app/main.py` (lines 40–205), `docs/DEPLOYMENT.md`, `docs/CONFIGURATION.md`, `docs/TESTING.md`

**Evidence:** The tracked repository has no backend/frontend production container definitions, reverse-proxy/TLS configuration, infrastructure manifests, monitoring/metrics stack, automated database backup job, restore drill, or release rollback automation. Operational logging now exists but is thin: an HTTP request-logging middleware (`spoilerless/app/main.py` line 73), startup/health handling, auth warnings (`spoilerless/app/api/auth.py`), and session-sweep error logging; there is no structured metrics/tracing stack.

**Problem:** Documentation can describe deployment considerations, but no executable production topology or operational control plane exists.

**Risk:** Production launch is blocked by missing secure cookie/TLS wiring, health-based rollout, observability, backup/restore, and rollback procedures. A Neo4j or release failure has no automated recovery path.

**Severity:** High as a production-readiness blocker; not a blocker for local prototype use.

**Scope:** Backend, frontend, Neo4j, secrets, monitoring, backups, and release management.

**Fix direction:** Choose a target platform; build immutable backend/frontend images; terminate TLS; set secure cookies and strict origins; add structured logs, metrics/traces, alerts, Neo4j backups with tested restore, migration-before-rollout, and documented application/database rollback.

**Effort:** Weeks.

### 6.3 No general HTTP abuse controls

**Files:** `spoilerless/app/main.py` (lines 58–121), `spoilerless/app/services/rate_limit.py`, `spoilerless/app/api/auth.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/user_content.py`

**Evidence:** Redis-backed rate limiters are wired on the highest-cost surfaces: `login_rate_limiter` (auth login), `chat_send_rate_limiter` (chat send), and `content_write_rate_limiter` (user-content writes) — defined in `spoilerless/app/services/rate_limit.py` and attached as `Annotated[None, Depends(...)]` dependencies (fastapi-limiter 0.2.0 / pyrate-limiter, guarded on `REDIS_URL` so local dev runs unthrottled). The process-local `_MAX_CONCURRENT_GENERATIONS_PER_USER = 1` chat ceiling remains. There is still no general per-IP/user budget on graph reads, candidate ingestion, or other GET surfaces.

**Problem:** (historical) Authentication attempts, graph reads, candidate ingestion, settings writes, and other API operations had no per-IP/user request budget or payload-cost policy.

**Risk:** Remaining un-throttled surfaces (graph reads, candidate ingestion) can still be flooded on an internet-reachable deployment; chat concurrency remains bounded per process.

**Severity:** Medium for internet exposure; Low for localhost-only use.

**Status:** RESOLVED (08-05 `1f8a3e9`) for the primary abuse surfaces — login, chat-send, and content-write are Redis-rate-limited across workers (D-14). Residual: no general rate budget on read-only/candidate routes and no payload-size caps.

**Scope:** HTTP API except the narrow in-process chat generation guard.

**Fix direction:** Add proxy- and application-level limits keyed by IP/user/route, cap extraction batch size and request bodies, return consistent 429 responses, and use a shared limiter for multi-worker deployment.

**Effort:** Days.

### 6.4 Expired and revoked sessions have no automated retention cleanup

**Files:** `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`, `spoilerless/app/services/auth.py`, `spoilerless/app/graph/seed.py` (lines 184–199), `spoilerless/app/main.py` (lines 121–150)

**Evidence:** A background sweep now runs inside the app lifespan (`spoilerless/app/main.py`, `_session_sweep_loop`, hourly): `sweep_expired()` deletes expired/revoked `:Session` nodes and the share repository's expired `ShareToken` nodes; a failed iteration is logged and never fatal. The sweep is started only when the app can reach its database.

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

---

*Concerns audit: 2026-08-12*
