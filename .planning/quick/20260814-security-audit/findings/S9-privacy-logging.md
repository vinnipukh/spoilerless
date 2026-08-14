# S9 — Privacy, Logging & Information Disclosure Audit

**Auditor:** S9 (subagent) · **Date:** 2026-08-14 · **Scope:** spoilerless/ backend + frontend/src (static analysis only; no live requests) · **Repo:** hdgrafcehennemi (Spoilerless)

**Areas:** (1) logging content, (2) `/health` endpoint, (3) error-response disclosure, (4) frontend logging/storage/telemetry, (5) LLM/chat data handling & retention, (6) session data, (7) security headers.

**Overall posture:** unusually strong. Request logging is an allowlist that excludes cookies/Authorization/X-LLM-*/bodies; session raw tokens are never stored (SHA-256 hash only); the LLM API key never appears in logs, responses, or revisions; the error envelope is sanitized with canonical codes; the frontend has zero console.log in src/, zero Sentry/telemetry, and chat content never touches localStorage/sessionStorage. Findings below are mostly hardening/retention items, plus two genuine data-in-logs issues (validation inputs, PII emails).

---

## Findings

### SEC-LOG-001 — Raw submitted values (chat questions, Google ID-token JWTs) written to server logs on validation failure
- **Severity:** Medium | **Confidence:** High
- **Component:** `spoilerless/app/core/errors.py:234` (`validation_handler` → `logger.error("validation_error", exc_info=exc)`)
- **Entry point:** any POST/PUT/PATCH body that fails pydantic validation — e.g. `POST /api/series/{id}/chat/sessions/{sid}/messages` with `question` > 4000 chars (`domain/chat.py:107`), or `POST /api/auth/login` with a malformed `credential` field.
- **Data flow:** client request body → FastAPI `RequestValidationError` → `logger.error(..., exc_info=exc)` → server log line whose exception text is `str(exc)` = `json.dumps(errors())`.
- **Vulnerability:** FastAPI's `RequestValidationError.errors()` includes an `input` key with the full rejected value, and `str(exc)` serializes it. Empirically verified against the installed FastAPI: `str(err)` contains the raw 20-char input. There is no debug-gating: this fires in production.
- **Attack scenario:** (a) Any client sends an oversized `question` — the full chat message text (possibly containing personal info) is persisted verbatim in server logs with no retention policy. (b) A malformed Google `credential` body (e.g. non-string type) writes the submitted JWT/ID-token material into logs — credential-adjacent material at rest in log storage (log vendor, SIEM). (c) Logs are routinely shipped to third parties; this makes chat/PII part of the log-data processing pipeline without notice.
- **Impact:** PII and chat content at rest in logs; ID-token material in logs; violates data-minimization; GDPR/noticed-processing exposure.
- **Reproduction:** `curl -X POST <api>/api/series/s/chat/sessions/s/messages -H 'Authorization: Bearer <user-session>' -d '{"question": "<4001 chars>"}'` → inspect server log line `validation_error`.
- **Existing defenses:** Error envelope returned to the client is generic (`INVALID_REQUEST`); only server-side logs are affected. No other body logging exists.
- **Recommended fix:** log sanitized validation metadata only: `logger.error("validation_error", extra={"errors": [{k: e[k] for k in ("loc","msg","type")} for e in exc.errors()]})` — drop `input`/`ctx`; or redact `input` for sensitive fields. Add a log-redaction policy for `credential`, `password`, `token`, `question` fields.
- **Verification:** send oversized question in a test; assert the log record contains `msg`/`loc` but not the question text.

