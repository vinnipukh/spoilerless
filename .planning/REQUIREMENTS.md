# HD Graf Cehennemi — v1.3 Production Deployment & Access Hardening Requirements

Gathered 2026-08-04, continuing directly from the completed v1.2 Spoiler-Safety
Hardening milestone. Moves the app from a local-only prototype to a real,
zero-cost hosted deployment, closing the gaps documented in
`docs/DEPLOYMENT.md`'s "Pre-production safety gaps" section and the
admin/role gap flagged in `PROJECT.md`.

## Stack Additions (locked for this milestone)

This milestone explicitly re-scopes in what v1.2's REQUIREMENTS.md locked
out: **Redis** (via Upstash, managed/free) for graph-query response caching,
and a hosted target (Vercel + Render + Neo4j AuraDB Free) replacing the
local-only Docker Compose + Uvicorn + Vite dev-server model. No other new
stack components (no second graph DB, no JWT auth, no frontend rewrite).

## Active Requirements

### Authentication & access control (AUTH)

- [x] **AUTH-01**: Only email addresses on an operator-configured allowlist (`ALLOWED_EMAILS`) can sign in via Google OAuth; a verified-but-unlisted email is rejected with `403 AUTH_EMAIL_NOT_ALLOWED`. An empty allowlist means unrestricted (any verified Google account may sign in).
- [x] **AUTH-02**: The development authentication bypass (`POST /api/auth/dev`, `AUTH_DEV_CODE`) is removed entirely from the codebase — no code path can create a session without a verified Google credential.
- [ ] **AUTH-03**: An admin role exists on the user record and is enforced on candidate review (approve/reject/edit) and ChangeSet approval endpoints; a non-admin user's request to these endpoints is rejected with a clear 403.
- [ ] **AUTH-04**: `/api/settings/llm` requires the admin role, or is retired in favor of the per-user BYOK flow (AI-01..03) — closing the SSRF/cross-user-takeover gap flagged in `PROJECT.md`'s Key Decisions.

### AI chat — bring your own key (AI)

- [ ] **AI-01**: A user can enter their own LLM provider API key (plus base URL/model) in the frontend; the value is stored only in the browser (`localStorage`) and sent per-request to the backend as a request header, never as a persisted server-side setting.
- [ ] **AI-02**: The backend never persists, logs, or writes a user-supplied LLM API key to any datastore, chat record, or log line; it exists only in request-scoped memory for the duration of a single chat call.
- [ ] **AI-03**: Chat is unavailable with a clear message (no request sent to the LLM provider) when the user has not supplied a key and no server-side fallback key is configured.

### Production security hardening (SEC)

- [ ] **SEC-01**: `SESSION_COOKIE_SECURE=true` and `FRONTEND_ORIGINS` restricted to the exact deployed frontend origin(s) in the production environment configuration.
- [ ] **SEC-02**: When frontend and backend are deployed on different origins, the session cookie uses `SameSite=None; Secure` without breaking the existing CSRF Origin/Referer check (`verify_origin`).
- [ ] **SEC-03**: Login, chat-send, and content-write endpoints (notes, custom nodes, custom relationships) enforce a rate limit per user/IP; exceeding it returns `429` in the existing error envelope.

### Infrastructure & hosting (INFRA)

- [ ] **INFRA-01**: Neo4j runs on Neo4j AuraDB Free instead of local Docker Compose in the production environment; existing seed data migrates without loss.
- [ ] **INFRA-02**: Upstash Redis caches spoiler-filtered graph query responses keyed by `(series_id, effective_boundary, user_id)`; entries are invalidated on any write that changes the underlying cached data.
- [ ] **INFRA-03**: The FastAPI backend runs on Render's free web service tier with all required environment variables (Neo4j, Redis, Google OAuth, frontend origins) configured.
- [ ] **INFRA-04**: The Vite frontend builds and deploys on Vercel's Hobby tier, reaching the Render backend through configured API routing/CORS.
- [ ] **INFRA-05**: All deployment secrets (Neo4j password, Google OAuth client credentials, Redis URL) are stored as platform environment variables on Render/Vercel/Upstash, never committed to the repository.

### Operations (OPS)

- [ ] **OPS-01**: A CI workflow runs backend `pytest` and frontend build+lint on every pull request.
- [ ] **OPS-02**: An external uptime check polls `GET /health` on the deployed backend and can alert (email/webhook) on a non-200 response or timeout.

### Documentation (DOCS)

- [ ] **DOCS-03**: `docs/DEPLOYMENT.md` is rewritten to describe the actual production target (Vercel/Render/Aura/Upstash) replacing its current "no production deployment target defined" statement, including a real rollback procedure for the hosted environment.

## Future Requirements (deferred)

- Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 is a minimal PR gate only)
- Full observability: centralized logs, metrics dashboards, incident/rollback runbook automation (OPS-02 is a single health-check ping only)
- Person / ACTED_AS / APPEARS_IN actor model (carried from v1.1/v1.2)
- Reviews, ratings, trivia, recommendations (carried from v1.1/v1.2)
- Automated ingestion/extraction from external sources (carried from v1.1/v1.2)

## Out of Scope (this milestone)

- Multi-region or high-availability hosting — single free-tier instance per service
- A paid tier / usage-based billing model for hosting costs — this milestone targets $0
- Mobile/social features
- Migrating off Neo4j, FastAPI, or React/Vite — hosting changes only, no rewrite
- Per-provider LLM proxy/normalization beyond the existing OpenAI-compatible interface

## Traceability

| Requirement | Phase |
|---|---|
| AUTH-01..04, AI-01..03, SEC-01..03, INFRA-01..05, OPS-01..02, DOCS-03 | Phase 8 — Production Deployment & Access Hardening (pending roadmap) |
