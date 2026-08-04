# Phase 8: Production Deployment & Automated CI/CD - Context

**Gathered:** 2026-08-04 (synthesized from an extended planning conversation — decisions below were made explicitly by the user during that session, not re-interviewed)
**Status:** Ready for planning

<domain>
## Phase Boundary

Get HD Graf Cehennemi live on real, zero-cost hosting behind production-grade
access control, with an automated CI gate. Covers AUTH-01..04, AI-01..03,
SEC-01..03, INFRA-01..05, OPS-01..03, DOCS-03. Does NOT cover the
`docs/PROBLEMS.md` audit remediation beyond what these requirements already
imply (that's Phase 9), and does not cover the 10 new features (also Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Hosting targets — locked, zero-cost
- **Frontend:** Vercel Hobby tier (free, no card).
- **Backend:** Render free web service tier (free, no card). Known tradeoff accepted: sleeps after ~15 min idle, ~30-50s cold start on first request — acceptable for this project.
- **Database:** Neo4j AuraDB Free (managed, free forever, no card) — replaces local Docker Compose Neo4j entirely in the production path.
- **Cache:** Upstash Redis free tier (10k commands/day, 256MB, no card).
- Rejected: Railway (no longer has a free tier, trial-credit only), Fly.io (now requires a card for any usage).

### Email allowlist — already implemented
- **D-01:** `ALLOWED_EMAILS` config field (comma-separated, case-insensitive), checked in `google_auth` after Google token verification succeeds (so rejection is based on a Google-attested email, not client input). Empty allowlist = unrestricted (any verified Google account may sign in) — this is the intended default; the user explicitly wants the site open, not invite-only, unless they later decide to populate the allowlist.
- Implementation: `backend/app/core/config.py` (`allowed_emails` field), `backend/app/services/auth.py` (`EmailNotAllowedError`, `authenticate(..., allowed_emails=...)`), `backend/app/api/auth.py` (`_allowed_emails()`, `AUTH_EMAIL_NOT_ALLOWED` 403).

### Dev-login backdoor — already removed
- **D-02:** `POST /api/auth/dev` and `AUTH_DEV_CODE` deleted entirely (route, service method `authenticate_dev`, config field, domain model `DevLoginRequest`). No debug-flag-gated variant — full removal, per `docs/PROBLEMS.md` #7 (the code found this backdoor actively armed in the live `.env`).
- Operator action still needed (not code): remove the stale `AUTH_DEV_CODE=...` line from the local `.env` file directly — outside repo/tool access.

### Admin role
- **D-03:** A `role` field on the user record (e.g. `admin` | `user`). Admin-only: candidate review (approve/reject/edit), ChangeSet approval, and `/api/settings/llm` (if that endpoint survives — see BYOK below, D-04..D-07). This closes the previously-deferred "no role infrastructure exists" gap noted in `PROJECT.md`'s Key Decisions and directly fixes `docs/PROBLEMS.md` #2 (anonymous candidate-approve = graph poisoning) and #3 (anonymous revert).
- No UI/registration flow for granting admin was discussed — Claude's discretion on how the first admin gets the role (e.g. a seed/env-configured admin email, or a one-time CLI/script). Must not be self-service (a user cannot grant themselves admin via the API).

### BYOK (bring-your-own-key) LLM chat — backend passthrough, chosen over full client-side
- **D-04:** User explicitly chose **"Backend passthrough"** over "Tam client-side" (full client-side LLM calls) when asked directly. Rationale given: keeps the existing spoiler-safe tool-calling loop entirely on the backend (unchanged architecture, no risk to the spoiler-boundary guarantee) while still achieving "zero LLM cost to the operator" and "key never persisted."
- **D-05:** Frontend: Settings UI gets fields for API key, base URL, model (provider stays `openai_compatible`, already configurable). Stored in browser `localStorage` only — never POSTed to a settings-persistence endpoint.
- **D-06:** Every chat request from the frontend includes the key/base_url/model as request headers (exact header names are Claude's discretion, e.g. `X-LLM-Api-Key` / `X-LLM-Base-URL` / `X-LLM-Model`). Backend constructs the LLM provider per-request from these headers instead of from `Settings.llm_api_key`/`llm_base_url`/`llm_model` (env). Server-side env values become an optional fallback only, not the primary path.
- **D-07:** The key must never be logged (redact in any request-logging middleware — see OPS-03) or persisted (not written to the chat message/session records in Neo4j). This directly resolves `docs/PROBLEMS.md` #5 (global shared key stealable via SSRF to an attacker `base_url`) by removing the shared-key model for the common case.
- **D-08:** If no header key is present and no server fallback is configured, chat is disabled with a clear message — no request reaches the LLM provider (AI-03).

### Production cookie/CORS/CSRF
- **D-09:** `SESSION_COOKIE_SECURE` must default to `true` (not merely be settable) — current default `false` is itself a finding (`docs/PROBLEMS.md` #8).
- **D-10:** Cross-origin deployment (Vercel frontend, Render backend — different domains) needs `SameSite=None; Secure` on the session cookie. Must not break the existing `verify_origin` CSRF check (`backend/app/api/auth.py`).
- **D-11:** `verify_origin`'s current fail-open behavior (missing Origin/Referer → request allowed through) is a named gap (`docs/PROBLEMS.md` #10) — must be tightened for state-changing routes. `POST /api/auth/logout` currently has no `verify_origin` dependency at all and must gain one.
- **D-12:** `FRONTEND_ORIGINS` in production must be the exact deployed Vercel origin(s), no wildcard.

### Rate limiting
- **D-13:** Login, chat-send, and content-write endpoints (notes, custom nodes, custom relationships) need per-user/IP rate limiting, returning `429` in the existing sanitized error envelope shape.
- **D-14:** Must be correct under Render's multi-worker deployment — the existing in-memory per-process chat concurrency slot (`services/chat.py`) is called out in `docs/PROBLEMS.md` #6 as broken under `--workers N` (each worker gets its own limit). The new rate-limit store must be shared across workers (e.g. Redis-backed, since Upstash Redis is already being introduced for INFRA-02 — reusing it here is a natural fit, Claude's discretion on exact mechanism).

### Neo4j migration
- **D-15:** Move from local Docker Compose Neo4j to Neo4j AuraDB Free. Existing seed data (Dexter S01E01-03 fixture graph) must migrate with no loss — reseed via the existing idempotent `backend.app.graph.setup` script against the Aura instance rather than a raw data dump/restore.
- **D-16:** The app should connect via a dedicated least-privilege database role, not the Aura default admin user, per `docs/PROBLEMS.md` #36.

### Redis usage
- **D-17:** Upstash Redis's first job is INFRA-02 (graph-query response cache, keyed by `(series_id, effective_boundary, user_id)`, invalidated on write). Its second job (D-14) is the shared rate-limit counter store. Session storage migration to Redis was discussed as a "nice to have, not required" — Claude's discretion whether to move sessions off Neo4j in this phase or leave that for later.

### CI/CD
- **D-18:** GitHub Actions, not another CI provider (user said "github actions" explicitly). Minimal gate: backend `pytest` + frontend build + frontend lint on every PR. No deployment automation required in this phase beyond the test/build gate (Vercel/Render's own git-integration auto-deploy is expected to handle actual deploy-on-push, not a custom GH Actions deploy step) — Claude's discretion on whether to also wire an explicit deploy step or rely on each platform's native git integration.

### Claude's Discretion
- Exact BYOK request-header names.
- How the first admin user is granted the role.
- Whether sessions move to Redis or stay in Neo4j.
- Rate-limit exact thresholds/windows.
- Whether CI includes an explicit deploy step or relies on Vercel/Render's native git-push auto-deploy.
- Exact Neo4j least-privilege role/permission grants on Aura.

</decisions>

<specifics>
## Specific Ideas

- User was explicit and firm that hosting cost must be **$0** — every infra choice was screened against "does this need a credit card / free tier only" before being accepted.
- User independently found and reported the dev-login backdoor via a working exploit snippet (`fetch('/api/auth/dev', ...)`) mid-session — treat backdoor removal as a hard requirement, not a nice-to-have, and re-verify no equivalent bypass exists anywhere else in the auth surface as part of this phase's testing.
- `docs/PROBLEMS.md` (2026-08-04 audit, committed this session) is the authoritative source for exactly which of its findings this phase's AUTH/AI/SEC/INFRA/OPS/DOCS-03 requirements resolve as a side effect — see the cross-references already written into `.planning/REQUIREMENTS.md`'s Phase 8 scope note. Do not re-fix those same findings again in Phase 9's PROB-* work (Phase 9 covers only what Phase 8 doesn't reach).

</specifics>

<canonical_refs>
## Canonical References

### Security & access-control gaps this phase must close
- `docs/PROBLEMS.md` #2, #3 (anonymous candidate-approve/revert), #5 (global LLM key SSRF/theft), #6 (no rate limiting, multi-worker-unsafe slot), #7 (dev backdoor — done), #8 (insecure cookie default), #10 (CSRF fail-open, logout uncovered), #27 & #31 (Docker Compose Neo4j exposed to the internet with hardcoded credentials), #36 (admin-superuser DB connection), #39 (no structured/error logging)
- `PROJECT.md` — Current Milestone section (v1.3 goal/target features) and Key Decisions row on the deferred global LLM Settings SSRF gap

### Deployment target and current gaps
- `docs/DEPLOYMENT.md` — "Pre-production safety gaps" section enumerates most of this phase's INFRA/SEC scope; "Detected Deployment Targets" table confirms no Dockerfiles/CI exist yet

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — Phase 8's full requirement set (AUTH-01..04, AI-01..03, SEC-01..03, INFRA-01..05, OPS-01..03, DOCS-03) with exact acceptance wording per requirement
- `.planning/ROADMAP.md` §Phase 8 — goal, dependencies (Phase 7), and the 5 success criteria this phase's plans must satisfy

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/core/config.py` (`Settings`, pydantic-settings) — add new fields here following the existing `Field(default=..., description=...)` pattern (see `allowed_emails` just added).
- `backend/app/api/auth.py` — `verify_origin`, `_make_cookie`/`_delete_cookie`, error-code constant pattern (`AUTH_*` uppercase strings) to extend for admin/rate-limit errors.
- `backend/app/services/auth.py` — `AuthService.authenticate` already takes an `allowed_emails` optional param; the same "verify, then policy-check" shape fits admin-role checks.
- `backend/app/llm/provider.py` — `OpenAICompatibleProvider` already reads provider config from `Settings`; BYOK needs this to become request-scoped instead of settings-scoped.
- `backend/app/api/chat.py`, `backend/app/services/chat.py` — chat route/service where BYOK headers must be threaded through to provider construction.

### Established Patterns
- Error envelope: `http_error(status, CODE, message)` from `backend/app/core/errors.py`, uppercase `CODE` constants defined per-router (contradicts the lowercase-only `ErrorDetail.code` regex per `docs/PROBLEMS.md` #20 — out of scope for Phase 8 unless it blocks a new error code; if so, flag it).
- CORS/session config is read once from `get_settings()` at router level (`backend/app/main.py`) — any new prod-mode branching should follow the same `Settings`-driven pattern, not hardcoded environment checks.

### Integration Points
- Frontend `frontend/src/api/client.ts` — central `apiFetch` wrapper; BYOK headers should be attached here (or a chat-specific client) rather than per-call.
- `frontend/src/components/settings/SettingsPage.tsx` — existing global-LLM-settings UI; BYOK likely replaces or significantly changes this page's purpose (per-user client-side key entry instead of admin-configured server key).

</code_context>

<deferred>
## Deferred Ideas

- Everything in `docs/PROBLEMS.md` not directly resolved by AUTH/AI/SEC/INFRA/OPS/DOCS-03 (ownership binding on user content, session-ID collision fix, test-suite isolation from the live DB, frontend lint debt, stale-doc corrections beyond DOCS-03/04's split, etc.) — Phase 9 (PROB-01..21).
- The 10 new features (search, timeline, etc.) — Phase 9 (FEAT-01..10).
- Full CI/CD (dependency scanning, staged promotion, branch protection) and full observability (metrics/tracing/log aggregation) — explicitly deferred in `.planning/REQUIREMENTS.md`'s Future Requirements, not this phase's OPS-01/03 scope.

</deferred>

---

*Phase: 08-production-deployment-automated-ci-cd*
*Context gathered: 2026-08-04*