### SEC-LOG-002 — PII (Google email addresses) logged on every denied sign-in attempt
- **Severity:** Low | **Confidence:** High
- **Component:** `spoilerless/app/api/auth.py:137` — `logger.warning("google_auth: email_not_allowed (%s)", exc.email)` (also `:144` `str(exc)` for verification errors, which can carry email context)
- **Entry point:** `POST /api/auth/login` with a verified Google credential whose email is outside `ALLOWED_EMAILS`.
- **Data flow:** Google ID token → email extracted in `services/auth.py` → `EmailNotAllowedError(email)` → log line with plaintext email.
- **Vulnerability:** full email addresses (PII) written to server logs on each rejected sign-in, without expiry/redaction; enables account-enumeration forensics against the log store and is unnecessary data at rest.
- **Attack scenario:** attacker mass-tries Google accounts; every rejected email persists in logs; log compromise leaks the full set of attempted identities. Low direct impact (no passwords/keys), but PII at rest without retention policy.
- **Impact:** PII in logs; operational necessity is real (admin needs to see who was rejected) but the plaintext-full-email form is avoidable.
- **Reproduction:** reject a sign-in with an email not in `ALLOWED_EMAILS`; observe log line.
- **Existing defenses:** allowlist is the primary control; logging is intentional (debugging aid).
- **Recommended fix:** log a redacted form (`a***@domain`) or hash; keep full email only at DEBUG level or behind an admin log sink.
- **Verification:** unit-test the auth failure path asserting the log record contains no full email.

