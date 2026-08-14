# SECURITY_AUDIT.md — Spoilerless (hdgrafcehennemi)

Adversarial security audit, 2026-08-14/15. Lead: Hermes agent. Ten specialist subagents (S1–S9 + independent adversarial reviewer S10). Method: static analysis + safe local verification only — no destructive actions, no live-DB writes, no prod traffic, no secrets printed. Base commit: 9d50500 (branch main).

---

# Executive Summary

**Overall posture: NOT READY for public exposure.** The application's core security property is **spoiler safety** — a user's watched-episode progress must bound what they (and anonymous visitors) can retrieve. That property is broken by **unauthenticated, unthrottled read routes** with client-chosen boundaries, and by a **one-request graph-poisoning write** available to any signed-in Google account. Availability and wallet are independently compromised by a global login rate-limit bucket and an open-signup LLM cost farm.

**Finding counts (after S10 adjudication, cross-agent duplicates merged):**

| Severity | Count |
|---|---|
| CRITICAL | 1 (config-dependent: LLM cost farm) |
| HIGH | 14 |
| MEDIUM | 27 |
| LOW | 28 |
| INFORMATIONAL / verified-positive | ~20 |

**Three most important risks:**

1. **Spoiler-boundary bypass, anonymous and certain (SEC-BE-002 / SEC-GR-005/006/007).** `GET /api/series/{id}/candidates`, `/notes`, `/custom-nodes/{id}`, `/custom-relationships/{id}`, `/revisions` accept any `visible_until_order` from an unauthenticated client with no clamp to order 1 (and in the notes/custom/revisions cases, no persisted-episode validation at all). Combined with `GET /graph?visible_until_order=<last>` on a fresh account with no progress record (SEC-BE-001), **the entire story corpus, all users' private notes, revision before/after snapshots, and author user_ids are extractable with zero privileges** — no account, no rate limit.
2. **One-request graph poisoning (SEC-BE-003 / SEC-GR-004 / SEC-ADV-001).** Any authenticated user can `POST /candidates/ingest` with client-chosen `visible_from_order: 1` and arbitrary claim/evidence text (spoilers, or "ignore previous instructions…" payloads). The content is immediately visible to every anonymous visitor and enters **every user's LLM retrieval context** — an indirect prompt-injection supply chain. Ingest is also the one write path with **no rate limiter** and no cache invalidation.
3. **Availability + wallet (SEC-BE-004/SEC-DOS-003, SEC-DOS-001, SEC-DOS-002).** uvicorn runs without `--proxy-headers`, so `request.client.host` is Render's proxy IP for every client: the 10-logins/5-min bucket is **site-global** — 10 scripted failed logins lock out all sign-ins, repeatable forever. Rate limiting is fail-open by design (any Redis absence/outage = no limits). With open Google signup (default), a 10-account farm burns the operator's stored LLM key at ~$600–860/day.

**The audit's only original CRITICAL was rejected:** SEC-INF-001 claimed a live Upstash Redis password in README/git history; S10 verified byte-for-byte that every occurrence is the literal placeholder `<token>` (endpoint names only are public — INFO). The secrets posture itself (hashed sessions, allowlist logging, no `.env` in git) is genuinely good.

**Verdict (S10): NO — do not expose to the public internet before the P0 list (§ Remediation Roadmap) lands.** The spoiler-boundary findings alone are product-fatal.

---

# Architecture

- **Frontend:** React 19 + Vite 8 + TypeScript + Tailwind 4 + Cytoscape.js graph rendering; shadcn/radix components. Served by Vercel (`vercel.json` = rewrites only). Google Identity Services script from `accounts.google.com`.
- **Backend:** FastAPI 0.140.7 + uvicorn on Render (free web service, `render.yaml`; dashboard service name `spoilerless`, blueprint `spoilerless-api`). 11 routers, 53 routes. Middleware: CORS (explicit origins + credentials), security headers, allowlist request logging.
- **Database:** Neo4j AuraDB (`neo4j+s://`, admin-level credentials). ~55 Cypher queries, all parameterized.
- **Cache/rate-limit:** Upstash Redis (`rediss://`, dashboard-only env). Graph/viz caches (TTL 300s, epoch-gated), `hdgraf:rate_limit:*` ZSETs.
- **Auth:** Google OAuth ID token → `verify_oauth2_token`; HttpOnly+Secure+SameSite=Lax session cookie (48-byte token, SHA-256 at rest, 7d TTL); `ALLOWED_EMAILS` allowlist (empty default), `ADMIN_EMAILS` role gate; CSRF Origin/Referer guard on state-changing routes; hourly expired-session sweep.
- **LLM/GraphRAG:** Gemini v1beta REST (`x-goog-api-key`) or OpenAI-compatible endpoint; config from admin `:AppSetting{key:'llm'}` (write-only key, masked GET) or per-request BYOK `X-LLM-*` headers. Deterministic retrieval pipeline: 12-tool allowlist (11 read-only Neo4j tools + `propose_changeset` draft), server-injected spoiler boundary, delimited context framing, citation validation.
- **Hosting/network:** Vercel (FE) → Cloudflare DNS → Render (BE, `spoilerless.onrender.com`); backend reachable directly (no edge protection on API, SEC-INF-007).

