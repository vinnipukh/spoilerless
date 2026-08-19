# 2026-08-15 Security Audit — S1 Architecture & Attack-Surface Map (condensed)

Full report: `.planning/quick/20260814-security-audit/findings/S1-architecture.md`.
Static analysis only; `.env` values never read (key names only); no DB/network calls.

## Verified facts (re-check before trusting drift)

- **Route count: 53 HTTP routes** = 52 OpenAPI operations over 39 path templates (locked by
  `spoilerless/tests/test_frontend_contract_doc.py:109-110` — if that test changes, the count
  changed) + 1 schema-hidden `HEAD /health` (`app/main.py:237`).
- **Auth split:** 17 public · 8 optional-user (anonymous fixed at boundary 1) · 19 any-user · 5 admin-only ·
  1 token-gated (share) · 3 auth endpoints. Admin gate = `RequireAdminDependency` on `ADMIN_EMAILS`
  membership (`api/deps.py:100-117`).
- **Trust boundaries: 14** (TB-01…TB-14 in report). The 8-field annotation format used:
  SOURCE → DATA → TRANSPORT → DESTINATION → VALIDATION → AUTHORIZATION → STORAGE/USE.
- **Stack:** FastAPI 0.140.7 / Python ≥3.13 (uv), uvicorn 0.51.0, neo4j driver 6.2.0
  (`neo4j+s://` → TLS via certifi, `graph/database.py:74-96`), redis 8.1.0 (Upstash `rediss://`),
  google-auth 2.56.0, fastapi-limiter 0.2.0 (pyrate-limiter rewrite — no `FastAPILimiter.init`
  API anymore), React 19.2.7 / Vite 8.1.1 / TS 6.0.2 / Cytoscape 3.34.
- **Deployment:** Render free web service (`render.yaml`, single worker) + Vercel SPA rewrite
  (`frontend/vercel.json`) + Cloudflare DNS; domains `app.spoilerless.net` / `api.spoilerless.net`.
  Dev proxy: Vite `/api` → `http://127.0.0.1:8000`.

## Entry-point enumeration recipe (worked well, reuse)

1. `wc -l` all `spoilerless/app/api/*.py` + `frontend/src/api/*.ts` to plan reads.
2. `main.py` for router registration order, middleware (CORS/security headers/logging), static mounts,
   lifespan tasks (hourly session+share sweep, `main.py:131-140`), error-handler installs.
3. `api/deps.py` for the auth dependency vocabulary: `CurrentUserDependency`, `OptionalUserDependency`,
   `RequireAdminDependency`, `CsrfGuardDependency` (`verify_origin`, fail-closed on missing Origin/Referer).
4. Every router: `@router.<verb>` + decorators (auth deps, rate limiters, `_csrf`).
5. Frontend `api/*.ts` cross-check (all use `credentials:'include'`, `VITE_API_BASE_URL` prefix).
6. Verify route-count claims against the OpenAPI contract test — it's the source of truth.

## Key findings (deep-dive targets for S2/S4/S5/S8/S9)

1. **BYOK = authenticated SSRF primitive:** any logged-in user sets `X-LLM-Base-URL` (any http/https host,
   loopback/private IPs explicitly allowed by design — `app/domain/settings.py:26-33,62-81`); backend
   httpx streams to it (`app/services/chat.py:77-178`, `app/llm/provider.py`). Headers never logged
   (`main.py:43-44`), never persisted.
2. **`/docs`, `/redoc`, `/openapi.json` exposed** — `main.py:164-168` does not disable them.
3. **Candidate ingest = any authenticated user** (`api/candidates.py:95-142`, deliberate, attribution via
   revisions); approve/reject/edit are admin-only. Check `ALLOWED_EMAILS`/`ADMIN_EMAILS` non-empty in prod.
4. **Anonymous reads unthrottled:** graph/viz/expand/export/path/candidates/notes/custom-*; only
   login (10/5min/IP), chat (20/min/user), content-write (30/min) are rate-limited; expansion
   deliberately uncached (`api/graph.py:358-360`).
5. **`httpx` is a dev-group-only dependency** (`pyproject.toml:22-26`) but imported at module level by
   `llm/provider.py:18` — works only because Render's `uv sync --frozen` installs dev deps.
6. **`AUTH_DEV_CODE` vestigial** — present in local `.env`, zero code references (PROBLEMS.md #7
   backdoor confirmed removed).
7. `POST /graph/path` (`api/graph.py:466-499`) is the only POST without `CsrfGuardDependency`
   (read-only, so low risk, but inconsistent).
8. Session cookies: HttpOnly + Secure + SameSite=Lax, 7-day TTL, no slide-on-read, SHA-256 stored,
   48-byte tokens (`core/tokens.py`, `repository/session.py`). Share tokens 32-byte, 30-day TTL.
9. Redis cache keys: `graph:{series}:{boundary}:{user|anon}`, `viz:...` epoch+focus-signature
   validated on read (poisoned entries → miss, `cache/graph_cache.py:212-222`); `graph_revision`
   epoch bump on every write invalidation.
10. LLM context budget caps: 40 items / 12,000 chars (`core/config.py:126-133`); tool traversal
    depth ≤3, hops ≤4, results ≤25 (`retrieval/tools.py:27-32`); per-user concurrent generation
    limit = 1, in-process dict (breaks across multi-worker).
