---
phase: 08
phase_name: "production-deployment-automated-ci-cd"
project: "HD Graf Cehennemi"
generated: "2026-08-07"
counts:
  decisions: 15
  lessons: 6
  patterns: 7
  surprises: 4
missing_artifacts: []
---

# Phase 08 Learnings: production-deployment-automated-ci-cd

## Decisions

### Deterministic CA Trust via Scheme Normalization & Certifi
Normalized the Neo4j driver connection URI from `neo4j+s://` to `neo4j://` with `encrypted=True` and `TrustCustomCAs(certifi.where())`. The Windows OS root cert store lacked the SSL.com root presented by Neo4j Aura, causing `SSLCertVerificationError`. Driver 6.x rejects explicit `trusted_certificates` on `+s` schemes (`ConfigurationError`), whereas scheme normalization enables explicit `certifi` CA trust deterministically across Windows and Render Linux environments.

**Rationale:** Resolves Windows SSL root store omission while preventing Neo4j Python Driver 6.x configuration errors.
**Source:** 08-01-SUMMARY.md

---

### Single Admin Credential Model for AuraDB Free
Adopted the single admin credential from the Aura credentials file as the runtime database credential.

**Rationale:** AuraDB Free console "Member" role is human console access only, and `CREATE USER` / custom DB role creation is denied (`CREATE USER` forbidden for `console_admin_free` role with error code 42NFF). Least-privilege DB user creation is a paid-tier ceiling on AuraDB.
**Source:** 08-01-SUMMARY.md

---

### Browser-Only BYOK (Bring Your Own Key) LLM Storage
Stored user LLM provider settings (key, base_url, model) exclusively in browser `localStorage` under `hdgraf:byok-llm-settings`. Deleted backend persistence API callers from frontend and attached settings per-request via `X-LLM-Api-Key`, `X-LLM-Base-URL`, and `X-LLM-Model` HTTP headers.

**Rationale:** Prevents storing user LLM keys in backend datastores or log files, eliminating SSRF and cross-user key leakage surfaces.
**Source:** 08-02-SUMMARY.md

---

### Selective Header Attachment for BYOK Settings
Configured `getLLMHeaders()` to always emit `X-LLM-Api-Key` when set, but attach `X-LLM-Base-URL` and `X-LLM-Model` only when non-blank.

**Rationale:** Allows the backend to treat omitted headers as signals to fall back to server environment defaults without parsing empty header strings.
**Source:** 08-02-SUMMARY.md

---

### Server-Derived Admin Role Re-Synced on Sign-In
Derived the user role (`admin` vs `user`) server-side from `ADMIN_EMAILS` membership during authentication and persisted it to Neo4j (`ON MATCH SET u.role = $role`). No request body payload can set or modify roles.

**Rationale:** Ensures administrative privileges are strictly controlled by server configuration, while allowing immediate demotion on the user's next sign-in if their email is removed from `ADMIN_EMAILS`.
**Source:** 08-03-SUMMARY.md

---

### Defensive Coalescing of Legacy User Roles
Updated `GET_USER_BY_ID_QUERY` to coalesce missing `u.role` properties to `'user'` when loading active user sessions.

**Rationale:** Prevents pre-existing user records created before the admin migration from failing schema validation when active session tokens are reused.
**Source:** 08-03-SUMMARY.md

---

### Scoped Admin Authorization Enforcement
Enforced `require_admin` dependency (returning 403 `forbidden`) exclusively on candidate approve/reject/edit, ChangeSet confirm, and `/api/settings/llm`. Kept candidate ingest/list/get and ChangeSet propose/reject/revert at standard user/authenticated scope.

**Rationale:** Scopes strict admin authorization to destructive graph modifications and system configuration while preserving non-destructive workflows for standard users.
**Source:** 08-03-SUMMARY.md

---

### Fail-Closed CSRF Origin Verification
Modified `verify_origin` to raise 403 `AUTH_ORIGIN_NOT_ALLOWED` when both `Origin` and `Referer` headers are missing on state-changing HTTP requests.

**Rationale:** Standard web browsers always supply `Origin` headers on cross-origin POST requests. Absence of both headers signals non-browser or forged client requests, requiring a fail-closed response.
**Source:** 08-04-SUMMARY.md

---

### CSRF Protection for Revocation and Logout
Added `verify_origin` dependency to `POST /api/auth/logout`.

**Rationale:** Ensures session revocation endpoints are protected against cross-site request forgery attacks alongside primary authentication endpoints like `google_auth`.
**Source:** 08-04-SUMMARY.md

---

### Redis-Backed Multi-Worker Rate Limiting with In-Memory Test Overrides
Implemented rate limiting using `fastapi-limiter` / `pyrate-limiter` with a Lua-scripted `RedisBucket` backend, keying by `request.state.user` or client IP fallback. Neutralized rate limiters in pytest runs via an autouse fixture in `conftest.py` that overrides `RateLimiter.__call__`.