## Trust boundaries (S1, 14 annotated)

1. Browser → Vercel/CDN (no CSP on shell — SEC-FE-001)
2. Session cookie (HttpOnly/Secure/Lax — sound)
3. CSRF Origin gate (fail-closed — sound)
4. BYOK `X-LLM-*` headers (authenticated SSRF primitive — SEC-LLM-001)
5. Spoiler-boundary clamp (BROKEN on 3 surfaces — SEC-BE-001/002)
6. Neo4j (parameterized, admin creds — SEC-GR-003)
7. Redis (rediss, fail-open limits — SEC-DOS-001)
8. LLM host (scheme-only validation — SEC-LLM-001/002)
9. Google certs (sound)
10. LLM → tools → Neo4j (allowlist, boundary injected — sound)
11. LLM → persistence (chat retained indefinitely — SEC-LOG-007)
12. Share token (32B, hashed — sound; URL exposure — SEC-BE-012)
13. Health probe (minimal — acceptable)
14. Seed/import data (trusted-at-import; drift risk non-security)

# Complete Entry Point Inventory

Full 53-route table (method/auth/CSRF/rate/params/headers per route), frontend API-call map, and non-HTTP entry points (env vars, Neo4j content fed to LLM, Redis values, seed data, hourly sweep): see **SECURITY_ATTACK_SURFACE.md** (living document).

# LLM Agent Capability Map

| Tool | Input | Boundary | Result cap | Authorization |
|---|---|---|---|---|
| search_entities | query ≤200, types allowlist-intersected, limit ≤25 | server-injected | 25 | any chat user |
| get_entity | entity_id | server-injected | 1 | any chat user |
| get_neighborhood | entity_id, depth ≤3 | server-injected | per-level bounded | any chat user |
| find_path | source/target, hops ≤4 | server-injected | 1 path | any chat user |
| get_timeline | limit ≤50 | server-injected | 50 | any chat user |
| get_character_context | character_id, limit ≤25 | server-injected | 25 | any chat user |
| get_claims | entity_ids, limit ≤50 | server-injected | 50 | any chat user |
| get_evidence | claim_ids, limit ≤50 | server-injected | 50 | any chat user |
| get_sources | claim_ids, limit ≤50 | server-injected | 50 | any chat user |
| get_current_visible_graph_summary | focus_entity_ids | server-injected | counts | any chat user |
| get_user_notes | entity_or_claim_ids | server-injected + user_id filter | own notes only | owner |
| propose_changeset | summary ≤500, operations 1..∞ (SEC-LLM-007) | server-derived, never model | draft only; admin confirms | owner, admin-applied |

**No URL/HTTP/scraper tool exists.** The only outbound network call in the LLM path is the provider itself. Per-turn caps: 4 tool rounds, 40 context items / 12k chars, 4k-char tool-result replay, 800 output tokens, 4000-char question, no provider retry, per-user concurrency slot = 1 (in-process).

# Attack Surface

- **Anonymous read (unthrottled):** graph, visualization, expand, export, path, episodes, candidates, notes, custom-nodes/relationships, revisions, share graphs, /docs, /health, /api/static.
- **Authenticated read/write:** progress, chat (limited), notes/custom CRUD (limited), ingest (UNLIMITED — SEC-ADV-001), change-sets, share links, sessions.
- **Admin:** settings/llm, candidate approve/reject/edit, change-set confirm.
- **SSRF:** BYOK `X-LLM-Base-URL` (authenticated), stored base_url (admin).

