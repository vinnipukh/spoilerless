# Phase 8: Production Deployment & Automated CI/CD - Research

**Researched:** 2026-08-04
**Domain:** Zero-cost production hosting (Vercel + Render + Neo4j AuraDB Free + Upstash Redis), cross-origin cookie auth, Redis-backed rate limiting, GitHub Actions CI
**Confidence:** MEDIUM (HIGH on installed-driver/codebase facts verified directly; MEDIUM on hosted-platform behavior verified via official docs; one HIGH-impact finding — cross-origin cookies vs. Safari/Firefox third-party-cookie blocking — is flagged for user re-confirmation, see Assumptions Log A1)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hosting targets — locked, zero-cost**
- Frontend: Vercel Hobby tier (free, no card).
- Backend: Render free web service tier (free, no card). Known tradeoff accepted: sleeps after ~15 min idle, ~30-50s cold start on first request.
- Database: Neo4j AuraDB Free (managed, free forever, no card) — replaces local Docker Compose Neo4j entirely in the production path.
- Cache: Upstash Redis free tier (10k commands/day, 256MB, no card).
- Rejected: Railway (no free tier), Fly.io (requires a card).

**Email allowlist — already implemented (D-01)** — `ALLOWED_EMAILS`, checked post Google-verification. Empty = unrestricted.

**Dev-login backdoor — already removed (D-02)** — `POST /api/auth/dev` and `AUTH_DEV_CODE` deleted entirely.

**Admin role (D-03)** — `role` field (`admin` | `user`) on the user record. Admin-only: candidate review, ChangeSet approval, `/api/settings/llm` (if it survives). Claude's discretion on how the first admin is granted; must not be self-service.

**BYOK LLM chat — backend passthrough (D-04..D-08)** — Frontend collects key/base_url/model, stored only in `localStorage`, sent per-request as headers (exact names Claude's discretion, e.g. `X-LLM-Api-Key`/`X-LLM-Base-URL`/`X-LLM-Model`). Backend builds the provider per-request from headers, never persists/logs the key. Server-side env values become optional fallback only. If no header key and no fallback, chat is disabled with a clear message (AI-03).

**Production cookie/CORS/CSRF (D-09..D-12)**
- `SESSION_COOKIE_SECURE` defaults to `true`.
- Cross-origin deployment (Vercel frontend, Render backend) needs `SameSite=None; Secure` on the session cookie, without breaking `verify_origin`.
- `verify_origin`'s fail-open behavior (missing Origin/Referer → allowed) must be tightened for state-changing routes; `POST /api/auth/logout` must gain the dependency.
- `FRONTEND_ORIGINS` in production = exact deployed Vercel origin(s), no wildcard.

**Rate limiting (D-13, D-14)** — Login, chat-send, content-write endpoints need per-user/IP rate limiting, `429` in the existing error envelope. Must be correct under Render's multi-worker deployment — store must be shared across workers (Redis-backed, reusing Upstash — Claude's discretion on exact mechanism).

**Neo4j migration (D-15, D-16)** — Move to AuraDB Free; reseed via existing idempotent `backend.app.graph.setup`, no data loss. Connect via a dedicated least-privilege database role, not the Aura default admin user.

**Redis usage (D-17)** — First job: INFRA-02 graph-query response cache keyed `(series_id, effective_boundary, user_id)`, invalidated on write. Second job (D-14): rate-limit counter store. Session storage → Redis is "nice to have, not required" — Claude's discretion.

**CI/CD (D-18)** — GitHub Actions. Minimal gate: backend `pytest` + frontend build + frontend lint on every PR. No deployment automation required beyond the gate — Claude's discretion on an explicit deploy step vs. relying on Vercel/Render's native git-push auto-deploy.

### Claude's Discretion
- Exact BYOK request-header names.
- How the first admin user is granted the role.
- Whether sessions move to Redis or stay in Neo4j.
- Rate-limit exact thresholds/windows.
- Whether CI includes an explicit deploy step or relies on Vercel/Render's native git-push auto-deploy.
- Exact Neo4j least-privilege role/permission grants on Aura.