**Rationale:** Provides multi-worker safe rate limiting in production shared across Render instances while keeping test suites fast, deterministic, and free of live Redis dependencies.
**Source:** 08-05-SUMMARY.md

---

### Per-Endpoint Window Multi-Bucket Rate Limiters
Created distinct `RedisBucket` instances for login (10 req / 5 min), chat-send (20 req / min), and content-write (30 req / min).

**Rationale:** Isolates traffic counters so heavy usage on chat endpoints does not trigger false rate-limit blocks on login or content creation.
**Source:** 08-05-SUMMARY.md

---

### Best-Effort Graph Cache-Aside with Write Invalidation
Implemented graph response caching (`GET /api/series/{series_id}/graph`) keyed by `graph:{series_id}:{effective_boundary}:{user_id|anon}` with a 300s TTL. Invalidated series cache keys upon candidate approval/rejection/edit, ChangeSet confirmation/reversion, and custom node/relation mutations.

**Rationale:** Significantly reduces Neo4j read query load for graph visualization while ensuring content mutations purge stale cache entries. Best-effort error handling ensures Redis glitches never fail database transactions.
**Source:** 08-06-SUMMARY.md

---

### Exclusion of User Notes from Graph Cache Invalidation
Excluded user note creation/update/deletion routes from triggering graph cache invalidations.

**Rationale:** User notes represent detail-panel content attached to nodes, and are not rendered as part of the core graph structure returned by `GraphService.fetch_graph`.
**Source:** 08-06-SUMMARY.md

---

### Redacting Request Middleware with Explicit Allowlist
Added request-logging middleware that records HTTP `method`, `path`, `status`, and `duration_ms` while allowing only safe headers (`User-Agent`, `Content-Type`, `Accept`).

**Rationale:** Prevents sensitive tokens, session cookies, and `X-LLM-Api-Key` headers from leaking into server log streams.
**Source:** 08-07-SUMMARY.md

---

### SHA-Pinned GitHub Actions CI Gate
Configured GitHub Actions CI with a throwaway `neo4j:2026.06.0-community` container for backend testing, Node 24 for frontend builds, and SHA-pinned third-party actions (`setup-uv`). Omitted deployment steps from CI.

**Rationale:** Ensures all pull requests pass type-checking, linting, and database integration tests before merge, while delegating production deployment to native Render/Vercel git triggers.
**Source:** 08-07-SUMMARY.md

---

## Lessons

### Windows Python SSL Root Omission on Neo4j Aura
Windows Python environment relies on the Windows OS certificate store, which did not include the SSL.com root CA presented by Neo4j Aura instances, raising `SSLCertVerificationError`. Using `certifi.where()` provides a self-contained, cross-platform certificate authority bundle.

**Context:** Discovered during initial Render and local deployment setup to Neo4j AuraDB Free.
**Source:** 08-01-SUMMARY.md

---

### Vercel `tsc -b` Inclusion of Test File Diagnostics
Vercel's build step executes `tsc -b` which type-checks project references including test files, whereas local development ran `tsc --noEmit` which skipped test directory references. Minor optional-chaining type issues (`options?.headers`) caused Vercel build failures despite local vitest passes.

**Context:** Discovered when deploying the BYOK frontend changes to Vercel.
**Source:** 08-01-SUMMARY.md

---

### Breaking API Changes in `fastapi-limiter` 0.2.0 Upgrade
Upgrading `fastapi-limiter` to 0.2.0 replaced the original API with `pyrate-limiter` v4 primitives, deprecating `FastAPILimiter.init` and static `RateLimiter(times, seconds)` signatures assumed in planning. Direct inspection of installed package source code was required to construct `RedisBucket` startup initializers.

**Context:** Encountered during rate-limiter implementation in Plan 08-05.
**Source:** 08-05-SUMMARY.md

---

### Requirement to Explicitly Stamp `request.state.user`
The rate-limiter identifier function expected user details on `request.state.user`, but `require_current_user` previously returned the user dict without assigning it to `request.state`. Explicitly setting `request.state.user = user` in `deps.py` was required for user-based rate limit keys to function.

**Context:** Discovered during rate-limiter integration testing in Plan 08-05.
**Source:** 08-05-SUMMARY.md

---

### Test Database Contamination from Missing Fixture Teardowns
Tests in `test_candidate_ingest.py` created candidate nodes (`Claim`, `EvidenceFragment`, `Source`) in the shared Neo4j database without cleanup, causing subsequent execution of `test_seed_idempotency.py` to fail exact node and relationship count assertions.

**Context:** Observed during full suite test runs across Phase 8 plans.
**Source:** 08-03-SUMMARY.md

---