# Confirmed Findings

## CRITICAL

### SEC-DOS-002 / SEC-LLM-003 — LLM cost amplification via account farming
- **Confidence:** CONFIRMED (config-dependent) · **Component:** `api/chat.py:136-263`, `services/chat.py:46-74`, `retrieval/pipeline.py:780-830`, `config.py:60-67`
- **Entry point:** `POST /api/series/{id}/chat/sessions/{sid}/messages` (any Google account)
- **Data flow:** burner account → 20 msg/min (per-user limiter) → ≤5 provider calls/turn (4 tool rounds + final) → 40–60k input tokens/turn → operator's stored key billed.
- **Vulnerability:** per-user-only limits + open signup (allowlist empty default) + no global semaphore. S8 arithmetic: 10 accounts ≈ $600–860/day at Gemini 2.5 Flash rates; concurrent turns saturate the free-tier worker (60s × 5 calls each).
- **Existing defenses:** BYOK shifts cost to attacker's own key; per-turn caps; no retries; per-user concurrency slot.
- **Fix:** require non-empty `ALLOWED_EMAILS` in prod; global generation semaphore; per-round tool-call cap; per-user daily token budget. **P0 (verify prod config first).**

## HIGH

### SEC-BE-002 / SEC-GR-005/006/007 — Anonymous spoiler-boundary bypass on candidates/notes/custom/revisions reads
- **Confidence:** CONFIRMED · **Component:** `api/candidates.py:145-207`, `api/user_content.py:51-76,126-129,177-179`, `api/revisions.py:44-97`
- **Entry point:** `GET /api/series/{id}/candidates?visible_until_order=999`, `/notes?...`, `/revisions?...` — anonymous.
- **Data flow:** attacker-chosen boundary → unclamped query → full corpus incl. candidate spoiler text, ALL users' notes, revision before/after snapshots + `user_id`, custom nodes/relationships.
- **Vulnerability:** no auth, no anonymous clamp to order 1; notes/custom/revisions also lack persisted-episode validation (any positive int accepted — SEC-ADV-003).
- **Impact:** complete defeat of the app's core guarantee, zero privileges, no rate limit. **Attack Chain A.**
- **Fix:** route reads through `_resolve_effective_boundary` (anonymous = 1); auth-gate or persist-validate candidates/revisions; strip `before`/`after`/`user_id` for non-owners. **P0.**

### SEC-BE-001 — Fresh-account graph/episodes boundary bypass
- **Confidence:** CONFIRMED · **Component:** `api/graph.py:124-140`, `api/series.py:87-94`
- **Entry point:** `GET /api/series/{id}/graph?visible_until_order=96` with a session whose user has no progress record.
- **Vulnerability:** clamp runs only when `progress_service.get()` returns a record; the fail-closed sibling `_resolve_effective_boundary` (`graph.py:426-437`) returns 1 — the two paths disagree.
- **Impact:** one Google account (any) → full graph dump at any boundary. **P0.**

### SEC-BE-003 / SEC-GR-004 — Candidate ingest graph poisoning (any authenticated user)
- **Confidence:** CONFIRMED · **Component:** `api/candidates.py:121-142`, `domain/extraction.py:111`, `graph/candidates.py:35-98`
- **Entry point:** `POST /api/series/{id}/candidates/ingest` — any signed-in user; body carries `visible_from_order` (client-chosen) + claim/evidence text.
- **Vulnerability:** no existence checks on subject/object/episode; `visible_from_order: 1` content visible to all anonymous readers (`spoiler/filter.py:16`) and enters every chat turn's `<claims>`/`<evidence>` context. **Attack Chain B (indirect prompt injection).**
- **Fix:** server-derive visibility; validate subject/object/episode; admin-gate or clamp; rate-limit (SEC-ADV-001); invalidate cache (SEC-ADV-002). **P0.**

### SEC-BE-004 / SEC-DOS-003 / SEC-INF-004 — Per-IP rate limits collapse into a site-global bucket
- **Confidence:** CONFIRMED (availability impact HIGH) · **Component:** `render.yaml:10`, `services/rate_limit.py:41-50`
- **Entry point:** `POST /api/auth/google` (any client).
- **Vulnerability:** no `--proxy-headers`/`--forwarded-allow-ips` → `request.client.host` is Render's proxy IP for everyone → 10-failed-logins/5min is site-wide → **login lockout DoS, repeatable forever**. Adding proxy flags without `--forwarded-allow-ips` would enable XFF spoofing instead.
- **Fix:** trusted-proxy config (or a site-wide login circuit breaker). **P0.**

