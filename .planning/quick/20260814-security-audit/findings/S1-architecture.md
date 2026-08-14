# S1 — Architecture & Attack-Surface Map

**Audit:** 20260814-security-audit · **Subagent:** S1 (architecture mapper) · **Scope:** static analysis only, no mutations
**Repo:** `C:/Users/arhan/PycharmProjects/hdgrafcehennemi` · **App:** "Spoilerless" — spoiler-safe TV-series knowledge graph (Dexter) with GraphRAG chat

---

## 1. Architecture overview

Spoilerless is a **3-tier server-rendered-API + SPA** knowledge-graph app:

- **Frontend:** React 19.2.7 + TypeScript 6.0.2 + Vite 8.1.1 SPA (`frontend/package.json`), Cytoscape 3.34 graph canvas, Tailwind 4.3 + shadcn 4.16 + radix-ui 1.6.7 UI. Deployed on **Vercel** (`frontend/vercel.json` — SPA rewrite to `/index.html`). Google Identity Services (GSI) loaded from `https://accounts.google.com/gsi/client` (`frontend/index.html:29`). `VITE_API_BASE_URL` (root `.env` via `envDir: '..'`, `frontend/vite.config.ts:9`) prefixes API calls; dev proxies `/api` → `http://127.0.0.1:8000` (`frontend/vite.config.ts:16-22`).
- **Backend:** FastAPI 0.140.7 / Python ≥3.13 (`pyproject.toml`), uvicorn 0.51.0 on **Render** free tier (`render.yaml` — `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0`), single process/worker. 11 routers registered in `spoilerless/app/main.py:170-180` plus `/health` and a StaticFiles mount `/api/static` for self-hosted character portraits (`main.py:187-188`).
- **Data:** **Neo4j AuraDB** (driver 6.2.0, `neo4j+s://` → TLS via certifi, `app/graph/database.py:74-96`). All state — users, sessions, chat, notes, custom nodes/rels, revisions, share tokens, LLM settings, ChangeSets, candidate claims — lives in one graph DB. Connection uses the configured `NEO4J_USERNAME` (issue #36: admin superuser, unresolved).
- **Cache/rate-limit:** **Upstash Redis** (`rediss://`, `redis 8.1.0`, `app/cache/redis_client.py:34`) — graph/viz cache-aside (`app/cache/graph_cache.py`) + pyrate-limiter `RedisBucket` rate limiting (`app/services/rate_limit.py`). Empty `REDIS_URL` degrades both to no-op (documented).
- **Auth:** Google OAuth2 ID-token (GSI) → `google-auth 2.56.0` verify → opaque 48-byte session token in HttpOnly cookie, SHA-256 hashed server-side in Neo4j (`app/core/tokens.py`, `app/repository/session.py`). Admin role from `ADMIN_EMAILS` env membership at login (`app/services/auth.py:169`).
- **LLM GraphRAG:** chat agent with 10 allowlisted retrieval tools (`app/retrieval/tools.py`), OpenAI-compatible `httpx` streaming or Gemini REST v1beta (`app/llm/provider.py:313-419`, default `https://generativelanguage.googleapis.com`). BYOK: browser-held key/base_url/model ride `X-LLM-*` headers (`frontend/src/lib/byok.ts`).
- **Deployment:** Cloudflare DNS → Vercel (`app.spoilerless.net`) + Render (`api.spoilerless.net`), operator-verified v1.3 (docs/architecture/project-spec.md:9,28). CI: `.github/workflows/ci.yml` (pytest against local Neo4j + frontend build/lint).

**Route inventory (verified):** 52 documented OpenAPI operations over 39 path templates (locked by `spoilerless/tests/test_frontend_contract_doc.py:109-110`) + 1 schema-hidden `HEAD /health` = **53 HTTP routes total**. `GET /openapi.json`, `/docs`, `/redoc` are **exposed** (FastAPI defaults, no `docs_url=None` in `main.py:164-168`).

## 2. Data-flow diagram with trust boundaries (TB-01 … TB-14)

```
        [Internet]
   ┌─────────┴──────────┐
 [Cloudflare DNS]   [Vercel SPA app.spoilerless.net]  ← Google GSI JS (accounts.google.com)
        │                        │
        │   TB-01  HTTPS, browser→Vercel edge (SPA assets; no backend logic)
        │                        │ /api/* + /api/static/*  (Vercel rewrite/proxy)
        ▼                        ▼
 [Render: uvicorn spoilerless-backend]  (FRONTEND_ORIGINS CORS allowlist, credentials)
   │  TB-02  Cookie session → deps.py require_current_user (SHA-256→Neo4j) 
   │  TB-03  Origin/Referer → verify_origin CSRF gate (all state-changing routes)
   │  TB-04  X-LLM-* BYOK headers → get_llm_provider (never logged/persisted)
   │  TB-05  Query params (visible_until_order/episode_order/focus_id) → server-side boundary clamp
   ├───────────┬──────────────┬──────────────────┐
   ▼           ▼              ▼                  ▼
 [Neo4j AuraDB] [Upstash Redis] [LLM host(s)] [Google OAuth certs]
   TB-06       TB-07          TB-08             TB-09
```

**TB-01 Browser → Vercel edge:** SPA HTML/JS/CSS + Google GSI script. SOURCE=browser, DATA=static assets + third-party `accounts.google.com` JS (script-src allowed in CSP, `main.py:48-54`), TRANSPORT=HTTPS, DESTINATION=Vercel CDN, VALIDATION=none (static), AUTHORIZATION=none, STORAGE/USE=executed in browser. Compromise of GSI script = full client takeover (XSS-equivalent).

**TB-02 Browser → FastAPI (session auth):** SOURCE=browser, DATA=`session` cookie (HttpOnly, Secure, SameSite=Lax, 7-day TTL; `api/auth.py:69-79`, `core/config.py:31-55`), TRANSPORT=HTTPS, DESTINATION=any route using `CurrentUserDependency`/`OptionalUserDependency` (`api/deps.py:53-97`), VALIDATION=SHA-256 lookup against `(:Session {token_hash})` with `revoked_at IS NULL AND expires_at > now` (`repository/session.py:226-255`), AUTHORIZATION=session↔user edge, STORAGE/USE=user id stamped on `request.state.user`; used for ownership scoping (progress/chat/change-set/notes), rate-limit keys, admin role gate.

**TB-03 Browser → FastAPI (CSRF):** SOURCE=browser, DATA=Origin or Referer header, TRANSPORT=HTTPS, DESTINATION=every state-changing route via `CsrfGuardDependency` (`api/deps.py:150-210`), VALIDATION=exact match against `FRONTEND_ORIGINS` list (fail closed on missing header; wildcard `*` disables), AUTHORIZATION=n/a, STORAGE/USE=none. Covers all writes incl. `/api/auth/google` and `/logout`.

**TB-04 Browser → FastAPI (BYOK LLM):** SOURCE=browser, DATA=`X-LLM-Api-Key`/`X-LLM-Provider`/`X-LLM-Base-URL`/`X-LLM-Model`, TRANSPORT=HTTPS, DESTINATION=`get_llm_provider` (`services/chat.py:77-178`), VALIDATION=base_url scheme http/https + host required (`domain/settings.py:62-81`), AUTHORIZATION=authenticated user (chat routes), STORAGE/USE=provider constructor only; header names denied from request logs (`main.py:43-44`). **SSRF-relevant:** any authenticated user can point the backend httpx client at any http(s) host incl. loopback/private IPs (explicit design comment `domain/settings.py:26-33`).

**TB-05 Browser → FastAPI (spoiler boundary):** SOURCE=browser, DATA=`visible_until_order`/`episode_order`/`focus_id`/`node_id` query params, TRANSPORT=HTTPS, DESTINATION=graph/viz/expand/path/export/episodes/candidates/notes reads, VALIDATION=anonymous fixed at order 1 (never client-chosen; `api/graph.py:124`, `api/series.py:87`), authenticated clamped to persisted progress `min(requested, view_as_of_order)` + `effective_view_order` (D-05), boundary must resolve to a persisted episode else 422 (`api/graph.py:397-457`), AUTHORIZATION=optional user, STORAGE/USE=Neo4j queries filtered by `visible_from_order <= $boundary` at every query layer.

**TB-06 Backend → Neo4j AuraDB:** SOURCE=FastAPI services/repositories, DATA=parameterized Cypher (no raw client fragments anywhere; `retrieval/tools.py:10`), TRANSPORT=neo4j:// + `encrypted=True` + `TrustCustomCAs(certifi)` (`graph/database.py:74-96`), VALIDATION=driver param binding, AUTHORIZATION=app user (admin superuser, issue #36 unresolved), STORAGE/USE=canonical graph, sessions, chat, user content, revisions, settings (incl. LLM API key in `:AppSetting {key:'llm'}` — `domain/settings.py:1-8`).

**TB-07 Backend → Upstash Redis:** SOURCE=graph_cache + rate_limit modules, DATA=JSON graph/viz payloads (TTL 300s), rate-limit ZSETs, `graph_revision` epochs, TRANSPORT=rediss:// TLS, VALIDATION=cached viz DTO re-validated against key metadata on read (poisoned entries → miss; `cache/graph_cache.py:212-222`), AUTHORIZATION=Upstash token, STORAGE/USE=cache-aside only; all Redis errors degrade to Neo4j (never fail requests).

**TB-08 Backend → LLM host(s):** SOURCE=`OpenAICompatibleProvider`/`GeminiProvider` (`llm/provider.py:114-247,313-419`), DATA=system prompt + retrieval context + conversation history + tool schemas (context budget 40 items/12000 chars, `core/config.py:126-133`), TRANSPORT=HTTPS (httpx streaming, 60s timeout), VALIDATION=SSE parse (malformed chunks skipped), AUTHORIZATION=Bearer or `x-goog-api-key`, STORAGE/USE=answer text, citations, graph_focus, proposed ChangeSet validated server-side before persistence (`services/chat.py:331-387`). Key is user-supplied (BYOK) or stored/app-env.

**TB-09 Backend → Google OAuth certs:** SOURCE=`ProductionGoogleVerifier` (`services/auth.py:67-111`), DATA=Google signing certs, TRANSPORT=HTTPS (google-auth transport), VALIDATION=signature/audience/issuer/expiry via `verify_oauth2_token`, AUTHORIZATION=n/a, STORAGE/USE=verified claims (sub, email, name, picture — picture scheme-sanitized, `services/auth.py:51-64`) drive user upsert, email allowlist, admin role.

**TB-10 LLM → retrieval tools → Neo4j (agentic boundary):** SOURCE=LLM tool-call JSON, DATA=tool name + args, TRANSPORT=in-process, VALIDATION=allowlisted 10 tools only; `visible_until_order` is server-injected, never read from model args (`retrieval/tools.py:4-11`); limits clamped server-side (depth ≤3, hops ≤4, results ≤25), AUTHORIZATION=user-scoped pipeline, STORAGE/USE=Neo4j reads at effective boundary; hidden ≡ missing (fail closed).

**TB-11 LLM output → Neo4j persistence:** SOURCE=LLM `done` event, DATA=content/citations/graph_focus/proposed_change_set, VALIDATION=citation ids validated against this turn's retrieved context; ChangeSet re-validated fresh at confirm (`api/change_set.py:78-117`), AUTHORIZATION=confirm is admin-only; propose/reject/revert any authenticated user, STORAGE/USE=chat messages + ChangeSet drafts in Neo4j.

**TB-12 Share token (URL) → FastAPI:** SOURCE=unauthenticated visitor, DATA=`/api/share/{token}/graph` path token, TRANSPORT=HTTPS, VALIDATION=SHA-256 lookup + validity window (`api/share.py:95-145`; 32-byte tokens, 30-day TTL, `repository/share.py:16-17,28`), AUTHORIZATION=token-as-credential (snapshot graph at creator's clamped boundary; `api/share.py:59-67`), STORAGE/USE=cache-aside graph read. Referer leakage mitigated page-wide `referrer no-referrer` (`frontend/index.html:12`).

**TB-13 Backend → Uptime monitors:** SOURCE=external monitor, DATA=none, TRANSPORT=HTTPS, DESTINATION=`GET|HEAD /health` (`main.py:222-249`), VALIDATION=none, AUTHORIZATION=none, STORAGE/USE=Neo4j connectivity probe (503 when DB down).

**TB-14 Seed/imported data → Neo4j → users:** SOURCE=operator scripts + seed files (`spoilerless/app/graph/seed.py`, `data/`, `neo4j_import/`, `scripts/add_portraits.py`), DATA=canonical story graph + `image_url` values, VALIDATION=none at import (schema = whatever seed last wrote, issue #19), AUTHORIZATION=operator env creds, STORAGE/USE=served to all visitors; `image_url` hotlinks external CDNs (img-src `https:` allows any host, `main.py:50`; comment at `frontend/index.html:4-7`).

## 3. Entry-point inventory — complete route table (53 HTTP routes)

Auth legend: **P**=public/anonymous · **U**=any authenticated user · **A**=admin only · **O**=optional user (anon ok, clamped) · **T**=token-gated · CSRF=Origin/Referer guard present.

### 3.1 App routes (FastAPI, `spoilerless/app/api/`)

| # | Method | Path | Auth | CSRF | Rate | Params / Body | Cookies / Headers | File:line |
|---|--------|------|------|------|------|----------------|--------------------|-----------|
| 1 | GET | /health | P | – | – | – | – | main.py:222 |
| 2 | HEAD | /health (not in schema) | P | – | – | – | – | main.py:237 |
| 3 | GET | /api/series | P | – | – | – | – | series.py:32 |
| 4 | GET | /api/series/{series_id} | P | – | – | path: series_id | – | series.py:38 |
| 5 | GET | /api/series/{series_id}/episodes | O | – | – | q: visible_until_order (def 1, anon fixed 1) | cookie session | series.py:49 |
| 6 | GET | /api/series/{series_id}/graph | O | – | – | q: visible_until_order (req) | cookie session | graph.py:102 |
| 7 | GET | /api/series/{series_id}/graph/visualization | O | – | – | q: view (Literal 6), episode_order (>0), focus_id[] (≤20, graphrag_focus only) | cookie session | graph.py:174 |
| 8 | GET | /api/series/{series_id}/graph/expand | O | – | – | q: node_id, expansion_key (Literal 7), episode_order, limit (1–25) | cookie session | graph.py:304 |
| 9 | POST | /api/series/{series_id}/graph/path | O | **–** | – | body: source_entity_id, target_entity_id, max_hops (≤4) | cookie session | graph.py:466 |
| 10 | GET | /api/series/{series_id}/export | O | – | – | q: visible_until_order (def 1), target_id (opt) → text/markdown attachment | cookie session | graph.py:502 |
| 11 | GET | /api/series/{series_id}/progress | U | – | – | path: series_id | cookie session | progress.py:42 |
| 12 | POST | /api/series/{series_id}/progress | U | ✔ | – | body: watched_through_order / view_as_of_order / visible_until_order (mutually exclusive) | cookie session | progress.py:73 |
| 13 | GET | /api/series/{series_id}/revisions | P | – | – | q: visible_until_order (req), resource_type, resource_id | – | revisions.py:44 |
| 14 | GET | /api/series/{series_id}/revisions/{revision_id} | P | – | – | q: visible_until_order (req) | – | revisions.py:77 |
| 15 | POST | /api/series/{series_id}/revisions/{revision_id}/revert | U | ✔ | – | q: visible_until_order (req); owner-or-admin check inside | cookie session | revisions.py:105 |
| 16 | GET | /api/series/{series_id}/candidates | P | – | – | q: visible_until_order (**required**, else 422) | – | candidates.py:145 |
| 17 | GET | /api/series/{series_id}/candidates/{claim_id} | P | – | – | q: visible_until_order (req) | – | candidates.py:174 |
| 18 | POST | /api/series/{series_id}/candidates/ingest | U | ✔ | – | body: ExtractionBatchEnvelope (claims with evidence/source) | cookie session | candidates.py:95 |
| 19 | POST | /api/series/{series_id}/candidates/{claim_id}/approve | A | ✔ | – | – | cookie session | candidates.py:213 |
| 20 | POST | /api/series/{series_id}/candidates/{claim_id}/reject | A | ✔ | – | – | cookie session | candidates.py:255 |
| 21 | PATCH | /api/series/{series_id}/candidates/{claim_id} | A | ✔ | – | body: EditCandidateRequest (11 optional fields) | cookie session | candidates.py:287 |
| 22 | POST | /api/series/{series_id}/chat/sessions | U | ✔ | – | body: title | cookie session | chat.py:52 |
| 23 | GET | /api/series/{series_id}/chat/sessions | U | – | – | – | cookie session | chat.py:72 |
| 24 | GET | /api/series/{series_id}/chat/sessions/{session_id} | U | – | – | – | cookie session | chat.py:88 |
| 25 | DELETE | /api/series/{series_id}/chat/sessions/{session_id} | U | ✔ | – | – | cookie session | chat.py:107 |
| 26 | POST | /api/series/{series_id}/chat/sessions/{session_id}/messages | U | ✔ | chat 20/60s/user | body: question; **X-LLM-Api-Key/Provider/Base-URL/Model** | cookie session | chat.py:136 |
| 27 | POST | /api/series/{series_id}/chat/sessions/{session_id}/messages/stream | U | ✔ | chat 20/60s/user | body: question; X-LLM-* headers; SSE response | cookie session | chat.py:168 |
| 28 | POST | /api/series/{series_id}/change-sets | U | ✔ | – | body: ChangeSetCreateRequest (series_id must match path) | cookie session | change_set.py:48 |
| 29 | POST | /api/series/{series_id}/change-sets/{id}/confirm | A | ✔ | – | – | cookie session | change_set.py:78 |
| 30 | POST | /api/series/{series_id}/change-sets/{id}/reject | U | ✔ | – | – | cookie session | change_set.py:120 |
| 31 | POST | /api/series/{series_id}/change-sets/{id}/revert | U | ✔ | – | – (create-shaped only, else 422) | cookie session | change_set.py:145 |
| 32 | GET | /api/settings/llm | A | – | – | – (key masked, never full) | cookie session | settings.py:33 |
| 33 | PUT | /api/settings/llm | A | ✔ | – | body: LLMSettingsUpdate (provider, api_key, base_url, model, enabled, language) | cookie session | settings.py:46 |
| 34 | POST | /api/share | U | ✔ | – | body: series_id, visible_until_order (clamped to creator progress) | cookie session | share.py:39 |
| 35 | GET | /api/share/{token}/graph | T | – | – | path: token (32B) | – | share.py:95 |
| 36 | GET | /api/share | U | – | – | – | cookie session | share.py:148 |
| 37 | DELETE | /api/share/{token} | U | ✔ | – | owner-or-admin (403 otherwise) | cookie session | share.py:172 |
| 38 | POST | /api/series/{series_id}/notes | U | ✔ | content-write 30/60s | body: NoteCreate | cookie session | user_content.py:37 |
| 39 | GET | /api/series/{series_id}/notes | P | – | – | q: visible_until_order (req), target_type, target_id | – | user_content.py:51 |
| 40 | GET | /api/series/{series_id}/notes/{note_id} | P | – | – | q: visible_until_order (req) | – | user_content.py:68 |
| 41 | PATCH | /api/series/{series_id}/notes/{note_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:79 |
| 42 | DELETE | /api/series/{series_id}/notes/{note_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:96 |
| 43 | POST | /api/series/{series_id}/custom-nodes | U | ✔ | content-write | body: CustomNodeCreate | cookie session | user_content.py:113 |
| 44 | GET | /api/series/{series_id}/custom-nodes/{node_id} | P | – | – | q: visible_until_order (req) | – | user_content.py:126 |
| 45 | PATCH | /api/series/{series_id}/custom-nodes/{node_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:132 |
| 46 | DELETE | /api/series/{series_id}/custom-nodes/{node_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:148 |
| 47 | POST | /api/series/{series_id}/custom-relationships | U | ✔ | content-write | body: CustomRelationshipCreate | cookie session | user_content.py:164 |
| 48 | GET | /api/series/{series_id}/custom-relationships/{id} | P | – | – | q: visible_until_order (req) | – | user_content.py:177 |
| 49 | PATCH | /api/series/{series_id}/custom-relationships/{id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:183 |
| 50 | DELETE | /api/series/{series_id}/custom-relationships/{id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:199 |
| 51 | POST | /api/auth/google | P | ✔ | login 10/300s/IP | body: credential (Google ID token) → sets session cookie | Origin/Referer | auth.py:92 |
| 52 | GET | /api/auth/me | U | – | – | – | cookie session | auth.py:177 |
| 53 | POST | /api/auth/logout | U | ✔ | – | – (revokes session, deletes cookie) | cookie session | auth.py:199 |

**Static mount:** `GET /api/static/*` — StaticFiles over `spoilerless/app/static/characters/` (`main.py:187-188`); used by `image_url` values (`/api/static/characters/<id>.webp`). Directory listing disabled (Starlette default).

### 3.2 Frontend API calls (`frontend/src/api/`)

| Call | Method+path | Source file:line |
|------|-------------|------------------|
| loginWithGoogleCredential | POST /api/auth/google | auth.ts:4 |
| getCurrentUser | GET /api/auth/me | auth.ts:11 |
| logout | POST /api/auth/logout | auth.ts:15 |
| getSeries | GET /api/series | series.ts:4 |
| getEpisodes | GET /api/series/{id}/episodes?visible_until_order | series.ts:8 |
| getGraph | GET /api/series/{id}/graph?visible_until_order | graph.ts:9 |
| findPath | POST /api/series/{id}/graph/path | graph.ts:15 |
| fetchVisualization | GET /api/series/{id}/graph/visualization?view&episode_order&focus_id[] | graph.ts:31 |
| fetchExpansion | GET /api/series/{id}/graph/expand?node_id&expansion_key&episode_order&limit | graph.ts:59 |
| fetchExportMarkdown | GET /api/series/{id}/export?visible_until_order&target_id (raw fetch, Content-Disposition parse) | export.ts:5 |
| getProgress / updateProgress | GET+POST /api/series/{id}/progress | progress.ts:27,31 |
| getRevisions / revertRevision | GET /revisions?visible_until_order; POST /revisions/{id}/revert | revisions.ts:4,16 |
| chat: create/list/get/delete sessions; sendMessage; streamMessage | /api/series/{id}/chat/sessions[…] (SSE via raw fetch, X-LLM-* headers from byok.ts) | chat.ts:7-164 |
| userContent: notes CRUD, custom-nodes, custom-relationships | /api/series/{id}/notes[…], /custom-nodes, /custom-relationships | userContent.ts:10-62 |
| share: createShareLink / getShareGraph / listShareLinks / revokeShareLink | /api/share[…], /api/share/{token}/graph | share.ts:5-30 |
| all apiFetch | `credentials:'include'`; VITE_API_BASE_URL prefix; 204/error-envelope normalization | client.ts:60-83 |

Frontend only *reads* `getStoredLLMSettings`/`saveLLMSettings` (localStorage `spoilerless:byok-llm-settings`) → `getLLMHeaders()` for chat (`lib/byok.ts:42-85`).

## 4. Non-HTTP entry points

1. **Env vars** (`.env` / Render dashboard; keys present in local `.env`: `NEO4J_URI/USERNAME/PASSWORD/DATABASE`, `GOOGLE_CLIENT_ID`, `AUTH_DEV_CODE`, `aura_username`, `aura_password` — values redacted; full schema in `.env.example` + `core/config.py:8-144`): Neo4j creds, Google client id (startup equality check vs `VITE_GOOGLE_CLIENT_ID`, `config.py:152-170`), `SESSION_COOKIE_*` (name/TTL/secure/samesite), `FRONTEND_ORIGINS` (CORS+CSRF), `ALLOWED_EMAILS`, `ADMIN_EMAILS`, `REDIS_URL`, `LLM_*` (enabled/provider/base_url/key/model/timeout/tokens/temperature/tool-rounds/context caps/fallback texts). **`AUTH_DEV_CODE` is referenced only in planning docs — no code reference (vestigial; PROBLEMS.md #7 backdoor appears removed).**
2. **Neo4j contents fed to LLM:** claims/evidence/sources/episodes at the effective boundary + user's own notes (`retrieval/tools.py:309-326`) — prompt-injection surface via attacker-authored content (defended: system prompt hardening + boundary injection; `spoilerless/tests/test_prompt_injection.py` exists).
3. **Redis values:** `graph:*`, `viz:*` (user-scoped keys, TTL 300s, epoch-validated), `hdgraf:rate_limit:*` ZSETs, `graph_revision:*` epochs (`cache/graph_cache.py`). Poisoning a viz entry is rejected by metadata re-validation (`graph_cache.py:212-222`).
4. **Imported/seed data:** `spoilerless/app/graph/seed.py`, `data/dexter/*`, `neo4j_import/`, `scripts/add_portraits.py`, ontology YAML (`app/graph/ontology.py`, `ontology/`) — no schema migration system (issue #19); live-DB/seed drift was an observed failure class (#44).
5. **Cron/background:** in-process hourly session+share sweep task (`main.py:131-140`, guarded on DB reachability); no external cron. Operator scripts `scripts/zombie_sweep.py` (dry-run-first, hardcoded protected dev user id `zombie_sweep.py:31`), `run_backend_tests.py`, `run_verification.py` — env-credentialed direct DB access.
6. **/docs, /redoc, /openapi.json** — full API schema public (see §6.1).

## 5. External network dependencies

| Target | Direction | Purpose | Trigger | Credential |
|--------|-----------|---------|---------|------------|
| accounts.google.com/gsi/client | frontend→ | Google Sign-In JS | page load (`frontend/index.html:29`) | none (public) |
| www.googleapis.com OAuth2 certs | backend→ | ID-token signature verification (`services/auth.py:86-93`) | POST /api/auth/google | none |
| generativelanguage.googleapis.com (v1beta) | backend→ | Gemini GraphRAG (`llm/provider.py:372-377`) | chat messages | `x-goog-api-key` (stored or BYOK) |
| *arbitrary user-chosen host* (http/https) | backend→ | BYOK OpenAI-compatible endpoint (`services/chat.py:142-146`) | chat messages | user key via X-LLM headers |
| Neo4j AuraDB (`neo4j+s://`) | backend↔ | all persistence | every request | `NEO4J_USERNAME/PASSWORD` |
| Upstash Redis (`rediss://`) | backend↔ | cache + rate limits | graph reads/writes, login/chat/content writes | `REDIS_URL` token |
| External portrait CDNs (e.g. static.wikia.nocookie.net) | browser→ | hotlinked images (CSP img-src https: allows) | graph render | none |
| Vercel / Render / Cloudflare DNS | – | hosting/deployment | – | platform secrets |

## 6. Observations (unusual / worth deep-dive)

1. **`/docs`, `/redoc`, `/openapi.json` exposed in production** — `main.py:164-168` never disables them. Publicly reveals the full route inventory, request models, Literal enums (view/expansion vocabularies), and auth model. Low direct risk, high reconnaissance value.
2. **BYOK = authenticated SSRF primitive.** Any logged-in user can make the Render backend issue `httpx` POSTs to any `http(s)://` host (including 127.0.0.1 / cloud metadata IPs — explicitly allowed by design comment `domain/settings.py:26-33`) with their own key via `X-LLM-Base-URL`. Scheme-only validation (`domain/settings.py:62-81`). Not exploitable anonymously, but it is a *server-side request forgery* shape; the LLM provider also sends the user's key as `Authorization: Bearer` — a malicious `base_url` exfiltrates nothing beyond what the user already holds, but response-body handling (SSE parsing) of attacker hosts is untested territory (PROBLEMS.md #52 flags provider edge cases).
3. **POST `/graph/path` is anonymous and CSRF-unguarded** (`api/graph.py:466-499`) — read-only computation, so low impact, but it is the only POST without `CsrfGuardDependency`; inconsistent with the route family's posture.
4. **Candidate ingest is any-authenticated-user, not admin** (`api/candidates.py:95-142`) — deliberate (attribution via revisions), but any Google account (if `ALLOWED_EMAILS` empty in prod) can write candidate claims into the shared graph DB; approve/reject/edit are admin-only. Graph-poisoning chain requires admin approval — verify `ALLOWED_EMAILS`/`ADMIN_EMAILS` non-empty in prod.
5. **Anonymous read surface is wide and unthrottled:** graph, visualization, expansion, export, path, candidates, notes, custom nodes/rels are all anonymous; only login/chat/content-write have rate limits (`services/rate_limit.py:33-38`). Projection/expansion queries are Neo4j-heavy — anonymous DoS surface (cache-aside helps for repeated identical keys, but expansion is deliberately uncached, `api/graph.py:358-360`).
6. **`httpx` is an undeclared production dependency** — used at import time in `llm/provider.py:18` but listed only in the dev group (`pyproject.toml:22-26`; uv.lock shows it under `[package.dev-dependencies]`). Works only because Render's `uv sync --frozen` installs dev deps by default; a `--no-dev` prod install would crash chat imports.
7. **Share-token revocation accepts raw token or hash, but the docstring also claims id** (`api/share.py:183-186` vs comment at 183) — minor contract drift; share tokens are 32B (weaker than 48B sessions, still 256-bit).
8. **Rate limiting & cache silently disabled when `REDIS_URL` empty** — documented (`rate_limit.py:86-89`, `graph_cache.py:79-81`); on Render with Upstash configured this is fine, but a misconfigured deploy runs unthrottled with no alert.
9. **Hardcoded protected dev user id** in `scripts/zombie_sweep.py:31` — operator script, but pins a specific AuraDB user as never-deletable; the same value is the app's seeded dev user.
10. **Per-process concurrency limit for chat generations** (`services/chat.py:50-51`) — in-memory dict; single Render worker makes it effective today, but multi-worker deployment silently doubles concurrency.
11. **CSP `img-src https:` + `referrer no-referrer`** — any https image host can be embedded (user-content/custom-node label rendering should be checked for `<img>` injection by S3); page-wide no-referrer is the mitigation for hotlinked portrait CDNs.
12. **Everything (users, secrets-adjacent LLM key, sessions, chat) in one Neo4j DB as one app user** — no least-privilege DB role (issue #36 unresolved); LLM API key persisted in graph (`:AppSetting`), only masked in responses (`domain/settings.py:84-101`).
13. **No slide-on-read session refresh, fixed 7-day TTL, hourly sweep** (`repository/session.py:257-263`, `main.py:131-140`) — good hygiene; note sessions are deleted, not tombstoned (revoked_at survives only until sweep).
14. **Live-DB hygiene** (from ledger, not re-tested): 3,855 AppUser rows / 21 expired sessions at audit time (issue #46); seed drift (#44) — schema/seed versioning absent (#19).

**Cross-cutting guidance for sibling subagents:** S2 should deep-dive BYOK SSRF (#2), anonymous-write surface (#4), CSRF coverage matrix, and `/docs` exposure; S4 the LLM tool-call boundary (TB-10) and prompt-injection; S5 spoiler-boundary enforcement completeness across the 17 boundary-aware routes and Redis cache-key correctness; S8 the anonymous read amplification (#5); S9 the request-logging allowlist (`main.py:76-101`) and `X-LLM-*` denial (`main.py:43-44`).

*Secrets handling: `.env` values were never read — only key names grepped. No live Neo4j/Redis/LLM/network calls made.*
