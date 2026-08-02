---
last_mapped: 2026-08-02
focus: concerns
last_mapped_commit: 0b4c83c8ca7c8c0004552cb55b53a5050978c30c
---
# Codebase Concerns

**Analysis Date:** 2026-08-02

Severity follows repository impact: High means a security breach, data loss, crash, or deployment blocker; Medium means a plausible load, correctness, or maintenance failure; Low means contained debt or a non-blocking edge case. Documented future scope is identified separately from defects.

## Technical Debt

### 1.1 Starter and roadmap residue obscures the executable product

**Files:** `main.py` (lines 1–16), `frontend/README.md` (lines 1–75), `ROADMAP.md` (lines 104–116, 301–475), `backend/app/repository/settings.py` (lines 1–6), `backend/app/graph/seed.py` (lines 113–217)

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

**Scope:** Documentation and root-level scaffolding; production execution uses `backend/app/main.py` and `frontend/src/main.tsx`.

**Fix direction:** Remove or clearly label the PyCharm sample, replace the Vite template README with a pointer to the root documentation, reconcile status language without deleting canonical future scope, and correct the repository docstring to match executable DDL.

**Effort:** Hours.

### 1.2 Integration tests share the application’s live Neo4j state

**Files:** `backend/tests/conftest.py` (lines 15–18), `backend/tests/test_settings_api.py` (lines 54–98, 129–144), `backend/tests/test_candidate_review.py` (lines 18–45), `backend/tests/test_session_repository.py`

**Evidence:**
```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```
`test_settings_api.py` must back up and restore the global `:AppSetting {key:'llm'}` value, while synchronous `TestClient` requests and `asyncio.run()` cleanup require separate drivers and event loops.

**Problem:** Integration isolation depends on every fixture using collision-resistant IDs, narrowly scoped cleanup, and correct sync/async driver ownership. The suite targets the same default database as local application use rather than provisioning an ephemeral test database.

**Risk:** An interrupted or incorrectly scoped test can pollute seed state, erase user configuration, become order-dependent, or fail through cross-event-loop Neo4j driver reuse.

**Severity:** Medium.

**Scope:** Cross-cutting backend integration tests, especially settings, sessions/auth, candidates, retrieval, chat, and ChangeSets.

**Fix direction:** Provision a disposable Neo4j database/container per test run, separate unit and integration markers, centralize scratch-data factories and teardown, and keep `TestClient`-owned drivers on one portal loop.

**Effort:** Days.

### 1.3 Schema evolution is bootstrap-driven rather than migration-driven

**Files:** `backend/app/graph/seed.py` (lines 113–217, 343–360), `backend/app/graph/setup.py`, `backend/app/graph/progress.py`, `backend/app/graph/chat.py`, `backend/app/graph/change_set.py`, `backend/app/repository/settings.py` (lines 17–42)