### SEC-DOS-001 — Rate limiting fail-open
- **Confidence:** CONFIRMED · **Component:** `services/rate_limit.py:86-105,116-145`
- Redis outage or empty `REDIS_URL` silently disables every limit (login, chat, content-write). Degrade-on-outage is defensible for reads; for login/chat it removes the only cost controls.
- **Fix:** fail-closed for auth + LLM paths in prod (or alert loudly). **P0.**

### SEC-DOS-004 — No request-body size limit
- **Confidence:** CONFIRMED · **Component:** `main.py` (no size middleware), `domain/change_set.py:263` (`operations` unbounded)
- OOM/free-tier instability via huge JSON bodies. **Fix:** size middleware + bounded lists. **P0.**

### SEC-DOS-005 — Visualization cache-key explosion
- **Confidence:** CONFIRMED · **Component:** `cache/graph_cache.py:164-167`, `api/graph.py:188-192`
- Anonymous attacker varies `focus_id[]` (≤20 ids) → unbounded distinct 100KB–1MB Redis entries per 300s window, each miss paying a 7-query `fetch_graph`. **Fix:** cap distinct keys per series/user; aggregate focus into bounded buckets. **P1.**

### SEC-FE-001 — No CSP / security headers on the Vercel SPA shell
- **Confidence:** CONFIRMED · **Component:** `vercel.json`, `frontend/index.html`
- Backend headers cover only `/api`; the shell has no CSP, no XFO/frame-ancestors, no nosniff. Backstops Chain D (XSS → BYOK key theft). **Fix:** headers/CSP meta on Vercel (`vercel.json` headers or platform). **P0/P1.**

### SEC-LLM-001 / SEC-BE-005 — BYOK authenticated SSRF primitive
- **Confidence:** CONFIRMED · **Component:** `domain/settings.py:62-81`, `services/chat.py:77-146`
- **Entry point:** any authenticated user sends `X-LLM-Base-URL: http://169.254.169.254/` (or `http://<render-internal-host>`) + own key.
- **Data flow:** header → `LLMSettingsUpdate._validate_base_url` (http/https + host only) → `httpx` POST `{base}/chat/completions` → status/timing oracle; SSE-shaped bodies echoed to attacker.
- **Impact:** blind port-scan/fingerprint of Render-internal services, POST side-effects on internal HTTP endpoints; metadata endpoints probeable; no redirects followed (partial mitigation); stored key not exfiltratable via headers (S6 SEC-INF-014 — adjudicated: covers key exfiltration only, not the network primitive).
- **Fix:** block loopback/private/link-local/metadata ranges for both BYOK and stored paths; DNS-resolve-and-pin. **P1.**

## MEDIUM (condensed)

