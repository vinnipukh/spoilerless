---
phase: 08-production-deployment-automated-ci-cd
plan: 01
subsystem: infra
tags: [deploy, render, vercel, aura, dns, tls, tracer]
status: complete
completed: 2026-08-04
---

# Phase 08 — Plan 08-01 Summary: Production Hosting Skeleton (tracer)

**Backend live on Render at `api.spoilerless.net`, frontend live on Vercel at
`app.spoilerless.net`, Neo4j on AuraDB Free (instance `03a8623b`, seeded with
the Dexter S01E01-03 fixture), real Google login working end-to-end through
the custom domains — the phase's tracer slice, everything later plans build on.**

## Performance
- Duration: ~2.5h (mostly human provisioning round-trips: Aura/Render/Vercel/Upstash/Cloudflare)
- Tasks: 2 (Task 1 = human provisioning checkpoint; Task 2 = config + deploy + verify)
- Files modified: 9 (+3 created)

## Accomplishments
- `session_cookie_secure` default flipped to `True` (SEC-01) — Secure-by-default, no env override required
- `Neo4jDatabase.open()`: explicit `max_connection_pool_size=50`, `connection_timeout=30.0`, `liveness_check_timeout=60.0` for Aura's ~5-min idle-connection cutoff (Pitfall 4)
- **TLS trust fix**: `neo4j+s://` normalized to `neo4j://` + `encrypted=True` + `TrustCustomCAs(certifi.where())` — the Windows OS store lacks the SSL.com root Aura's chain presents (`SSLCertVerificationError: self-signed certificate in certificate chain`); certifi verifies the same chain. Deterministic on Windows and Linux/Render. Driver 6.x rejects explicit `trusted_certificates` on `+s` schemes (ConfigurationError), hence the scheme normalization
- `frontend/src/api/client.ts`: `apiFetch` prefixes every request with `VITE_API_BASE_URL` ('' locally → Vite proxy; origin in production)
- Created `render.yaml` (uv-based Blueprint: `uv sync --frozen` / `uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`, free plan), `frontend/vercel.json` (SPA catch-all rewrite only — no /api proxy, Pitfall 2), `.python-version` (3.13)
- `docker-compose.yml` hardened (local-dev only): ports bound to 127.0.0.1, image pinned `neo4j:2026.06.0-community`, `NEO4J_AUTH` from `${NEO4J_PASSWORD}` env
- `.env.example`/`frontend/.env.example` updated: `SESSION_COOKIE_SECURE=true` default note; `VITE_API_BASE_URL=https://api.spoilerless.net` commented (local dev uses the Vite proxy)
- Deployed: Render web service (manual, matching render.yaml commands) + Vercel project (root `frontend/`), custom domains `api.`/`app.spoilerless.net` via Cloudflare (api record DNS-only to avoid proxy idle-timeout on long SSE streams; app proxied), AuraDB reseeded
- AuraDB Free credential model verified live: console "Member" role is human console access, not a DB credential; `CREATE USER` denied on Free (console_admin_free role + 42NFF as instance admin) → **single admin credential** from the credentials file used as the runtime credential (D-16 least-privilege documented as a Free-tier ceiling, see 08-RESEARCH.md correction)

## Verification (production, live)
- `GET https://api.spoilerless.net/health` → `{"status":"ok","database":"connected"}` HTTP 200
- `GET https://app.spoilerless.net` → HTTP 200
- `GET /api/auth/me` (no session) → 401 `AUTH_UNAUTHENTICATED`
- AuraDB reseed: "Dexter graph setup complete: 41 nodes, 26 relationships"
- Human-check (user, 2026-08-04): real Google login at `app.spoilerless.net` succeeds, graph view loads; sign-out returns to login
- AUTH-01 regression proven live: Google account not on `ALLOWED_EMAILS` rejected ("This account is not authorized") — allowlist enforced in production; configured to the operator's own email after the initial `()` misconfiguration was corrected
- AUTH-02 regression: `grep` of `backend/app` for `auth/dev|AUTH_DEV_CODE|authenticate_dev|DevLoginRequest` → absent
- `git check-ignore .env frontend/.env.local` → both ignored; no secret committed (Render/Vercel platform env vars only)
- Local suites: `pytest backend/tests/test_chat_api.py backend/tests/test_auth.py` 55/55; frontend vitest 192/192 (serial) + `npm run build` (tsc -b && vite build) green

## Task Commits
1. `9cf1a4b` feat(08-01): production hosting skeleton — secure cookie default, Aura-ready driver config, API base URL wiring, Render/Vercel deploy files
2. `46b2356` fix(08-01): deterministic CA trust for neo4j+s — normalize to neo4j:// + encrypted + certifi store
3. `f89f0a5` fix(08-01): chat.test.ts optional-chain fetch init headers — TS18048 broke Vercel's tsc -b build
4. `881b90b` docs(08): correct AuraDB Free credential guidance
5. `6b3d5b8` docs(08): record live finding — CREATE USER denied on AuraDB Free
6. `768acba` docs(PROBLEMS): fact-check #55 (sibling agent's empty-client-id claim was wrong; confirmed live)

## Deviations from Plan
- **AuraDB credential**: plan's "Console Member-role user" path doesn't exist as a DB credential on Free (console roles are human access). Used the instance admin credential from the credentials file (single-credential). Recorded in 08-RESEARCH.md correction + execution finding
- **TLS**: `trusted_certificates` cannot be passed with `neo4j+s://` in driver 6.x — normalized scheme with explicit `encrypted=True` + certifi (equivalent security, deterministic)
- **Local `.env.local` migration**: `VITE_API_BASE_URL=/api` removed from `frontend/.env.local` (would double-prefix with the new apiFetch wiring); Vercel supplies the production origin
- **Test-infra fix**: `chat.test.ts` TS18048 — `options` possibly undefined under `tsc -b` project references (plain `tsc --noEmit` missed it; caught by Vercel's build)
- **ALLOWED_EMAILS**: Render env initially set to `()` (rejected all emails); corrected to the operator's email

## Issues Encountered
- Vercel build red on TS18048 (test files type-checked under `tsc -b`) — fixed + verified with `npm run build` locally
- Render crash: `NEO4J_URI: Field required` — env var missing in the first manual setup; corrected
- SSL.com root missing from Windows OS store (Aura TLS) — certifi fix (above)

## Next Phase Readiness
- 08-03 (admin role): gates the still-live `GET/PUT /api/settings/llm` endpoints; the frontend no longer calls them (BYOK, 08-02)
- 08-04 (cookie/CSRF): `verify_origin` now has a real production origin to defend
- 08-05 (rate limiting): Upstash Redis provisioned (`rediss://` URL in the operator's hands) during this plan's Task 1

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