**Evidence:**
```python
await create_constraints(database)
await seed_graph(database, data)
await audit_visibility_integrity(database, data["series"]["id"])
```
No tracked migration directory or migration runner exists. DDL is an idempotent setup routine, and persisted labels including `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, and `AppSetting` do not all have explicit identity constraints in `create_constraints()`.

**Problem:** Setup/seed can prepare the present schema but cannot express ordered data transformations, rollback steps, or a database’s applied-version history.

**Risk:** A future property rename, relationship rewrite, or uniqueness change can leave existing databases in mixed states or require undocumented manual intervention.

**Severity:** Medium.

**Scope:** All persisted Neo4j data and every repository that introduces a new label or relationship shape.

**Fix direction:** Add versioned, forward-only Neo4j migrations with an applied-migration ledger, preflight/rollback guidance, and explicit identity/index decisions for runtime-owned labels; retain setup only for fresh databases and deterministic seed content.

**Effort:** Days.

## Security

### 2.1 Candidate administration is unauthenticated and bypasses spoiler authority

**Files:** `backend/app/api/candidates.py` (lines 18–25, 79–157, 163–321), `backend/app/graph/candidates.py` (lines 35–98, 182–263), `backend/tests/test_candidate_review.py` (lines 28–107)

**Evidence:**
```python
async def ingest_candidates(series_id, envelope, repo): ...
async def approve_candidate(series_id, claim_id, repo): ...
async def reject_candidate(series_id, claim_id, repo): ...
async def edit_candidate(series_id, claim_id, body, repo): ...
```
No candidate route accepts `CurrentUserDependency`. `GET /candidates` makes `visible_until_order` optional, `GET /candidates/{claim_id}` has no boundary, and the repository returns claim, evidence, and source fields without per-hop visibility predicates. The integration tests invoke mutation routes without a session cookie.

**Problem:** Any network client that can reach the backend can ingest graph content, inspect candidate evidence from any episode, edit candidates, and promote or reject them. Candidate `visible_from_order` arrives through the extraction payload rather than a persisted user boundary.

**Risk:** Unauthorized graph poisoning and review-state mutation are possible, and future-episode claim/evidence text can bypass the spoiler boundary entirely.

**Severity:** High.

**Scope:** The complete `/api/series/{series_id}/candidates` read/write surface and candidate-derived graph content.

**Fix direction:** Require authenticated admin/reviewer authorization on every route; derive or validate episode visibility server-side; resolve the requester’s persisted progress for reads; apply claim, endpoint, evidence, source, and relationship visibility predicates on every hop; add unauthenticated, foreign-user, and hidden-equals-missing tests.

**Effort:** Days.

### 2.2 Revision reads and reverts are unauthenticated and trust a caller-supplied boundary

**Files:** `backend/app/api/revisions.py` (lines 13–17, 21–46, 58–130, 133–280), `backend/app/revisions/__init__.py` (lines 10–27, 64–90), `backend/tests/test_revisions.py` (lines 32–54, 320–350)

**Evidence:**
```python
async def list_revisions(series_id, visible_until_order, database, ...): ...
async def get_revision(series_id, revision_id, visible_until_order, database): ...
async def revert_revision(series_id, revision_id, visible_until_order, database): ...
```
These routes do not use `CurrentUserDependency` or `ProgressService`. Revision snapshots include before/after user content, and `revert_revision()` performs a managed write transaction based only on series, revision ID, and the client’s positive integer boundary.

**Problem:** A caller can submit a higher valid order than they have watched, enumerate revision snapshots, and invoke revert without proving identity or resource ownership.

**Risk:** User notes/custom content can be disclosed or mutated by unauthenticated clients; a supplied future boundary can reveal spoilery snapshot values.

**Severity:** High.

**Scope:** All revision list/get/revert operations and user-content history stored as `:Revision` nodes.

**Fix direction:** Require the authenticated user, resolve progress server-side, scope revisions to the owning `AppUser` or an explicit shared-content policy, enforce ownership inside the same revert transaction, and add direct security contract tests rather than relying on an authenticated fixture whose cookie the route ignores.

**Effort:** Days.

### 2.3 Every authenticated user can replace a shared provider target and credential

**Files:** `backend/app/api/settings.py` (lines 29–53), `backend/app/domain/settings.py` (lines 19–30, 39–77), `backend/app/services/settings.py` (lines 29–81), `backend/app/services/chat.py` (lines 74–113), `backend/app/llm/provider.py` (lines 112–123, 311–323)

**Evidence:**
```python
# settings update requires a user, but no role/owner
_user: CurrentUserDependency
# URL validation allows any host over HTTP or HTTPS, including loopback by design
_ALLOWED_LLM_URL_SCHEMES = ("http", "https")
```
One global `:AppSetting {key:'llm'}` supplies the API key and base URL for all users; stored values override environment fallbacks. Provider construction sends the stored credential to that configured host.

**Problem:** Authentication is treated as administration. Any signed-in user can redirect the shared provider to an attacker-controlled HTTP(S) endpoint or an internal/loopback service and can replace the shared API key/model.

**Risk:** A malicious or compromised user can exfiltrate the existing provider credential on a subsequent chat call, probe services reachable from the backend, disable chat for everyone, or redirect all generated content.

**Severity:** High for multi-user or internet-reachable deployment; Medium in the documented single-user local prototype.

**Scope:** Global LLM configuration and every chat request that constructs a provider from it.

**Fix direction:** Gate settings behind an explicit administrator role or deployment-only configuration; separate per-user credentials if multi-user configuration is intended; require HTTPS/host allowlists for hosted deployments; block private/link-local/metadata destinations unless an explicit local-provider mode is enabled; rotate any credential after suspected redirection.

**Effort:** Days.

### 2.4 LLM API keys are plaintext application data at rest

**Files:** `backend/app/domain/settings.py` (lines 108–127), `backend/app/repository/settings.py` (lines 17–42), `backend/app/services/settings.py` (lines 50–81)

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

**Files:** `backend/app/services/graph.py` (lines 50–110), `backend/app/spoiler/filter.py` (lines 43–187), `frontend/src/components/graph/GraphCanvas.tsx` (530 lines), `frontend/src/components/graph/graphElements.ts`

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

**Files:** `backend/app/services/chat.py` (lines 74–113), `backend/app/llm/provider.py` (lines 112–123, 164–230, 311–323, 354–480)

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

**Files:** `backend/app/services/chat.py` (lines 42–72, 147–159, 211–297)

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

**Files:** `backend/app/retrieval/pipeline.py` (853 lines), `backend/app/llm/system_prompt.py` (837 lines), `backend/app/repository/change_set.py` (816 lines), `backend/app/retrieval/tools.py` (807 lines), `backend/app/repository/user_content.py` (748 lines), `frontend/src/components/detail/DetailPanel.tsx` (797 lines), `frontend/src/components/graph/GraphCanvas.tsx` (530 lines)

**Evidence:** The largest production modules combine orchestration, normalization, validation, persistence/query definitions, UI state, dialogs, effects, and rendering. `backend/app/llm/system_prompt.py` is user-owned prompt prose and must not be casually refactored or rewritten.

**Problem:** Feature changes cross large modules with mixed abstraction levels, increasing review surface and the chance of accidental coupling.

**Risk:** Spoiler predicates, transaction behavior, prompt framing, and UI focus/layout behavior can regress during otherwise localized changes.

**Severity:** Medium.

**Scope:** Retrieval/LLM, ChangeSets/user content, and the graph/detail frontend.

**Fix direction:** Extract named query modules and narrow repository helpers; split `DetailPanel` dialogs/tabs into feature components; extract GraphCanvas lifecycle/focus/reveal hooks; protect the user-owned prompt prose while separating executable composition/guards into small tested modules.

**Effort:** Days–Weeks.

### 4.2 The configured frontend lint gate fails

**Files:** `frontend/eslint.config.js` (lines 8–30), `frontend/src/components/detail/DetailPanel.tsx` (notably lines 259, 288, 454–455, 486–510, 544, 707), `frontend/src/components/graph/GraphCanvas.tsx` (lines 168, 182), `frontend/src/hooks/useChatSessions.ts` (line 34), `frontend/src/hooks/useNotes.ts` (line 35), `frontend/src/hooks/useRevisions.ts` (line 32), related revision tests

**Evidence:** `npm run lint` reports 28 errors and 0 warnings, including render-time ref access, synchronous state updates inside effects, memoization preservation failures, and explicit `any` usage.

**Problem:** A declared quality command is red at the repository baseline, so it cannot act as a simple regression gate.

**Risk:** New violations blend into existing output, React lifecycle problems remain difficult to distinguish from deliberate workarounds, and CI cannot require a clean lint result without a cleanup phase.

**Severity:** Medium.

**Scope:** Frontend source and tests, concentrated in graph/detail state management and revision tests.

**Fix direction:** Triage behavior-affecting hook/ref findings before type-only test findings, refactor without changing graph refresh/focus semantics, establish a clean baseline, and then gate lint in CI.

**Effort:** Days.

### 4.3 Candidate review bypasses service/domain boundaries

**Files:** `backend/app/api/candidates.py` (lines 21–25, 33–73, 105–321), `backend/app/graph/candidates.py` (lines 157–263), `backend/app/domain/extraction.py`

**Evidence:** Candidate routes access `repo._db`, define transaction callbacks inline, build `dict` responses, duplicate claim projection, and translate broad `Exception` values to 422. Edit fields such as predicate/claim type/confidence are strings in a route-local model rather than shared ontology-backed domain types.

**Problem:** The API layer owns persistence transactions and validation that other features place in services/repositories.

**Risk:** Authentication, spoiler checks, ontology validation, error shaping, and revision semantics can diverge across ingest/list/get/edit/approve/reject paths.

**Severity:** Medium.

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

**Files:** `docker-compose.yml` (lines 1–27), `.env.example` (lines 1–11), `backend/app/core/config.py` (lines 7–33)

**Evidence:** Compose exposes both Neo4j ports, uses host bind mounts, embeds a local-development authentication value, and selects the broad `neo4j:2026-community` tag rather than an immutable image digest.

**Problem:** The file is suitable for local setup but is not portable production orchestration and can change underneath a rebuild as the image tag advances.

**Risk:** Production reuse can expose the database/browser, produce platform-specific bind-mount behavior, or introduce an unreviewed database image change.

**Severity:** Low because the repository documents this as local orchestration.

**Scope:** Neo4j container startup only; backend and frontend are not containerized here.

**Fix direction:** Keep this file explicitly development-only, pin a tested Neo4j patch/digest, move all credentials to runtime secret injection, and create separate production deployment manifests rather than overloading local Compose.

**Effort:** Hours–Days.

## Missing Features

### 6.1 No automated quality gate, coverage threshold, or browser E2E suite

**Files:** `pyproject.toml` (lines 18–27), `frontend/package.json` (lines 6–11, 31–50), `frontend/vite.config.ts` (lines 23–27), `backend/tests/`, `frontend/src/**/*.test.tsx`

**Evidence:** No tracked `.github/workflows/` or other CI workflow exists. Pytest has no coverage plugin/fail-under setting, Vitest has no coverage configuration/script, and no Playwright/Cypress configuration is tracked.

**Problem:** Pytest, Vitest, lint, and build are developer-invoked only. Test counts do not establish coverage, and jsdom plus backend integration tests do not exercise the real browser-to-database system.

**Risk:** Broken contracts, authentication cookies, SSE behavior, responsive sheets, or deployment-specific failures can merge without an automated gate.

**Severity:** Medium.

**Scope:** Whole repository and pull-request/release workflow.

**Fix direction:** Add CI with frozen installs, non-destructive unit suites, isolated Neo4j integration jobs, frontend build/lint, coverage reporting with an initially evidence-based threshold, and a small Playwright smoke suite for login/session, graph boundary, chat SSE, and mutation/revert paths.

**Effort:** Days.

### 6.2 Production deployment and operations are not implemented

**Files:** `docker-compose.yml`, `backend/app/main.py` (lines 40–105), `docs/DEPLOYMENT.md`, `docs/CONFIGURATION.md`, `docs/TESTING.md`

**Evidence:** The tracked repository has no backend/frontend production container definitions, reverse-proxy/TLS configuration, infrastructure manifests, monitoring/metrics stack, automated database backup job, restore drill, or release rollback automation. Application logging is limited to authentication warnings in `backend/app/api/auth.py` and `backend/app/services/auth.py`.

**Problem:** Documentation can describe deployment considerations, but no executable production topology or operational control plane exists.

**Risk:** Production launch is blocked by missing secure cookie/TLS wiring, health-based rollout, observability, backup/restore, and rollback procedures. A Neo4j or release failure has no automated recovery path.

**Severity:** High as a production-readiness blocker; not a blocker for local prototype use.

**Scope:** Backend, frontend, Neo4j, secrets, monitoring, backups, and release management.

**Fix direction:** Choose a target platform; build immutable backend/frontend images; terminate TLS; set secure cookies and strict origins; add structured logs, metrics/traces, alerts, Neo4j backups with tested restore, migration-before-rollout, and documented application/database rollback.

**Effort:** Weeks.

### 6.3 No general HTTP abuse controls

**Files:** `backend/app/main.py` (lines 58–90), `backend/app/services/chat.py` (lines 42–72), `backend/app/api/auth.py`, `backend/app/api/candidates.py`, `backend/app/api/settings.py`

**Evidence:** No rate-limit middleware or dependency is configured. The only ceiling is `_MAX_CONCURRENT_GENERATIONS_PER_USER = 1`, which protects active LLM generations in one process.

**Problem:** Authentication attempts, graph reads, candidate ingestion, settings writes, and other API operations have no per-IP/user request budget or payload-cost policy.

**Risk:** A reachable deployment can be subjected to brute-force/noise traffic, expensive Neo4j reads, oversized extraction batches, and request floods even while chat generation concurrency remains bounded.

**Severity:** Medium for internet exposure; Low for localhost-only use.

**Scope:** HTTP API except the narrow in-process chat generation guard.

**Fix direction:** Add proxy- and application-level limits keyed by IP/user/route, cap extraction batch size and request bodies, return consistent 429 responses, and use a shared limiter for multi-worker deployment.

**Effort:** Days.

### 6.4 Expired and revoked sessions have no automated retention cleanup

**Files:** `backend/app/repository/session.py`, `backend/app/services/auth.py`, `backend/app/graph/seed.py` (lines 184–199)

**Evidence:** Session lookup rejects invalid/expired records and an expiry index exists, but no tracked scheduler or startup/background job removes retained `:Session` nodes.

**Problem:** Security validation is correct at read time, but stale records accumulate indefinitely.

**Risk:** Session storage and indexes grow with login churn, increasing administrative noise and eventual query/storage cost.

**Severity:** Low.

**Scope:** Neo4j `:Session` retention only.

**Fix direction:** Add an idempotent scheduled cleanup query with retention metrics and tests; keep cleanup separate from request authentication.

**Effort:** Hours.

### 6.5 Documented future extraction work is not a present defect

**Files:** `ROADMAP.md` (lines 104–116, 447–475), `backend/app/api/candidates.py` (lines 76–157), `backend/app/domain/extraction.py`, `docs/ARCHITECTURE.md` (lines 616–635)

**Evidence:** The structured candidate ingestion and human review surface exists, while subtitle/script/podcast extraction connectors and an automated extractor do not.

**Problem:** No significant current-state defect is identified: the repository explicitly treats automated extraction as future scope, and the implemented intake contract is the preparation layer. The security and boundary defects in the existing candidate API are separate concerns documented above.

**Risk:** Misclassifying aspirational extractor work as a bug would distort priorities away from securing the already-executable intake/review endpoints.

**Severity:** Not applicable as a defect.

**Scope:** Future ingestion/connectors only.

**Fix direction:** Preserve the candidate contract, secure it first, and schedule extractor/connectors as product work with source provenance, batch limits, and review gates.

**Effort:** Product-dependent.

---

*Concerns audit: 2026-08-02*