| ID | Finding | Component |
|---|---|---|
| SEC-BE-006 | Neo4j driver exception messages verbatim to clients on ingest | `api/candidates.py` |
| SEC-BE-007 | `email_verified` never checked; `ALLOWED_EMAILS` default empty (prod value unverifiable) | `services/auth.py:162-164`, `config.py:60-67` |
| SEC-GR-003 | Admin-level Neo4j credentials for a read-mostly app | `core/config.py:12-24` |
| SEC-GR-008 | Write endpoints = hidden-node existence/reveal-order oracle | `repository/user_content.py:175-...` |
| SEC-GR-009 | Spoiler boundary is self-attestation (user sets own progress) — design-level | `api/progress.py:73-110` |
| SEC-GR-012 / SEC-INF-013 | LLM key plaintext in Neo4j `:AppSetting`; any-user spend of shared key | `repository/settings.py:17-18` |
| SEC-GR-013 | User content reaches other users' graphs + LLM contexts (prompt-injection/stored-XSS data feed) | `repository/user_content.py:214-...` |
| SEC-INF-003 / SEC-LOG-004 | `/docs`, `/redoc`, `/openapi.json` exposed in prod | `main.py:164-168` |
| SEC-INF-005 | render.yaml has zero env config; infra-as-code drift | `render.yaml` |
| SEC-INF-006 | CORS origin list unverifiable from repo (default localhost-only) | `config.py:56-59` |
| SEC-INF-007 | Backend reachable directly around Cloudflare | deployment |
| SEC-INF-015 | Release workflow CI gate is a non-functional skeleton | `.github/workflows/release.yml` |
| SEC-FE-002 / SEC-LOG-003 | BYOK LLM key plaintext in localStorage; transits backend each request | `frontend/src/lib/byok.ts:9,53-62` |
| SEC-FE-003 | No URL-scheme validation on DB-supplied URLs in `<a href>`/`<img src>` | frontend |
| SEC-FE-005 | All CSRF defense delegated to backend Origin guard (works, but single-layer) | frontend api client |
| SEC-FE-007 | `envDir: '..'` pulls root `.env` into frontend build surface | `vite.config.ts` |
| SEC-FE-008 | Caret dependency ranges (lockfile + `npm ci` mitigate) | `package.json` |
| SEC-LLM-004 | Prompt-injection defense is framing-only; uncited fabricated answers pass `_finalize` | `retrieval/pipeline.py:1072-1076` |
| SEC-LLM-007 | `propose_changeset` operations list unbounded | `retrieval/pipeline.py:343-364` |
| SEC-LLM-008 | Notes (global) are the one user-controlled text channel into LLM context | `retrieval/tools.py:309-326` |
| SEC-LOG-001 | Validation errors log raw submitted values (chat questions, Google JWTs) | `core/errors.py:234` |
| SEC-LOG-007 | Chat messages retained indefinitely; full history sent to LLM provider each turn | `repository/chat.py` |
| SEC-ADV-001 | Ingest unthrottled + unpaginated list query (S10 new) | `api/candidates.py:121-127`, `graph/candidates.py:292-337` |
| SEC-DOS-006 | Unbounded chat history read per turn | `repository/chat.py` |
| SEC-DOS-008 | Per-user concurrency slot is in-process only (multi-worker gap) | `services/chat.py:46-74` |
| SEC-DOS-009 | Unthrottled write endpoints (session/progress/change-set/share) | various |
| SEC-DOS-010 | Unauthenticated heavy reads uncached (expand/path) | `api/graph.py:304-386` |

## LOW / INFORMATIONAL (condensed)

SEC-BE-008 unbounded string fields · SEC-BE-009 `/graph/expand` 7-query anonymous DoS · SEC-BE-010 no cookie Max-Age · SEC-BE-011 closed-set f-string Cypher (safe today) · SEC-BE-012 share tokens in URLs · SEC-GR-014 latent label interpolation in revert · SEC-GR-015 limiter no-op without Redis · SEC-GR-016 `EPISODE_CODES_QUERY` unscoped · SEC-INF-001 (DOWNGRADED from CRITICAL) Upstash endpoint name public in README/history, token never committed · SEC-INF-002 no secret scanning in CI · SEC-INF-008 /health discloses service marker + DB state (acceptable) · SEC-INF-009 dev-password patterns in history · SEC-INF-010 mutable Actions tags · SEC-INF-011 loose range pins (lockfile mitigates) · SEC-INF-012 Neo4j TLS not enforced for plain `neo4j://` · SEC-INF-014 BYOK header handling verified safe (key exfiltration only) · SEC-FE-006 (DOWNGRADED) forgeable visitor flag yields nothing beyond anonymous access — server-side auth verified · SEC-FE-009 no open redirects · SEC-FE-010 no XSS sinks (positive) · SEC-LLM-002 stored base_url redirection requires admin (LOW) · SEC-LLM-006 episode-codes tool unscoped (defense-in-depth) · SEC-DOS-007 cache-flush DoS via writes · SEC-DOS-011 Redis key growth · SEC-DOS-012 per-request httpx clients + INFO log flood · SEC-LOG-002 denied sign-in emails logged · SEC-LOG-005 /health internal name · SEC-LOG-006 no TrustedHostMiddleware · SEC-LOG-008/009 uvicorn access log + user ids in Redis keys · SEC-ADV-002 ingest never invalidates cache · SEC-ADV-003 notes/custom/revisions GET no persisted-episode check · SEC-ADV-004 infra fingerprints in README · SEC-DEP-001..014 (S7: no reachable runtime vulns; shadcn CLI misdeclared as runtime dep is root cause of all 5 npm advisories; CI audit gate will fail next PR; fastapi-limiter abandonment risk; Actions tags; no Python vuln scan in CI)