### React-Compiler Era ESLint Strictness in CI
Integrating GitHub Actions CI revealed 30 pre-existing frontend ESLint violations caused by react-hooks v6 rules and `no-explicit-any` usage in test files that passed local development without error.

**Context:** Discovered during the initial GitHub Actions CI workflow run in Plan 08-07.
**Source:** 08-VERIFICATION.md

---

## Patterns

### Explicit Driver Scheme Normalization with `certifi`
Normalize database URIs from `neo4j+s://` to `neo4j://` with `encrypted=True` and `TrustCustomCAs(certifi.where())` to guarantee deterministic TLS trust across Windows and Linux runtime environments.

**When to use:** When connecting to Neo4j Aura or custom TLS database instances from multi-platform environments.
**Source:** 08-01-SUMMARY.md

---

### Typed LocalStorage BYOK Module
Encapsulate browser-held credentials in a dedicated module (`byok.ts`) providing typed `getStoredSettings()`, `saveSettings()`, and `getLLMHeaders()` helpers. Component UI reads state on mount, and API clients spread `getLLMHeaders()` directly into fetch headers.

**When to use:** When building client-side API key management where server persistence is avoided for security or privacy reasons.
**Source:** 08-02-SUMMARY.md

---

### Layered FastAPI Authorization Dependency
Define authorization levels as FastAPI dependencies (e.g., `RequireAdminDependency = Annotated[dict, Depends(require_admin)]`) that wrap lower-level authentication dependencies (`require_current_user`), enforcing role validation directly in endpoint function signatures.

**When to use:** When adding role-based access control (RBAC) to existing authenticated FastAPI endpoints.
**Source:** 08-03-SUMMARY.md

---

### Real-App Integration Test Auth Pattern
Create real `:AppUser` and `:Session` nodes in Neo4j using production repositories on a fresh async event loop, pass the session cookie to `TestClient`, and execute explicit teardown deletion in fixture cleanup.

**When to use:** When integration testing authenticated endpoints against a live graph database without mocking auth dependencies.
**Source:** 08-03-SUMMARY.md

---

### Autouse Class Method Test Override for Third-Party Services
Use an `autouse=True` fixture in `conftest.py` to overwrite class method implementations (such as `RateLimiter.__call__`) with no-op implementations during test execution.

**When to use:** When integrating external infrastructure services (like Redis or rate limiters) that should not execute during automated test runs.
**Source:** 08-05-SUMMARY.md

---

### Post-Transaction Best-Effort Cache Invalidation
Trigger cache clearing functions (e.g., `invalidate_series(series_id)`) strictly after database write transactions commit, wrapping all cache calls in exception handlers that log and swallow errors.

**When to use:** When implementing cache-aside architectures where database transaction integrity must never depend on cache availability.
**Source:** 08-06-SUMMARY.md

---

### Sanitized Exception Logging Pattern
In exception handlers, invoke `logger.error("handler_name", exc_info=exc)` to record the full error traceback in internal logs before constructing and returning a sanitized, sanitized JSON error response to the client.

**When to use:** In top-level HTTP exception handlers to preserve diagnostic tracebacks without exposing internal stack traces to users.
**Source:** 08-07-SUMMARY.md

---

## Surprises

### AuraDB Free Restriction on `CREATE USER`
Attempting to create separate database user accounts via Neo4j Cypher `CREATE USER` returned an unexpected `42NFF` error stating that `CREATE USER` is forbidden for the `console_admin_free` role on AuraDB Free.

**Impact:** Forced reliance on a single admin database credential for runtime connectivity, documenting the least-privilege limitation on Aura Free tier.
**Source:** 08-01-SUMMARY.md

---

### Cloudflare Proxy Connection Cutoff on SSE Streams
Enabling Cloudflare HTTP proxying (orange cloud) on the backend API domain caused long-lived Server-Sent Events (SSE) streaming connections for chat responses to terminate prematurely due to proxy idle timeouts.

**Impact:** Required switching the backend DNS record in Cloudflare to DNS-Only (gray cloud) to allow unbuffered SSE streaming.
**Source:** 08-01-SUMMARY.md

---

### `tsc -b` Failure on Test Files in Production Vercel Build
Local development builds using `tsc --noEmit` passed, but Vercel's production build failed because `tsc -b` evaluated test files that contained subtle type mismatches.

**Impact:** Required fixing optional-chaining header types in test files to unblock Vercel deployment.
**Source:** 08-01-SUMMARY.md

---

### Missing User State Stamping in Authentication Dependency
Discovered during rate limiter implementation that authenticated chat and write requests were silently falling back to IP-based rate limiting because `require_current_user` did not populate `request.state.user`.

**Impact:** Required adding `request.state.user = user` to `deps.py` to enable per-user rate limiting.
**Source:** 08-05-SUMMARY.md