### SEC-LOG-003 — BYOK LLM API key persisted in plaintext localStorage (browser)
- **Severity:** Medium | **Confidence:** High (fact); intentional design per D-06/AI-01
- **Component:** `frontend/src/lib/byok.ts:15` (`BYOK_STORAGE_KEY = 'spoilerless:byok-llm-settings'`, `saveLLMSettings` writes `api_key` raw) and `frontend/src/components/settings/SettingsPage.tsx:38` (form reads/writes it)
- **Entry point:** user saves LLM settings in the Settings page.
- **Data flow:** settings form → `JSON.stringify({api_key, ...})` → `localStorage` → on every chat request `getLLMHeaders()` sends it as `X-LLM-Api-Key` to the backend (backend forwards to the user's chosen provider endpoint).
- **Vulnerability:** any XSS (e.g. via a future third-party script, hotlinked image exfil chain, browser extension, or shared-device user) reads the key from localStorage. The CSP restricts script-src but the app already loads Google's third-party script, and one injection point anywhere in the SPA yields the key.
- **Attack scenario:** stored XSS or malicious extension → `localStorage.getItem('spoilerless:byok-llm-settings')` → attacker spends the user's LLM provider quota / bills the user's account / exfiltrates key to abuse other services.
- **Impact:** credential theft; financial/quota abuse of the user's LLM account. No server-side compromise (backend never logs or persists the header — verified).
- **Reproduction:** open devtools on a page with saved BYOK settings: `localStorage.getItem('spoilerless:byok-llm-settings')` returns the plaintext key.
- **Existing defenses:** documented BYOK tradeoff (D-06, AI-01); key only ever travels to the user's configured endpoint; CSP mitigates script injection; backend request-log middleware explicitly drops `x-llm-*` headers.
- **Recommended fix:** accept and document (it is a UX-driven BYOK design), but mitigate: (a) consider sessionStorage (key lost on tab close — user re-enters), or (b) keep localStorage but add an explicit XSS-risk warning in the settings UI, and (c) ensure no third-party script (beyond Google Identity) is ever added to the SPA.
- **Verification:** code review of `byok.ts` + settings UI; no automated test needed for a documented tradeoff.

### SEC-LOG-004 — `/docs` and `/openapi.json` exposed unauthenticated (API schema disclosure)
- **Severity:** Low | **Confidence:** High
- **Component:** `spoilerless/app/main.py:164-168` — `FastAPI(title="Spoilerless API", version="0.1.0")` with default `docs_url="/docs"`, `openapi_url="/openapi.json"`, `redoc_url="/redoc"`.
- **Entry point:** `GET /docs`, `GET /openapi.json` (no auth).
- **Data flow:** request → FastAPI default schema routes → full OpenAPI document.
- **Vulnerability:** the complete API surface — every route, parameter, schema, and the canonical error-code registry — is served to unauthenticated clients, including on the production deployment.
- **Attack scenario:** attacker enumerates endpoints and request shapes for targeted probing (e.g. exactly how to hit `/chat/.../messages/stream`, which error codes exist); reduces recon cost to zero. No secret material is in the schema, so impact is limited to information disclosure.
- **Impact:** aids reconnaissance; also confirms framework/version fingerprint (`0.1.0`).
- **Reproduction:** `curl https://<host>/openapi.json`.
- **Existing defenses:** none (defaults left in place).
- **Recommended fix:** `FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)` in production, or gate behind an admin token; keep enabled in dev via env flag.
- **Verification:** request `/docs` after change → 404.

### SEC-LOG-005 — `/health` discloses internal service name and DB reachability
- **Severity:** Low | **Confidence:** High
- **Component:** `spoilerless/app/main.py:222-234` (`health_check`) + `HealthResponse` (`:104-109`); `SERVICE_NAME = "spoilerless-backend"` (`:38`)
- **Entry point:** `GET /health`, `HEAD /health` (unauthenticated, intended for uptime monitors).
- **Data flow:** none — response is constructed from app state.
- **Vulnerability / exposure:** the response is minimal and well-shaped: `{status: ok|degraded, database: connected|unavailable, service: "spoilerless-backend"}`. No DB name, no version, no env name, no redis info, no host details. The `service` field leaks the internal service identifier, and the `database` field + 200/503 split tells an attacker whether Neo4j is reachable right now.
- **Attack scenario:** attacker monitors `/health` to time DB outages against exploit windows; uses the service name for internal-name guessing in other endpoints. Marginal, but unnecessary.
- **Impact:** infra fingerprinting (very mild).
- **Reproduction:** `curl https://<host>/health` → `{"status":"ok","database":"connected","service":"spoilerless-backend"}`.
- **Existing defenses:** `extra="forbid"` on the model; fixed literal values; no config/env/version leakage — this is close to the ideal health payload.
- **Recommended fix:** drop `service` (or make it a generic public name), keep status + database. Optionally return 503 only for true DB outage (already the case).
- **Verification:** response-model test asserting exact field set.

### SEC-LOG-006 — No TrustedHostMiddleware (Host header not validated)
- **Severity:** Low | **Confidence:** Medium (no absolute-URL-from-Host generation found)
- **Component:** `spoilerless/app/main.py` middleware stack (`:215-216`) — only CORS + custom security-headers + request-logging middlewares.
- **Entry point:** any HTTP request.
- **Data flow:** `Host` header → accepted by Starlette; never validated.
- **Vulnerability:** Host-header injection is unfiltered. The app does not appear to generate absolute URLs from the Host header (share URLs are relative: `api/share.py:88` `f"/share/{raw_token}"`), so classic cache-poisoning/password-reset-link poisoning is not currently reachable; the risk is DNS-rebinding against cookie-authenticated endpoints (SameSite=Lax + CSRF origin guard mitigate) and future regressions.
- **Attack scenario:** rebinding attack against a user's session via a malicious origin pointing at the app's IP; mitigated today by the Origin/Referer CSRF guard on state-changing routes but not by host validation.
- **Impact:** defense-in-depth gap; low immediate exploitability.
- **Reproduction:** `curl -H "Host: evil.example" https://<host>/api/series/...` — accepted.
- **Existing defenses:** CORS allowlist, CSRF origin guard (`api/deps.py:150`), SameSite=Lax cookie.
- **Recommended fix:** `app.add_middleware(TrustedHostMiddleware, allowed_hosts=[...frontend origins' hosts...])`.
- **Verification:** request with foreign Host → 400.

### SEC-LOG-007 — Chat conversations stored indefinitely in Neo4j; full history transmitted to third-party LLM provider every turn
- **Severity:** Medium (privacy/governance) | **Confidence:** High
- **Component:** `spoilerless/app/repository/chat.py` (message CREATE/DELETE), `spoilerless/app/services/chat.py:306-321` (history load + message persistence), `spoilerless/app/retrieval/pipeline.py` (history → provider), `spoilerless/app/llm/provider.py:146-152` (payload with full `messages`)
- **Entry point:** any chat turn (`/messages` or `/messages/stream`).
- **Data flow:** user question + full prior conversation → (a) persisted as `(:ChatMessage)`-style nodes in Neo4j with `visible_until_order_snapshot`, `status`, citations, graph_focus; (b) transmitted in full to the configured LLM endpoint (BYOK user endpoint or server-side `LLM_*` config).
- **Vulnerability / gaps:** (a) **No retention policy** — messages live until the user deletes the session (hard delete exists, `delete_session`), there is no TTL, no bulk-delete/export, no "delete account" flow that also purges chat; (b) **third-party processing** — every turn ships the entire conversation history to an external provider without any user-facing privacy notice in the app; the BYOK path lets the user choose the endpoint, but the server-key path (persisted `:AppSetting` llm key) sends data to a provider the user never chose.
- **Attack scenario:** long-lived accounts accumulate years of private reading/chat data in Neo4j (compromise of the DB = full conversation history); regulatory request (GDPR erasure) has no automated path beyond per-session delete.
- **Impact:** data-at-rest accumulation; un-noticed third-party data processing; erasure/export burden.
- **Reproduction:** send 3 messages, query Neo4j — all persist; no expiry property exists on messages.
- **Existing defenses:** per-session hard delete; boundary snapshotting limits what older messages reveal (messages only returned up to `visible_until_order`); sessions have TTL+sweep (sessions, not messages).
- **Recommended fix:** add a documented retention policy (e.g. messages older than N days are eligible for sweep, mirroring `sweep_expired`), a privacy notice covering LLM-provider processing, and a user-facing "delete all chat data" action.
- **Verification:** add `sweep_old_messages` test with TTL property.

### SEC-LOG-008 — Internal user IDs in Redis cache and rate-limit keys (transient identifiers)
- **Severity:** Low | **Confidence:** High
- **Component:** `spoilerless/app/cache/graph_cache.py:71-72` — `_cache_key` = `f"graph:{series_id}:{effective_boundary}:{user_id or 'anon'}"`; `spoilerless/app/services/rate_limit.py` — `key = f"{rate_key}:{bucket_key}"` where `rate_key` resolves to the authenticated user id (`rate_limit_identifier`).
- **Entry point:** authenticated graph reads; chat sends; login attempts (IP-keyed).
- **Data flow:** user id (internal UUID) → Redis keys (Upstash) with TTLs (`setex`), plus `EPOCH_KEY_PREFIX` invalidation counters.
- **Vulnerability:** user identifiers at rest in a third-party Redis (Upstash) with no explicit data-processing agreement review; also graph responses cached per-user-boundary are keyed by id but the payload itself is series data (not user PII) — no cross-user leak found. Rate-limit ZSETs leak identifiers in the reverse direction (which ids are active users).
- **Impact:** minimal; transient; PII-adjacent identifiers in third-party infra.
- **Reproduction:** `redis-cli keys 'graph:*'` on the Upstash instance.
- **Existing defenses:** TTLs on all values; keys are opaque UUIDs.
- **Recommended fix:** accept (low risk) or document Upstash data processing; optionally hash the user id in cache keys.
- **Verification:** none required beyond documentation.

### SEC-LOG-009 — Uvicorn default access log logs client IPs (in addition to app's sanitized middleware line)
- **Severity:** Low | **Confidence:** Medium (deployment-dependent)
- **Component:** `render.yaml:10` — `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` (default access log enabled; no `--no-access-log`).
- **Entry point:** every HTTP request.
- **Data flow:** client IP → uvicorn access log line (alongside the app's own INFO line that intentionally omits IP).
- **Vulnerability:** client IPs (personal data under GDPR-style regimes) are logged at the platform layer by default; the app-level middleware deliberately avoids IP logging, so this partially undoes that intent.
- **Attack scenario:** log-store compromise correlates IPs with timestamps/routes → user activity profiles.
- **Impact:** IP PII at rest in platform logs.
- **Reproduction:** check Render log stream during any request.
- **Existing defenses:** app middleware logs no IP; IPs are only used transiently for rate limiting.
- **Recommended fix:** `--no-access-log` in production (app middleware already covers the useful request line), or accept and document.
- **Verification:** request once with `--no-access-log`, confirm no IP line in uvicorn output.

---

## Verified controls (no action needed — audit evidence)

- **Request logging allowlist** — `main.py:76-101`: logs method/path/status/duration + only `user-agent`, `content-type`, `accept`. Explicitly denies `cookie`, `set-cookie`, `authorization`, any `x-llm-*` header, and never logs bodies (`_DENIED_HEADER_PREFIXES`/`_DENIED_HEADER_NAMES` at `:43-44`).
- **LLM API key hygiene** — `llm/provider.py` (key only on the httpx client / per-request header), `services/chat.py:77-178` (BYOK values reach only the provider constructor, never responses/logs/persistence). Provider errors raise sanitized `LLMProviderUnavailable` messages (status code only, `provider.py:181-184`).
- **Error envelope** — `core/errors.py`: canonical `ERROR_CODES` registry, `extra="forbid"` models, generic messages for 401/403/404/409/422/429/503; Neo4j errors sanitized (`database_error_response`); sentinel registry (`api/exceptions.py`) emits fixed texts; stream failures emit generic `event: error` with real exception server-side only (`api/chat.py:233-261`). No custom 500 handler → Starlette default plain "Internal Server Error" (no traceback) with `debug` never enabled (verified: no `debug=True` anywhere).
- **Sessions** — `core/tokens.py`: 48-byte `secrets.token_urlsafe`, SHA-256 hash persisted only (`repository/session.py`); expiry+revocation sweep hourly; cookie `HttpOnly=True`, `Secure` default true, `SameSite=lax` (`api/auth.py:69-78`); raw token never logged.
- **Frontend** — zero `console.log`/`console.debug` in `frontend/src` (only `test/setup.ts`); zero Sentry/telemetry/analytics libraries; chat content never in localStorage/sessionStorage (`ChatPanel.tsx:71` in-memory only); watch progress in sessionStorage only (`useWatchProgress.ts`); fetch errors normalized to the shared envelope with no sensitive detail (`api/client.ts`).
- **Headers/CORS** — `main.py:47-59,198-214`: CSP (self + Google Identity), HSTS, `nosniff`, XFO DENY, Referrer-Policy; CORS with explicit origins, `allow_credentials=True` + explicit method/header lists (no wildcard with credentials); CSRF origin guard on every state-changing route (`api/deps.py:150`).
- **No chat/LLM caching in Redis** — `graph_cache.py` caches only graph query responses (per series/boundary/user), never chat messages.

## Audit method
Static analysis: grep for `logger.`/`print(`/`loguru`/`structlog` across `spoilerless/`; read `main.py`, `core/errors.py`, `core/config.py`, `core/tokens.py`, `api/deps.py`, `api/auth.py`, `api/chat.py`, `api/exceptions.py`, `services/chat.py`, `llm/provider.py`, `repository/session.py`, `repository/chat.py`, `cache/graph_cache.py`, `services/rate_limit.py`, `retrieval/pipeline.py`; greps for `console.*`, `localStorage`, `sessionStorage`, `sentry|telemetry|analytics` in `frontend/src`; read `lib/byok.ts`, `api/chat.ts`, `api/client.ts`, `ChatPanel.tsx`, `SettingsPage.tsx`, `useWatchProgress.ts`; empirical check of `RequestValidationError.__str__` input inclusion with the repo's FastAPI. No live requests were made.