**Verified positives:** parameterized Cypher everywhere, no LLM-generated Cypher, boundary in-query + context filter, citation validation, session/share token hashing, CSRF origin guard fail-closed, security headers on backend, allowlist request logging, error envelope sanitized, cache keys carry series+boundary+user+epoch, viz metadata re-validation, SSE framing-injection safe, Redis key-collision-free, admin endpoints admin-gated, no IDOR on write paths.

# Potential Findings Requiring Verification

- **SEC-BE-007** — prod `ALLOWED_EMAILS` / `ADMIN_EMAILS` values (dashboard-only; empty allowlist = open signup + no admin).
- **SEC-DOS-002** — prod `LLM_ENABLED` + stored key presence determines cost-farm exploitability.
- **SEC-INF-006** — prod `FRONTEND_ORIGINS` (default `localhost:5173` would break prod CORS; wildcard would disable CSRF guard).
- **SEC-FE-004** — Google Identity Services script loaded without SRI (supply-chain consideration, not an exploit today).
- **SEC-GR-009** — boundary self-attestation is design intent; accept or revisit.

# Attack Chains (S10)

| Chain | Steps | Impact | Likelihood |
|---|---|---|---|
| **A. Anonymous full-spoiler dump** | No account: `/candidates?visible_until_order=<last>` + `/notes?...=999` + `/revisions?...=999` + `/custom-nodes/...`; or fresh account: `/graph?visible_until_order=96` | Complete defeat of the core guarantee; all claims/evidence text, all users' notes, revision snapshots, user_ids | **Certain** — P0 |
| **B. Graph poisoning → cross-user indirect prompt injection** | Any Google account → ingest `visible_from_order:1` + payload → visible to all in graph UI + enters every chat `<claims>`/`<evidence>` context → uncited fabricated/spoilered answers served as grounded | App integrity; spoiler bypass via chat; system-prompt disclosure attempts | High — P0 |
| **C. Redis takeover via git history** | README/history `REDIS_URL` | **N/A — REJECTED** (placeholder `<token>`; endpoint name alone ≠ access) | — |
| **D. XSS → BYOK key theft** | Any future XSS (none today) → localStorage key → attacker spends user's quota | Key theft | Low today; rises with rich-render features (no CSP) — P1 |
| **E. Site-wide login lockout** | 10 failed logins/5min (any origin) → global bucket via proxy IP; repeat | Total login outage | Certain — P0 |
| **F. Cost farm** | N burner accounts × 20 msg/min × ≤5 calls × 40-60k tokens | $600–860/day (10 accounts) on operator's key; worker saturation | High if allowlist empty — P0 verify |
| **G. BYOK SSRF vs internal network** | Any account → `X-LLM-Base-URL: http://<internal>` → blind POST/timing oracle; 200-SSE echo | Port-scan/fingerprint, POST side-effects on internal endpoints | Medium (authenticated) — P1 |
| **H. Info-leak + SSRF + LLM exfil combo** | A+B+G chained | No secret-exfiltration path exists (keys never enter context; no URL tool) — degrades to A+B+G independently | n/a |

# LLM / Agent Abuse Analysis

See Capability Map + SEC-DOS-002 + SEC-LLM-004. Summary: the agent has no network tools (no scraper/SSRF in-band); spoiler boundary is enforced pre-retrieval (verified — data beyond the boundary never enters context); the residual LLM risks are (1) cost amplification via open signup + per-user limits, (2) prompt-injection via poisoned graph content (Chain B), (3) BYOK SSRF as an out-of-band network primitive, (4) uncited fabricated answers passing through (SEC-LLM-004 — delimiter neutralization recommended).

# Scraping & SSRF Analysis

**No arbitrary-URL scraping is possible through the LLM** — the tool allowlist contains zero HTTP tools. The **only** SSRF surface is the provider `base_url` (BYOK for any authenticated user; stored for admin). Both accept any http(s) host including loopback/private/link-local/metadata; both lack IP-range blocking and DNS-rebinding protection. httpx default (no redirect-follow) partially mitigates redirect-based escapes. Recommended: block private ranges + resolve-and-pin DNS, or drop BYOK `base_url` entirely and restrict provider hosts to a curated allowlist.

# Spoiler Boundary Analysis