### Deferred Ideas (OUT OF SCOPE)
- Everything in `docs/PROBLEMS.md` not directly resolved by AUTH/AI/SEC/INFRA/OPS/DOCS-03 — Phase 9 (PROB-01..21).
- The 10 new features — Phase 9 (FEAT-01..10).
- Full CI/CD (dependency scanning, staged promotion, branch protection) and full observability — explicitly deferred, not this phase's OPS-01/03 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Email allowlist (already landed) | Verification only — see `backend/app/api/auth.py::_allowed_emails` (existing code, no new research needed) |
| AUTH-02 | Dev-login bypass removed (already landed) | Verification only — confirmed absent from `backend/app/api/auth.py` read this session |
| AUTH-03 | Admin role enforced on candidate review / ChangeSet approval | See Architecture Patterns → Pattern 1 (admin role + dependency), `domain/auth.py::UserPublic` verified schema |
| AUTH-04 | `/api/settings/llm` admin-gated or retired for BYOK | See Q&A 5 area is unrelated; see BYOK pattern in Architecture Patterns → Pattern 2 |
| AI-01..03 | BYOK header flow, never persisted, graceful disable | Architecture Patterns → Pattern 2 (request-scoped provider construction) |
| SEC-01 | `SESSION_COOKIE_SECURE=true` default, exact `FRONTEND_ORIGINS` | Common Pitfalls → Pitfall 3; Code Examples → cookie helper |
| SEC-02 | `SameSite=None; Secure` cross-origin cookie without breaking CSRF | Q4 research — Common Pitfalls → Pitfall 1 (third-party cookie blocking), Pattern 3 |
| SEC-03 | Redis-backed multi-worker-safe rate limiting, `429` envelope | Q5 research — Standard Stack, Code Examples → rate limiter |
| INFRA-01 | Neo4j on AuraDB Free, no exposed Compose recipe | Q1 research — Standard Stack, Common Pitfalls → Pitfall 5 |
| INFRA-02 | Upstash Redis response cache, invalidated on write | Standard Stack (redis-py client shared with SEC-03) |
| INFRA-03 | Render free tier, least-privilege DB role, explicit pool/timeout/TLS | Q1 + Q2 research — Code Examples → Neo4j driver init, Pitfall 4 |
| INFRA-04 | Vercel Hobby deploy, API routing/CORS | Q3 research — Architecture Patterns → Pattern 3, Pitfall 1/2 |
| INFRA-05 | All secrets as platform env vars | Environment Availability section |
| OPS-01 | GitHub Actions: pytest + frontend build/lint per PR | Q6 research — Code Examples → GH Actions workflow, Pitfall 6 |
| OPS-02 | External uptime check on `/health` | Open Questions (Claude's discretion tool choice) |
| OPS-03 | Structured request/error logs | Architecture Patterns → Pattern 4 |
| DOCS-03 | Rewrite `docs/DEPLOYMENT.md` for the real target | Consumes this entire document |
</phase_requirements>

## Summary

The four locked platforms (Vercel Hobby, Render free, Neo4j AuraDB Free, Upstash Redis) are all technically workable for this stack at $0 platform cost, and the existing codebase (Python 3.13, FastAPI, `neo4j==6.2.0` async driver, React 19 + Vite 8) is compatible with the versions verified in this research — no library incompatibilities found. However, one locked decision (D-10/SEC-02's plain cross-origin `SameSite=None; Secure` cookie between the default `*.vercel.app` and `*.onrender.com` subdomains) has a real, well-documented failure mode: **Safari and Firefox already block/partition third-party cookies by default in 2026**, so a plain cross-origin cookie session will not reliably authenticate Safari users out of the box. The standard, low-cost fix — putting the frontend and backend on subdomains of one shared custom root domain (e.g. `app.example.com` + `api.example.com`) — turns the cookie same-site and sidesteps the problem entirely, at the cost of a domain registration (~$10-15/yr), which is a small but real deviation from the milestone's strict "$0" framing and needs explicit user sign-off before Phase 8 planning locks it in (see Assumptions Log A1).

The second major finding concerns AuraDB Free's least-privilege requirement (D-16): Aura Free no longer supports Cypher `CREATE ROLE`/custom RBAC (removed for Free/Professional tiers) — the practical "least privilege" available is assigning a second Aura-Console-created database user the predefined **Member** role (read/write, no security-admin privileges) instead of using the original Administrator account, done through the Aura Console UI, not Cypher. This still resolves `docs/PROBLEMS.md` #36 (no more raw admin-superuser connection) even though it isn't a custom-grants RBAC setup.

Third, for Q3 (Vercel routing to Render), this research recommends **against** `vercel.json` rewrites as the primary `/api` proxy for this app specifically: Vercel's external-rewrite hard timeout is 120s, and this app's chat pipeline can legitimately run up to `llm_max_tool_rounds (4) × llm_timeout_seconds (60s) = 240s` worst case — a rewritten chat stream risks being killed mid-stream by `ROUTER_EXTERNAL_TARGET_ERROR`. Direct cross-origin `fetch` (wiring up the currently-dead `VITE_API_BASE_URL`) avoids this entirely and pairs naturally with the custom-domain cookie fix above.

**Primary recommendation:** Use custom subdomains on a shared root domain for frontend/backend (converts the cookie problem from cross-site to same-site), direct cross-origin `fetch` (not Vercel rewrites) for all `/api` calls including the chat SSE stream, a second AuraDB Console user with the `Member` role for the app's DB credentials, explicit `neo4j+s://`-scheme driver config with a short `liveness_check_timeout` to survive Aura's ~5-minute idle-connection cutoff, and `redis` (redis-py `asyncio`) + `fastapi-limiter` sharing one Upstash Redis client for both SEC-03 rate limiting and INFRA-02 caching.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session cookie issuance/validation | API / Backend | Browser / Client | Backend sets `HttpOnly` cookie; browser stores/sends it — backend owns policy (`SameSite`, `Secure`, TTL) |
| CSRF (Origin/Referer) check | API / Backend | — | `verify_origin` is a FastAPI dependency; no client-side enforcement possible |
| Admin-role authorization | API / Backend | — | Role check must happen server-side on every mutating candidate/ChangeSet/settings route |
| BYOK key storage | Browser / Client | — | `localStorage` only, per D-05; never reaches a persistence tier |
| BYOK key transport | API / Backend (receives) | Browser / Client (sends) | Header-based, request-scoped; backend must never write it past request memory |
| Rate limiting | API / Backend | Database / Storage (Redis) | Counters must be centralized (Redis) because Render may run >1 worker in the future |
| Graph query response cache | Database / Storage (Redis) | API / Backend | Cache-aside pattern: API checks Redis before hitting Neo4j |
| Neo4j connection/pooling | API / Backend | Database / Storage | Driver lives in the backend process; Aura enforces its own idle-connection policy |
| Static asset serving | CDN / Static (Vercel) | — | Vite build output served directly by Vercel's edge network |
| `/api` routing from frontend origin | Browser / Client (direct fetch) | CDN / Static (rejected: rewrite proxy) | See Summary — direct fetch avoids Vercel's 120s external-rewrite cap on chat streams |
| CI test gate | API / Backend (pytest) + Frontend (build/lint) | — | GitHub Actions runs both; needs its own throwaway Neo4j service container, not Aura |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `neo4j` (Python driver) | 6.2.0 (already pinned `>=6.2.0` in `pyproject.toml`) [VERIFIED: `uv run python -c "import neo4j; print(neo4j.__version__)"` → `6.2.0`] | Official async Neo4j driver, already in use | Official, already the project's driver — no change needed, only explicit config |
| `redis` (redis-py) | 8.1.0 current [VERIFIED: `pip index versions redis` → `8.1.0`] | Async Redis client (`redis.asyncio`) for both rate-limit counters and response cache, over Upstash's TCP/TLS endpoint | Official Redis Inc. client, ships built-in asyncio support since 5.x — no separate sync/async package split needed |
| `fastapi-limiter` | 0.2.0 current [VERIFIED: `pip index versions fastapi-limiter` → `0.2.0`] | Per-route Redis-backed rate limiting as a FastAPI dependency | Matches this codebase's existing `Depends(...)` dependency-injection style (`CurrentUserDependency`, `verify_origin`); wraps `redis.asyncio` directly, no second Redis client needed |
| `uv` | already the project's package manager (`uv.lock` at repo root) | Build/CI dependency resolution | Render natively detects a `uv.lock` and uses `uv` for the Python build automatically [CITED: render.com/changelog/added-uv-to-the-python-native-runtime] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `astral-sh/setup-uv` (GH Action) | pin to a specific release tag/commit, e.g. `v8.1.0` [CITED: docs.astral.sh/uv/guides/integration/github/, fetched 2026-08-04] | Installs `uv` in GitHub Actions runners | Backend CI job |
| `actions/checkout` | `v5`+ (repo already uses modern Actions conventions; verify latest at implementation time) | Checkout step | Every CI job |
| `actions/setup-node` | Node 24.x (current Active LTS as of Aug 2026) [CITED: Node.js release schedule, cross-checked multiple sources] | Frontend build/lint/test | Must satisfy the repo's own `jsdom` engines constraint — see Pitfall 6 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `redis` + `fastapi-limiter` | `upstash-ratelimit` + `upstash-redis` (Upstash's own Python SDKs, REST-based) [VERIFIED on PyPI: `upstash-ratelimit==1.1.0`, `upstash-redis==1.7.0`] | Upstash's REST SDKs are built for edge/serverless (no persistent TCP connection needed) — irrelevant here since Render is a persistent long-running process; a REST call per rate-limit check adds latency vs. a pooled TCP connection. Only reach for these if the backend ever moves to a serverless/edge runtime. |
| Direct cross-origin `fetch` (recommended) | `vercel.json` rewrites proxying `/api/*` to Render | Rewrites avoid a CORS preflight and can make the cookie same-origin from the browser's view, **but** Vercel's external-rewrite timeout is a hard 120s and this app's chat stream can legitimately run up to ~240s worst case — a real risk of killing in-flight chat responses. Also: Vercel's own community threads note limited control over cookie/header forwarding through rewrites. Not recommended as the sole mechanism for this app. |
| Custom root-domain subdomains (recommended) | Keep default `*.vercel.app` / `*.onrender.com` domains | Free (no domain purchase) but Safari/Firefox will not reliably persist the session cookie by default — see Common Pitfalls → Pitfall 1. This is a real product-usability tradeoff, not a hypothetical one. |
| AuraDB Console-assigned `Member` role (recommended) | Custom Cypher `CREATE ROLE` grants | Not available on AuraDB Free/Professional as of the `2025.06.2`+ change — Cypher `CREATE USER`/`CREATE ROLE` was removed for these tiers [CITED, cross-checked WebSearch summaries of Neo4j Aura docs/changelog]. `Member` is the closest available non-admin role. |

**Installation:**
```bash
# Backend (uv-managed)
uv add redis fastapi-limiter

# No new frontend packages required for Phase 8 (BYOK is a settings-UI change using
# existing patterns; custom-domain/CORS changes are config, not new dependencies).
```

**Version verification:** Verified live 2026-08-04 via `pip index versions <pkg>` against the real PyPI index (not training-data recall) — see Package Legitimacy Audit below for the same packages' registry-existence/maintainer signals.

## Package Legitimacy Audit

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `redis` | PyPI | latest `8.1.0` published 2026-07-30; package itself (`redis-py`) is a long-established Redis Inc. project, not new | Not queryable by the legitimacy tool (PyPI download counts unavailable to it) | `github.com/redis/redis-py` (official Redis org) | `SUS` (tool flag: `too-new`, `unknown-downloads` — a tooling false positive; the flag is measuring the *latest release date*, not the package's age; `redis-py` has existed for over a decade) | Approved, with `checkpoint:human-verify` per protocol (tool verdict is SUS even though manual repo check is clean) |
| `fastapi-limiter` | PyPI | latest `0.2.0` published 2026-02-06 | Not queryable (`unknown-downloads`) | `github.com/long2ice/fastapi-limiter` | `SUS` (`unknown-downloads`) | Approved, with `checkpoint:human-verify` |
| `upstash-ratelimit` (not recommended, listed for completeness) | PyPI | `1.1.0`, first published 2024-05-16 | Not queryable | `github.com/upstash/ratelimit-python` (official Upstash org) | `SUS` (`unknown-downloads`) | Not recommended (see Alternatives Considered) — no action needed |
| `upstash-redis` (not recommended, listed for completeness) | PyPI | `1.7.0`, first published 2026-03-18 | Not queryable | `github.com/upstash/redis-python` (official Upstash org) | `SUS` (`unknown-downloads`) | Not recommended — no action needed |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `redis`, `fastapi-limiter` — both verdicts are driven by the legitimacy tool's inability to fetch PyPI download telemetry (`unknown-downloads` signal), not by any actual red flag; manual verification confirms both point to their real, official GitHub source repos with long publication histories. The planner should still add a `checkpoint:human-verify` task before the `uv add` step per protocol, since the automated tool cannot clear them itself.

*Package names in this document were discovered via WebSearch/training knowledge and cross-checked against the live PyPI registry this session — per the provenance rule, they remain `[ASSUMED]`-sourced names (not Context7/official-docs-sourced) even though registry existence and repo identity were verified. Treat the package **names** as needing the same human-verify gate as any SUS-flagged package.*

## Architecture Patterns

### System Architecture Diagram

```
Browser (user)
  |
  |  1. GET app.<domain>/ (or default *.vercel.app if custom domain declined)
  v
Vercel (CDN/Static) --- serves Vite build (dist/), SPA rewrite for client routes
  |
  |  2. fetch("https://api.<domain>/api/...", { credentials: "include" })
  |     -- direct cross-origin call, NOT proxied through Vercel rewrites (see Pitfall 2)
  |     -- session cookie sent if same-site (custom domain) or SameSite=None;Secure (fallback)
  v
Render free web service (API / Backend) — FastAPI + Uvicorn, single worker
  |                                   |
  |  3. verify_origin (CSRF)         |  4. require_current_user / require_admin
  |  dependency chain                |  dependency chain
  v                                   v
  +--- Rate limiter dependency (fastapi-limiter) ---> Upstash Redis (SEC-03 counters)
  |                                                         ^
  |  5. cache-aside read/write for graph queries -----------+  (INFRA-02 response cache)
  v
Neo4j AuraDB Free (Database/Storage)
  -- connected via neo4j+s:// URI, Member-role app user (not Administrator)
  -- explicit pool/timeout config, short liveness_check_timeout (Aura idle-connection cutoff)
  |
  |  6. chat turn: tool-calling loop, up to 4 rounds x 60s LLM timeout
  v
LLM provider (BYOK: user's own key/base_url/model via request headers, or server fallback)
```

Reading the primary use case (login → browse graph → chat) end-to-end: the browser loads static assets from Vercel (step 1), then every data/API call goes directly cross-origin to Render (step 2), passing CSRF (step 3) and auth/role checks (step 4) before hitting the rate limiter (step 4.5) and either the Redis cache or Neo4j (step 5), with chat turns additionally reaching out to the BYOK-configured LLM provider (step 6).

### Recommended Project Structure
```
backend/app/
├── core/
│   ├── config.py         # add: session_cookie_samesite, redis_url, rate_limit_* settings
│   └── errors.py         # existing http_error() — reuse for new 429/403 codes
├── api/
│   ├── auth.py           # verify_origin hardening, cookie samesite becomes settings-driven
│   ├── deps.py            # add: require_admin dependency, rate-limit Depends() wiring
│   └── chat.py            # BYOK header extraction -> request-scoped provider construction
├── services/
│   └── rate_limit.py      # NEW: fastapi-limiter init + identifier/callback wiring
├── graph/
│   └── database.py        # explicit pool/timeout/TLS kwargs on AsyncGraphDatabase.driver()
└── cache/
    └── redis_client.py    # NEW: shared redis.asyncio client (rate limit + INFRA-02 cache)

.github/workflows/
└── ci.yml                 # NEW: backend pytest (with Neo4j service container) + frontend build/lint

render.yaml                # NEW: Render Blueprint (optional but recommended for reproducibility)
vercel.json                 # NEW: SPA catch-all rewrite only (not an /api proxy — see Pitfall 2)
.python-version             # NEW: pins "3.13" for both Render and local/CI consistency
```

### Pattern 1: Admin-role dependency (AUTH-03)
**What:** A `require_admin` FastAPI dependency layered on top of the existing `require_current_user`, following the exact shape already used for `CurrentUserDependency` in `backend/app/api/deps.py`.
**When to use:** Candidate approve/reject/edit, ChangeSet approval, and (if retained) `/api/settings/llm`.
**Example (pattern, not verified library code — matches this repo's existing dependency style)[VERIFIED shape cross-checked against `backend/app/api/auth.py`'s existing `CurrentUserDependency`/`verify_origin` composition pattern]:**
```python
# backend/app/api/deps.py — new dependency, same shape as require_current_user
async def require_admin(user: CurrentUserDependency) -> dict:
    if user.get("role") != "admin":
        raise http_error(403, "forbidden", "Admin role required for this action.")
    return user

RequireAdminDependency = Annotated[dict, Depends(require_admin)]
```
Note: the existing lowercase `"forbidden"` code already appears in `backend/app/core/errors.py`'s `_ERROR_SPECS[403]` [VERIFIED: `backend/app/core/errors.py:64` — `403: ("forbidden", "Forbidden.", "The request is forbidden.")`] — reuse it rather than inventing a new uppercase code, to avoid adding to the casing inconsistency PROBLEMS.md #20 already flags.

### Pattern 2: BYOK request-scoped provider construction (AI-01..03)
**What:** Instead of `get_llm_provider` reading `Settings.llm_api_key`/`llm_base_url`/`llm_model` (env-scoped, current behavior at `backend/app/services/chat.py:74`), read three request headers first and fall back to `Settings` only if all three are absent.
**When to use:** Every chat-send route.
**Example (pattern; header names are Claude's discretion per CONTEXT.md D-06):**
```python
async def get_llm_provider(
    database: DatabaseDependency,
    x_llm_api_key: Annotated[str | None, Header()] = None,
    x_llm_base_url: Annotated[str | None, Header()] = None,
    x_llm_model: Annotated[str | None, Header()] = None,
) -> LLMProvider:
    settings = get_settings()
    api_key = x_llm_api_key or settings.llm_api_key
    base_url = x_llm_base_url or settings.llm_base_url
    model = x_llm_model or settings.llm_model
    if not api_key:
        raise http_error(503, "llm_disabled", "No LLM key configured for this request.")
    # never log api_key; never write it to any repository/record
    return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model, ...)
```
This mirrors the existing "read only inside the provider constructor" comment already in `backend/app/core/config.py` [VERIFIED: `backend/app/core/config.py:56-58` — `llm_api_key: str = Field(default="", description="LLM provider API key. Read only inside OpenAICompatibleProvider.")`].

### Pattern 3: Cross-origin cookie + CSRF hardening (SEC-01, SEC-02)
**What:** Make `samesite` and `secure` on the session cookie settings-driven instead of hardcoded, and tighten `verify_origin`'s fail-open branch for production.
**Current code (verified, must change):**
```python
# backend/app/api/auth.py:119-128 — VERIFIED, hardcodes samesite="lax"
def _make_cookie(response: Response, raw_token: str, secure: bool, cookie_name: str) -> None:
    response.set_cookie(
        key=cookie_name, value=raw_token, httponly=True,
        secure=secure, samesite="lax", path="/",
    )
```
```python
# backend/app/api/auth.py:103-108 — VERIFIED, fail-open on missing Origin/Referer
    if candidate is None:
        return
```
```python
# backend/app/api/auth.py:247-260 — VERIFIED, logout has NO verify_origin dependency
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> Response:
```
**Recommended shape:** add `session_cookie_samesite: str = Field(default="lax", ...)` to `Settings`, pass it through `_make_cookie`/`_delete_cookie`; add a `strict_origin_required: bool` (or reuse an existing "is production" signal) so `verify_origin` raises instead of returning when `candidate is None` in production; add `_csrf: Annotated[None, Depends(verify_origin)]` to the `logout` route signature (matching how `google_auth` already declares it at `backend/app/api/auth.py:156` [VERIFIED]).

### Pattern 4: Structured exception logging (OPS-03)
**What:** `install_error_handlers` currently sanitizes and returns a response but never logs the original exception [VERIFIED: `backend/app/core/errors.py:143-168` — none of `constraint_handler`/`database_handler`/`validation_handler` call `logger.*`].
**When to use:** Every installed handler, plus a request-logging middleware for method/path/status/duration.
**Example:**
```python
import logging
logger = logging.getLogger(__name__)

async def database_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("database_error", exc_info=exc)  # log before sanitizing (OPS-03 requirement)
    return database_error_response(exc)
```

### Anti-Patterns to Avoid
- **Proxying `/api` through `vercel.json` rewrites for this app:** works for short requests but risks killing chat streams past Vercel's 120s external-rewrite timeout — see Pitfall 2.
- **Using the Aura Administrator account as the app's runtime credential:** defeats INFRA-03/D-16 entirely; always provision a second Console user with the `Member` role.
- **Leaving `max_connection_lifetime` at the driver default (3600s) against Aura:** Aura's idle-connection cutoff (~5 min) is far shorter — will surface as intermittent "defunct connection" errors in production, not in local dev against Compose (see Pitfall 4).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redis-backed rate limiting | A custom `INCR`+`EXPIRE` Lua script wrapped by hand | `fastapi-limiter` (`RateLimiter` dependency with custom `identifier`/`http_callback`) | Sliding/fixed-window correctness under concurrent requests is easy to get subtly wrong (race conditions between check and increment); the library already handles this atomically and integrates as a `Depends()`, matching the codebase's existing dependency-injection idiom |
| Session cookie `SameSite`/`Secure` policy | Ad hoc per-route cookie-setting logic | Centralize in `_make_cookie`/`_delete_cookie`, driven by one `Settings` field | Two cookie-setting code paths already exist (`_make_cookie`, `_delete_cookie`) — any hand-rolled per-route override reintroduces the exact "two rules for one concept" pattern PROBLEMS.md #49 already flags elsewhere in this codebase |
| CI Neo4j test database | A bespoke wait-for-Neo4j polling script | GitHub Actions `services:` container + the project's own `verify_connection()`/health-check retry (already exists in `backend/app/main.py`'s lifespan) | The repo already has connection-retry logic; a service container plus a short retry loop before `uv run pytest` is standard and avoids a second bespoke readiness mechanism |

**Key insight:** Every "don't hand-roll" item above already has a matching primitive somewhere in this codebase (dependency injection, centralized cookie helpers, connection-retry logic) — the risk in this phase is fragmenting that existing pattern across new code, not lacking a pattern to follow.

## Common Pitfalls

### Pitfall 1: Cross-origin session cookies silently fail for Safari (and privacy-hardened Firefox/Chrome) users
**What goes wrong:** `SameSite=None; Secure` is necessary but not sufficient for a cross-site cookie to actually reach the browser's cookie jar in 2026 — Safari fully blocks third-party (cross-site) cookie **setting** by default (WebKit's Intelligent Tracking Prevention has done full third-party cookie blocking since 2020 and remains the default in 2026), and Firefox's Total Cookie Protection partitions cross-site cookies per top-level site by default. Chrome still allows third-party cookies by default as of 2026 (Google abandoned its 2024 deprecation plan in April 2025) [CITED, cross-checked via two independent WebSearch queries — MEDIUM-HIGH confidence].
**Why it happens:** From every browser's perspective, a cookie `Set-Cookie`'d by `api.onrender.com` while the top-level page is `*.vercel.app` is a third-party/cross-site cookie for that subresource request — exactly the pattern ITP and Total Cookie Protection target, independent of whether the request is a deliberate `fetch(..., {credentials:'include'})` rather than a tracking pixel/iframe.
**How to avoid:** Put the frontend and backend on subdomains of one shared, custom, registrable root domain (e.g. `app.example.com` on Vercel, `api.example.com` on Render via CNAME — both platforms support custom domains/subdomains at $0 platform cost on their free tiers [CITED: Render `custom-domains` docs + Vercel `working-with-domains` docs, cross-checked]). This converts the cookie to same-site, sidestepping ITP/TCP entirely and even permitting a fallback to `SameSite=Lax`. The only cost is registering a domain (~$10-15/yr), which is outside the milestone's literal "$0 hosting" framing — **flag to the user before locking this in** (see Assumptions Log A1). If the user declines a custom domain, document Safari/strict-Firefox login breakage as a known, accepted limitation rather than silently shipping a broken auth flow for a meaningful chunk of users.
**Warning signs:** Login "succeeds" (the `POST /api/auth/google` 200s and the response `Set-Cookie` header is present) but a subsequent `GET /api/auth/me` 401s — this is the signature of the cookie never actually being stored by the browser, not a backend bug.

### Pitfall 2: Vercel `vercel.json` rewrites can kill long-running chat streams
**What goes wrong:** External-destination rewrites on Vercel have a hard 120-second timeout, after which the client receives `ROUTER_EXTERNAL_TARGET_ERROR` [CITED: Vercel `/docs/limits`, via WebSearch summary of the official limits page].
**Why it happens:** This app's chat pipeline can legitimately run up to `llm_max_tool_rounds (4, default) × llm_timeout_seconds (60, default) = 240s` in the worst case [VERIFIED: `backend/app/core/config.py:64-79` — `llm_timeout_seconds: int = Field(default=60, ...)`, `llm_max_tool_rounds: int = Field(default=4, ...)`], which exceeds Vercel's external-rewrite cap.
**How to avoid:** Route `/api` calls with a direct cross-origin `fetch` from the frontend straight to the Render backend origin (wiring up the currently-dead `VITE_API_BASE_URL` build-time variable — `frontend/.env.example` declares it but no frontend source file reads it yet, per `docs/PROBLEMS.md` #30), not through a Vercel rewrite. Keep `vercel.json` limited to the SPA catch-all rewrite (`/(.*) -> /index.html`) for client-side routing, which is unrelated to this timeout.
**Warning signs:** Chat streams that work fine for short answers but consistently die partway through longer, multi-tool-round conversations once deployed (but work locally against the dev server) — this is the fingerprint of an infra timeout, not a pipeline bug.

### Pitfall 3: `FRONTEND_ORIGINS` widening silently widens CSRF acceptance too
**What goes wrong:** `verify_origin` and CORS share one origin list (`_allowed_origins()` in `backend/app/api/auth.py:46-53`, and the same `settings.frontend_origins` in `backend/app/main.py:76-80`) [VERIFIED]. Adding a Vercel preview-deployment origin (e.g. to test a PR) to `FRONTEND_ORIGINS` for convenience also grants that origin CSRF-bypass privileges.
**Why it happens:** No separate CSRF allowlist exists — this is already flagged as PROBLEMS.md #30's last bullet.
**How to avoid:** Keep `FRONTEND_ORIGINS` in production restricted to the exact deployed origin(s) only (per D-12, already locked) — do not add preview/staging URLs to the production env var; use a separate `FRONTEND_ORIGINS` value for any preview/staging Render+Vercel deployment pair instead.

### Pitfall 4: Aura's idle-connection cutoff outlives the driver's default `max_connection_lifetime`
**What goes wrong:** The installed driver's default `max_connection_lifetime` is 3600 seconds (1 hour) [VERIFIED via runtime introspection: `AsyncGraphDatabase.driver(...)._pool.pool_config.max_connection_lifetime` → `3600`, `neo4j==6.2.0`], but Aura instances terminate idle connections after roughly 5 minutes [CITED, cross-referenced against a real-world GitHub bug report of exactly this symptom against Aura — MEDIUM confidence]. A pooled connection idle for longer than Aura's cutoff but shorter than the driver's lifetime gets reused by the driver and fails with a "defunct connection" error.
**Why it happens:** The driver only proactively recycles connections older than `max_connection_lifetime`; it does not know about Aura's shorter server-side idle timeout unless told to actively liveness-check.
**How to avoid:** Set `liveness_check_timeout` (default `None`, meaning "never check" [VERIFIED: introspected default is `None`]) to a value shorter than Aura's idle cutoff, e.g. 60-120 seconds, so idle-too-long connections are tested and replaced before use rather than failing mid-query.
**Warning signs:** Intermittent 503s from `/health` or any Neo4j-backed route specifically after a period of low traffic (e.g. right after Render's own cold start, or after a quiet overnight period), not reproducible under sustained load.

### Pitfall 5: AuraDB Free does not support custom Cypher roles — "least privilege" means something narrower here
**What goes wrong:** Planning a custom `CREATE ROLE app_readwrite` grant (the Enterprise/Business-Critical pattern) will fail on Free tier.
**Why it happens:** Cypher `CREATE USER`/role administration commands were removed from Free/Professional Aura tiers as of the `2025.06.2`+ platform change; only three **predefined** roles are selectable per database user via the Aura Console: Administrator, Member, Viewer [CITED, cross-checked WebSearch summaries of Neo4j's own Aura changelog/support content — MEDIUM confidence].
**How to avoid:** Create the app's runtime credential as a second Console-managed database user with the **Member** role (read/write to data, no security-admin capability) rather than reusing the original Administrator account created at instance provisioning. Document this Free-tier ceiling explicitly in `docs/DEPLOYMENT.md` (DOCS-03) so a future upgrade to a paid tier is understood as the path to true custom RBAC.
**Warning signs:** Any attempt to run `CREATE ROLE ...`/`GRANT ...` Cypher against the Aura instance returning a permission or "unsupported" error — this is expected on Free tier, not a misconfiguration.

### Pitfall 6: CI Node version must satisfy the repo's own `jsdom` engines constraint
**What goes wrong:** Picking an arbitrary/older Node LTS (e.g. 20) for the GitHub Actions frontend job will fail `npm ci` or produce undefined behavior in `vitest`.
**Why it happens:** `frontend/package-lock.json`'s pinned `jsdom@30.0.1` declares `"engines": {"node": "^22.22.2 || ^24.15.0 || >=26.0.0"}` [VERIFIED: `frontend/package-lock.json:5830-5832`, read this session — `"engines": { "node": "^22.22.2 || ^24.15.0 || >=26.0.0" }`], which excludes Node 20 and Node 23 entirely.
**How to avoid:** Use `actions/setup-node` with `node-version: '24'` (current Active LTS as of August 2026 [CITED, cross-checked Node.js release-schedule sources]) for the frontend CI job — satisfies the constraint and matches a maintained LTS line.
**Warning signs:** `npm ci` failing with an `EBADENGINE` warning/error, or `vitest` producing cryptic DOM-related failures only in CI, not locally.

### Pitfall 7: CI `pytest` needs its own Neo4j — it cannot point at AuraDB or the (retired) local Compose file
**What goes wrong:** OPS-01 requires `pytest` to run on every PR. This repo's existing test suite connects to a real Neo4j via `NEO4J_URI`/`NEO4J_USERNAND`/`NEO4J_PASSWORD` env vars (no mock DB layer — confirmed by `docs/PROBLEMS.md` #15, independently re-confirmed by this session's read of `backend/app/graph/database.py`, which has no test-double indirection). Pointing CI at production AuraDB would mutate/pollute prod data on every PR (and is explicitly the anti-pattern #15 already documents); pointing at the retired Compose file is a dead end since INFRA-01 removes it from the deployment path.
**Why it happens:** Test isolation from a live database (PROB-06/PROB-18) is explicitly deferred to Phase 9 — Phase 8 must not silently depend on that future work to make its own CI gate (OPS-01) function.
**How to avoid:** Add a GitHub Actions `services:` block running a throwaway, pinned-tag Neo4j container (e.g. `neo4j:2026.06.0-community` — a specific patch, not the floating `2026-community` tag PROBLEMS.md #31 already flags as a risk in the retired Compose file) scoped only to the CI job's lifetime, seeded via the existing `uv run --project backend python -m backend.app.graph.setup` before `uv run pytest` runs. This is a CI test fixture, not a "deployment path" — it does not conflict with INFRA-01/D-15.
**Warning signs:** `pytest` hanging or failing with `ServiceUnavailable`/connection-refused errors in CI specifically, with no corresponding local failure.

## Code Examples

### Neo4j driver initialization for AuraDB (INFRA-03)
```python
# backend/app/graph/database.py — recommended explicit config, replacing the
# current all-defaults call (VERIFIED current code has zero kwargs beyond auth):
#   self._driver = AsyncGraphDatabase.driver(
#       self._settings.neo4j_uri,
#       auth=(self._settings.neo4j_username, self._settings.neo4j_password),
#   )
self._driver = AsyncGraphDatabase.driver(
    self._settings.neo4j_uri,        # must be "neo4j+s://<dbid>.databases.neo4j.io"
    auth=(self._settings.neo4j_username, self._settings.neo4j_password),
    max_connection_lifetime=3600,        # driver default [VERIFIED introspected] — fine to keep
    max_connection_pool_size=50,         # reduced from driver default 100 [VERIFIED] for Free-tier headroom
    connection_timeout=30.0,             # driver default [VERIFIED] — explicit per INFRA-03
    liveness_check_timeout=60.0,         # NEW — survive Aura's ~5min idle cutoff (Pitfall 4)
    # Do NOT pass encrypted= / trusted_certificates= — the "neo4j+s://" scheme sets
    # encrypted=True automatically and raises ConfigurationError if you also pass it
    # explicitly [VERIFIED: neo4j==6.2.0 site-packages/neo4j/_async/driver.py:219-243].
)
```

### render.yaml (INFRA-03)
```yaml
# Source: github.com/render-examples/fastapi/blob/main/render.yaml, fetched verbatim
# this session, adapted for this repo's uv-managed layout and module path.
services:
  - type: web
    name: hdgrafcehennemi-backend
    runtime: python
    plan: free
    autoDeploy: true
    buildCommand: uv sync --frozen
    startCommand: uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```
Add a `.python-version` file at repo root containing `3.13` (repo currently has none — verified via directory listing) so both Render and any local `uv`/`pyenv` tooling resolve the same interpreter [CITED: render.com/docs/python-version].

### GitHub Actions CI (OPS-01)
```yaml
# Source: docs.astral.sh/uv/guides/integration/github/ (backend job pattern, fetched
# verbatim this session) + this repo's own DEPLOYMENT.md-documented test/build commands.
name: ci
on: [pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:2026.06.0-community   # pinned patch tag, not the floating "2026-community"
        env:
          NEO4J_AUTH: neo4j/ci-test-password-not-used-elsewhere
        ports: ["7687:7687"]
        options: >-
          --health-cmd "wget -q --spider http://localhost:7474 || exit 1"
          --health-interval 10s --health-timeout 5s --health-retries 10
    env:
      NEO4J_URI: bolt://localhost:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: ci-test-password-not-used-elsewhere
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
      - run: uv sync --frozen
      - run: uv run --project backend python -m backend.app.graph.setup
      - run: uv run pytest

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v4
        with:
          node-version: "24"      # satisfies jsdom's engines range — see Pitfall 6
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
      - run: npm run lint
```

### fastapi-limiter initialization + custom envelope (SEC-03)
```python
# backend/app/services/rate_limit.py — NEW. Pattern verified against
# long2ice/fastapi-limiter's README/depends.py source (fetched this session);
# re-check exact class/callback signatures against the pinned version at
# implementation time, since this library's internals have shifted across releases.
from redis.asyncio import Redis
from fastapi_limiter import FastAPILimiter
from fastapi import Request, Response

from backend.app.core.errors import http_error

async def rate_limit_identifier(request: Request) -> str:
    user = getattr(request.state, "user", None)
    return f"user:{user['id']}" if user else f"ip:{request.client.host}"

async def rate_limit_callback(request: Request, response: Response, pexpire: int) -> None:
    raise http_error(429, "too_many_requests", "Too many requests. Please slow down.")
    # reuses the SAME lowercase code already used at backend/app/api/chat.py:51
    # and backend/app/core/errors.py:72-76 [VERIFIED] — do not invent a new
    # uppercase RATE_LIMIT_* code; it would fail ErrorDetail.code's regex
    # `^[a-z][a-z0-9_]*$` [VERIFIED: backend/app/core/errors.py:25].

async def init_rate_limiter(redis_url: str) -> None:
    redis_client = Redis.from_url(redis_url)  # e.g. "rediss://default:<pw>@<host>:6379"
    await FastAPILimiter.init(
        redis_client,
        identifier=rate_limit_identifier,
        http_callback=rate_limit_callback,
    )
```
Wire `init_rate_limiter` into `backend/app/main.py`'s existing `lifespan` context manager, alongside the current `database.open()` call [VERIFIED: `backend/app/main.py:40-56` already establishes the pattern of opening resources at startup and closing them in the `finally` block].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Chrome phasing out third-party cookies by default (Privacy Sandbox) | Chrome retains today's cookie controls; user-choice prompt instead of default blocking | April 2025 [CITED] | Cross-origin cookie auth "works in Chrome" is still a valid assumption for now, but is not portable to Safari/Firefox — don't rely on Chrome-only manual testing to validate SEC-02 |
| AuraDB Free/Professional supported Cypher `CREATE USER`/role admin | Removed for Free/Professional; Console-managed predefined roles only | `2025.06.2`+ [CITED] | D-16's "dedicated least-privilege role" must be implemented via Console UI, not a Cypher migration script |
| Render Python builds required `pip`/`requirements.txt` only | Native `uv` detection via a committed `uv.lock` | Render changelog, undated but current as of this research [CITED] | `buildCommand: uv sync --frozen` is now a first-class option, matching this repo's actual tooling instead of requiring a `requirements.txt`-only fallback |

**Deprecated/outdated:** `docs/DEPLOYMENT.md`'s current "no production deployment target defined" framing (DOCS-03 replaces this) — see Q&A traceability above.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A custom root domain (shared between Vercel and Render subdomains) is the correct fix for cross-origin cookie auth, and the user will accept the small domain-registration cost outside the "$0 hosting" framing | Summary, Pitfall 1 | If the user rejects this, the plan must instead explicitly document and accept Safari/strict-Firefox login breakage as a shipped limitation — a materially different (and worse) UX outcome that should be confirmed before Phase 8 planning locks in either path |
| A2 | Aura Free/Professional's removal of Cypher `CREATE ROLE`/`CREATE USER` and its replacement with Console-only predefined roles (Administrator/Member/Viewer) is accurately summarized from WebSearch results, not a fetched primary Neo4j docs page (WebFetch to `neo4j.com/docs/aura/*` returned HTTP 403 in this environment) | Standard Stack, Pitfall 5 | If Aura's actual Free-tier role model differs (e.g. custom roles are in fact available via a UI path not surfaced by search), the "Member role via Console" recommendation may be unnecessarily restrictive or subtly wrong — verify directly against the Aura Console UI during execution before writing the DEPLOYMENT.md rewrite (DOCS-03) |
| A3 | Vercel's external-rewrite 120s timeout figure and the cookie-forwarding limitations of rewrites, as summarized by WebSearch (not a direct fetch of `vercel.com/docs/limits`, which also 403'd) | Pitfall 2, Alternatives Considered | If the actual timeout is longer (or configurable), the case against using rewrites weakens — worth a 5-minute direct check of the current Vercel limits page before finalizing the "direct fetch, not rewrites" plan decision |
| A4 | Render free-tier RAM/CPU figures (512MB / 0.1 CPU) and the "single worker recommended" conclusion drawn from them, sourced via WebSearch community/article summaries rather than Render's own primary pricing page | Standard Stack, Summary | If Render's actual free-tier allocation differs, the "don't run --workers N" guidance could be over- or under-cautious — low risk either way since SEC-03's Redis-backed rate limiter is required regardless of worker count |
| A5 | `fastapi-limiter`'s exact `RateLimiter`/`FastAPILimiter.init` API surface (parameter names for `identifier`/`http_callback`) as shown in Code Examples, assembled from a README/source fetch that itself noted the library's internals had shifted across recent releases | Code Examples → fastapi-limiter | If the pinned version's actual API differs, the example code as written won't run — re-verify against `python -c "import fastapi_limiter; help(fastapi_limiter)"` immediately after `uv add fastapi-limiter` during implementation, before writing dependent route code |

**If this table is empty:** N/A — see entries above; all five need a lightweight confirmation pass before or during implementation, none blocks starting the phase.

## Open Questions

1. **Should the domain-registration cost (Assumption A1) be raised back to the user before Phase 8 planning locks in the cross-origin cookie approach?**
   - What we know: the technical tradeoff (custom domain = reliable cross-browser auth; no custom domain = documented Safari/Firefox breakage) is now well understood.
   - What's unclear: whether the user considers a ~$10-15/yr domain an acceptable exception to the "$0 hosting" constraint, given it was framed as a hard requirement in CONTEXT.md's Specific Ideas section ("hosting cost must be $0").
   - Recommendation: surface this explicitly in `/gsd-plan-phase`'s planning pass (or a fast `/gsd-discuss-phase` follow-up) rather than the planner silently choosing one path — this is exactly the kind of decision CONTEXT.md's own locked-decision process exists to capture.

2. **Which external uptime-check tool for OPS-02?**
   - What we know: OPS-02 requires "an external uptime check polls `GET /health` ... and can alert (email/webhook)." Free-tier options exist (e.g. UptimeRobot, cron-job.org, BetterStack) but were not deeply researched this session — this is explicitly Claude's discretion territory, not a locked decision.
   - What's unclear: which specific tool best fits a $0-cost, low-maintenance setup for this project.
   - Recommendation: treat as a low-risk implementation-time choice; UptimeRobot's free tier (5-minute interval, email alerts, no card) is a reasonable default `[ASSUMED — not verified this session]`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Backend build/CI | ✓ (already the project's package manager) | project-pinned via `uv.lock` | — |
| `node`/`npm` | Frontend build/CI | ✓ (local machine has Node v24.18.0) [VERIFIED: `node --version`] | 24.18.0 locally; CI should pin `24` explicitly | — |
| Neo4j (local) | Local dev only, not this phase's production path | ✓ via `docker-compose.yml` (being retired from the *deploy* path per INFRA-01, but still fine for local dev) | `neo4j:2026-community` (floating tag — PROBLEMS.md #31 flags this; out of this phase's fix list except where it collides with CI, see Pitfall 7) | — |
| Neo4j AuraDB Free | INFRA-01, INFRA-03 | Not yet provisioned (external platform action, outside repo/tool access) | — | None — this is a hard requirement for the milestone; provisioning is a manual operator step |
| Upstash Redis | INFRA-02, SEC-03 | Not yet provisioned (external platform action) | — | None — required for both cache and rate-limit correctness under multi-worker |
| Render account | INFRA-03 | Not yet provisioned | — | None |
| Vercel account | INFRA-04 | Not yet provisioned | — | None |
| Custom domain (if A1 is accepted) | Pitfall 1 mitigation | Not yet purchased | — | Fallback: accept documented Safari/Firefox limitation instead |

**Missing dependencies with no fallback:** AuraDB Free instance, Upstash Redis instance, Render account, Vercel account — all are manual operator-side provisioning steps outside this repo's/tool's access, required before any of this phase's plans can be executed end-to-end.

**Missing dependencies with fallback:** Custom domain (Pitfall 1) has a documented fallback (accept Safari/Firefox breakage) if the user declines the purchase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.1.1+ (backend, per `pyproject.toml` dev group) [VERIFIED: `pyproject.toml:19-23`]; `vitest` 4.1.10+ (frontend, per `package.json`) [VERIFIED: `frontend/package.json:50`] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `testpaths = ["backend/tests"]`) [VERIFIED: `pyproject.toml:25-27`]; frontend vitest config not read this session — confirm location during planning |
| Quick run command | `uv run pytest backend/tests/test_auth.py -x` (backend); `cd frontend && npx vitest run <file>` (frontend) |
| Full suite command | `uv run pytest` (backend); `cd frontend && NODE_ENV=test CI=1 npm run test` (frontend, per `docs/DEPLOYMENT.md:116`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-03 | Non-admin rejected 403 from candidate/ChangeSet routes | unit/integration | `uv run pytest backend/tests/test_candidate_review.py -x` | ✅ (existing file, needs new admin-role assertions) |
| AUTH-04 | `/api/settings/llm` admin-gated or retired | unit | `uv run pytest backend/tests/test_settings_api.py -x` | ✅ (existing file, needs new assertions) |
| AI-01..03 | BYOK headers used, never persisted/logged, graceful disable | unit | `uv run pytest backend/tests/test_chat_api.py -x` | ✅ (existing file, needs new BYOK-header test cases) |
| SEC-01 | `SESSION_COOKIE_SECURE=true` default | unit | `uv run pytest backend/tests/test_auth.py -x` | ✅ |
| SEC-02 | `SameSite` cross-origin cookie + CSRF logout coverage | unit | `uv run pytest backend/tests/test_auth.py -x` | ✅ (existing file, needs new logout-CSRF + samesite assertions) |
| SEC-03 | Redis-backed 429 on rate-limit exceed | unit/integration | new file, e.g. `uv run pytest backend/tests/test_rate_limit.py -x` | ❌ Wave 0 |
| INFRA-01..05 | Aura/Render/Vercel/Upstash reachability, secrets not in repo | manual/smoke | `curl https://<render-url>/health` | N/A — platform-level, not a pytest target |
| OPS-01 | GH Actions runs pytest + build/lint per PR | CI config validation | manual review of `.github/workflows/ci.yml` on a test PR | N/A — infra config, not a unit test |
| OPS-03 | Exceptions logged before sanitized response | unit | new/extend `backend/tests/test_openapi_contract.py` or a new `test_error_handlers.py` with a `caplog` assertion | ❌ Wave 0 (or extend existing) |

### Sampling Rate
- **Per task commit:** targeted `uv run pytest backend/tests/test_<affected>.py -x` and/or `cd frontend && npx vitest run <file>`
- **Per wave merge:** `uv run pytest` (full backend), `cd frontend && npm run build && npm run lint`
- **Phase gate:** Full suite green (backend + frontend) before `/gsd-verify-work`, run against the new CI Neo4j service container pattern (Pitfall 7), not the live Aura instance

### Wave 0 Gaps
- [ ] `backend/tests/test_rate_limit.py` — covers SEC-03 (429 envelope, per-user/IP keying)
- [ ] `.github/workflows/ci.yml` — the CI workflow itself, including the Neo4j service container (OPS-01, Pitfall 7)
- [ ] Extend `backend/tests/test_auth.py` — cookie `samesite` configurability + logout CSRF dependency (SEC-02)
- [ ] Extend `backend/tests/test_chat_api.py` — BYOK header precedence over env fallback, and the "no key anywhere" disabled-chat path (AI-01..03)
- [ ] `backend/tests/test_error_handlers.py` (or extend `test_openapi_contract.py`) — exception logged before sanitized response (OPS-03)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing Google ID-token verification (`ProductionGoogleVerifier`) — Phase 8 does not change the verification mechanism, only session-cookie policy around it |
| V3 Session Management | yes | `HttpOnly` + `Secure` + settings-driven `SameSite` cookie (Pattern 3); session TTL already exists (`session_ttl_seconds`) |
| V4 Access Control | yes | New `require_admin` dependency (Pattern 1) for AUTH-03/04 |
| V5 Input Validation | yes (pre-existing) | Pydantic `extra="forbid"` models throughout `domain/*.py` — no new validation surface introduced by this phase beyond BYOK headers, which should be length/format-validated before use |
| V6 Cryptography | yes | Redis/Upstash and Neo4j/Aura connections must use TLS (`rediss://`, `neo4j+s://`) — never fall back to plaintext `redis://`/`neo4j://`/`bolt://` in production |
| V13 API and Web Service | yes | CORS narrowing (exact origins, no wildcard-with-credentials combination — PROBLEMS.md #38 flags the current `allow_methods=["*"]`/`allow_headers=["*"]` + `allow_credentials=True` combination; Phase 8 should at minimum not widen this further, though full remediation of #38 is Phase 9/PROB-17 scope) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSRF via missing Origin/Referer (fail-open) | Tampering | `verify_origin` strict mode in production (Pattern 3) — reject state-changing requests with neither header present |
| BYOK key exfiltration via attacker-controlled `base_url` header | Information Disclosure | Per-request, never-persisted key (already the D-04..D-08 design) — the SSRF surface shrinks from "any authenticated user redirects the shared operator key" (docs/PROBLEMS.md #5) to "a user can only ever exfiltrate their own key to their own chosen host," which is no longer a cross-user vulnerability |
| Rate-limit bypass via distributed IPs when unauthenticated | Denial of Service | `rate_limit_identifier` (Code Examples) keys by user ID when authenticated, falling back to IP only for anonymous requests — accept that anonymous IP-based limiting is inherently weaker, consistent with this being a lower-severity fallback tier |
| Session fixation / cross-origin cookie leakage to unintended subdomains | Spoofing | Host-only cookies (no explicit `Domain=` attribute) already avoid leaking to sibling subdomains; if a custom domain (Pitfall 1/A1) is adopted, keep the cookie scoped to the API subdomain, not the shared root domain, unless session sharing across subdomains is explicitly desired |

## Sources

### Primary (HIGH confidence)
- `backend/app/api/auth.py`, `backend/app/core/config.py`, `backend/app/core/errors.py`, `backend/app/graph/database.py`, `backend/app/main.py`, `backend/app/domain/auth.py`, `backend/app/services/chat.py`, `pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json` — read directly this session
- `neo4j==6.2.0` installed package source (`.venv/Lib/site-packages/neo4j/_async/driver.py`, `_conf.py`) — read directly + runtime introspection this session
- `pip index versions <pkg>` — live PyPI registry queries this session (`redis`, `fastapi-limiter`, `upstash-ratelimit`, `upstash-redis`)
- `github.com/render-examples/fastapi/blob/main/render.yaml` — fetched verbatim this session
- `docs.astral.sh/uv/guides/integration/github/` — fetched verbatim this session (GitHub Actions uv workflow)

### Secondary (MEDIUM confidence)
- Render docs (`render.com/docs/deploy-fastapi`, `render.com/docs/python-version`, `render.com/changelog/added-uv-to-the-python-native-runtime`) — via WebSearch summaries of official Render documentation
- Vercel docs (`vercel.com/docs/frameworks/frontend/vite` fetched directly; `vercel.com/docs/limits`, `vercel.com/docs/custom-domains`-equivalent pages via WebSearch summaries)
- Neo4j Aura changelog/support content on predefined roles and Free-tier `CREATE ROLE` removal — via WebSearch summaries, `neo4j.com/docs/aura/*` primary pages returned HTTP 403 to direct WebFetch in this environment (see Assumption A2)
- Upstash rate-limiting tutorial (`upstash.com/docs/redis/tutorials/python_rate_limiting`) — fetched directly
- `long2ice/fastapi-limiter` README/`depends.py` — fetched directly, noted as possibly version-drifted (Assumption A5)
- Third-party cookie status (Chrome/Safari/Firefox, 2026) — cross-checked via two independent WebSearch queries, consistent results

### Tertiary (LOW confidence)
- Render free-tier exact RAM/CPU figures (512MB/0.1 CPU) — community forum posts and third-party articles, not Render's own primary pricing page (Assumption A4)
- Vercel external-rewrite 120s timeout and cookie-forwarding limitations — WebSearch summaries only, primary `vercel.com/docs/limits` page returned HTTP 403 to direct WebFetch (Assumption A3)

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — package versions/existence verified live against PyPI; hosted-platform build/start commands verified via at least one direct official-source fetch each
- Architecture: MEDIUM — codebase-side patterns (cookie helper, dependency style, error envelope) are HIGH (read directly); cross-platform interaction patterns (cookie/domain, rewrite timeout) are MEDIUM, resting on cross-checked but not fully primary-source-fetched claims (several official docs pages 403'd to WebFetch in this environment)
- Pitfalls: MEDIUM-HIGH — the two highest-impact pitfalls (cross-origin cookies vs. browser third-party blocking; Aura idle-connection cutoff vs. driver defaults) are each cross-checked against multiple independent sources and, for the Aura connection-lifetime default, directly verified via runtime introspection of the installed driver

**Research date:** 2026-08-04
**Valid until:** ~30 days for the codebase-verified facts (stable); ~14 days for hosted-platform specifics (Render/Vercel/Aura free-tier terms, third-party-cookie browser policy) given these evolve faster than the codebase itself — re-verify platform-specific claims (especially Assumptions A2-A4) directly against each platform's current docs at the start of implementation, not just at planning time.