**Model:** server-side `min(view_as_of, watched_through)` from the persisted progress record (anonymous = order 1) → threaded as `visible_until_order` into every retrieval query + a defense-in-depth `_visible_at` filter in context assembly. This is genuine **pre-retrieval enforcement** — the system prompt is redundant, not load-bearing (positive, verified by S4/S5).

**Broken surfaces (all CONFIRMED):**
1. `/graph` + `/episodes` for authenticated users with NO progress record — unclamped (SEC-BE-001).
2. candidates list/get, notes list/get, custom-node/relationship get, revisions list/get — anonymous, client-chosen boundary, no persisted-episode check on notes/custom/revisions (SEC-BE-002, SEC-ADV-003).
3. Ingest writes content at client-chosen `visible_from_order` (SEC-BE-003).
4. Cache keys include boundary + user + epoch and are isolated (positive — no cross-boundary cache hit).
5. Share snapshots clamp to creator progress (positive — CR-01 verified).

# Authentication / Authorization Analysis

- **Sound:** 48-byte tokens, SHA-256 at rest, HttpOnly/Secure/Lax cookie, TTL 7d, hourly sweep; `verify_oauth2_token` (signature/audience/issuer/expiry); CSRF Origin guard fail-closed on all state-changing routes except read-only `POST /graph/path`; admin role derived server-side from `ADMIN_EMAILS`; owner-or-admin checks on user-content writes; identical 404 for foreign/missing chat sessions; no IDOR on write paths.
- **Gaps:** `email_verified` not checked (SEC-BE-007); allowlist default empty (open signup); no cookie Max-Age (SEC-BE-010); boundary self-attestation (SEC-GR-009, design); visitor-mode flag forgeable but harmless (SEC-FE-006 downgraded — server-side auth verified).

# Frontend Analysis

No XSS sinks (React-text/canvas rendering; no dangerouslySetInnerHTML/eval/markdown) — positive. Main gaps: no CSP on the shell (SEC-FE-001), BYOK key in localStorage transiting the backend (SEC-FE-002), Google Identity script without SRI (SEC-FE-004), no URL-scheme validation on DB-supplied URLs (SEC-FE-003), root `.env` in build surface (SEC-FE-007), caret ranges (SEC-FE-008), cosmetic-only visitor blur (SEC-FE-006 — enforcement server-side, holds).

# Backend Analysis

Strong skeleton (parameterized Cypher, error envelope, log allowlist, CORS/CSRF, security headers). Fatal gaps cluster around boundary clamping on anonymous/fresh-account reads (SEC-BE-001/002), ingest trust (SEC-BE-003), rate-limit collapse/fail-open (SEC-BE-004, SEC-DOS-001), missing body limits (SEC-DOS-004), validation-error logging (SEC-LOG-001), /docs exposure (SEC-INF-003).

# Database / Neo4j Analysis

All ~55 queries parameterized (positive); two closed-set f-string interpolations (SEC-BE-011); latent label interpolation in revert path (SEC-GR-014); admin-level credentials (SEC-GR-003); LLM key plaintext at rest (SEC-GR-012); write endpoints double as existence/reveal-order oracles (SEC-GR-008); no LLM-generated Cypher (positive). No injection, no procedure abuse, no arbitrary-MATCH path.

# Infrastructure Analysis

Render free tier (single process — concurrency dict valid; multi-worker would break the per-user slot), no proxy-headers (SEC-BE-004), render.yaml env-less (SEC-INF-005), backend reachable directly (SEC-INF-007), /docs public (SEC-INF-003), release workflow skeleton (SEC-INF-015), infra fingerprints in README (SEC-ADV-004).

# Dependency Analysis

No reachable runtime vulnerabilities (S7). All 5 npm advisories (brace-expansion, fast-uri, js-yaml, nanoid, hono) trace to `shadcn@4.16.0` misdeclared as a runtime dependency — CLI-only, not in `dist/assets` (SEC-DEP-001). CI audit gate already red (SEC-DEP-007). Python tree current (fastapi 0.140.7, certifi 2026.7.22). Minor: mutable Actions tags (SEC-DEP-008), lower-bound pins (SEC-DEP-009), fastapi-limiter abandonment risk (SEC-DEP-010), no Python vuln scan in CI (SEC-DEP-011), Neo4j image tag-only pin (SEC-DEP-012). No typosquats; install-time surface minimal (SEC-DEP-014).

# Rate Limiting / Denial-of-Wallet Analysis

Three independent failures compound: fail-open design (SEC-DOS-001), proxy-collapsed per-IP keys (SEC-BE-004), per-user-only LLM limits with open signup (SEC-DOS-002). Secondary: cache-key explosion (SEC-DOS-005), unthrottled ingest (SEC-ADV-001), unthrottled writes (SEC-DOS-009), unbounded history reads (SEC-DOS-006), in-process concurrency slot (SEC-DOS-008), Redis key growth (SEC-DOS-011).

# Secrets Analysis

**No live credential in git** (S10 byte-level verification — SEC-INF-001 rejected). `.env` never tracked; .gitignore solid; request logging denies auth/X-LLM headers; LLM key masked in GET, never logged; BYOK key only in httpx client. Residuals: endpoint-name fingerprints in README/docs (SEC-ADV-004, SEC-INF-001-INFO), dev-password patterns in history (SEC-INF-009), plaintext LLM key in Neo4j (SEC-GR-012), no secret scanning in CI (SEC-INF-002).

# Recommended Remediation Roadmap

### P0 — Fix before public exposure
1. **Anonymous/fresh-account boundary clamps** (SEC-BE-001, SEC-BE-002, SEC-ADV-003): route every read through `_resolve_effective_boundary` (anonymous = order 1, no-record = order 1); auth-gate or persist-validate candidates/revisions; strip `before`/`after`/`user_id` for non-owners.
2. **Ingest hardening** (SEC-BE-003, SEC-ADV-001, SEC-ADV-002): server-derive `visible_from_order`, validate subject/object/episode existence, add rate limiter, invalidate series cache.
3. **Trusted proxy** (SEC-BE-004/SEC-DOS-003): uvicorn `--proxy-headers --forwarded-allow-ips=<Render CIDR>` or a site-wide login circuit breaker.
4. **Fail-closed rate limiting** (SEC-DOS-001): never silent no-op for login/chat in prod.
5. **LLM cost controls** (SEC-DOS-002): require `ALLOWED_EMAILS` in prod (operator), global generation semaphore, per-round tool-call cap, per-user budget.
6. **SSRF hardening** (SEC-LLM-001/002): block loopback/private/link-local/metadata in `_validate_base_url`; resolve-and-pin DNS.
7. **Body-size limit** (SEC-DOS-004) + bounded `operations` lists.
8. **Disable /docs, /redoc, /openapi.json in prod** (SEC-INF-003).
9. **CSP + security headers on the Vercel shell** (SEC-FE-001).
10. **Log sanitization** (SEC-LOG-001): drop `input`/`ctx` from validation-error logging.

### P1 — Immediately after
LLM output guard + delimiter neutralization (SEC-LLM-004); viz cache-key redesign (SEC-DOS-005); session Max-Age (SEC-BE-010); `email_verified` check (SEC-BE-007); TrustedHostMiddleware (SEC-LOG-006); candidate list pagination (SEC-ADV-001); error-message sanitization on ingest (SEC-BE-006); BYOK key storage (sessionStorage/in-memory) (SEC-FE-002); move shadcn to devDependencies + refresh lockfile (SEC-DEP-001/007); SHA-pin Actions (SEC-DEP-008).

### P2 — Hardening
Least-privilege Neo4j user (SEC-GR-003); encrypt LLM key at rest or move to env (SEC-GR-012); SRI on Google Identity script (SEC-FE-004); chat retention policy + deletion flow (SEC-LOG-007); per-user session cap (SEC-BE-010); /health service-marker trim (optional); origin-lock backend behind Cloudflare (SEC-INF-007).

### P3 — Defense in depth
Revisions revert label allowlist (SEC-GR-014); EPISODE_CODES scoping (SEC-GR-016, SEC-LLM-006); `propose_changeset` ops cap (SEC-LLM-007); cache-flush cost caps (SEC-DOS-007); Redis key TTL hygiene (SEC-DOS-011); Python vuln scan in CI (SEC-DEP-011); secret scanning pre-commit (SEC-INF-002); scrub infra fingerprints (SEC-ADV-004); Neo4j TLS enforcement for `neo4j://` URIs (SEC-INF-012).

---

*Companion docs: SECURITY_ATTACK_SURFACE.md (living endpoint doc) · SECURITY_TEST_PLAN.md (regression test plan) · full per-agent reports in `.planning/quick/20260814-security-audit/findings/S{1..10}-*.md`.*
